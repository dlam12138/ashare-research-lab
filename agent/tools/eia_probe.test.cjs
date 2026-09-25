const test=require('node:test'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {seal,unseal,scanData,rowKeys,metadataReview,wrapKey}=require('./eia_probe.cjs');
test('authenticated encryption preserves exact bytes including synthetic key echo',()=>{
 const k=crypto.randomBytes(32),raw=Buffer.from('{"api_key":"SYNTHETIC_NOT_A_CREDENTIAL","value":"1.00"}\r\n');
 const b=seal(raw,k);assert.deepEqual(unseal(b,k),raw);assert(!b.includes(raw));
 b[16]^=1;assert.throws(()=>unseal(b,k));assert.throws(()=>unseal(seal(raw,k),crypto.randomBytes(32)));
});
test('Windows DPAPI wrapped key roundtrip', {skip:process.platform!=='win32'},()=>{
 const k=crypto.randomBytes(32),wrapped=wrapKey(k);assert(!wrapped.equals(k));assert.deepEqual(wrapKey(wrapped,true),k);
});
function fixture(){return {response:{total:'5',data:[9,10,11,12,13].map(d=>({...Object.fromEntries(rowKeys.map(k=>[k,'synthetic'])),period:`2015-03-${String(d).padStart(2,'0')}`,series:'RBRTE','series-description':'Synthetic Brent',units:'$/BBL',value:'1.00'}))}};}
test('five-day scan emits only structural proof',()=>assert.equal(scanData(fixture()).raw_date_scan_count,5));
test('reject holdout, malformed/duplicate/missing dates, extra columns, wrong series/units',()=>{
 for(const mutate of [x=>x.response.data[0].period='2023-01-01',x=>x.response.data[0].period='2015-02-30',x=>x.response.data[0].period='2015-03-10',x=>x.response.data.pop(),x=>x.response.data[0].extra='x',x=>x.response.data[0].series='OTHER',x=>x.response.data[0].units='other',x=>x.response.total='6']){const x=fixture();mutate(x);assert.throws(()=>scanData(x));}
});
test('metadata requires terms, daily/value/series and complete Brent facets',()=>{
 const t='You may use the EIA API to develop a service Attribution';
 const m={response:{frequency:[{id:'daily'}],data:{value:{}},facets:[{id:'series'}]}};
 const f={response:{totalFacets:1,facets:[{id:'RBRTE',name:'Brent'}]}};
 assert.equal(metadataReview(t,m,f).brent_identity,true);assert.throws(()=>metadataReview('',m,f));f.response.totalFacets=2;assert.throws(()=>metadataReview(t,m,f));
});
