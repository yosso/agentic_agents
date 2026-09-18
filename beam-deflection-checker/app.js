const form = document.querySelector('#inputs');
const set = (id, value) => { document.getElementById(id).textContent = value; };
const number = value => value !== 0 && (Math.abs(value) < 0.001 || Math.abs(value) >= 1e7) ? value.toExponential(3) : value.toLocaleString('en-US', { maximumFractionDigits: 3 });
let revision = 0;
let checkTimer;
let awatifModule;
function scheduleAwatif(values, reference, current) {
  set('awatif-status', 'Running Awatif check…');
  set('awatif-message', 'Solving the same beam with the Awatif WebAssembly solver.');
  document.getElementById('awatif-results').hidden = true;
  document.getElementById('awatif-legend').hidden = true;
  document.querySelector('.cross-check').classList.remove('check-error');
  checkTimer = setTimeout(async () => {
    try {
      awatifModule ??= import('./awatif-analysis.mjs');
      const { analyzeBeam, compareResults } = await awatifModule;
      if (current !== revision) return;
      const result = analyzeBeam(values);
      const comparison = compareResults(reference, result);
      set('awatif-status', comparison.agrees ? 'Methods agree' : 'Methods differ — review results');
      set('awatif-message', 'Independent stiffness-matrix solution using awatif-fem 1.0.1.');
      set('awatif-deflection', `${number(result.maximum)} in`);
      set('awatif-difference', `${number(comparison.difference)} in${comparison.percent === null ? ' (zero-load reference)' : ` (${number(comparison.percent)}%)`}`);
      set('awatif-limit', `${result.passes ? 'Within limit' : 'Exceeds limit'} · ${number(result.utilization * 100)}%`);
      set('awatif-reactions', result.reactions.map(value => `${number(value)} kip`).join(' / '));
      document.getElementById('awatif-results').hidden = false;
      document.getElementById('awatif-legend').hidden = false;
      document.querySelector('.cross-check').classList.toggle('check-error', !comparison.agrees);
      const points = result.deflections.map((value, i) => {
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', 60 + 640 * i / result.divisions);
        circle.setAttribute('cy', 110 + (reference.maximum ? value / reference.maximum * 75 : 0));
        circle.setAttribute('r', 3);
        circle.setAttribute('fill', '#bd6b21');
        return circle;
      });
      document.getElementById('diagram').append(...points);
    } catch (error) {
      if (current !== revision) return;
      awatifModule = undefined;
      set('awatif-status', 'Awatif check unavailable');
      set('awatif-message', `The formula results remain available. Run npm install, restart npm start, and refresh. ${error.message}`);
      document.querySelector('.cross-check').classList.add('check-error');
    }
  }, 180);
}
function update() {
  const current = ++revision;
  clearTimeout(checkTimer);
  try {
    updateSection();
    const values = Object.fromEntries(Array.from(form.querySelectorAll('input[name]'), input => [input.name, input.value.trim() === '' ? NaN : Number(input.value)]));
    const r = Beam.calculate(values);
    document.getElementById('error').hidden = true;
    document.getElementById('output').hidden = false;
    set('status', r.passes ? 'Within deflection limit' : 'Exceeds deflection limit');
    set('comparison', 'Calculated deflection / allowable deflection');
    set('utilization', `${number(r.utilization * 100)}%`);
    document.querySelector('.result-head').classList.toggle('fail', !r.passes);
    for (const [id, value] of Object.entries({ deflection: r.maximum, allowable: r.allowable, uniform: r.uniform, point: r.point })) set(id, `${number(value)} in`);
    set('span', `${number(r.span)} ft`);
    set('reaction', `${number(r.reaction)} kip`);
    set('limit-label', `L / ${number(values.ratio)}`);
    const path = Array.from({ length: 101 }, (_, i) => {
      const t = i / 100;
      return `${i ? 'L' : 'M'}${60 + 640 * t},${110 + (r.maximum ? r.at(t) / r.maximum * 75 : 0)}`;
    }).join(' ');
    const arrow = x => `<path d="M${x} 55V95m-5-7 5 7 5-7" fill="none" stroke="#6a8290" stroke-width="2"/>`;
    document.getElementById('diagram').innerHTML = `
      <line x1="60" y1="110" x2="700" y2="110" stroke="#8397a3" stroke-width="5"/>
      ${values.w > 0 ? Array.from({length:17}, (_, i) => arrow(60 + i * 40)).join('') : ''}
      ${values.P > 0 ? '<path d="M380 20V100m-7-10 7 10 7-10" fill="none" stroke="#203648" stroke-width="3"/>' : ''}
      <path d="M60 112l-13 22h26Z M700 112l-13 22h26Z" fill="#dce8ec" stroke="#627584"/>
      <circle cx="693" cy="140" r="4" fill="#627584"/><circle cx="707" cy="140" r="4" fill="#627584"/>
      <path d="${path}" fill="none" stroke="#008574" stroke-width="3"/>
      <text x="380" y="215" text-anchor="middle" fill="#008574" font-size="14">δmax = ${number(r.maximum)} in</text>
      <text x="60" y="164" text-anchor="middle" fill="#627584" font-size="13">A</text>
      <text x="700" y="164" text-anchor="middle" fill="#627584" font-size="13">B</text>
      <text x="380" y="246" text-anchor="middle" fill="#627584" font-size="13">L = ${number(r.span)} ft</text>`;
    scheduleAwatif(values, r, current);
  } catch (error) {
    set('error', error.message);
    document.getElementById('error').hidden = false;
    document.getElementById('output').hidden = true;
  }
}
form.addEventListener('input', update);
form.addEventListener('submit', event => event.preventDefault());
form.addEventListener('reset', () => setTimeout(update, 0));
update();
