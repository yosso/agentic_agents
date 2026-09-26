# OpenSeesPy pile example review

Reviewed `inputs/openseepy_pile.py` (the uploaded filename uses `openseepy`, not `opensees`). The source was not modified. Review comprised source inspection and isolated execution of the three parameter functions, extracted using Python's AST without importing/running the model. No full OpenSees analysis or numerical validation was performed.

## Model and workflow

The script demonstrates a static lateral pushover of one elastic pile on nonlinear soil springs. Geometry is hard-coded: 1 m above ground, 20 m embedded, 1 m diameter, 84 beam elements. It defines one homogeneous cohesionless soil with unit weight 17 kN/m³ and friction angle 36 degrees. It creates p–y lateral, t–z shaft, and nominal q–z tip parameters, assembles zero-length spring elements, and connects them to beam nodes using equalDOF constraints. A 3,500 kN horizontal head load is ramped through a Path time series.

This is a useful example of model assembly, not the project's layered-soil, multi-combination, depth-sizing routine. The [published OpenSeesPy example](https://openseespydoc.readthedocs.io/en/latest/src/pile.html) provides its context.

## Findings

| Finding | Source lines | Implication |
| --- | --- | --- |
| Conflicting unit comments | 406, 419 | Header says kN/m; another comment says N/mm. Geometry, soil conversions and E=25,000,000 are consistent with the intended kN/m framework. Establish one unit system explicitly; RSA raw N/N-m require conversion if kN/m is chosen. |
| Single-plane restraints despite 3D declarations | 472, 578–592 | Pile Y translation and X/Z rotations are fixed, preventing general Fy, Mx, and Mz response. Spring-side Z translation is fixed and tied to the embedded pile Z translation, restraining embedded axial movement. The present setup does not validate compression/uplift behavior through the intended t–z/q–z springs. |
| Pile/spring coordinate offset | 456, 568, 592 | Spring node 101 is at z=0, but its paired pile node 201 is at z=0.25 m. All corresponding pairs are shifted by one element length. Head node 285 is at z=21.25 m rather than the nominal 21 m. Use a common coordinate list. |
| Opposite depth conventions | 510, 521–523 | p–y uses depth L2-z; t–z uses z measured upward from the tip. Shaft effective stress is therefore assigned in the opposite direction to the p–y depth convention. Define a common ground datum and depth-below-ground calculation. |
| Tip material differs from stated intent | 540–541 | QzSimple1 is commented out and replaced by TzSimple1 with tip parameters. This does not establish the intended end-bearing and uplift response. |
| Homogeneous sand only | 480–500 and parameter functions | No workbook layer lookup, clay/rock parameter generation, or layered effective-overburden calculation. A single groundwater switch is not the workbook's per-pier water-table depth. |
| Section properties hard-coded | 608–623 | Area, inertias and torsional constant do not update when diameter changes. The section is elastic; it does not reproduce the VBA C/R section-stiffness updates. An additional torsional material is defined, but torsional rotation is restrained in this model. |
| Analysis status ignored | 692–704 | analyze() return code is discarded and results are printed regardless of success. Full-load attainment and convergence must be checked before accepting results. |
| Recorder scope differs from node creation | 654 | The reaction recorder requests nodes 1–85, but only fixed spring nodes 1–81 are created with the default geometry. Use actual created-node lists. |
| Spring tributary lengths need verification | 118–119, 352–353, 508–528 | Every spring receives a full element length, including endpoints. Establish consistent end tributary lengths and layer-boundary treatment, then check mesh sensitivity. |

The [PySimple1 documentation](https://openseespydoc.readthedocs.io/en/latest/src/PySimple1.html) specifies that its ultimate capacity is a nodal force, obtained from distributed resistance using tributary length. The [QzSimple1 documentation](https://openseespydoc.readthedocs.io/en/latest/src/QzSimple1.html) separately defines tip capacity and suction-controlled uplift. The [analyze documentation](https://openseespydoc.readthedocs.io/en/latest/src/analyze.html) identifies zero as success and a negative return as failure.

## Reproduced helper-function errors

- `get_pyParam(5, 17, 40, 1, .25, 1, 1, 1)` raises IndexError: the friction-angle interpolation loop accesses `ph[i+1]` at the last index. Out-of-range inputs also lack reliable handling.
- `get_tzParam(38, 1, 85, .25)` raises IndexError at the upper interpolation endpoint for the same reason.
- `get_pyParam(5, 17, 36, 1, .25, 2, 1, 1)` raises UnboundLocalError for `tan_2`: the Hansen branch uses variables assigned only in the API branch. Its later use of A also needs review.
- Default-branch helper calls at phi=36 returned numeric values. That confirms execution only, not correctness of the engineering formulas.

Two additional equations warrant independent checking: the extra 0.5 factor in the p–y y50 expression at line 225, and t–z z50=tult/kSIunits at line 378. As annotated, tult is a force while kSIunits is force/volume; their quotient is not a displacement. Resolve the intended stiffness normalization rather than copying these equations unchanged.

## Available outputs

| Output | Contents and use |
| --- | --- |
| pileDisp.out | Pseudo-time and node translations in directions 1/2/3; locate the head node explicitly and validate final load attainment. |
| reaction.out | Pseudo-time and global X reactions at requested fixed spring nodes; not a six-component pier-force envelope. |
| pileForce.out | Pseudo-time and beam global end-force responses; establish component ordering, axes, signs and end locations before extracting shear/moment extrema. |
| Nodedisplacements dictionary | Final nodeDisp results keyed by pile node ID, after the analysis attempt. |
| Nodereactions dictionary | Final nodeReaction results at pile nodes after reactions(); these are not a replacement for beam internal force outputs. |

Static recorder time is a load-stepping parameter, not physical dynamic time. Recorders are sampled every 0.5 while the analysis step is 0.05; do not assume the last recorded row is the final analysis state. The script has no structured success flag, source combination ID, controlling-force report, or allowable-deflection check. It also wipes the current OpenSees domain and writes fixed output filenames on import/execution, so it should be refactored before being imported into the app.

## Proposed adaptation

1. Keep the example as reference; build a callable model routine around the prepared pier/soil data classes.
2. Resolve workbook units, layer/model parameters, water table, section material data, head geometry, and support conditions.
3. Correct and independently test spring parameter functions, coordinate/depth conventions, constraints, tributary lengths, and tip behavior.
4. Establish a simple independently known benchmark, followed by a representative layered profile and mesh-convergence checks.
5. Apply complete RSA combination vectors with explicit reaction-to-applied-load sign/axis mapping. Implement the required biaxial, axial, and torsional behavior; a 3D model declaration alone is insufficient.
6. Return structured convergence status, attained load factor, top displacement, and signed shear/moment profiles with governing locations. Rebuild/reset state for independent combinations before adding the embedment-depth search.
