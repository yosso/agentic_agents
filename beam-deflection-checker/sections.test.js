const assert = require('node:assert/strict');
const { properties, presets } = require('./sections.js');
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-10, `${actual} vs ${expected}`);
// I-section: outer rectangle minus two side voids, independent of the composite implementation.
const ibeam = properties('ibeam', { d: 8, b: 4, tw: 0.25, tf: 0.375 });
close(ibeam.area, 4 * 8 - (4 - 0.25) * (8 - 0.75));
close(ibeam.ix, (4 * 8 ** 3 - (4 - 0.25) * (8 - 0.75) ** 3) / 12);
close(ibeam.iy, (2 * 0.375 * 4 ** 3 + (8 - 0.75) * 0.25 ** 3) / 12);
close(ibeam.ixy, 0);
// A 2 x 2 x 1 L = 2x2 square minus upper-right unit square.
const angle = properties('angle', { b: 2, t: 1 });
close(angle.area, 3);
close(angle.cx, 5 / 6);
close(angle.cy, 5 / 6);
close(angle.ix, 11 / 12);
close(angle.iy, 11 / 12);
close(angle.ixy, -1 / 3);
close(angle.major, 5 / 4);
close(angle.minor, 7 / 12);
const doubled = properties('angle', { b: 4, t: 2 });
close(doubled.major, angle.major * 16);
for (const [type, items] of Object.entries(presets)) for (const item of items) assert.ok(properties(type, item).minor > 0);
for (const invalid of [{ b: 1, t: 1 }, { b: 2, t: -1 }, { b: NaN, t: 1 }]) assert.throws(() => properties('angle', invalid));
assert.throws(() => properties('ibeam', { d: 2, b: 2, tw: 0.25, tf: 1 }));
console.log('Section checks passed: area, centroid, principal inertias, scaling, presets, invalid dimensions.');
