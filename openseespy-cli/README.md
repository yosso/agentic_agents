# OpenSeesPy pier CLI

Command-line application for single-pier analysis using OpenSeesPy. It reads prepared pier data and an analysis settings file, including an `opensees` solver-controls block. Python 3.12 and OpenSeesPy 3.8.0.0 have been tested on Windows.

From the repository root in PowerShell:

```powershell
python -m venv openseespy-cli/.venv
openseespy-cli/.venv/Scripts/python -m pip install -r openseespy-cli/requirements.txt

openseespy-cli/.venv/Scripts/python openseespy-cli/cli.py validate --inputs openseespy-cli/examples/prepared.json --settings openseespy-cli/examples/settings.json --output openseespy-cli/results/my-validation
openseespy-cli/.venv/Scripts/python openseespy-cli/cli.py run --inputs openseespy-cli/examples/prepared.json --settings openseespy-cli/examples/settings.json --output openseespy-cli/results/my-run
```

Use a new output folder for each command. `validate` does not require OpenSeesPy. Exit codes are 0 for success, 2 for invalid inputs, and 3 for solver failure. The included data is synthetic, not a project design.

## Project data and settings

To create settings with a desktop form, run `python pile-settings-builder/app.py` from the repository root. The [pile settings builder](../pile-settings-builder/README.md) reads prepared pier inputs or raw viewer reaction results, lets you select a footing/reaction and configure materials and soil models, and saves the settings JSON. Prepared inputs support full CLI validation; raw reaction results produce drafts.

Export prepared JSON from the viewer or use its preparation command:

```powershell
python rsa-reaction-viewer/pier_designs.py --reactions rsa-reaction-viewer/live-results.json --output rsa-reaction-viewer/prepared-inputs.json
```

The CLI reads two separate JSON files:

| Argument | File contents | Source |
| --- | --- | --- |
| `--inputs` | Footing assignments, pier diameter, soil layers, water depth, and extracted RSA reactions | Exported by the viewer or the preparation command above |
| `--settings` | Which pier and reaction to analyze, plus the material and analysis choices | A settings file that you edit for the project |

For `--inputs`, use the path to the generated `rsa-reaction-viewer/prepared-inputs.json`. Create your project settings by copying `openseespy-cli/examples/settings.json` to a separate file, such as `openseespy-cli/project-settings.json`, and replacing the demonstration values. Here, **reviewed settings** means you have checked that those values describe the intended project analysis; it does not refer to a separate approval step in the software.

| Settings field | What you choose |
| --- | --- |
| `footing` | The footing callout to analyze, matching the prepared file |
| `reaction.model`, `.group`, `.node`, `.case` | The exact RSA model path/name, support group, node ID, and load-combination ID for one extracted reaction row; `case` here identifies a combination |
| `plane` | `X` for FX/MY with FZ, or `Y` for FY/MX with FZ |
| `material.E_psi` | The material's modulus of elasticity E, in psi; converted to kPa internally |
| `embedment_ft` | The trial pier depth in feet |
| `mesh_size_ft` | The maximum beam-element length in feet |
| `load_signs` | +1 or -1 for each load component's mapping into the solver's axes |
| `soil_models` | Which supported soil model and parameter fields to use for each soil label |

Pier diameter is read from the prepared workbook data, so it is not entered again in the settings. The remaining settings for this OpenSeesPy CLI are:

| Settings field | Meaning in this CLI |
| --- | --- |
| `material.unit_weight_pcf` | Positive material unit weight in lb/ft³ retained in the input record; self-weight loading is not applied |
| `material.poisson_ratio` | Value from zero to less than 0.5, retained in the input record; not used by the Euler-Bernoulli formulation |
| `boundary` | Currently must be `free_head_axially_fixed_tip`: only vertical translation at the pile tip is restrained |
| `max_iterations` | Positive integer limiting Newton iterations per load step |
| `opensees` | OpenSeesPy load-step, convergence, water-weight, drag and transformation settings described below |

Each entry in `soil_models` must match a soil label in the prepared data. `model: "API_clay"` selects the clay parameter conversion for OpenSees `PySimple1` soil type 1; supply `cohesion` (`cohesion_ultimate` or `cohesion_factored`), `strain` (`e50` or `e50_factored`), `J` (0.25 to 0.5), and `kind: "static"`. `model: "API_sand"` selects soil type 2; supply `modulus` (`k_static` or `k_static_factored`) and `kind: "static"`. These names are settings labels in our CLI, not OpenSeesPy class names. The soil-spring section below describes their conversion to `PySimple1` parameters.

After creating and editing `project-settings.json`, validate the project inputs with:

```powershell
openseespy-cli/.venv/Scripts/python openseespy-cli/cli.py validate `
  --inputs rsa-reaction-viewer/prepared-inputs.json `
  --settings openseespy-cli/project-settings.json `
  --output openseespy-cli/results/project-validation
```

This command checks the inputs and writes a report; it does not run an analysis. To analyze them, use `run` instead of `validate` and specify another new output folder.

This CLI uses `rsa-reaction-viewer/pile_analysis_inputs.py` to check the prepared data and convert units before building the OpenSeesPy model. An error affecting the selected footing, or an error recorded without a footing assignment, prevents the run. Errors assigned only to other footings are retained in the report. Missing water depth, invalid strain values, unsupported soil-model choices, or a reaction selection that does not identify exactly one row must be resolved before analysis.

The example settings already include this `opensees` block. Keep it in your project settings and review its values:

```json
"opensees": {
  "load_steps": 20,
  "energy_tolerance_lbf_ft": 7.375621492772653e-08,
  "water_unit_weight_pcf": 62.4492862753314,
  "drag_ratio": 0,
  "transformation": "Linear"
}
```

Material and water unit weights are entered in lb/ft³ (`unit_weight_pcf` and `water_unit_weight_pcf`); energy tolerance is entered in lbf-ft (`energy_tolerance_lbf_ft`). The CLI converts these to kN/m³ and kN-m internally. Legacy metric keys are still accepted; supply exactly one unit variant for each quantity. Converted example defaults preserve the previous physical values.

`transformation` accepts `Linear` or `PDelta`. Newton iterations use an energy-increment convergence test and the common `max_iterations` limit per step. A failed step aborts without issuing successful response tables. There is no automatic algorithm switching or step-size reduction. The full load factor must reach one.

The base soil mappings retain the names `API_clay` and `API_sand` to select the strength/stiffness inputs. Here they generate **OpenSees PySimple1 approximations**. Only `kind: "static"` is accepted. This is a monotonic push with no unloading or cycle history. The `inputs/openseepy_pile.py` learning example is not imported or modified.

## Model and units

The pile is a solid circular elastic Euler-Bernoulli beam, with A = pi D^2/4 and I = pi D^4/64. E is supplied as `material.E_psi` in psi and converted internally using 1 psi = 6.894757293168 kPa. Legacy `material.E_kpa` inputs are also accepted; supply exactly one modulus field. The example value of approximately 4,351,132 psi preserves the original 30,000,000 kPa stiffness. Pile nodes use global X for lateral displacement, global Y for vertical displacement, and Rz for rotation. Ground level is Y=0; workbook depth becomes negative Y in meters. Only vertical translation at the tip is fixed; lateral resistance comes from soil springs. Head translations and rotation are free. No self-weight loads, cracking, reinforcement, axial soil springs, torsion, or group interaction are included. Material unit weight and Poisson ratio remain in the common input record but do not enter this elastic beam formulation.

For plane X the selected coincident loads are FX, MY, FZ; for plane Y they are FY, MX, FZ. The explicit sign multipliers must be reviewed for each RSA reaction convention. The common converted Py/Pz/Mx vector becomes OpenSees global Fx/Fy/Mz with the same handedness. Positive axial force is upward. Do not reuse example signs as unreviewed project defaults.

This CLI uses kN and m internally; OpenSeesPy itself accepts consistent unit systems. This CLI converts ft to m, lb/ft^3 to kN/m^3, lb/ft^2 to kPa, lb/in^3 to kN/m^3, and N/N-m to kN/kN-m. Strain remains a unitless fraction. The shared adapter retains the existing minimum total-soil-unit-weight check of 10 kN/m^3.

## Soil springs

Mesh nodes include all layer interfaces and the water table within the pile. Each beam interval contributes two half-length soil springs, one to each end node. Properties are evaluated at the midpoint of each half interval. At a layer interface, separate springs retain the properties on each side. The tributary lengths sum to the full embedment, including head and tip half intervals.

Effective vertical stress is integrated through the supplied layers using total unit weight above water and total minus water unit weight below it. No surcharge or capillary effects are assumed. This layered-stress treatment and the selected constitutive model require review for the site.

- Clay: `pult_per_length = min(9 Su D, (3 Su + sigma_effective) D + J Su z)` and `y50 = 2.5 epsilon50 D`. Su, epsilon50, and J come from the explicitly selected fields/settings.
- Sand: shallow/deep API wedge capacities are evaluated using phi, effective stress, depth and diameter, with static factor `A = max(0.9, 3 - 0.8 z/D)`. `y50 = atanh(0.5) pult_per_length / (k z)` uses the selected static subgrade modulus. The implementation uses the standard static A expression, not the smoothed A fit in PySimple1Gen.
- Each PySimple1 receives **force capacity**, `pult_per_length * tributary_length`, rather than force per unit length. Soil type 1 represents the clay approximation and 2 the sand approximation. Drag ratio is explicit; viscous damping is zero for this static model.

The sand half-capacity conversion matches a point on the API tanh backbone; it does not make the complete PySimple1 curve identical to that backbone. Direct result equality with OpenPile is not expected, particularly at small clay displacement. Mesh/step convergence and appropriate geotechnical benchmarks remain necessary for project acceptance.

## Outputs

Result exports use imperial units: elevation/depth in ft, displacement in in, forces in kip, moments in kip-ft, stress in psi, and unit weights in lb/ft�. Rotation remains in radians. The solver continues to calculate internally in kN and m. Original settings and source records retain their declared units. `solver.log` contains native solver diagnostics. Existing result folders are not converted; rerun into a new folder.

- `validation.json` and `analysis-inputs.json`: findings, converted values, source cells, settings, and the complete selected reaction vector.
- `springs.csv`: node/layer assignments, sample depth, tributary length, effective stress, pult, y50, and drag ratio.
- `displacements.csv`: pile-node elevation, lateral displacement, vertical displacement and rotation.
- `forces.csv`: element **local resisting end forces**, with explicit i/j labels. These have opposite end-force sign conventions across adjoining elements; they are not a sign-normalized section-force diagram. Elements run from head toward tip.
- `reactions.csv`: global forces and moments at the fixed soil anchors and vertically restrained pile tip.
- `convergence.json`: return code, load factor, and iterations for each attempted step. `solver.log` captures native diagnostic messages.
- `summary.json`: solver/version, convergence, head deflection, absolute response maxima, and limitations. `design_pass` remains null.

Loaded displacement is not the workbook's NON-RECOVERABLE displacement after unloading. This CLI does not claim compliance with that limit or complete pier acceptance.

## Verification

```powershell
openseespy-cli/.venv/Scripts/python -m unittest discover -s openseespy-cli -v
```

Tests exercise clay/sand analyses, global force equilibrium, elastic cantilever deflection versus PL^3/(3EI), failed-step handling, layer-interface tributaries, water stress, and validation. Solver tests skip when OpenSeesPy is absent. These are implementation checks, not site-specific design validation.

References: [PySimple1](https://openseespydoc.readthedocs.io/en/latest/src/PySimple1.html), [elasticBeamColumn](https://openseespydoc.readthedocs.io/en/latest/src/elasticBeamColumn.html), [zeroLength](https://openseespydoc.readthedocs.io/en/latest/src/ZeroLength.html), and the mathematical capacity/half-displacement relations in [OpenSees PySimple1Gen](https://github.com/OpenSees/OpenSees/blob/master/SRC/material/uniaxial/PY/PySimple1Gen.cpp). The spring calculations are separate from the uploaded learning example and from the OpenPile runtime.


### Pier projection above ground

In Step 1 > Analysis settings, set **Projection above ground (ft)** (`projection_height_ft` in settings JSON). The default is **1 ft (12 inches)**, including settings files that omit this field. Zero is allowed for a flush pier head; negative or non-finite heights are rejected.

Trial embedment remains the depth below ground. Total modeled pier length is embedment plus projection. The exposed beam has no soil springs, the applied reaction vector acts at the raised pier head, and head deflection is measured there. This introduces the exposed-length lever arm into the analysis. Supply head-level loads; do not also add that lever arm to the input moment. Ground and soil elevations remain unchanged. Batch depth searches and fixed-embedment load-limit searches retain the projection setting.
