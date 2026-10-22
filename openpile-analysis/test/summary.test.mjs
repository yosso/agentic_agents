import {test} from 'node:test';
import assert from 'node:assert/strict';
import {summarize} from '../summary.mjs';
const response=(id,moment,shear,deflection,plane='X')=>({reaction:{case:id,node:4,model:'a.rtd',group:'A'},plane,
  summary:{status:'converged',max_abs_moment_kn_m:moment,max_abs_shear_kn:shear,max_abs_deflection_m:deflection}});
test('summary selects each response independently at accepted depth and retains ties',()=>{
 const report={footings:[{footing:'A',status:'deflection_pass',accepted_depth_ft:12,trials:[
  {depth_ft:10,cases:[response(99,999,999,999)]},
  {depth_ft:12,cases:[response(1,20,3,.01),response(2,10,8,.02),response(3,20,2,.03,'Y')]}
 ]}]};
 const [s]=summarize(report,{});
 assert.equal(s.depth_ft,12);assert.deepEqual(s.moment.controls.map(c=>c.case),[1,3]);
 assert.equal(s.shear.controls[0].case,2);assert.equal(s.deflection.controls[0].case,3);
 assert.equal(s.deflection.controls[0].plane,'Y');assert.equal(s.deflection.value,.03/.0254);
});
test('incomplete final trial does not borrow results from earlier depths',()=>{
 const [s]=summarize({footings:[{footing:'A',status:'error',trials:[{depth_ft:10,cases:[response(1,2,3,4)]},{depth_ft:11,cases:[]}]}]},{});
 assert.equal(s.depth_ft,11);assert.equal(s.incomplete,true);assert.equal(s.moment,null);
});
test('single run carries the exact reaction selector',()=>{
 const r=response(7,2,3,.01);
 const [s]=summarize(r,{footing:'B',embedment_ft:9,reaction:r.reaction,plane:'X'});
 assert.equal(s.footing,'B');assert.equal(s.moment.controls[0].case,7);
});
