# Beam deflection checker

With Node.js 22 or newer and npm installed, run these commands from the workspace root:

```powershell
cd beam-deflection-checker
npm install
npm start
```

Open `http://127.0.0.1:3000`. `npm run dev` starts the same local server; refresh the browser after edits. Stop it with Ctrl+C. Restart any server running before the Awatif addition. Both start commands prepare the local Awatif assets automatically. Internet access is needed for installation; calculations then run locally. Opening `index.html` directly still provides formula results, but the Awatif check requires the local server.

Implements the simple-span deflection workflow in `../beam-optimization.md`: calculate span from geometry, enter member properties, and compare calculated deflection with an allowable value.

- Enter two support coordinates in feet; span is their straight-line distance.
- Enter E in ksi and bending-axis I in in⁴.
- Enter a full-span uniform load in kip/ft and/or a midspan point load in kip. Loads are nonnegative and act transversely in the same direction.
- Set the allowable deflection denominator. The default L/360 is a user-editable example, not a code compliance determination.
- Inputs immediately update the results. The plotted shape is exaggerated and normalized to the current maximum; compare numerical results across cases.

The model assumes a simply supported, prismatic, linear-elastic Euler–Bernoulli beam. Self-weight is not added automatically. It excludes shear deformation and all checks other than bending deflection.

With L in inches and w in kip/in, the midspan results are `5wL⁴/(384EI)` and `PL³/(48EI)`. Their sum is the maximum for the supported load cases. The default example gives 0.248276 in versus 0.666667 in allowable.

## Aluminum section inputs

Select **Aluminum I-beam** or **Aluminum equal-leg angle** under Member stiffness. Each includes three illustrative starting sizes and editable dimensions in inches. These are geometric examples, not supplier catalog designations. The section calculator sums nonoverlapping rectangles with the parallel-axis theorem; it omits fillets, corner radii, and flange taper. Use **Manual E and I** to enter verified catalog properties instead.

Selecting aluminum sets E to 10,000 ksi, which remains editable. This value is listed in [Titanium Industries' 6061 alloy data](https://titanium.com/alloys/aluminum-alloys/aluminum-alloy-6061/). Changing size or axis updates I automatically for both the formula and Awatif checks. I is read-only in section mode. Self-weight is still entered as part of the uniform load.

I-beams allow centroidal x-axis (parallel to flanges) or y-axis (parallel to web) bending. Equal-leg angles allow major u-axis (+45° from the horizontal leg) or minor v-axis (−45°) bending only. The sketch marks the selected axis. The load must be perpendicular to that axis and act through the shear center without torsion. General leg-aligned loading, coupled lateral deflection, and angle torsion are outside this planar model. The principal inertias are `(Ix + Iy)/2 ± sqrt(((Ix − Iy)/2)² + Ixy²)`.

## Independent Awatif check

The second panel calls the actual C++/WebAssembly solver from [Awatif](https://github.com/madil4/awatif), through `awatif-fem@1.0.1`'s `deformCpp` adapter. The npm package is deprecated by its publisher; this integration pins the inspected source and WASM release rather than tracking the evolving upstream application. `build.js` transpiles the upstream TypeScript adapter and copies the unmodified solver assets. The unused transitive mathjs dependency is overridden to 15.2.0 to avoid the advisories in the package's original dependency range.

The adapter creates 20 equal beam elements with a node at midspan, using inches and kips. Geometry is expressed in local beam coordinates to preserve the original transverse-load convention for diagonal or vertical spans. In-plane rotations are free at both supports; axial translation is fixed at A and free at B. Out-of-plane degrees of freedom are restrained. A unit axial area stabilizes the unloaded axial degrees of freedom and does not affect the uncoupled linear bending solution.

Uniform loading uses consistent nodal forces **and moments** on every element; the point load is applied at the middle node. Physical reactions subtract the applied nodal forces from Awatif's reported `K*u`. No formula deflections are supplied to Awatif. Orange markers plot its nodal displacements on the same scale as the formula curve.

The comparison reports absolute and relative differences, independent limit status, and reactions. Agreement means a difference of at most `max(1e-9 in, formula deflection × 1e-5)` (0.001% relative). A zero formula deflection has no percentage difference. Solver agreement is separate from passing the deflection limit. A loading or solver error shows “Awatif check unavailable” without treating formula results as an independent verification.

Run `npm test` to build and test both engines against uniform, point, combined, zero-load, changed-stiffness, and rotated-geometry cases, including reactions and mesh checks. Run `npm run test:browser` for the interactive checks (requires installed Google Chrome). Tests use port 31849.
