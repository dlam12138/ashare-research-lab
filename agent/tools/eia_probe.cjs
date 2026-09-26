'use strict';
// One-shot evidence tooling, not a production data adapter.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const net = require('node:net');
const tls = require('node:tls');
const https = require('node:https');
const cp = require('node:child_process');
const root = path.resolve(__dirname, '../..');
const dir = path.join(root, 'data/quarantine/m4_eia_direct_01');
const ledgerFile = path.join(root, 'evidence/m4/eia_direct_run_01.json');
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const order = x => Array.isArray(x) ? x.map(order) : x && typeof x === 'object'
  ? Object.fromEntries(Object.keys(x).sort().map(k => [k, order(x[k])])) : x;
const canonical = x => JSON.stringify(order(x));
const write = (p, x) => {const t = p + '.pending'; fs.writeFileSync(t, canonical(x)+'\n', {flag:'wx'}); fs.renameSync(t,p);};
function wrapKey(bytes, decrypt=false) {
  const method = decrypt ? 'Unprotect' : 'Protect';
  const script = `$ErrorActionPreference='Stop'; $b=[Convert]::FromBase64String([Console]::In.ReadToEnd()); $r=[Security.Cryptography.ProtectedData]::${method}($b,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser); [Console]::Out.Write([Convert]::ToBase64String($r))`;
  const r = cp.spawnSync('pwsh', ['-NoProfile','-NonInteractive','-Command',script],
    {input:bytes.toString('base64'), encoding:'utf8', windowsHide:true,
     env:{...process.env,EIA_API_KEY:''}, timeout:10000});
  if(r.status!==0) throw Error('KEY_PROTECTION_FAILED');
  return Buffer.from(r.stdout.trim(),'base64');
}
function getKey(create=false) {
  const p=path.join(dir,'key.dpapi');
  if(!fs.existsSync(p)) {
    if(!create) throw Error('KEY_MISSING');
    fs.mkdirSync(dir,{recursive:true});
    const k=crypto.randomBytes(32); fs.writeFileSync(p,wrapKey(k),{flag:'wx'}); k.fill(0);
  }
  const k=wrapKey(fs.readFileSync(p),true);
  if(k.length!==32) throw Error('KEY_INVALID'); return k;
}
function seal(raw,key) {
  const nonce=crypto.randomBytes(12), c=crypto.createCipheriv('aes-256-gcm',key,nonce);
  c.setAAD(Buffer.from('M4_EIA_RAW_V1'));
  return Buffer.concat([Buffer.from('EIA1'),nonce,c.update(raw),c.final(),c.getAuthTag()]);
}
function unseal(blob,key) {
  if(blob.length<32||blob.subarray(0,4).toString()!=='EIA1') throw Error('CIPHERTEXT_INVALID');
  const d=crypto.createDecipheriv('aes-256-gcm',key,blob.subarray(4,16));
  d.setAAD(Buffer.from('M4_EIA_RAW_V1')); d.setAuthTag(blob.subarray(-16));
  return Buffer.concat([d.update(blob.subarray(16,-16)),d.final()]);
}
function retain(raw,key) {
  const digest=sha(raw), dest=path.join(dir,digest+'.aesgcm');
  const blob=seal(raw,key);
  if(fs.existsSync(dest)) throw Error('RAW_ALREADY_EXISTS');
  const temp=dest+'.pending'; fs.writeFileSync(temp,blob,{flag:'wx'});
  if(!unseal(fs.readFileSync(temp),key).equals(raw)) throw Error('RAW_ROUNDTRIP_FAILED');
  fs.renameSync(temp,dest);
  return {raw_sha256:digest,raw_bytes_length:raw.length,
    encrypted_locator:path.relative(root,dest).replaceAll('\\','/'),ciphertext_sha256:sha(blob),
    encryption:'AES-256-GCM',key_protection:'Windows-DPAPI-CurrentUser'};
}
function rawOf(a,key) {
  const blob=fs.readFileSync(path.join(root,a.encrypted_locator));
  if(sha(blob)!==a.ciphertext_sha256) throw Error('CIPHERTEXT_HASH_MISMATCH');
  const b=unseal(blob,key);
  if(sha(b)!==a.raw_sha256||b.length!==a.raw_bytes_length) throw Error('RAW_HASH_MISMATCH');
  return b;
}
// Errors are deliberately fixed local codes; never emit URLs/provider bodies.
function request(host,pathname,query,remaining,onBytes) {
  return new Promise((resolve,reject)=>{
    let tunnel,secure,req,res,agent,done=false;
    const finish=(err,value)=>{if(done)return;done=true;clearTimeout(timer);
      res?.destroy(); req?.destroy(); agent?.destroy(); secure?.destroy(); tunnel?.destroy();
      err?reject(Error(err)):resolve(value);};
    const timer=setTimeout(()=>finish('REQUEST_DEADLINE'),15000);
    tunnel=net.createConnection({host:'127.0.0.1',port:10808});
    tunnel.once('error',()=>finish('PROXY_ERROR'));
    tunnel.once('connect',()=>tunnel.write(`CONNECT ${host}:443 HTTP/1.1\r\nHost: ${host}:443\r\n\r\n`));
    let header=Buffer.alloc(0);
    const onTunnel=b=>{
      header=Buffer.concat([header,b]); if(header.length>8192)return finish('PROXY_HEADER_LIMIT');
      const end=header.indexOf('\r\n\r\n'); if(end<0)return;
      if(!/^HTTP\/1\.[01] 200(?: |\r|$)/.test(header.toString('ascii',0,end)))return finish('PROXY_REJECTED');
      tunnel.removeListener('data',onTunnel);
      if(header.length>end+4)tunnel.unshift(header.subarray(end+4));
      secure=tls.connect({socket:tunnel,servername:host,rejectUnauthorized:true,ALPNProtocols:['http/1.1']});
      secure.once('error',()=>finish('TLS_ERROR'));
      secure.once('secureConnect',()=>{
        agent=new https.Agent({keepAlive:false});agent.createConnection=()=>secure;
        req=https.request({host,path:pathname+(query?'?'+query:''),method:'GET',agent,
          headers:{Accept:host==='www.eia.gov'?'text/html':'application/json',
            'Accept-Encoding':'identity','User-Agent':'M4-private-evidence-probe/1.0'}},r=>{
          res=r;let used=0;const chunks=[];
          const length=r.headers['content-length'];
          if(length!==undefined&&(!/^\d+$/.test(length)||Number(length)>remaining))return finish('BODY_LIMIT');
          r.on('data',b=>{if(done)return;if(b.length>remaining-used)return finish('BODY_LIMIT');
            used+=b.length;onBytes(used);chunks.push(b);});
          r.once('error',()=>finish('BODY_ERROR'));
          r.once('aborted',()=>finish('BODY_ABORTED'));
          r.once('end',()=>finish(null,{body:Buffer.concat(chunks),status:r.statusCode,
            content_type:String(r.headers['content-type']||''),encoding:String(r.headers['content-encoding']||'identity'),
            certificate_sha256:sha(secure.getPeerCertificate().raw)}));
        });req.once('error',()=>finish('HTTP_ERROR'));req.end();
      });
    };tunnel.on('data',onTunnel);
  });
}
function metadataReview(terms,meta,facets) {
  if(!terms.includes('You may use the EIA API to develop a service') || !terms.includes('Attribution')) throw Error('TERMS_UNPROVEN');
  const r=meta.response,f=facets.response;
  if(!r||!Array.isArray(r.frequency)||!r.frequency.some(x=>x.id==='daily')||!r.data?.value)throw Error('METADATA_UNPROVEN');
  if(!Array.isArray(r.facets)||!r.facets.some(x=>x.id==='series'))throw Error('SERIES_FACET_MISSING');
  if(!f||!Array.isArray(f.facets)||Number(f.totalFacets)!==f.facets.length)throw Error('FACET_INCOMPLETE');
  const brent=f.facets.filter(x=>x.id==='RBRTE');
  if(brent.length!==1||!String(brent[0].name).toLowerCase().includes('brent'))throw Error('BRENT_IDENTITY_MISSING');
  return {daily:true,value:true,series_facet:true,brent_identity:true,facet_count:f.facets.length};
}
const rowKeys=['period','duoarea','area-name','product','product-name','process','process-name','series','series-description','value','units'].sort();
function scanData(doc) {
  const r=doc.response;if(!r||!Array.isArray(r.data)||r.data.length!==5||Number(r.total)!==5)throw Error('ROW_COUNT');
  const dates=[];
  for(const row of r.data) {
    if(typeof row.period!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(row.period))throw Error('AMBIGUOUS_DATE');
    if(row.period>='2023-01-01')throw Error('REAL_HOLDOUT_INJECTION');
    if(row.period<'2015-03-09'||row.period>'2015-03-13')throw Error('OUT_OF_WINDOW');
    if(JSON.stringify(Object.keys(row).sort())!==JSON.stringify(rowKeys))throw Error('ROW_SCHEMA');
    if(row.series!=='RBRTE'||!String(row['series-description']).toLowerCase().includes('brent')||row.units!=='$/BBL')throw Error('ROW_IDENTITY');
    if(typeof row.value!=='string'||!/^\d+(\.\d+)?$/.test(row.value))throw Error('VALUE_STRUCTURE');
    dates.push(row.period);
  }
  if(JSON.stringify(dates)!==JSON.stringify(['2015-03-09','2015-03-10','2015-03-11','2015-03-12','2015-03-13']))throw Error('DATE_COMPLETENESS');
  return {raw_date_scan_count:5,response_min_date:dates[0],response_max_date:dates[4],ambiguous_date_count:0,out_of_window_count:0,undeclared_field_count:0,requested_window_only:true};
}
const stages=[['terms','www.eia.gov','/opendata/register.php'],['metadata','api.eia.gov','/v2/petroleum/pri/spt/'],['facets','api.eia.gov','/v2/petroleum/pri/spt/facet/series/'],['data','api.eia.gov','/v2/petroleum/pri/spt/data/']];
async function main(mode) {
  const ledger=fs.existsSync(ledgerFile)?JSON.parse(fs.readFileSync(ledgerFile)):
    {schema_id:'M4_EIA_ENCRYPTED_RUN_01',max_body_bytes:1048576,timeout_ms:15000,retry_count:0,min_interval_ms:15000,attempts:[]};
  const key=getKey(mode==='terms');
  try {
    if(mode==='verify'||mode==='review') {
      for(const a of ledger.attempts)if(a.encrypted_locator)rawOf(a,key);
      let result={encrypted_hashes_verified:true,attempt_count:ledger.attempts.length};
      if(ledger.attempts.length>=3&&ledger.attempts.slice(0,3).every(a=>a.state==='RETAINED'))
        result.metadata=metadataReview(rawOf(ledger.attempts[0],key).toString(),JSON.parse(rawOf(ledger.attempts[1],key)),JSON.parse(rawOf(ledger.attempts[2],key)));
      if(ledger.attempts[3]?.state==='RETAINED') result.date_scan=scanData(JSON.parse(rawOf(ledger.attempts[3],key)));
      console.log(canonical(result));return;
    }
    const index=stages.findIndex(s=>s[0]===mode);
    if(index!==ledger.attempts.length||index<0||ledger.attempts.some(a=>a.state!=='RETAINED'))throw Error('RUN_STAGE_DENIED');
    if(index===1&&!rawOf(ledger.attempts[0],key).toString().includes('You may use the EIA API to develop a service'))throw Error('TERMS_UNPROVEN');
    if(index===3)metadataReview(rawOf(ledger.attempts[0],key).toString(),JSON.parse(rawOf(ledger.attempts[1],key)),JSON.parse(rawOf(ledger.attempts[2],key)));
    const remaining=1048576-ledger.attempts.reduce((s,a)=>s+a.received_bytes,0);
    if(remaining<=0)throw Error('BODY_LIMIT');
    const credential=process.env.EIA_API_KEY;
    if(index>0&&(!credential||!/^[a-zA-Z0-9]+$/.test(credential)))throw Error('CREDENTIAL_UNAVAILABLE');
    if(index){const wait=15000-(Date.now()-Date.parse(ledger.attempts.at(-1).started_at));if(wait>0)await new Promise(r=>setTimeout(r,wait));}
    const [stage,host,endpoint]=stages[index];
    const q=new URLSearchParams();
    if(index>0)q.set('api_key',credential);
    if(index===3)for(const [k,v]of Object.entries({frequency:'daily','data[0]':'value','facets[series][]':'RBRTE',start:'2015-03-09',end:'2015-03-13','sort[0][column]':'period','sort[0][direction]':'asc',offset:'0',length:'5'}))q.set(k,v);
    const a={stage,host,endpoint,started_at:new Date().toISOString(),state:'STARTED',received_bytes:0};
    ledger.attempts.push(a);write(ledgerFile,ledger);const t=performance.now();
    try {
      const r=await request(host,endpoint,q.toString(),remaining,n=>{a.received_bytes=n;});
      a.http_status=r.status;a.content_encoding=r.encoding;
      Object.assign(a,retain(r.body,key));a.peer_certificate_sha256=r.certificate_sha256;
      if(r.status!==200)throw Error('HTTP_STATUS');
      if(r.encoding!=='identity')throw Error('CONTENT_ENCODING');
      if(index===0&&!r.body.toString().includes('You may use the EIA API to develop a service'))throw Error('TERMS_UNPROVEN');
      if(index>0){const doc=JSON.parse(r.body);if(doc.error||doc.warning)throw Error('PROVIDER_ERROR');}
      if(index===3)a.date_scan=scanData(JSON.parse(r.body));
      a.state='RETAINED';
    }catch(e){a.state='FAILED';a.error_code=/^[A-Z_]+$/.test(e.message)?e.message:'RESPONSE_PROCESSING_FAILED';}
    a.elapsed_ms=Math.round(performance.now()-t);write(ledgerFile,ledger);
    console.log(canonical(a));if(a.state!=='RETAINED')process.exitCode=2;
  }finally{key.fill(0);}
}
module.exports={seal,unseal,scanData,metadataReview,rowKeys,sha,canonical,wrapKey};
if(require.main===module)main(process.argv[2]).catch(()=>{console.error('PROBE_STOPPED_BEFORE_REQUEST_OR_LOCAL_FAILURE');process.exitCode=2;});
