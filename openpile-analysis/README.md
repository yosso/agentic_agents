# OpenPile analysis — Node.js app

Local browser interface for `openpile-cli`. Node.js serves the interface and manages jobs; Python runs OpenPile. Source workbooks and Robot files are not changed.

## Start

With Node.js 22 or newer, from the repository root:

```powershell
node openpile-analysis/server.mjs
```

Open **http://127.0.0.1:3210** in your browser. Alternatively, double-click `start.bat` in this folder, or run `npm start` from this folder. No npm dependencies or build step are required.

The server uses `openpile-cli/.venv/Scripts/python.exe` on Windows and `.venv/bin/python` on other platforms. If the environment is not installed yet:

```powershell
python -m venv openpile-cli/.venv
openpile-cli/.venv/Scripts/python -m pip install -r openpile-cli/requirements.txt
```

Excel extraction uses `python` with `openpyxl` installed. Set `EXTRACTION_PYTHON` to a different interpreter if needed; this is separate from the OpenPile environment. Step 0 reads local paths rather than uploading workbooks so relative Robot filenames remain meaningful. Source workbooks are never saved by the app.

Override the interpreter or port before starting if needed:

```powershell
$env:OPENPILE_PYTHON = 'D:\path\to\python.exe'
$env:PORT = '3211'
node openpile-analysis/server.mjs
```

## Workflow

0. In **Extract Excel / Robot inputs**, click **Find default paths**, choose the saved workbook, worksheet/table and Robot API DLL, then **Load / review mapping**. Review expected support counts and groups; override Robot file paths if needed. Click **Read Robot and prepare inputs**. The existing reader extracts combinations only, checks group quantities, and assembles soil layers, assignments, diameter, deflection limits and findings. Prepared data loads automatically into Step 1; preparation errors remain visible and block analysis through existing validation. Save workbook edits first. Live extraction requires Windows and installed/licensed Robot. If Robot is already open, the existing reader uses that session and does not switch projects.
1. Alternatively, load a **prepared-input JSON** exported by the existing RSA reaction viewer. Raw RSA results alone are insufficient: the export must also contain soil profiles and pier assignments. The synthetic example button provides a runnable demonstration.
2. Import settings if available, or edit the form. Choose the footing and exact model/group/node/combination. Review material values, load signs, trial embedment, mesh, and soil-model mappings. The defaults are demonstration values; unknown soil labels are not automatically assigned models. The source details panel displays soil data, source cells, units, and existing findings.
3. Validate or run one selected reaction and axis. Forces remain coincident from the selected row. X axis uses FX/MY/FZ and Y axis uses FY/MX/FZ.
4. For batch depth sizing, select footings, increment, maximum depth, and directional/resultant screening. Starts are `max(trial embedment, workbook minimum)`. The maximum is capped at soil coverage. All exact ties for component/resultant shear and moment, torsion, compression, and uplift extremes are retained. Every selected vector is solved in both axes at each depth.
5. Review results and open individual artifacts. Summary cards use inches, kips, and kip-ft; raw CLI CSVs retain their labelled SI units. Settings can be downloaded for reuse.

The default **projection above ground is 1 ft**. Zero is permitted. OpenPile now models the exposed length and applies the load at the raised head. No soil springs are assigned above ground; embedment remains below grade. Supply head-level loads without separately adding the projection lever arm to the applied moment. This option is also available directly in the CLI as `projection_height_ft`; older settings files that omit it now use 1 ft.

Soil input units follow the current prepared schema: cohesion in **lb/ft²**, density in lb/ft³, subgrade modulus in lb/in³, depths in ft, and epsilon50 as a **fractional strain**, not percent. Stale unit declarations and preparation errors block execution. See [CLI documentation](../openpile-cli/README.md) for model settings and assumptions.

## Results and cancellation

Jobs run one at a time. The page polls progress without blocking the browser. Cancellation prevents additional solver cases after the current Python process finishes. A solver error stops that footing; other batch footings continue. Failed or incomplete responses never pass the displacement screen.

Each job has a unique directory under ignored `results/`, containing input/settings snapshots, per-case CLI artifacts, and `job.json`. Refreshing the browser reconnects to the latest job while the server is running. Restarting the server clears the in-memory job list; existing reports remain on disk. Result links open readable JSON/CSV/log files, which can be saved through the browser.

The server binds only to 127.0.0.1, validates Host/Origin for local use, invokes the fixed Python CLI without a shell, and serves only registered job artifacts. This app is not configured for remote hosting or multi-user deployment. Uploaded JSON is limited to 25 MB.

## Scope

This version provides prepared-input review, settings editing, single-case validation/analysis, and batch embedment search. Step 0 reuses the desktop Excel/Robot extraction routines; the desktop app's fixed-depth load-limit search is not yet included here.

Batch passing means only the configured **loaded-displacement screen**. The workbook's non-recoverable displacement criterion is not modeled by these monotonic runs. Two independent axis analyses are not a coupled 3D model. Torsion, axial soil capacity, reinforcement design, and full design acceptance are outside the analysis. Extreme-load selection does not guarantee the governing displacement among every combination.

## Tests

```powershell
cd openpile-analysis
npm test
```

Tests cover extreme selection, depth limits, resultant checking, cancellation/failure handling, and HTTP-to-Python validation and solver runs. Integration tests require the OpenPile environment. The CLI's own solver tests include the projection geometry and a closed-form elastic beam benchmark.

Optional browser smoke test (uses Playwright already installed in `beam-deflection-checker/node_modules` and local Chrome): `node openpile-analysis/test/browser-smoke.mjs` from the repository root. It exercises example loading, depth preview, validation, and a real solver run. The screenshot is saved under ignored `results/`.

Step 2 lists the exact soil labels from loaded prepared profiles. Existing matching mappings are retained; new labels appear as `null` (unassigned). Use the per-soil dropdowns to select the model, curve type and parameter fields, or import project settings. JSON is generated automatically and displayed read-only. Download soil mappings exports a soil_models object; Download settings includes it in the complete CLI settings file. Demo clay is supplied only by the synthetic example button.

## Soil mapping choices

Step 2's expanded **How to assign a soil model** guide lists every supported mapping field and includes a complete JSON example. Keep each workbook soil label exactly as extracted. A mapping applies to all layers sharing that label, using each layer's own values.

| Field | API_clay | API_sand |
| --- | --- | --- |
| `kind` | `static` or `cyclic` | `static` or `cyclic` |
| `cohesion` | `cohesion_ultimate` or `cohesion_factored` | Not used |
| `strain` | `e50` or `e50_factored` | Not used |
| `J` | Number from 0.25 to 0.50 inclusive | Not used |
| `modulus` | Not used | Static: `k_static` or `k_static_factored`; cyclic: `k_cyclic` |

Sand uses the layer's `friction_angle` directly. Both models use layer density and depths. Mapping values select fields, not new numeric soil parameters. Factored fields are read as provided without applying another factor. Prepared strain values are fractions. Selecting cyclic curves does not simulate load history or determine non-recoverable displacement.

Only these two soil models are currently exposed by this CLI; rock requires additional implementation and a reviewed model choice. Null mappings cannot be analyzed. Validate each selected footing and depth after assigning mappings. See [OpenPile API documentation](https://openpile.readthedocs.io/en/latest/API.html) for model definitions.

Soil assignment controls flag missing selected Excel parameter values. Switching between clay and sand removes irrelevant fields; cyclic sand selects k_cyclic. Model selection remains explicit because soil labels alone do not establish model applicability.

## Controlling response summary

Results includes a per-footing table of maximum absolute moment (kip-ft), shear (kip), and deflection (in) along the pier. Each metric lists its controlling combination, node, axis, group and model; exact ties are retained. Batch results use the accepted embedment or last attempted depth, not the envelope of rejected depths. Incomplete trials are labelled and missing metrics are unavailable. Values are per-axis responses, not X/Y resultants or the head-displacement acceptance criterion. Only analyzed combinations are covered. Download `response-summary.json` from the result artifacts for the same summary data.
