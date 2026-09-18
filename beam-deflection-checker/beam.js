/* Pure calculation functions. Units: ft, kip, ksi, in^4; output deflection: in. */
(function (root) {
  function calculate(v) {
    for (const key of ['ax', 'ay', 'bx', 'by', 'E', 'I', 'w', 'P', 'ratio']) {
      if (!Number.isFinite(v[key])) throw new Error('Enter a finite number in every field.');
    }
    const span = Math.hypot(v.bx - v.ax, v.by - v.ay);
    if (!(span > 0)) throw new Error('Support coordinates must define a nonzero span.');
    if (v.E <= 0 || v.I <= 0) throw new Error('Elastic modulus and moment of inertia must be greater than zero.');
    if (v.w < 0 || v.P < 0) throw new Error('Loads must be zero or positive (downward).');
    if (v.ratio < 1) throw new Error('The deflection limit denominator must be at least 1.');
    const L = span * 12, EI = v.E * v.I, w = v.w / 12;
    const uniform = 5 * w * L ** 4 / (384 * EI);
    const point = v.P * L ** 3 / (48 * EI);
    const maximum = uniform + point, allowable = L / v.ratio;
    const utilization = maximum / allowable;
    const reaction = (v.w * span + v.P) / 2;
    if (![L, EI, uniform, point, maximum, allowable, utilization, reaction].every(Number.isFinite) || EI === 0 || allowable === 0) {
      throw new Error('Inputs exceed the numerical range. Use smaller, physically reasonable values.');
    }
    // Symmetry places the maximum at L/2 for these two nonnegative load cases.
    function at(t) {
      const x = Math.min(t, 1 - t) * L;
      return w * x * (L ** 3 - 2 * L * x ** 2 + x ** 3) / (24 * EI)
        + v.P * x * (3 * L ** 2 - 4 * x ** 2) / (48 * EI);
    }
    return { span, uniform, point, maximum, allowable, utilization, reaction, passes: maximum <= allowable, at };
  }
  root.Beam = { calculate };
  if (typeof module !== 'undefined') module.exports = { calculate };
})(typeof globalThis !== 'undefined' ? globalThis : window);
