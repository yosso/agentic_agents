# Drilled Pier Design
## 1. Goal
Size the embedment depth and obtain the maximum shear and moment on the drilled pier from the applied loading

## 2. How it is currentlly done
1. We obtain all of the load cases for each pier
2. We use a program called Allpile to obtain the depth which will keep the pier deflection below the deflection criteria
3. We use the same program to obtain the maximum shear and moment seen by the concrete
4. We next take the depth and loading and place into an excel worksheet to track and create the data required to create the drawings.

## 3. How will I do it?

OpenSeesPy is the planned analysis engine for the pile / drilled pier / caisson workflow. Excel supplies the design inputs and receives the results. The VBA workbook serves as a reference for input organization and optional comparison cases; implementing the new workflow does not depend on repairing or porting its solver.

This overview shows the main functions and their outputs. Ovals represent functions; rectangles represent data. Load extraction, controlling-load reporting, and input preparation are implemented in the [reaction viewer](rsa-reaction-viewer/README.md). OpenSeesPy analysis and result export to Excel remain planned.

```mermaid
flowchart TD
    INPUTS(["read_mapping()"])
    MAPPING["Footing mappings<br/>Footing mark, expected quantity,<br/>Robot filename, support-node group"]
    LOADS(["read_rsa_loads()<br/>Implemented by read_robot.ps1"])
    LOAD_DATA["Extracted combination reactions<br/>Footing, model, group, node, combination,<br/>Fx, Fy, Fz, Mx, My, Mz; actual node/support counts"]
    CHECK(["assess_group()"])
    CHECK_DATA["Mapping validation report<br/>Expected versus actual quantities,<br/>source cell, mismatch and read-error details"]
    CONTROL(["controlling_combinations()"])
    CONTROL_DATA["Five controlling checks per footing group<br/>Shear, bending, torsion, compression, uplift<br/>Governing node/combination and coincident reactions"]
    EXCEL["Excel design inputs<br/>Footing-to-boring assignments, diameters,<br/>depths, allowable deflection, and soil tables"]
    ASSEMBLE(["prepare_pier_designs()"])
    PIER_DATA["Prepared pier inputs and validation findings<br/>Assigned soil layers, source cells, fixed diameter,<br/>all extracted combination reactions, missing/invalid inputs"]
    SIZE(["size_embedment_depth() — planned"])
    ANALYSIS_DATA["Depth-sizing results<br/>Accepted depth, deflection, analysis responses,<br/>governing combination, and success/failure status"]
    FORCES(["summarize_pier_results() — planned"])
    RESULT_DATA["Pier results table<br/>Diameter, depth, maximum shear/moment,<br/>governing combinations/locations, and status"]
    EXPORT(["export_results_to_excel() — planned"])
    WORKBOOK["Updated Excel tracking and drawing data"]

    INPUTS --> MAPPING
    MAPPING --> LOADS
    LOADS --> LOAD_DATA
    MAPPING --> CHECK
    LOAD_DATA --> CHECK
    CHECK --> CHECK_DATA
    LOAD_DATA --> CONTROL
    CONTROL --> CONTROL_DATA
    LOAD_DATA --> ASSEMBLE
    CHECK_DATA --> ASSEMBLE
    EXCEL --> ASSEMBLE
    ASSEMBLE --> PIER_DATA
    PIER_DATA -->|After input and model validation| SIZE
    SIZE --> ANALYSIS_DATA
    ANALYSIS_DATA --> FORCES
    FORCES --> RESULT_DATA
    RESULT_DATA --> EXPORT
    EXPORT --> WORKBOOK
```

The input workbook is `inputs/DVLP_FTG_MTL_QTY.xlsm`. The current mapping is `INPUT TABLES!RSA_GROUP_MAPPING`, with these columns:

| Input | Purpose |
| --- | --- |
| MARK | Footing callout, such as A, B, or C |
| FOOTING QTY | Expected quantity to compare with the Robot group |
| GROUP NAME | Support-node group in the specified Robot model |
| ROBOT FILE NAME | Source model filename/path; different mappings may use different models |

`read_mapping()` reads the saved workbook. Relative Robot paths are resolved from the workbook folder, and `.rtd` is added when omitted. `read_rsa_loads()` is the workflow name for the extraction implemented in `read_robot.ps1`: it opens each mapped model, obtains group membership from Robot, and reads **load combinations only**. Individual load cases are excluded even if their numbers are entered in the selection field. The current reader supports ordinary linear combinations; unsupported combination types are flagged for further implementation.

Each extracted row retains the footing mark, full model path, group, node, combination number/name, and all six global reaction components. Raw API values are retained in N and N-m; the viewer can display kip/kip-ft or kN/kN-m. Components from different nodes or combinations are never combined into a fabricated load vector, and reactions are not summed across supports or models. The reader uses available, current results without recalculating or saving the model; missing or out-of-date results are reported.

`assess_group()` compares Excel's expected quantity with the actual group-node and support counts. Missing models/groups, non-support nodes, failed reads, and quantity mismatches are flagged. The viewer highlights affected rows and identifies the Excel source cell, expected value, actual value, and difference. Unavailable counts are not treated as zero, and the workbook is not automatically corrected.

`controlling_combinations()` reports the following checks separately for each footing callout across its extracted nodes/models:

| Check | Governing criterion |
| --- | --- |
| Maximum shear | Largest `sqrt(Fx² + Fy²)` |
| Maximum bending moment | Largest `sqrt(Mx² + My²)` |
| Maximum torsion | Largest `abs(Mz)`, retaining the signed Mz in the associated reaction row |
| Maximum compression | Largest positive Fz |
| Maximum uplift | Most negative Fz, displayed with its negative sign |

Global Z is treated as vertical; positive Fz denotes compression and negative Fz denotes uplift. Each check identifies its controlling combination, node, model/group, and all six coincident reactions. Different checks may be controlled by different combinations. Exact ties show their count and one deterministic source; absent compression/uplift is reported as “None found.” These are load extremes, not proof of the governing pier deflection or capacity condition. All extracted combination rows are retained for input preparation and subsequent analysis.

`prepare_pier_designs()` joins each footing callout to `INPUT TABLES!tblBoringAssignment`, which supplies its boring, anchor-pattern-based diameter, minimum embedment, water-table depth, and allowable deflection. Soil layers come from the `tblSOIL_BORING_*` tables on `GEOTECH PARAMETERS`: `_03` identifies boring 3 (`SB3`), and the BORING/NUMBER cell above the table is cross-checked. Disagreements, missing/ambiguous assignments, invalid layers, missing numeric inputs, and soil schema mismatches are reported with source locations. The viewer carries extraction and quantity errors into this validation report.

`prepare_pier_designs()` reads the named table `tblDEFLECTION_SIZE` on `DP WORKFLOW and GUIDELINES` and matches the fixed pier diameter to exactly one row. That row supplies minimum embedment depth and both tip/non-recoverable deflection limits, with source cells retained in the report. Assignment-table differences are flagged; the diameter table supplies the minimum depth. The confirmed allowable top-of-pier deflection is `NON-RECOVERABLE (IN)` from the matched diameter row. `TIP DEF (IN)` is retained for reference. Missing or duplicate diameter matches block validation.

`size_embedment_depth()` builds and runs the OpenSeesPy models using the specified diameter, checks top deflection against the Excel table value for the applicable load combinations, and adjusts depth within the configured search limits. The diameter stays fixed during depth sizing. It returns the first passing trial depth or an explicit failure / unresolved status. `summarize_pier_results()` extracts the shear and moment envelopes for accepted designs and carries unsuccessful pier statuses into the results table.

The depth search settings still need to be defined. Specify whether deflection is checked by direction or as a resultant.

Section stiffness is calculated from the section code and its geometry/material inputs: `C` for circular sections and `R` for rectangular sections. EI is never a fixed user input in this workflow. Circular sections use the specified diameter; rectangular sections require width and depth. The OpenSeesPy implementation must define and validate how the calculated section stiffness is updated during analysis.

Before implementing `size_embedment_depth()` and `summarize_pier_results()`, research and validate how OpenSeesPy provides the required outputs for the selected pier model and element types:

- Select and validate the pier elements, soil interaction model, section stiffness assumptions, and boundary conditions against the intended loading and soil profiles.
- How to retrieve top-of-pier displacement and identify the relevant directions.
- How to retrieve shear and moment along the pier, including output component order, sign conventions, coordinate systems, and response locations.
- How output values relate to the model's unit system and individual load combinations.
- How to identify analysis success, nonconvergence, and incomplete results.

The output of this research will be a documented mapping from OpenSeesPy responses to the workflow's result fields, supported by a small benchmark with independently known deflection, shear, and moment. The analysis-output fields shown above are proposed requirements until this validation is complete.

The existing VBA workbook, `inputs/TEST_SUB_LAT_PILE_PY.xlsm`, provides an optional comparison case and a six-column response layout. See the [workbook inspection](workbook-review/inspection.md) for its input/output mapping and extracted-code findings. Resolve its unit, argument, convergence, and summary-formula issues only if its results will be used for comparison. Begin OpenSeesPy validation with an independently known benchmark, then a representative layered-soil pier case with a trusted comparison solution.


### Soil table schema

Each `GEOTECH PARAMETERS!tblSOIL_BORING_*` table has a header row followed by one row per layer, ordered from the first layer downward. The table suffix identifies the boring. The confirmed 12-column layout is:

| Column | Parameter | Units | Prepared field |
| --- | --- | --- | --- |
| 1 | Starting depth | ft | `start` |
| 2 | Ending depth | ft | `end` |
| 3 | Soil model (clay, rock, sand, etc.) | None | `model` |
| 4 | Soil density | lb/ft^3 | `density` |
| 5 | Ultimate cohesion | kip/ft^2 | `cohesion_ultimate` |
| 6 | Factored cohesion | kip/ft^2 | `cohesion_factored` |
| 7 | Friction angle for non-cohesive soils | degrees | `friction_angle` |
| 8 | Static modulus of subgrade reaction | lb/in^3 | `k_static` |
| 9 | Cyclic modulus of subgrade reaction | lb/in^3 | `k_cyclic` |
| 10 | Factored static modulus (`fKh`) | lb/in^3 | `k_static_factored` |
| 11 | Epsilon 50 | unitless | `e50` |
| 12 | Factored epsilon 50 | unitless | `e50_factored` |

Epsilon 50 is the soil strain corresponding to 50% of the maximum principal stress difference in an undrained compression laboratory test on cohesive soils. Values are retained as supplied, without percentage or unit conversion. Extraction maps headers to fields and retains raw values and source cells. Missing cyclic values remain unavailable; applicability must be resolved before analysis.

START and END are depths in feet measured positive downward from the top of the hole (zero). The first data row starts at zero; each subsequent row is a deeper layer whose START equals the preceding row's END. END must exceed START. Negative depths, a nonzero first START, and gaps or overlaps are reported with source cells. Rows remain in worksheet order.

The saved tables match the corrected 12-column schema. Column 10 (`fKh`) supplies the factored static modulus; no factored cyclic modulus is required. The descriptive header `FACTORED MODULUS OF SUBGRADE REACTION (STATIC)` is also accepted for that field. Missing fields are reported explicitly. The workbook is not modified by extraction.


### Python soil parameter type

`rsa-reaction-viewer/soil_parameters.py` defines `SoilParameters`, a dataclass with one named, typed field for each of the 12 columns above. Each `SoilLayer.properties` holds this object; the layer also retains `source_row`, `cells`, and `raw_properties` for traceability. Each boring's `SoilProfile.layers` preserves worksheet order.

```python
layer = prepared.soil_profiles[0].layers[0]
soil = layer.properties
start_depth_ft = soil.start
static_modulus_lb_in3 = soil.k_static
factored_static_modulus_lb_in3 = soil.k_static_factored
source_cell = layer.cells["k_static_factored"]
```

Numeric fields can be `None` when missing or invalid, so all findings can still be reported. A missing model is an empty string. The class is immutable and takes keyword arguments to avoid mixing up similarly named parameters. Extraction performs validation; creating an instance alone does not establish validity. JSON exports retain the existing `properties` object and field names, and the report retains the same source values and units.


### OpenPile single-pier CLI

The [OpenPile CLI](openpile-cli/README.md) consumes the prepared-input JSON and a separate settings file. `validate` checks the selected footing, exact node/combination, source units, layer coverage, material properties, and explicit soil-model/load-direction choices. Its output is a traceable set of converted inputs and validation findings. `run` uses those checks before building a solid circular pier and running one 2D analysis with API clay or API sand springs. Its output includes displacement, force, and reaction CSVs, a solver log, and a JSON summary.

The settings select a trial embedment, one lateral plane, material stiffness, constitutive models, and signed mapping of the coincident RSA reaction vector. Soil depths are converted to negative elevations. This first version uses a free head and an axial tip restraint. It does not size embedment automatically or analyze torsion or axial soil capacity. Loaded displacement is reported separately from the workbook's non-recoverable deflection limit; a complete pier acceptance check remains future work.


### OpenSeesPy alternative CLI

The [OpenSeesPy CLI](openseespy-cli/README.md) provides the same `validate`/`run` workflow for a single selected pier and reaction vector. It shares input validation and unit conversion with OpenPile, then builds a 2D elastic beam with tributary-length-scaled PySimple1 springs. Extra settings define load increments, convergence tolerance, water unit weight, drag ratio, and Linear/PDelta transformation. The first version supports monotonic static clay/sand response only.

Outputs include traceable analysis inputs, spring parameters, displacements, local element end forces, support reactions, convergence history and a summary. The solver checks the return code at every load step and requires the full target load. The two libraries use different spring backbones; agreement is a comparison to investigate rather than an assumed acceptance criterion. The non-recoverable deflection and complete pier design checks remain unresolved.

### Batch deflection and embedment app

The [opensee-analysis app](opensee-analysis/README.md) now integrates prepared footing inputs and a reviewed settings template with the OpenSeesPy CLI. It selects all tied extreme coincident load vectors, runs both lateral planes, and increases depth from the workbook minimum by a configurable increment until the configured head-displacement check passes or the depth/soil-coverage limit is reached. It retains each trial and reports accepted depths, governing cases, shear/moment envelopes and failures. Directional and resultant checks are available. This implements a loaded elastic displacement screen; residual deformation and complete design acceptance remain unresolved. Excel result write-back remains planned. Current cohesion input units are psf, and plain numeric workbook E50/FE50 percentages are converted to fractions during preparation.
