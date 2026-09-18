(function () {
  const form = document.getElementById('inputs');
  const type = document.getElementById('section-type');
  const preset = document.getElementById('section-preset');
  const axis = document.getElementById('section-axis');
  const fields = Object.fromEntries(['d', 'b', 'tw', 'tf', 't'].map(key => [key, document.getElementById(`section-${key}`)]));
  let previousType = 'manual', previousPreset = '';
  form.addEventListener('input', event => {
    if (Object.values(fields).includes(event.target)) preset.value = 'custom';
  });
  window.updateSection = function () {
    const selected = type.value;
    const automatic = selected !== 'manual';
    document.getElementById('section-options').hidden = !automatic;
    form.elements.I.readOnly = automatic;
    if (selected !== previousType) {
      previousType = selected;
      if (automatic) {
        preset.replaceChildren(...Sections.presets[selected].map((item, i) => new Option(item.name, String(i))), new Option('Custom dimensions', 'custom'));
        axis.replaceChildren(...(selected === 'ibeam'
          ? [new Option('x · parallel to flanges', 'ix'), new Option('y · parallel to web', 'iy')]
          : [new Option('u · major principal axis (+45°)', 'major'), new Option('v · minor principal axis (−45°)', 'minor')]));
        preset.value = '0';
        previousPreset = '';
        form.elements.E.value = '10000';
      }
    }
    if (!automatic) return;
    for (const [key, field] of Object.entries(fields)) {
      const relevant = selected === 'ibeam' ? key !== 't' : ['b', 't'].includes(key);
      field.closest('label').hidden = !relevant;
      field.disabled = !relevant;
    }
    document.getElementById('section-b-label').textContent = selected === 'ibeam' ? 'Flange width, b (in)' : 'Equal leg length, b (in)';
    document.getElementById('angle-note').hidden = selected !== 'angle';
    if (preset.value !== previousPreset) {
      previousPreset = preset.value;
      if (preset.value !== 'custom') {
        for (const [key, value] of Object.entries(Sections.presets[selected][Number(preset.value)])) {
          if (fields[key]) fields[key].value = value;
        }
      }
    }
    // Clear the old stiffness before validation, so invalid geometry cannot leave a usable stale I.
    form.elements.I.value = '';
    document.getElementById('section-properties').textContent = '';
    document.getElementById('section-sketch').replaceChildren();
    const dimensions = Object.fromEntries(Object.entries(fields).map(([key, field]) => [key, field.value === '' ? NaN : Number(field.value)]));
    const p = Sections.properties(selected, dimensions);
    form.elements.I.value = p[axis.value];
    const fmt = value => value.toLocaleString('en-US', { maximumSignificantDigits: 6 });
    document.getElementById('section-properties').textContent = `Area: ${fmt(p.area)} in² · Ix: ${fmt(p.ix)} in⁴ · Iy: ${fmt(p.iy)} in⁴` +
      (selected === 'angle' ? ` · Iu: ${fmt(p.major)} in⁴ · Iv: ${fmt(p.minor)} in⁴` : '');
    const { d, b, tw, tf, t } = dimensions;
    const height = selected === 'ibeam' ? d : b;
    const scale = 130 / Math.max(b, height);
    const x = value => 35 + value * scale;
    const y = value => 175 - value * scale;
    const polygon = selected === 'ibeam'
      ? [[0, 0], [b, 0], [b, tf], [(b + tw) / 2, tf], [(b + tw) / 2, d - tf], [b, d - tf], [b, d], [0, d], [0, d - tf], [(b - tw) / 2, d - tf], [(b - tw) / 2, tf], [0, tf]]
      : [[0, 0], [b, 0], [b, t], [t, t], [t, b], [0, b]];
    const theta = selected === 'angle' ? (axis.value === 'major' ? Math.PI / 4 : -Math.PI / 4) : (axis.value === 'ix' ? 0 : Math.PI / 2);
    const dx = 75 * Math.cos(theta), dy = -75 * Math.sin(theta);
    document.getElementById('section-sketch').innerHTML = `<polygon points="${polygon.map(([a, c]) => `${x(a)},${y(c)}`).join(' ')}" fill="#dceae7" stroke="#008574" stroke-width="2"/><line x1="${x(p.cx) - dx}" y1="${y(p.cy) - dy}" x2="${x(p.cx) + dx}" y2="${y(p.cy) + dy}" stroke="#bd6b21" stroke-width="2" stroke-dasharray="5 3"/><circle cx="${x(p.cx)}" cy="${y(p.cy)}" r="3" fill="#bd6b21"/><text x="15" y="215" fill="#627584" font-size="11">Dashed line: selected centroidal bending axis</text>`;
  };
})();
