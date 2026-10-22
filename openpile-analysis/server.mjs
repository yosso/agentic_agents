import http from 'node:http';
import {readFile, writeFile, mkdir, readdir} from 'node:fs/promises';
import {spawn} from 'node:child_process';
import {randomUUID} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {batch} from './batch.mjs';
import {summarize} from './summary.mjs';

const home = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(home);
const readJSON = async p => JSON.parse((await readFile(p,'utf8')).replace(/^\uFEFF/,''));
const writeJSON = (p,v) => writeFile(p,JSON.stringify(v,null,2));
const allowedFiles = new Set(['summary.json','validation.json','analysis-inputs.json','displacements.csv','forces.csv','reactions.csv','solver.log']);
export function createApp({python=process.env.OPENPILE_PYTHON || path.join(root,'openpile-cli','.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python'), extractionPython=process.env.EXTRACTION_PYTHON || 'python', results=path.join(home,'results')}={}) {
  const jobs = new Map(); let active = null;
  async function execute(job, request) {
    const folder = path.join(results,job.id); let sequence = 0;
    const addLog = text => {job.log=(job.log+text).slice(-64000);};
    const artifact = (name, file) => {job.files.push({name,file});};
    try {
      await mkdir(folder,{recursive:true});
      if (['defaults','mapping','extract'].includes(request.command)) {
        await writeJSON(path.join(folder,'extraction-request.json'),request);
        const output=path.join(folder,'extraction-result.json');
        const code=await new Promise((resolve,reject)=>{
          const child=spawn(extractionPython,[path.join(home,'extract_inputs.py'),path.join(folder,'extraction-request.json'),output],{shell:false,windowsHide:true,cwd:root});
          child.stdout.on('data',v=>addLog(v.toString()));child.stderr.on('data',v=>addLog(v.toString()));
          child.once('error',reject);child.once('close',resolve);
        });
        artifact('extraction-request.json','extraction-request.json');
        if(code!==0)throw Error(`Extraction failed. ${job.log}`);
        job.report=await readJSON(output);
        artifact('extraction-result.json','extraction-result.json');
        if(job.report.document){
          await writeJSON(path.join(folder,'prepared-inputs.json'),job.report.document);
          artifact('prepared-inputs.json','prepared-inputs.json');
          await writeJSON(path.join(folder,'reactions.json'),job.report.extraction);
          artifact('reactions.json','reactions.json');
        }
        job.state=job.cancelled?'cancelled':'completed';
        return;
      }
      await writeJSON(path.join(folder,'prepared-inputs.json'),request.document);
      await writeJSON(path.join(folder,'settings.json'),request.settings);
      artifact('prepared-inputs.json','prepared-inputs.json'); artifact('settings.json','settings.json');
      async function run(settings, command='run') {
        const name = `case-${String(++sequence).padStart(4,'0')}`;
        const output = path.join(folder,name);
        const config = `${name}-settings.json`;
        await writeJSON(path.join(folder,config),settings); artifact(config,config);
        const code = await new Promise((resolve,reject)=> {
          const child = spawn(python,[path.join(root,'openpile-cli','cli.py'),command,'--inputs',path.join(folder,'prepared-inputs.json'),'--settings',path.join(folder,config),'--output',output],{shell:false,windowsHide:true,cwd:root});
          child.stdout.on('data',v=>addLog(v.toString())); child.stderr.on('data',v=>addLog(v.toString()));
          child.once('error',reject); child.once('close',resolve);
        });
        for (const nameOfFile of await readdir(output).catch(()=>[])) if (allowedFiles.has(nameOfFile)) artifact(`${name}/${nameOfFile}`,`${name}/${nameOfFile}`);
        if (code !== 0) {
          const validation = await readJSON(path.join(output,'validation.json')).catch(()=>null);
          const summary = await readJSON(path.join(output,'summary.json')).catch(()=>null);
          throw Error(validation?.error || summary?.error || `OpenPile CLI exited with code ${code}. See log.`);
        }
        const data = await readJSON(path.join(output,command==='validate'?'validation.json':'summary.json'));
        return {summary:data,results_folder:name};
      }
      if (request.command === 'batch') {
        job.report = await batch(request.document,request.settings,request.options,run,()=>job.cancelled,m=>{job.progress=m;addLog(m+'\n');});
        job.state = job.report.cancelled ? 'cancelled' : job.report.footings.some(p=>p.status==='error') ? 'failed' : 'completed';
      } else {
        job.report = await run(request.settings,request.command);
        job.state = job.cancelled ? 'cancelled' : 'completed';
      }
      if(['run','batch'].includes(request.command)) {
        job.report.response_summary=summarize(job.report,request.settings);
        await writeJSON(path.join(folder,'response-summary.json'),job.report.response_summary);
        artifact('response-summary.json','response-summary.json');
      }
    } catch (e) {job.state=job.cancelled?'cancelled':'failed';job.error=e.message;addLog(e.message+'\n');}
    finally {
      job.progress = job.state === 'completed' ? (request.command === 'validate' ? 'Validation finished' : 'Results ready') : (job.state === 'cancelled' ? 'Cancelled' : 'Review errors');
      try { await writeJSON(path.join(folder,'job.json'),job); artifact('job.json','job.json'); }
      catch(e) {job.state='failed';job.error=`Could not save report: ${e.message}`;}
      active=null;
    }
  }
  const server = http.createServer(async (req,res)=> {
    const origin = `http://127.0.0.1:${server.address().port}`;
    const send = (code,data,type='application/json') => {
      res.writeHead(code,{'Content-Type':type,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; style-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'"});
      res.end(type==='application/json'?JSON.stringify(data):data);
    };
    try {
      if (req.headers.host !== new URL(origin).host || (req.headers.origin && req.headers.origin !== origin)) return send(403,{error:'Use the local app URL.'});
      const url = new URL(req.url,origin);
      if (req.method==='GET' && ['/','/app.js','/style.css'].includes(url.pathname)) {
        const name = url.pathname==='/'?'index.html':url.pathname.slice(1);
        return send(200,await readFile(path.join(home,'public',name)),name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':'text/html');
      }
      if (req.method==='GET' && url.pathname==='/api/example') return send(200,{document:await readJSON(path.join(root,'openpile-cli/examples/prepared.json')),settings:{...await readJSON(path.join(root,'openpile-cli/examples/settings.json')),projection_height_ft:1}});
      if (req.method==='GET' && url.pathname==='/api/jobs') return send(200,[...jobs.values()].map(j=>({id:j.id,state:j.state,command:j.command})));
      const match = url.pathname.match(/^\/api\/jobs\/([\w-]+)(?:\/(cancel|file))?$/);
      if (match) {
        const job = jobs.get(match[1]); if (!job) return send(404,{error:'Unknown job.'});
        if (req.method==='GET' && !match[2]) return send(200,job);
        if (req.method==='GET' && match[2]==='file') {
          const file = job.files.find(f=>f.file===url.searchParams.get('name'));
          if (!file) return send(404,{error:'Unknown artifact.'});
          return send(200,await readFile(path.join(results,job.id,file.file)),'text/plain; charset=utf-8');
        }
        if (req.method==='POST' && match[2]==='cancel' && req.headers['x-local-app']==='1') {
          if (job.state==='running') job.cancelled=true;
          return send(200,{state:job.state,cancelled:job.cancelled});
        }
      }
      if (req.method==='POST' && url.pathname==='/api/jobs') {
        if (req.headers['x-local-app']!=='1' || !req.headers['content-type']?.startsWith('application/json')) return send(403,{error:'JSON app request required.'});
        if (active) return send(409,{error:'A job is already running.'});
        req.setEncoding('utf8');
        let body='', bytes=0;
        for await (const data of req) {bytes+=Buffer.byteLength(data);if(bytes>25*1024*1024)throw Error('Input exceeds 25 MB.');body+=data.toString();}
        const request=JSON.parse(body);
        if (!['defaults','mapping','extract'].includes(request.command) && (!['validate','run','batch'].includes(request.command) || !Array.isArray(request.document?.piers) || !Array.isArray(request.document?.soil_profiles) || !request.settings || typeof request.settings!=='object')) throw Error('Supply prepared inputs, settings and a valid command.');
        if (active) return send(409,{error:'A job is already running.'});
        const job={id:randomUUID(),command:request.command,state:'running',progress:['defaults','mapping','extract'].includes(request.command)?'Reading Excel / Robot inputs':'Starting OpenPile',cancelled:false,log:'',files:[]};
        active=job.id;jobs.set(job.id,job);void execute(job,request);
        return send(202,{id:job.id});
      }
      send(404,{error:'Not found.'});
    } catch(e) {send(400,{error:e.message});}
  });
  return server;
}
if (process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const server=createApp();
  server.listen(Number(process.env.PORT || 3210),'127.0.0.1',()=>console.log(`OpenPile analysis: http://127.0.0.1:${server.address().port}`));
  server.on('error',e=>{console.error(e.message);process.exitCode=1;});
}
