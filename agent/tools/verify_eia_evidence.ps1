# Independent .NET decryption/date validation. No network and no plaintext output.
$ErrorActionPreference = 'Stop'
$verificationKey = $null
try {
    $repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
    $ledger = Get-Content -Raw (Join-Path $repo 'evidence/m4/eia_direct_run_01.json') | ConvertFrom-Json
    $auth = Get-Content -Raw (Join-Path $repo 'evidence/m4/eia_direct_authorization_01.json') | ConvertFrom-Json
    $wrapped = [IO.File]::ReadAllBytes((Join-Path $repo 'data/quarantine/m4_eia_direct_01/key.dpapi'))
    $verificationKey = [Security.Cryptography.ProtectedData]::Unprotect($wrapped,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser)
    $eiaStoredKey = [Environment]::GetEnvironmentVariable('EIA_API_KEY','User')
    if ([string]::IsNullOrWhiteSpace($eiaStoredKey)) { throw 'CREDENTIAL_CHECK_UNAVAILABLE' }
    if ($ledger.attempts.Count -ne 4) { throw 'REQUEST_COUNT' }
    $total = 0
    $prior = $null
    $index = 0
    foreach ($a in $ledger.attempts) {
        if ($a.host -cne $auth.approved_routes[$index].host -or $a.endpoint -cne $auth.approved_routes[$index].path) { throw 'ROUTE' }
        if ($a.state -cne 'RETAINED' -or $a.http_status -ne 200 -or $a.content_encoding -cne 'identity') { throw 'STATUS' }
        if ($a.elapsed_ms -gt 15000) { throw 'DEADLINE' }
        $start = [DateTimeOffset]::Parse($a.started_at)
        if ($null -ne $prior -and ($start-$prior).TotalMilliseconds -lt 15000) { throw 'RATE' }
        $prior=$start
        $blob=[IO.File]::ReadAllBytes((Join-Path $repo $a.encrypted_locator))
        $cipherHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($blob)).ToLowerInvariant()
        if ($cipherHash -cne $a.ciphertext_sha256) { throw 'CIPHER_HASH' }
        if ([Text.Encoding]::ASCII.GetString($blob,0,4) -cne 'EIA1') { throw 'FORMAT' }
        [byte[]]$plain=[byte[]]::new($blob.Length-32)
        $aes=[Security.Cryptography.AesGcm]::new($verificationKey,16)
        try { $aes.Decrypt([byte[]]$blob[4..15],[byte[]]$blob[16..($blob.Length-17)],[byte[]]$blob[($blob.Length-16)..($blob.Length-1)],$plain,[Text.Encoding]::UTF8.GetBytes('M4_EIA_RAW_V1')) } finally { $aes.Dispose() }
        $hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($plain)).ToLowerInvariant()
        if ($hash -cne $a.raw_sha256 -or $plain.Length -ne $a.raw_bytes_length -or $plain.Length -ne $a.received_bytes) { throw 'RAW_HASH' }
        $total += $plain.Length
        if ($total -gt 1048576) { throw 'BYTE_LIMIT' }
        $body=[Text.Encoding]::UTF8.GetString($plain)
        if ($index -eq 0) {
            if (!$body.Contains('You may use the EIA API to develop a service') -or !$body.Contains('Attribution')) { throw 'TERMS' }
        } else {
            $doc=ConvertFrom-Json -InputObject $body -AsHashtable
            if ($doc.ContainsKey('error') -or $doc.ContainsKey('warning')) { throw 'PROVIDER_ERROR' }
            # Verify any echoed credential without displaying or hashing the key alone.
            $echoParams=$doc.request.params
            if ($echoParams -is [System.Collections.IDictionary]) {
                if ($echoParams.Contains('api_key') -and $echoParams['api_key'] -cne $eiaStoredKey) { throw 'CREDENTIAL_ECHO' }
            } elseif ($null -ne $echoParams -and @($echoParams).Count -ne 0) { throw 'UNKNOWN_ECHO_SHAPE' }
            if ($index -eq 1) {
                if ('daily' -cnotin @($doc.response.frequency.id) -or !$doc.response.data.ContainsKey('value') -or 'series' -cnotin @($doc.response.facets.id)) { throw 'METADATA' }
            }
            if ($index -eq 2) {
                $facets=@($doc.response.facets)
                $brent=@($facets | Where-Object { $_.id -ceq 'RBRTE' -and $_.name -match 'Brent' })
                if ($brent.Count -ne 1 -or [int]$doc.response.totalFacets -ne $facets.Count) { throw 'FACETS' }
            }
            if ($index -eq 3) {
                $rows=@($doc.response.data)
                if ($rows.Count -ne 5 -or [int]$doc.response.total -ne 5) { throw 'ROW_COUNT' }
                $expected=($auth.requested_row_fields | Sort-Object) -join ','
                for ($n=0; $n -lt 5; $n++) {
                    $row=$rows[$n]
                    $date=([datetime]'2015-03-09').AddDays($n).ToString('yyyy-MM-dd')
                    if ($row.period -cne $date -or $row.series -cne 'RBRTE' -or $row.units -cne '$/BBL' -or $row.'series-description' -notmatch 'Brent') { throw 'ROW_IDENTITY_DATE' }
                    if ((($row.Keys | Sort-Object) -join ',') -cne $expected) { throw 'ROW_FIELDS' }
                    if ($row.value -isnot [string] -or $row.value -notmatch '^\d+(\.\d+)?$') { throw 'VALUE_STRUCTURE' }
                }
            }
        }
        [Array]::Clear($plain)
        $body=$null; $doc=$null
        $index++
    }
    $paths = git -C $repo ls-files --cached --others --exclude-standard
    foreach ($p in $paths) {
        $full=Join-Path $repo $p
        if ([IO.File]::Exists($full) -and [IO.File]::ReadAllText($full).Contains($eiaStoredKey)) { throw 'TRACKED_SECRET_LEAK' }
    }
    Write-Output "PASS: independent AES-GCM/DPAPI verification; four requests; $total bytes; five historical dates; secret absent from tracked/unignored files."
} catch {
    Write-Output ('FAIL: independent evidence verification at line ' + $_.InvocationInfo.ScriptLineNumber + '; exception=' + $_.Exception.GetType().Name)
    exit 1
} finally {
    if ($null -ne $verificationKey) { [Array]::Clear($verificationKey) }
    $eiaStoredKey=$null
}
