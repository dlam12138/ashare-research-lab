# EIA direct-source plan

Status: DOCUMENTATION_REVIEWED / ACQUISITION_NOT_AUTHORIZED.
Reviewed 2026-09-25. This is a proposed replacement transport, not acceptance
of a current provider or an amendment to frozen v2 authorization.

## First-party findings

- [API terms](https://www.eia.gov/opendata/register.php) expressly allow service
  development for retrieving, displaying and analyzing EIA information. They
  require attribution, prohibit implied endorsement and reserve access limits.
- [Reuse policy](https://www.eia.gov/about/copyrights_reuse.php) allows reuse of
  EIA information products with attribution, subject to protected third-party
  material and logo exclusions. Dataset-specific rights still need review.
- [Technical documentation](https://www.eia.gov/opendata/documentation.php)
  specifies individual free API keys and server-side start/end filtering. It
  also documents request echo metadata containing api_key. These are documented
  capabilities, not verified responses from the proposed route.
- [Petroleum spot-price browser](https://www.eia.gov/opendata/browser/petroleum/pri/spt)
  identifies the candidate route family. The Brent facet RBRTE remains a
  candidate requiring authenticated metadata verification before observations.

Web discovery is not a retained original licence artifact. No observations or
bulk files were requested. API-specific terms support this proposed service
use more directly than the unresolved FRED evidence.

## Concrete proposed request

HTTPS host `api.eia.gov`, metadata path `/v2/petroleum/pri/spt/`, series facet
metadata `/v2/petroleum/pri/spt/facet/series/`, observation path
`/v2/petroleum/pri/spt/data/`. Verify the exact facet/route before observation.

Candidate observation parameters (never run until separately authorized):

```text
frequency=daily
data[0]=value
facets[series][]=RBRTE
start=2015-03-09
end=2015-03-13
sort[0][column]=period
sort[0][direction]=asc
offset=0
length=5
api_key=<read securely at execution; never log>
```

One observation GET, no pagination/redirect/retry, per-request total deadline 15000 ms,
at least 15000 ms between request starts, maximum four requests/minute and
1 MiB cumulative body budget for the authorized run, including metadata.
Maximum two metadata calls and one observation call. Missing facet identity,
overflow or incomplete metadata stops the run without pagination.
Use a capped streaming reader; reject an oversized declared Content-Length and
abort before appending any chunk that exceeds the remaining cumulative budget.
Metadata review may pause the workflow; there is no 15-second whole-run deadline.
Persist the request count and byte budget across that pause; no restart resets
either budget. All keyed calls require approved secure retention first.
Dates must be checked in every returned row; row limits alone do not prove
the requested date window. Reject ambiguous, duplicate, extra-series or
out-of-window rows; reject any date on/after 2023-01-01 under the existing
holdout rule. Do not silently truncate or filter an invalid response to pass.
Expected response data roles are period, value, series identity and units;
the exact returned columns must be frozen after metadata review and before
observations. Units, daily frequency and Brent identity must be proven.
The data selector requests the measured value; identity/unit fields are expected
metadata, not assumed additional measures. Missing identity/unit evidence blocks
acceptance. Require the exact five distinct requested dates for this diagnostic
probe; fewer rows produce an incomplete-probe result, never filled or treated
as zero. Response totals exceeding retained rows indicate truncation and fail.

## Changes required before execution

1. A new contract/authorization must explicitly permit the EIA host, paths,
   scoped API credential, new field mapping and a new dossier identity such as
   `eia_direct_brent_transport_probe_01`. Preserve v1/v2 terminal lineage and
   the unused FRED identity. Never edit the old authorization to imply consent.
2. The user obtains a free personal key and accepts EIA's registration terms.
   Provision through a local secret mechanism; never paste the key in chat,
   command-line arguments, tracked files, exceptions or HTTP debug output.
3. Resolve exact raw retention when responses contain an echoed secret.
   Proposed contract extension: authenticated encryption of the original
   response bytes in private quarantine, with separate protected local key
   storage and verification that decryption reproduces the original SHA256.
   Plaintext must stay out of logs and disk; a redacted derivative is never
   the original proof. Encryption/storage implementation and failure handling
   require review before the first keyed metadata call. The present v2 .bin
   retention contract does not already authorize this extension.
4. Retain current first-party permission and identity evidence under the new
   envelope, then evaluate all applicable gates. Historical observation dates
   do not establish historical publication availability or vintage: point-in-
   time use remains unproven, and evidence-only rows cannot enter research.

## Alternatives and decision

The registration page offers keyless bulk downloads. They are not approved for
this probe because server-side five-day filtering and the byte ceiling have not
been established. Downloading broad history and filtering locally would violate
the requested-window rule. No bulk download was attempted.

Recommended next implementation is the EIA credential-aware contract and secure
raw-retention extension, followed by synthetic-only tests and the bounded live
probe after key provisioning. Current readiness is a reviewed design, not a
cleared acquisition gate. PR #29 remains unmerged.
