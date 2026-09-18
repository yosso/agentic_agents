const assert = require('node:assert/strict');
const { calculate } = require('./beam.js');
const base = { ax: 0, ay: 0, bx: 20, by: 0, E: 29000, I: 500, w: 1, P: 0, ratio: 360 };
const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-10, `${a} != ${b}`);
const uniform = calculate(base);
close(uniform.maximum, 0.2482758620689655);
close(uniform.allowable, 2 / 3);
close(uniform.reaction, 10);
close(uniform.at(0), 0);
close(uniform.at(1), 0);
close(uniform.at(0.5), uniform.maximum);
const point = calculate({ ...base, w: 0, P: 10 });
close(point.maximum, 0.1986206896551724);
close(point.at(0.5), point.maximum);
const both = calculate({ ...base, P: 10 });
close(both.maximum, uniform.maximum + point.maximum);
close(both.at(0.2), both.at(0.8));
close(calculate({ ...base, bx: 3, by: 4 }).span, 5);
close(calculate({ ...base, w: 0 }).maximum, 0);
assert.equal(uniform.passes, true);
assert.equal(calculate({ ...base, w: 10 }).passes, false);
for (const override of [{ bx: 0 }, { E: 0 }, { I: -1 }, { w: -1 }, { P: -1 }, { ratio: 0 }, { ax: NaN }, { bx: Infinity }, { E: 1e308, I: 1e308 }]) {
  assert.throws(() => calculate({ ...base, ...override }));
}
console.log('Calculation checks passed: reference values, superposition, supports, symmetry, geometry, limits, and invalid inputs.');
