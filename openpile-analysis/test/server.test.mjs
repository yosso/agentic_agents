import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {createApp} from '../server.mjs';
test('real HTTP validation, solver, artifacts and failure reporting',async()=>{
 const directory=await mkdtemp(path.join(tmpdir(),'openpile-node-'));
 const server=createApp({results:directory});await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const base=`http://127.0.0.1:${server.address().port}`;
 try{
  assert.equal((await fetch(base)).status,200);
  const example=await(await fetch(base+'/api/example')).json();
  const post=data=>fetch(base+'/api/jobs',{method:'POST',headers:{'Content-Type':'application/json','X-Local-App':'1'},body:JSON.stringify(data)});
  const wait=async id=>{for(let i=0;i<180;i++){const j=await(await fetch(base+'/api/jobs/'+id)).json();if(j.state!=='running')return j;await new Promise(r=>setTimeout(r,500));}throw Error('Job timed out');};
  const defaultsJob=await wait((await(await post({command:'defaults'})).json()).id);
  assert.equal(defaultsJob.state,'completed',defaultsJob.log);
  assert.equal(defaultsJob.report.sheet,'INPUT TABLES');
  const mappingJob=await wait((await(await post({...defaultsJob.report,command:'mapping'})).json()).id);
  assert.equal(mappingJob.state,'completed',mappingJob.log);
  assert.ok(mappingJob.report.mappings.length>0);
  const staleJob=await wait((await(await post({...defaultsJob.report,command:'extract',snapshot:[]})).json()).id);
  assert.equal(staleJob.state,'failed');assert.match(staleJob.error,/mapping changed/);
  for(const command of ['validate','run','batch']){
   const res=await post({...example,command,options:{footings:['DEMO'],increment:1,maximum:35,mode:'resultant'}});assert.equal(res.status,202);const {id}=await res.json();
   const job=await wait(id);assert.equal(job.state,'completed',job.log);assert.ok(job.files.length>2);
   if(command==='run'){assert.equal(job.report.summary.status,'converged');assert.ok(Number.isFinite(job.report.summary.head_deflection_in));}
   if(command==='batch') assert.equal(job.report.footings[0].status,'deflection_pass',JSON.stringify(job.report));
   const file=job.files.find(f=>f.name.endsWith('analysis-inputs.json'));
   const data=await(await fetch(base+`/api/jobs/${id}/file?name=${encodeURIComponent(file.file)}`)).json();assert.equal(data.projection_height_m,.3048);
   assert.equal((await fetch(base+`/api/jobs/${id}/file?name=../../.git/config`)).status,404);
  }
  example.document.piers[0].water_table_depth_ft=null;
  const res=await post({...example,command:'run'});const job=await wait((await res.json()).id);assert.equal(job.state,'failed');assert.match(job.error,/water_table_depth_ft/);
  assert.equal((await fetch(base+'/api/jobs',{method:'POST',headers:{Origin:'https://other.example'}})).status,403);
 }finally{await new Promise(r=>server.close(r));await rm(directory,{recursive:true,force:true});}
});
