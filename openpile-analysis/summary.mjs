// Summarize solved response envelopes, not applied reaction extremes.
export function summarize(report, settings) {
  const groups=report.footings ? report.footings.map(p=>({
    footing:p.footing,status:p.status,
    trial:p.trials.find(t=>t.depth_ft===p.accepted_depth_ft) || p.trials.at(-1)
  })) : [{footing:settings.footing,status:report.summary?.status,
    trial:{depth_ft:settings.embedment_ft,cases:[{...report,reaction:settings.reaction,plane:settings.plane}]}}];
  return groups.map(g=>{
    const cases=g.trial?.cases || [];
    const maxima={};
    for(const [name,key,factor,unit] of [
      ['moment','max_abs_moment_kn_m',1/(4.4482216152605*.3048),'kip-ft'],
      ['shear','max_abs_shear_kn',1/4.4482216152605,'kip'],
      ['deflection','max_abs_deflection_m',1/.0254,'in']
    ]) {
      const eligible=cases.filter(c=>c.summary?.status==='converged' && Number.isFinite(c.summary[key]));
      if(!eligible.length){maxima[name]=null;continue;}
      const peak=Math.max(...eligible.map(c=>Math.abs(c.summary[key])));
      maxima[name]={value:peak*factor,unit,controls:eligible.filter(c=>Math.abs(c.summary[key])===peak).map(c=>({
        ...c.reaction,plane:c.plane,results_folder:c.results_folder
      }))};
    }
    return {footing:g.footing,status:g.status,depth_ft:g.trial?.depth_ft,
      scope:'Maximum absolute response along the pier, across solved planes and combinations at this depth. Exact ties retained.',
      incomplete:['error','cancelled','running'].includes(g.status),...maxima};
  });
}
