(function (root) {
  const presets = {
    ibeam: [
      { name: 'Example I · 6 × 3 in', d: 6, b: 3, tw: 0.25, tf: 0.375 },
      { name: 'Example I · 8 × 4 in', d: 8, b: 4, tw: 0.25, tf: 0.375 },
      { name: 'Example I · 10 × 5 in', d: 10, b: 5, tw: 0.375, tf: 0.5 },
    ],
    angle: [
      { name: 'Example L · 2 × 2 × ¼ in', b: 2, t: 0.25 },
      { name: 'Example L · 3 × 3 × ¼ in', b: 3, t: 0.25 },
      { name: 'Example L · 4 × 4 × ⅜ in', b: 4, t: 0.375 },
    ],
  };
  function properties(type, dimensions) {
    const keys = type === 'ibeam' ? ['d', 'b', 'tw', 'tf'] : type === 'angle' ? ['b', 't'] : [];
    if (!keys.length) throw new Error('Select an I-beam or equal-leg angle.');
    if (keys.some(key => !Number.isFinite(dimensions[key]) || dimensions[key] <= 0)) throw new Error('Section dimensions must be finite and greater than zero.');
    let rectangles;
    const { d, b, tw, tf, t } = dimensions;
    if (type === 'ibeam') {
      if (2 * tf >= d || tw >= b) throw new Error('I-beam needs depth > 2 × flange thickness and flange width > web thickness.');
      rectangles = [[b, tf, b / 2, tf / 2], [tw, d - 2 * tf, b / 2, d / 2], [b, tf, b / 2, d - tf / 2]];
    } else {
      if (t >= b) throw new Error('Angle thickness must be smaller than the leg length.');
      rectangles = [[b, t, b / 2, t / 2], [t, b - t, t / 2, (b + t) / 2]];
    }
    const area = rectangles.reduce((sum, [w, h]) => sum + w * h, 0);
    const cx = rectangles.reduce((sum, [w, h, x]) => sum + w * h * x, 0) / area;
    const cy = rectangles.reduce((sum, [w, h, , y]) => sum + w * h * y, 0) / area;
    let ix = 0, iy = 0, ixy = 0;
    for (const [w, h, x, y] of rectangles) {
      ix += w * h ** 3 / 12 + w * h * (y - cy) ** 2;
      iy += h * w ** 3 / 12 + w * h * (x - cx) ** 2;
      ixy += w * h * (x - cx) * (y - cy);
    }
    const radius = Math.hypot((ix - iy) / 2, ixy);
    const major = (ix + iy) / 2 + radius;
    const minor = (ix + iy) / 2 - radius;
    if (![area, cx, cy, ix, iy, ixy, major, minor].every(Number.isFinite) || minor <= 0) throw new Error('Section dimensions exceed the numerical range.');
    return { area, cx, cy, ix, iy, ixy, major, minor };
  }
  root.Sections = { presets, properties };
  if (typeof module !== 'undefined') module.exports = root.Sections;
})(globalThis);
