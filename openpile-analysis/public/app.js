const $ = id => document.getElementById(id);

let documentData, template, jobId, busy=false, mappingSnapshot, mappingSource, appliedJob;

const parse = text => JSON.parse(text.replace(/^\uFEFF/,''));

const safe = fn => async (...args) => {try{ $('error').textContent='';await fn(...args); }catch(e){$('error').textContent=e.message;}};

const option = (value,text) => {const el=document.createElement('option');el.value=value;el.textContent=text;return el;};

function setSettings(s) {

  template=structuredClone(s);

  for(const [id,key] of Object.entries({depth:'embedment_ft',mesh:'mesh_size_ft',iterations:'max_iterations',plane:'plane'})) $(id).value=s[key];

  $('projection').value=s.projection_height_ft ?? 1;

  $('E').value=s.material.E_psi ?? s.material.E_kpa/6.894757293168;

  $('weight').value=s.material.unit_weight_pcf ?? s.material.unit_weight_kn_m3/(.0044482216152605/.3048**3);

  $('nu').value=s.material.poisson_ratio;

  for(const key of ['lateral','moment','axial']) $(key).value=s.load_signs[key];

  $('soils').value=JSON.stringify(s.soil_models,null,2);
  syncSoilMappings();

  if(documentData?.piers.some(p=>p.footing===s.footing)) {$('footing').value=s.footing;showPier();}

}

function showPier() {

  const p=documentData.piers.find(p=>p.footing===$('footing').value);

  if(!p){$('reaction').replaceChildren();$('pierInfo').textContent='No prepared footings. Review source findings.';return;}

  $('reaction').replaceChildren(...p.reactions.map((r,i)=>option(i,`${r.model} / ${r.group} / node ${r.node} / ${r.case}: ${r.case_name}`)));

  const index=p.reactions.findIndex(r=>['model','group','node','case'].every(k=>r[k]===template?.reaction?.[k]));

  if(index>=0)$('reaction').value=index;

  $('pierInfo').textContent=`Diameter ${p.diameter_ft} ft · Workbook minimum ${p.minimum_embedment_ft} ft · Water depth ${p.water_table_depth_ft ?? 'MISSING'} ft · Allowable ${p.allowable_deflection_in} in`;

  updateStarts();
  showLoads();

}

function showLoads() {
  const p=documentData?.piers.find(p=>p.footing===$('footing').value);
  const r=p?.reactions[Number($('reaction').value)];
  const panel=$('loadPreview');
  if(!r){panel.textContent='Select a reaction to review applied loads.';return;}
  const plane=$('plane').value, force=plane==='X'?'FX':'FY', moment=plane==='X'?'MY':'MX';
  const kip=4448.2216152605, kipft=kip*.3048;
  const fmt=v=>Number(v).toLocaleString('en-US',{maximumSignificantDigits:6});
  panel.textContent=`Node ${r.node} · ${r.case}: ${r.case_name} · ${plane} axis: lateral ${force} = ${fmt(r[force]*Number($('lateral').value)/kip)} kip; moment ${moment} = ${fmt(r[moment]*Number($('moment').value)/kipft)} kip-ft; axial FZ = ${fmt(r.FZ*Number($('axial').value)/kip)} kip (configured signs applied). Other axis: ${plane==='X'?'FY':'FX'} = ${fmt(r[plane==='X'?'FY':'FX']/kip)} kip; ${plane==='X'?'MX':'MY'} = ${fmt(r[plane==='X'?'MX':'MY']/kipft)} kip-ft (Robot signs).`;
}

function updateStarts() {

  if(!documentData)return;

  for(const el of $('batchFootings').options){const p=documentData.piers.find(p=>p.footing===el.value);el.textContent=`${p.footing} — min ${p.minimum_embedment_ft} ft; start ${Math.max(Number($('depth').value),p.minimum_embedment_ft)} ft`;}

}

function load(document,label) {

  if(!Array.isArray(document.piers)||!Array.isArray(document.soil_profiles))throw Error('Choose a prepared-input JSON with piers and soil_profiles.');

  const mappings=parse($('soils').value || '{}');
  documentData=document;
  syncSoilMappings(mappings);

  $('source').textContent=`${label} · ${document.piers.length} footings · ${document.soil_profiles.length} borings`;

  $('sourceDetails').textContent=JSON.stringify({issues:document.issues,soil_profiles:document.soil_profiles},null,2);

  $('footing').replaceChildren(...document.piers.map(p=>option(p.footing,p.footing)));

  $('batchFootings').replaceChildren(...document.piers.map(p=>{const el=option(p.footing,p.footing);el.selected=true;return el;}));

  showPier();

}

function syncSoilMappings(existing=parse($('soils').value || '{}')) {
  if(!documentData)return;
  const labels=[...new Set(documentData.soil_profiles.flatMap(p=>(p.layers||[]).map(l=>l.properties?.model)).filter(v=>typeof v==='string' && v.trim()))];
  const mappings=Object.fromEntries(labels.map(label=>[label,Object.hasOwn(existing,label)?existing[label]:null]));
  $('soilControls').replaceChildren();
  for(const label of labels){
    const box=document.createElement('fieldset'),title=document.createElement('legend');title.textContent=label;box.append(title);
    const layers=documentData.soil_profiles.flatMap(p=>(p.layers||[]).filter(l=>l.properties?.model===label));
    const note=document.createElement('p');note.textContent=`${layers.length} extracted layers. Parameter values come from Excel; choose the model and fields below.`;box.append(note);
    const grid=document.createElement('div');grid.className='grid';box.append(grid);
    const controls={};
    function select(key,name,choices,value){const wrap=document.createElement('label');wrap.textContent=name;const el=document.createElement('select');el.setAttribute('aria-label',`${label}: ${name}`);el.append(...choices.map(v=>option(v,v||'Choose model')));el.value=value;wrap.append(el);grid.append(wrap);controls[key]=el;return el;}
    const current=mappings[label]||{};
    select('model','OpenPile model',['','API_clay','API_sand'],current.model||'');
    select('kind','Curve type',['static','cyclic'],current.kind||'static');
    select('cohesion','Strength field',['cohesion_ultimate','cohesion_factored'],current.cohesion||'cohesion_ultimate');
    select('strain','Strain field',['e50','e50_factored'],current.strain||'e50');
    select('modulus','Subgrade field',['k_static','k_static_factored','k_cyclic'],current.modulus||'k_static');
    const wrap=document.createElement('label');wrap.textContent='Clay factor J';const j=document.createElement('input');j.type='number';j.min='.25';j.max='.5';j.step='.01';j.value=current.J??.5;j.setAttribute('aria-label',`${label}: Clay factor J`);wrap.append(j);grid.append(wrap);controls.J=j;
    const finding=document.createElement('p');box.append(finding);
    function update(changed=false){
      const model=controls.model.value,kind=controls.kind.value;
      const modulus=controls.modulus;
      if(model==='API_sand' && changed && (kind==='cyclic')!==(modulus.value==='k_cyclic'))modulus.value=kind==='cyclic'?'k_cyclic':'k_static';
      for(const opt of modulus.options)opt.disabled=kind==='cyclic'?opt.value!=='k_cyclic':opt.value==='k_cyclic';
      for(const key of ['cohesion','strain','J'])controls[key].parentElement.hidden=model!=='API_clay';
      modulus.parentElement.hidden=model!=='API_sand';
      mappings[label]=!model?null:model==='API_clay'?{model,kind,cohesion:controls.cohesion.value,strain:controls.strain.value,J:j.value===''?null:Number(j.value)}:{model,kind,modulus:modulus.value};
      const fields=model==='API_clay'?[controls.cohesion.value,controls.strain.value]:model==='API_sand'?['friction_angle',modulus.value]:[];
      const missing=fields.filter(f=>layers.some(l=>l.properties[f]==null));
      finding.textContent=!model?'Select a model to generate this mapping.':missing.length?`Missing Excel values: ${missing.join(', ')}. Update the workbook and re-extract.`:'Mapping generated. Review choices, then validate the selected case.';
      $('soils').value=JSON.stringify(mappings,null,2);
      const unresolved=labels.filter(name=>!mappings[name]?.model);
      $('soilMappingStatus').textContent=unresolved.length?`Choose models for: ${unresolved.join(', ')}.`:'Mapping JSON generated from your selections. Review parameter choices before analysis.';
    }
    for(const el of Object.values(controls))el.onchange=()=>update(true);
    update();$('soilControls').append(box);
  }
  $('soils').value=JSON.stringify(mappings,null,2);
}
function collect() {

  if(!documentData||!template)throw Error('Load prepared inputs and settings first.');

  const s=structuredClone(template), p=documentData.piers.find(p=>p.footing===$('footing').value),r=p.reactions[Number($('reaction').value)];

  if(!r)throw Error('Select a reaction.');

  s.footing=p.footing;s.reaction=Object.fromEntries(['model','group','node','case'].map(k=>[k,r[k]]));

  for(const [id,key] of Object.entries({depth:'embedment_ft',projection:'projection_height_ft',mesh:'mesh_size_ft',iterations:'max_iterations'})) {

    if($(id).value==='')throw Error(`Enter ${key}.`);s[key]=Number($(id).value);

  }

  s.plane=$('plane').value;

  s.material={E_psi:Number($('E').value),unit_weight_pcf:Number($('weight').value),poisson_ratio:Number($('nu').value)};

  s.load_signs=Object.fromEntries(['lateral','moment','axial'].map(k=>[k,Number($(k).value)]));

  s.soil_models=parse($('soils').value);return s;

}

async function api(url, data) {

  const res=await fetch(url,data?{method:'POST',headers:{'Content-Type':'application/json','X-Local-App':'1'},body:JSON.stringify(data)}:{});

  const value=await res.json();if(!res.ok)throw Error(value.error);return value;

}

function lock(value){busy=value;for(const id of ['validate','run','batch','demo','inputs','import','defaults','mapping','extract'])$(id).disabled=value;$('cancel').disabled=!value;}

function cell(row,text,tag='td'){const el=document.createElement(tag);el.textContent=text;row.append(el);}

function render(job){

  $('status').textContent=`${job.state} · ${job.progress}`;$('log').textContent=job.log;$('error').textContent=job.error||'';

  $('report').textContent=JSON.stringify(job.report||{},null,2);

  $('files').replaceChildren(...job.files.map(f=>{const a=document.createElement('a');a.textContent=f.name;a.href=`/api/jobs/${job.id}/file?name=${encodeURIComponent(f.file)}`;a.target='_blank';a.rel='noopener';return a;}));

  $('metrics').replaceChildren();$('table').replaceChildren();

  $('responseSummary').replaceChildren();
  if(job.report?.response_summary){
    const head=document.createElement('tr');
    for(const name of ['Footing','Status','Embedment (ft)','Response','Maximum','Controlling combination / node / axis / group / model'])cell(head,name,'th');
    $('responseSummary').append(head);
    for(const entry of job.report.response_summary)for(const metric of ['moment','shear','deflection']){
      const row=document.createElement('tr'),value=entry[metric];
      const controls=value?.controls.map(c=>`${c.case} / ${c.node} / ${c.plane} axis / ${c.group} / ${c.model}`).join('; ');
      for(const v of [entry.footing,entry.status+(entry.incomplete?' (incomplete)':''),entry.depth_ft??'Unavailable',metric,value?`${value.value.toPrecision(5)} ${value.unit}`:'Unavailable',controls||'Unavailable'])cell(row,v);
      $('responseSummary').append(row);
    }
  }
  const summary=job.report?.summary;

  if(summary?.status==='converged') for(const [label,value,unit] of [['Head deflection',summary.head_deflection_in,'in'],['Max |shear|',summary.max_abs_shear_kn/4.4482216152605,'kip'],['Max |moment|',summary.max_abs_moment_kn_m/(4.4482216152605*.3048),'kip-ft']]) {

    const box=document.createElement('div');box.textContent=label;const v=document.createElement('strong');v.textContent=`${value.toPrecision(5)} ${unit}`;box.append(v);$('metrics').append(box);

  }

  if(job.report?.footings){const head=document.createElement('tr');for(const name of ['Footing','Status','Start (ft)','Accepted (ft)','Displacement (in)','Finding'])cell(head,name,'th');$('table').append(head);

    for(const p of job.report.footings){const row=document.createElement('tr');for(const v of [p.footing,p.status,p.starting_depth_ft,p.accepted_depth_ft,p.checked_deflection_in,p.error])cell(row,v??'—');$('table').append(row);}}

}

async function poll(){try{const job=await api(`/api/jobs/${jobId}`);render(job);if(job.state==='running')setTimeout(poll,1000);else {lock(false);applyExtraction(job);}}catch(e){$('error').textContent=e.message;lock(false);}}

async function start(command){

  const settings=collect();lock(true);$('metrics').replaceChildren();$('table').replaceChildren();$('files').replaceChildren();$('report').textContent='';

  try{const job=await api('/api/jobs',{command,document:documentData,settings,options:{increment:Number($('increment').value),maximum:Number($('maximum').value),mode:$('mode').value,footings:[...$('batchFootings').selectedOptions].map(o=>o.value)}});jobId=job.id;poll();}catch(e){lock(false);throw e;}

}

$('demo').onclick=safe(async()=>{const data=await api('/api/example');documentData=undefined;setSettings(data.settings);load(data.document,'Synthetic example — not project design data');});

$('inputs').onchange=safe(async e=>{if(e.target.files[0])load(parse(await e.target.files[0].text()),e.target.files[0].name);});

$('import').onchange=safe(async e=>{if(e.target.files[0])setSettings(parse(await e.target.files[0].text()));});

$('footing').onchange=showPier;$('depth').oninput=updateStarts;
for(const id of ['reaction','plane','lateral','moment','axial'])$(id).onchange=showLoads;

for(const cmd of ['validate','run','batch'])$(cmd).onclick=safe(()=>start(cmd));

$('cancel').onclick=safe(async()=>{await api(`/api/jobs/${jobId}/cancel`,{});$('cancel').disabled=true;});

$('save').onclick=safe(()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(collect(),null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='openpile-settings.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});

safe(async()=>{const example=await api('/api/example');setSettings({...example.settings,soil_models:{}});const jobs=await api('/api/jobs');const last=jobs.at(-1);if(last){jobId=last.id;lock(last.state==='running');poll();}})();



function extractionSource(){return {workbook:$('workbook').value.trim(),sheet:$('sheet').value.trim(),table:$('mappingTable').value.trim()};}

function applyExtraction(job){

  if(job.state!=='completed'||appliedJob===job.id)return;

  appliedJob=job.id;

  if(job.command==='defaults'){

    for(const [id,key] of Object.entries({workbook:'workbook',sheet:'sheet',mappingTable:'table',robotApi:'api'}))$(id).value=job.report[key];

  }

  if(job.command==='mapping'){

    mappingSnapshot=job.report.mappings;mappingSource=job.report.source;

    $('mappingRows').replaceChildren();

    const head=document.createElement('tr');for(const title of ['Footing','Expected nodes','Group','Robot file'])cell(head,title,'th');$('mappingRows').append(head);

    for(const m of mappingSnapshot){const row=document.createElement('tr');for(const v of [m.mark,m.expected,m.group])cell(row,v);const td=document.createElement('td'),input=document.createElement('input');input.value=m.model;input.dataset.row=m.row;input.setAttribute('aria-label',`Robot file for ${m.mark} / ${m.group}`);td.append(input);row.append(td);$('mappingRows').append(row);}

    $('mappingStatus').textContent=`${mappingSnapshot.length} assignments loaded. Review model paths before reading Robot.`;

  }

  if(job.command==='extract')load(job.report.document,'Excel / Robot extraction � review validation findings below');

}

async function startExtraction(command){

  const source=extractionSource();

  if(command==='extract'&&(!mappingSnapshot||JSON.stringify(source)!==JSON.stringify(mappingSource)))throw Error('Load the mapping again for the selected workbook, worksheet and table.');

  const models=Object.fromEntries([...$('mappingRows').querySelectorAll('input')].map(el=>[el.dataset.row,el.value.trim()]));

  lock(true);

  try{const job=await api('/api/jobs',{command,...source,api:$('robotApi').value.trim(),cases:$('cases').value,snapshot:mappingSnapshot,models});jobId=job.id;poll();}catch(e){lock(false);throw e;}

}

for(const command of ['defaults','mapping','extract'])$(command).onclick=safe(()=>startExtraction(command));




$('saveMappings').onclick=safe(()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({soil_models:parse($('soils').value||'{}')},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='soil-mappings.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
