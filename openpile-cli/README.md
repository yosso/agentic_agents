# OpenPile CLI

Validate the prepared pier JSON and analyze one footing, one node/combination, and one lateral plane. The desktop viewer and Excel workbook are not modified. Python 3.12 is used for development; OpenPile 1.0.3 and pandas 2.2.3 are pinned in `requirements.txt`; pandas 3 causes a read-only-array failure in this OpenPile version.

Run commands from the repository root in PowerShell:

```powershell
python -m venv openpile-cli/.venv
openpile-cli/.venv/Scripts/python -m pip install -r openpile-cli/requirements.txt

# Synthetic example, not project design data
openpile-cli/.venv/Scripts/python openpile-cli/cli.py validate --inputs openpile-cli/examples/prepared.json --settings openpile-cli/examples/settings.json --output openpile-cli/results/demo-validation
openpile-cli/.venv/Scripts/python openpile-cli/cli.py run --inputs openpile-cli/examples/prepared.json --settings openpile-cli/examples/settings.json --output openpile-cli/results/demo-run
```

Each output directory must be new to avoid mixing results from separate runs. `validate` works with standard Python without installing OpenPile. Exit codes: 0 success, 2 input/validation error, 3 solver/dependency failure.

## Project inputs

Export prepared JSON from the reaction viewer, or use its existing preparation command with the Python environment that has openpyxl installed:

```powershell
python rsa-reaction-viewer/pier_designs.py --reactions rsa-reaction-viewer/live-results.json --output rsa-reaction-viewer/prepared-inputs.json
```

Copy `examples/settings.json` to a project settings file. Replace the example values with reviewed inputs. Then pass that settings file and `rsa-reaction-viewer/prepared-inputs.json` to `validate` and `run`.

- `footing` selects the callout. `reaction` must match exactly one complete row by model filename/path, group, node, and case. No envelopes or summation are used.
- `embedment_ft` is the trial depth; diameter and minimum depth come from prepared inputs. The entire embedment must be covered by the soil profile. Pile head and ground surface are at zero. This version supports a solid circular section.
- `material` specifies E in kPa, total unit weight in kN/m^3, and Poisson ratio. OpenPile calculates the section properties from diameter. No material is inferred from Excel.
- `plane: "X"` selects FX and MY; `"Y"` selects FY and MX. Both include FZ from that same reaction row. Torsion and the other plane remain in the traceable reaction vector but are not analyzed.
- `load_signs` explicitly maps the selected source force/moment to OpenPile Py/Mx/Pz. Each multiplier must be +1 or -1. Verify support-reaction versus applied-load conventions and the local axis orientation for the Robot model. The example signs are for the synthetic example only. OpenPile positive Pz points upward, so compression requires negative Pz.
- `boundary: "free_head_axially_fixed_tip"` prescribes only tip axial restraint. The lateral tip and head rotation remain unrestrained. This is a lateral analysis with axial load, not an axial soil-capacity/settlement analysis.
- `mesh_size_ft` controls discretization, with Euler-Bernoulli elements. `max_iterations` limits nonlinear iterations. Mesh convergence still needs review for project analyses.

## Soil model selection

Every soil label encountered within the trial depth needs an explicit entry in `soil_models`. Labels such as STIFF CLAY do not automatically select a constitutive model.

For `API_clay`, select `cohesion_ultimate` or `cohesion_factored` as Su, select `e50` or `e50_factored` as epsilon50, and supply J (0.25 to 0.5) and `kind` (`static`/`cyclic`). Selecting cohesion as Su is an explicit modeling decision. Epsilon50 must be a fraction between zero and one; values are never divided by 100 automatically. API clay does not use the workbook subgrade-modulus fields.

For `API_sand`, supply `kind` and `modulus`: static curves use `k_static` or `k_static_factored`; cyclic curves use `k_cyclic`. The friction angle and selected modulus must be supplied. No factored cyclic modulus is invented. Example mapping:

```json
{"SAND": {"model": "API_sand", "kind": "static", "modulus": "k_static"}}
```

Rock and other constitutive models are not implemented in this first version and block analysis when selected. Original soil values and cell references are carried into the converted analysis inputs, which also list fields actually used. The CLI converts ft to m, lb/ft^3 to kN/m^3, kip/ft^2 to kPa, lb/in^3 to kN/m^3, and N/N-m to kN/kN-m. Positive-downward soil depths become negative elevations. Unit declarations must match the prepared schema.

## Outputs and checks

`validation.json` reports input success/failure. `analysis-inputs.json` records the settings, converted layers, loads, source cells, complete selected reaction, and preparation findings. Global and selected-footing preparation errors block execution; errors assigned solely to other footings are retained for review. The preparation export's `solver_ready=false` is not a blanket blocker: this CLI supplies and validates its own explicit analysis settings.

Successful runs write `displacements.csv`, `forces.csv`, `reactions.csv` with OpenPile's unit-labelled columns, and `summary.json` with convergence details, head deflection (m/in), and absolute maxima of displacement, shear, and moment. `solver.log` retains solver messages. Convergence requires the actual success message as well as finite result tables, because OpenPile 1.0.3 can label the last iteration as converged after exhaustion. Failed runs return exit code 3 and a failed summary; they do not report a design pass.

The workbook's allowable deflection is non-recoverable deflection. The computed loaded response is not a residual displacement after unloading, so the CLI retains the limit for reference and leaves `design_pass` unset. No embedment optimization, torsion check, reinforcement design, or complete pier acceptance is performed.

Tests:

```powershell
openpile-cli/.venv/Scripts/python -m unittest discover -s openpile-cli -v
```

Implementation references: [OpenPile usage](https://openpile.readthedocs.io/en/latest/usage.html) and [API documentation](https://openpile.readthedocs.io/en/latest/API.html). The installed 1.0.3 package is used to verify the actual API and result format.


Alternative solver: [OpenSeesPy CLI](../openseespy-cli/README.md). Both CLIs share prepared-input validation and conversions in `rsa-reaction-viewer/pile_analysis_inputs.py`; the OpenSeesPy runtime does not depend on OpenPile.
