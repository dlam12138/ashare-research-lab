'use strict';
const fs=require('node:fs'), path=require('node:path'), cp=require('node:child_process'), crypto=require('node:crypto');
const {seal,unseal,wrapKey,sha,canonical}=require('./eia_probe.cjs');
const root=path.resolve(__dirname,'../..');
const dir=path.join(root,'data/quarantine/m4_eia_table11_01');
const ledgerPath=path.join(root,'evidence/m4/eia_table11_run_01.json');
const prefix='https://www.eia.gov/petroleum/supply/weekly/archive/2015/2015_03_18/';
const landing=prefix+'wpsr_2015_03_18.php';
function linkOf(html) {
  const rows=html.match(/<tr\b[^>]*>[\s\S]*?<\/tr>/gi)||[];
  const row=rows.filter(x=>/Spot Prices of Crude Oil, Motor Gasoline, and Heating Oil/i.test(x));
  if(row.length!==1)throw Error('TABLE_LINK_AMBIGUOUS');
  const links=[...row[0].matchAll(/href\s*=\s*["']([^"']+)["']/gi)]
    .map(m=>new URL(m[1],landing).href).filter(x=>x.endsWith('.csv'));
  if(links.length!==1||!links[0].startsWith(prefix))throw Error('CSV_LINK_DENIED');
  return links[0];
}
function get(url,limit) {
  return new Promise((resolve,reject)=>{
    const child=cp.spawn('curl.exe',['--silent','--show-error','--http1.1','--proxy','http://127.0.0.1:10808',
      '--noproxy','','--proto','=https','--max-time','15','--retry','0','--max-redirs','0',
      '--max-filesize',String(limit),'--header','Accept-Encoding: identity','--fail','--write-out','%{stderr}%{http_code}',url],
      {windowsHide:true,env:{...process.env,EIA_API_KEY:''}});
    let size=0,over=false;const chunks=[];
    const timer=setTimeout(()=>{over=true;child.kill();},15000);
    child.stdout.on('data',b=>{size+=b.length;if(size>limit){over=true;child.kill();}else chunks.push(b);});
    let statusTail='';child.stderr.on('data',b=>{statusTail=(statusTail+b.toString()).slice(-3);});
    child.on('error',()=>{clearTimeout(timer);reject(Error('TRANSPORT_START_FAILED'));});
    child.on('close',code=>{clearTimeout(timer);if(over||code!==0||statusTail!=='200')reject(Error('TRANSPORT_FAILED_NO_RETRY'));
      else resolve(Buffer.concat(chunks));});
  });
}
function writeLedger(l){fs.writeFileSync(ledgerPath+'.pending',canonical(l)+'\n',{flag:'wx'});fs.renameSync(ledgerPath+'.pending',ledgerPath);}
function retain(raw,key) {
  const blob=seal(raw,key), name=sha(raw)+'.aesgcm';
  fs.writeFileSync(path.join(dir,name),blob,{flag:'wx'});
  if(!unseal(fs.readFileSync(path.join(dir,name)),key).equals(raw))throw Error('ROUNDTRIP_FAILED');
  return {raw_sha256:sha(raw),ciphertext_sha256:sha(blob),bytes:raw.length,encrypted_file:name};
}
function readRaw(a,key){
  if(!/^[a-f0-9]{64}\.aesgcm$/.test(a.encrypted_file))throw Error('LOCATOR_DENIED');
  const b=fs.readFileSync(path.join(dir,a.encrypted_file));
  if(sha(b)!==a.ciphertext_sha256)throw Error('CIPHER_HASH');
  const raw=unseal(b,key);if(sha(raw)!==a.raw_sha256||raw.length!==a.bytes)throw Error('RAW_HASH');return raw;
}
function parseCsv(text){
  const rows=[];let row=[],cell='',quoted=false,closed=false;
  for(let i=0;i<text.length;i++){
    const c=text[i];
    if(quoted){if(c==='"'){if(text[i+1]==='"'){cell+='"';i++;}else{quoted=false;closed=true;}}else cell+=c;continue;}
    if(c==='"'){if(cell||closed)throw Error('CSV_QUOTE');quoted=true;}
    else if(c===','){row.push(cell);cell='';closed=false;}
    else if(c==='\n'||c==='\r'){if(c==='\r'&&text[i+1]==='\n')i++;row.push(cell);rows.push(row);row=[];cell='';closed=false;}
    else {if(closed)throw Error('CSV_TRAILING_TEXT');cell+=c;}
  }
  if(quoted)throw Error('CSV_UNCLOSED');if(cell||row.length||closed){row.push(cell);rows.push(row);}return rows;
}
function inspectCsv(raw){
  const rows=parseCsv(raw.toString('utf8').replace(/^\uFEFF/,'')),cells=rows.flat();
  // Emit only alphabetic labels and date-shaped tokens, never price cells.
  const labels=[...new Set(cells.map(c=>c.trim()).filter(c=>/^[A-Za-z][A-Za-z ()/.,:-]{1,160}$/.test(c)))];
  const dates=[...new Set(cells.flatMap(c=>c.match(/\b\d{1,2}\/\d{1,2}\/\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b/g)||[]))];
  const monthly=JSON.stringify(rows[0]?.slice(4))===JSON.stringify(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']);
  return {record_count:rows.length,column_counts:[...new Set(rows.map(r=>r.length))],labels,date_tokens:dates,
    monthly_header:monthly,year_labels_in_first_column:monthly?[...new Set(rows.slice(1).map(r=>r[0].trim()).filter(c=>/^(19|20)\d{2}$/.test(c)))]:[],
    header_shape_numbers_redacted:rows.slice(0,4).map(r=>r.map(c=>c.replace(/\d+(?:[.,]\d+)*/g,'[NUMBER]'))),
    brent_text_present:cells.some(c=>/\bBrent\b/i.test(c)),rbrte_text_present:cells.some(c=>/\bRBRTE\b/.test(c)),
    research_ready:false,dates_are_not_publication_proof:true};
}
async function main(mode){
  if(!['discover','acquire','verify','inspect'].includes(mode))throw Error('MODE_DENIED');
  let l=fs.existsSync(ledgerPath)?JSON.parse(fs.readFileSync(ledgerPath)):
    {schema:'M4_EIA_TABLE11_RUN_01',attempts:[],research_ready:false};
  if(!['verify','inspect'].includes(mode)&&(l.attempts.length!==(mode==='discover'?0:1)||l.attempts.some(a=>a.state!=='RETAINED')))throw Error('REPLAY_DENIED');
  fs.mkdirSync(dir,{recursive:true});
  if(mode==='discover'){
    const k=crypto.randomBytes(32);try{fs.writeFileSync(path.join(dir,'key.dpapi'),wrapKey(k),{flag:'wx'});}finally{k.fill(0);}
  }
  const key=wrapKey(fs.readFileSync(path.join(dir,'key.dpapi')),true);
  try{
    if(mode==='inspect'){
      if(l.attempts.length!==2||l.attempts[1].state!=='RETAINED')throw Error('CSV_NOT_RETAINED');
      console.log(canonical(inspectCsv(readRaw(l.attempts[1],key))));return;
    }
    if(mode==='verify'){
      for(const a of l.attempts)if(a.encrypted_file)readRaw(a,key);
      console.log(canonical({encrypted_hashes_verified:true,attempts:l.attempts.length,research_ready:false}));return;
    }
    const url=mode==='discover'?landing:linkOf(readRaw(l.attempts[0],key).toString());
    if(l.attempts.length){const wait=15000-(Date.now()-Date.parse(l.attempts[0].started_at));if(wait>0)await new Promise(r=>setTimeout(r,wait));}
    const limit=1048576-l.attempts.reduce((s,a)=>s+(a.bytes||0),0);
    if(limit<=0)throw Error('BODY_LIMIT');
    const a={mode,url,started_at:new Date().toISOString(),state:'STARTED'};
    l.attempts.push(a);writeLedger(l);const start=performance.now();
    try{
      const raw=await get(url,limit);Object.assign(a,retain(raw,key));
      if(mode==='discover')a.csv_url=linkOf(raw.toString());
      else if(/<\s*(?:!doctype|html)/i.test(raw.toString('utf8',0,512)))throw Error('HTML_NOT_CSV');
      a.state='RETAINED';
    }catch(e){a.state='FAILED';a.error_code=/^[A-Z_]+$/.test(e.message)?e.message:'LOCAL_PROCESSING_FAILED';}
    a.elapsed_ms=Math.round(performance.now()-start);writeLedger(l);console.log(canonical(a));
    if(a.state!=='RETAINED')process.exitCode=2;
  }finally{key.fill(0);}
}
module.exports={linkOf,parseCsv,inspectCsv};
if(require.main===module)main(process.argv[2]).catch(()=>{console.error('STOPPED_NO_REQUEST_OR_LOCAL_FAILURE');process.exitCode=2;});
