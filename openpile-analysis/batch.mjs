const identity = r => JSON.stringify(['model', 'group', 'node', 'case'].map(k => r[k]));
export const positive = (v, label) => {
  if (typeof v !== 'number' || !Number.isFinite(v) || v <= 0) throw Error(`${label} must be positive and finite.`);
  return v;
};
export function selectCases(pier) {
  const rows = pier.reactions;
  if (!rows?.length) throw Error('No reactions for this footing.');
  if (new Set(rows.map(identity)).size !== rows.length) throw Error('Reaction selectors are ambiguous.');
  for (const r of rows) for (const k of ['FX','FY','FZ','MX','MY','MZ']) {
    if (typeof r[k] !== 'number' || !Number.isFinite(r[k])) throw Error(`Invalid ${k} reaction.`);
  }
  const criteria = ['FX','FY','MX','MY','MZ'].map(k => [k, r => Math.abs(r[k])]);
  criteria.push(['Resultant shear', r => Math.hypot(r.FX,r.FY)], ['Resultant moment', r => Math.hypot(r.MX,r.MY)],
    ['Compression', r => r.FZ > 0 ? r.FZ : null], ['Uplift', r => r.FZ < 0 ? -r.FZ : null]);
  const selected = new Map();
  for (const [name, measure] of criteria) {
    const eligible = rows.map(measure).filter(v => v !== null);
    if (!eligible.length) continue;
    const max = eligible.reduce((a,b) => Math.max(a,b), -Infinity);
    for (const r of rows) if (measure(r) === max) {
      const key = identity(r);
      if (!selected.has(key)) selected.set(key, {reaction: Object.fromEntries(['model','group','node','case'].map(k=>[k,r[k]])), criteria:[]});
      selected.get(key).criteria.push(name);
    }
  }
  return [...selected.values()];
}

export async function batch(document, settings, options, run, cancelled, update) {
  positive(options.increment, 'Depth increment'); positive(options.maximum, 'Maximum depth');
  positive(settings.embedment_ft, 'Trial embedment');
  if (!['directional','resultant'].includes(options.mode)) throw Error('Invalid check mode.');
  const piers = document.piers.filter(p => options.footings.includes(p.footing));
  if (!piers.length || new Set(piers.map(p=>p.footing)).size !== piers.length) throw Error('Select unique footing marks.');
  const report = {mode:options.mode, footings:[], limitations:[
    'Selected extremes do not guarantee the governing deflection among all combinations.',
    'Two independent 2D analyses; no torsion or axial soil capacity check.',
    'Loaded displacement screening only; non-recoverable deflection and full design acceptance are not evaluated.']};
  for (const pier of piers) {
    if (cancelled()) break;
    const result = {footing:pier.footing, status:'running', trials:[]}; report.footings.push(result);
    try {
      const cases = selectCases(pier);
      const profiles = document.soil_profiles.filter(p=>p.table_name===pier.soil_table);
      if (profiles.length !== 1) throw Error('Missing or ambiguous soil profile.');
      const start = Math.max(positive(settings.embedment_ft,'Trial depth'),positive(pier.minimum_embedment_ft,'Workbook minimum'));
      const limit = Math.min(options.maximum, positive(profiles[0].layers.at(-1).properties.end,'Soil coverage'));
      positive(pier.allowable_deflection_in,'Allowable deflection');
      result.starting_depth_ft = start;
      if (start > limit) throw Error('Starting depth exceeds maximum or soil coverage.');
      for (let depth = start, index = 0; ; index++, depth = Math.min(start+index*options.increment, limit)) {
        if (cancelled()) { result.status='cancelled'; break; }
        const trial = {depth_ft:depth, cases:[]}; result.trials.push(trial);
        for (const c of cases) {
          const responses = [];
          for (const plane of ['X','Y']) {
            if (cancelled()) throw Error('Cancelled between solver runs.');
            update(`${pier.footing}: ${depth} ft, node ${c.reaction.node}, combination ${c.reaction.case}, ${plane}`);
            const response = await run({...structuredClone(settings),footing:pier.footing,reaction:c.reaction,plane,embedment_ft:depth});
            if (response.summary?.status !== 'converged' || !Number.isFinite(response.summary.head_deflection_in)) throw Error('Incomplete solver response.');
            responses.push(response.summary.head_deflection_in);
            trial.cases.push({reaction:c.reaction,criteria:c.criteria,plane,...response});
          }
          const value = options.mode === 'resultant' ? Math.hypot(...responses) : Math.max(...responses.map(Math.abs));
          trial.checked_deflection_in = Math.max(trial.checked_deflection_in ?? 0,value);
        }
        trial.passed = trial.checked_deflection_in <= pier.allowable_deflection_in;
        if (trial.passed) {
          result.status='deflection_pass'; result.accepted_depth_ft=depth;
          result.checked_deflection_in=trial.checked_deflection_in;
          result.max_shear_kip=Math.max(...trial.cases.map(c=>c.summary.max_abs_shear_kn))/4.4482216152605;
          result.max_moment_kip_ft=Math.max(...trial.cases.map(c=>c.summary.max_abs_moment_kn_m))/(4.4482216152605*.3048);
          break;
        }
        if (depth >= limit) {result.status='depth_limit'; break;}
      }
    } catch (e) {result.status=cancelled()?'cancelled':'error';result.error=e.message;}
  }
  report.cancelled=cancelled(); return report;
}
