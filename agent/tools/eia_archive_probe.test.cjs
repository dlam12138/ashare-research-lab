const {test}=require('node:test'),assert=require('node:assert/strict');
const {linkOf,parseCsv,inspectCsv}=require('./eia_archive_probe.cjs');
const title='Spot Prices of Crude Oil, Motor Gasoline, and Heating Oil';
const row=href=>`<tr><td>11</td><td>${title}</td><td><a href="${href}">CSV</a></td></tr>`;
test('resolve same-issue CSV only',()=>assert.equal(linkOf(row('csv/table11.csv')),'https://www.eia.gov/petroleum/supply/weekly/archive/2015/2015_03_18/csv/table11.csv'));
test('reject external/other issue/PDF/query links',()=>{for(const p of ['https://evil.test/a.csv','../a.csv','a.pdf','a.csv?x=1'])assert.throws(()=>linkOf(row(p)));});
test('reject missing and ambiguous rows',()=>{assert.throws(()=>linkOf(''));assert.throws(()=>linkOf(row('a.csv')+row('b.csv')));});
test('CSV quoted commas, escaped quotes, CRLF and empty fields',()=>assert.deepEqual(parseCsv('"a,b","c""d",\r\n'),[['a,b','c"d','']]));
test('malformed CSV fails closed',()=>{for(const t of ['"a','a"b','"a"b'])assert.throws(()=>parseCsv(t));});
test('inspection never emits numeric prices or admits research',()=>{
  const r=inspectCsv(Buffer.from('Brent,3/13/2015,123.456\nWTI,3/12/2015,987.654'));
  assert.equal(r.brent_text_present,true);assert.equal(r.research_ready,false);
  assert.deepEqual(r.date_tokens,['3/13/2015','3/12/2015']);
  assert.ok(!JSON.stringify(r).includes('123.456'));assert.ok(!JSON.stringify(r).includes('987.654'));
});
test('monthly year headers are not daily coverage',()=>{
  const r=inspectCsv(Buffer.from('STUB_1,STUB_2,STUB_3,STUB_4,Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec\n2015,Crude Oil,Brent,,1,2,3,4,5,6,7,8,9,10,11,12'));
  assert.equal(r.monthly_header,true);assert.deepEqual(r.year_labels_in_first_column,['2015']);
  assert.deepEqual(r.date_tokens,[]);assert.equal(r.research_ready,false);
});
