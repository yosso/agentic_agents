import {test} from 'node:test';
import assert from 'node:assert/strict';
import {batch,selectCases} from '../batch.mjs';
const row={model:'m',group:'g',node:1,case:10,FX:1,FY:2,FZ:3,MX:4,MY:5,MZ:6};
const doc=()=>({piers:[{footing:'A',reactions:[{...row}],minimum_embedment_ft:9,allowable_deflection_in:.1,soil_table:'soil'}],soil_profiles:[{table_name:'soil',layers:[{properties:{end:20}}]}]});
const opts={footings:['A'],increment:1,maximum:15,mode:'directional'};
test('ties preserve coincident vectors and duplicate selectors are rejected',()=>{
 const p=doc().piers[0];p.reactions.push({...row,node:2});assert.equal(selectCases(p).length,2);
 p.reactions.push({...row});assert.throws(()=>selectCases(p),/ambiguous/);
});
test('batch honors requested depth, minimum and both planes',async()=>{
 const calls=[];const result=await batch(doc(),{embedment_ft:11,projection_height_ft:1},opts,async s=>{
 calls.push(s);return {summary:{status:'converged',head_deflection_in:s.embedment_ft<12?.2:.05,max_abs_shear_kn:1,max_abs_moment_kn_m:2}};
 },()=>false,()=>{});
 assert.equal(result.footings[0].accepted_depth_ft,12);assert.equal(calls.length,4);assert.deepEqual(calls.map(s=>s.plane),['X','Y','X','Y']);assert.equal(calls[0].projection_height_ft,1);
});
test('failures and cancellation never pass the screen',async()=>{
 const r=await batch(doc(),{embedment_ft:8},opts,async()=>{throw Error('nonconvergence');},()=>false,()=>{});
 assert.equal(r.footings[0].status,'error');assert.equal(r.footings[0].starting_depth_ft,9);
 const c=await batch(doc(),{embedment_ft:8},opts,()=>assert.fail(),()=>true,()=>{});assert.equal(c.cancelled,true);
});
test('resultant screen respects combined response and soil coverage',async()=>{
 const d=doc();d.soil_profiles[0].layers[0].properties.end=10.5;
 const r=await batch(d,{embedment_ft:9},{...opts,mode:'resultant'},async()=>({summary:{status:'converged',head_deflection_in:.08,max_abs_shear_kn:1,max_abs_moment_kn_m:2}}),()=>false,()=>{});
 assert.equal(r.footings[0].status,'depth_limit');assert.deepEqual(r.footings[0].trials.map(t=>t.depth_ft),[9,10,10.5]);
});
