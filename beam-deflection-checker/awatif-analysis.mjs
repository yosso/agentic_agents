import { deformCpp } from './dist/awatif/deformCpp.js';

export function analyzeBeam(v, divisions = 20) {
  for (const key of ['ax', 'ay', 'bx', 'by', 'E', 'I', 'w', 'P', 'ratio']) {
    if (!Number.isFinite(v[key])) throw new Error('All inputs must be finite.');
  }
  const L = Math.hypot(v.bx - v.ax, v.by - v.ay) * 12;
  if (!(L > 0) || !Number.isFinite(L) || v.E <= 0 || v.I <= 0 || v.w < 0 || v.P < 0 || v.ratio < 1) {
    throw new Error('Invalid beam geometry, stiffness, load, or limit.');
  }
  if (!Number.isInteger(divisions) || divisions < 2 || divisions > 100 || divisions % 2) {
    throw new Error('Use an even mesh size between 2 and 100.');
  }
  // Local axes: x along the span, y transverse, z out of plane. This
  // matches the transverse-load convention for any entered orientation.
  const length = L / divisions;
  const nodes = Array.from({ length: divisions + 1 }, (_, i) => [i * length, 0, 0]);
  const elements = Array.from({ length: divisions }, (_, i) => [i, i + 1]);
  const supports = new Map(nodes.map((_, i) => [i,
    [i === 0, i === 0 || i === divisions, true, true, true, false],
  ]));
  const loads = new Map(nodes.map((_, i) => [i, [0, 0, 0, 0, 0, 0]]));
  const q = -v.w / 12;
  // Consistent beam load vector: [q*l/2, q*l^2/12, q*l/2, -q*l^2/12]
  // in [vy1, rz1, vy2, rz2]. End moments are essential for a true UDL.
  for (let i = 0; i < divisions; i++) {
    loads.get(i)[1] += q * length / 2;
    loads.get(i)[5] += q * length ** 2 / 12;
    loads.get(i + 1)[1] += q * length / 2;
    loads.get(i + 1)[5] -= q * length ** 2 / 12;
  }
  loads.get(divisions / 2)[1] -= v.P;
  const property = value => new Map(elements.map((_, i) => [i, value]));
  const elementInputs = {
    elasticities: property(v.E), momentsOfInertiaZ: property(v.I),
    // Unit axial area keeps the unloaded axial DOFs stable. It has no
    // influence on this uncoupled, linear transverse bending solution.
    areas: property(1),
  };
  const output = deformCpp(nodes, elements, { supports, loads }, elementInputs);
  const deflections = nodes.map((_, i) => {
    const values = output?.deformations?.get(i);
    if (!values || !values.every(Number.isFinite)) throw new Error('Awatif returned an invalid displacement.');
    return -values[1];
  });
  const maximum = Math.max(...deflections.map(Math.abs));
  // This Awatif version reports K*u. Physical support reactions are K*u - F.
  const reactions = [0, divisions].map(i => output?.reactions?.get(i)?.[1] - loads.get(i)[1]);
  const allowable = L / v.ratio;
  if (![maximum, allowable, ...reactions].every(Number.isFinite) || allowable <= 0) throw new Error('Awatif returned invalid results.');
  return { maximum, allowable, utilization: maximum / allowable, passes: maximum <= allowable, deflections, reactions, divisions };
}

export function compareResults(reference, result) {
  const difference = Math.abs(result.maximum - reference.maximum);
  const tolerance = Math.max(1e-9, Math.abs(reference.maximum) * 1e-5);
  return {
    difference, tolerance,
    percent: reference.maximum === 0 ? null : difference / Math.abs(reference.maximum) * 100,
    agrees: difference <= tolerance,
  };
}
