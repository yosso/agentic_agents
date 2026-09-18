import assert from 'node:assert/strict';
import beam from './beam.js';
import sections from './sections.js';
import { analyzeBeam, compareResults } from './awatif-analysis.mjs';
const base = { ax: 0, ay: 0, bx: 20, by: 0, E: 29000, I: 500, w: 1, P: 0, ratio: 360 };
function close(actual, expected, label) {
  assert.ok(Math.abs(actual - expected) <= Math.max(1e-9, Math.abs(expected) * 1e-7), `${label}: ${actual} vs ${expected}`);
}
for (const [name, override] of [
  ['uniform', {}], ['point', { w: 0, P: 10 }], ['combined', { P: 10 }],
  ['zero', { w: 0, P: 0 }], ['over limit', { w: 10 }],
  ['diagonal', { ax: 1, ay: 2, bx: 13, by: 18 }],
  ['vertical', { bx: 0, by: 20 }], ['reversed', { ax: 20, bx: 0 }],
  ['different stiffness', { E: 1600, I: 1200, bx: 12, w: 0.2, P: 2 }],
]) {
  const values = { ...base, ...override };
  const reference = beam.calculate(values);
  const result = analyzeBeam(values);
  close(result.maximum, reference.maximum, `${name} maximum`);
  result.reactions.forEach(value => close(value, reference.reaction, `${name} reaction`));
  result.deflections.forEach((value, i) => close(value, reference.at(i / result.divisions), `${name} node ${i}`));
  assert.equal(result.passes, reference.passes, `${name} limit`);
  assert.equal(compareResults(reference, result).agrees, true);
  console.log(`${name}: formula ${reference.maximum.toFixed(9)} in; Awatif ${result.maximum.toFixed(9)} in`);
}
for (const divisions of [2, 10, 40]) close(analyzeBeam(base, divisions).maximum, beam.calculate(base).maximum, `mesh ${divisions}`);
assert.equal(compareResults({ maximum: 1 }, { maximum: 1.1 }).agrees, false);
assert.equal(compareResults({ maximum: 0 }, { maximum: 0 }).percent, null);
assert.throws(() => analyzeBeam({ ...base, E: 0 }));
assert.throws(() => analyzeBeam(base, 3));
console.log('Awatif checks passed: deflections, reactions, full nodal shape, mesh sizes, geometry, and agreement detection.');
for (const [type, presets] of Object.entries(sections.presets)) {
  for (const preset of presets) {
    const properties = sections.properties(type, preset);
    for (const axis of type === 'ibeam' ? ['ix', 'iy'] : ['major', 'minor']) {
      const values = { ...base, E: 10000, I: properties[axis], P: 2 };
      close(analyzeBeam(values).maximum, beam.calculate(values).maximum, `${preset.name} ${axis}`);
    }
  }
}
console.log('Both solvers agree for all aluminum examples and supported bending axes.');
