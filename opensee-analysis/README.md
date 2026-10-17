# OpenSeesPy batch footing analysis

Windows desktop app in `opensee-analysis`, using the adjacent OpenSeesPy CLI to select extreme load cases and size embedment. Python + Tkinter launches the interface; the solver interpreter must have OpenSeesPy installed (the existing `openseespy-cli/.venv` is selected by default).

From the repository root:

```powershell
python opensee-analysis/app.py
```

Or double-click `start.bat`.

1. Open the viewer's prepared-input JSON. It must use current psf cohesion declarations and fractional epsilon50 values.
2. Open Step 1 to review the integrated pile settings builder: material, concrete modulus calculator, load signs, mesh, solver controls and soil model mappings. A separate settings file is not required; importing existing settings is optional. Soil labels and layer details come from all footing profiles. Material, soil model mappings, load signs, mesh, boundary condition and solver controls are shared across selected footings. If those differ between footing groups, run separate batches with different templates. Missing soil mappings remain errors, with no inferred proxies.
3. Select footings. The app shows the number of selected extreme vectors, workbook minimum, batch starting depth and allowable for each. The batch starting depth updates when the Step 1 trial embedment changes.
4. Set a depth increment (default 1 ft) and maximum depth (default 60 ft). The starting depth is the greater of the Step 1 trial embedment and each footing's workbook minimum. The Step 1 value applies to all selected footings. A starting depth above the maximum or soil coverage is reported as an error; it is not silently reduced. The effective limit is the smaller of the user maximum and soil profile coverage. The final trial can be a partial increment at that limit; no soil extrapolation occurs.
5. The default `resultant` check compares sqrt(X^2+Y^2) with the allowable, combining the X and Y head displacements of the same reaction case. Optional `directional` checks each plane separately. Both modes run both planes for every selected coincident vector.
6. Enter a NEW output folder and run. Cancellation waits for the current solver subprocess to finish. Solver failures and invalid inputs stop the affected footing; other footings continue. A failed solver result cannot pass a deflection check.

The selection includes all exact ties for maximum absolute FX, FY, MX, MY and MZ, maximum resultant lateral force and bending moment, maximum compression and maximum uplift. Duplicate selectors are rejected. Each selected row retains its original coincident force/moment vector; independent extrema are never combined. X uses FX/MY, Y uses FY/MX, and both use FZ with the template's sign settings. Torsion extrema select a coincident case for lateral checking; the 2D solver does not analyze torsion itself.

At every depth, every selected vector is rerun in both planes. The first passing trial becomes `deflection_pass`. Exceeding the allowable at the configured limit becomes `depth_limit`; invalid inputs or nonconvergence become `error`. The search does not assume displacement decreases monotonically and does not interpolate between depths. These load extremes need not contain the governing deflection among all combinations.

The checked value is loaded elastic head displacement. The workbook currently supplies a non-recoverable deflection limit, but the solver does not model residual deformation. `deflection_pass` is only the configured displacement screen; it is not full design acceptance or an axial/torsional capacity check. Resultant mode combines two independent 2D solutions, not a coupled 3D model.

## Outputs

- `batch-summary.json`: selected cases and their selection reasons, every trial, governing reaction/plane and deflection, accepted depth/status, errors, and shear/moment envelope locations at the accepted depth.
- `footings.csv`: one row per processed footing with status, accepted depth, displacement, allowable, maximum shear and maximum moment. Units are ft, in, kip and kip-ft.
- `prepared-inputs.json` and `template-settings.json`: source and integrated-editor settings snapshots for this batch. Command-line mode still accepts a settings file.
- `footing-NNN/depth-NNN/case-NNN-X` and `case-NNN-Y`: standard CLI result folders and adjacent settings files. Open any converged folder in `openseespy-results-viewer` to review its inputs and plots.

Existing folders cannot be overwritten. Earlier trial results are retained even when a deeper trial passes. Force envelopes use the largest absolute local end force across all selected cases/planes at the accepted depth and preserve the original local end sign and location.

Optional command-line mode:

```powershell
python opensee-analysis/app.py --inputs rsa-reaction-viewer/20261002_inputs.json --settings rsa-reaction-viewer/20261001_settings.json --output opensee-analysis/results/project-01 --increment 1 --max-depth 40 --check resultant
```

CLI exit codes: 0 when every footing passes the deflection screen; 2 when a processed footing does not pass. Top-level configuration errors report an exception. Select another solver interpreter with `--python path/to/python.exe`.

Run tests:

```powershell
python -m unittest discover -s opensee-analysis -v
```

## Load limit at default embedment

Step 3 scales the selected coincident reaction case at the footing's workbook minimum embedment. Select the footing and reaction in Step 1, review the material and soil settings, then enter a new capacity output folder and run the search. All six reaction components, including axial load, scale by the same nonnegative multiplier; the original load signs remain in effect. Depth and diameter remain fixed.

The check is sqrt(delta_X^2 + delta_Y^2) against the footing's allowable deflection. The search doubles the multiplier until it finds a converged failing displacement or reaches the user maximum, then bisects the passing/failing bracket to the relative multiplier tolerance. A maximum multiplier that still passes is reported as `load_limit`, not a discovered capacity. Nonconvergence is `unresolved`, not evidence of exceeding the deflection allowable. Cancellation is honored between solver runs.

`capacity-summary.json` records the bracket, passing displacement, applied resultant head shear (kip) and bending moment (kip-ft), and internal shear/moment envelopes with locations. Each trial contains both plane result folders compatible with the results viewer. `bracketed` means a numerical displacement-limit bracket along this loading path, assuming continuous monotonic response. It is not a structural shear or moment strength, residual-deflection capacity, or complete design acceptance.

Step 3 displays capacity reports in Load limit, Internal force maxima and Search trials tables, with units in headings and a separate JSON details tab. Use Open saved capacity-summary.json to review a previous run without rerunning the solver.

The single-window workflow opens on **Step 0: Excel & Robot inputs**, followed by **Step 1: Settings**, **Step 2: Batch analysis** and **Step 3: Load limit**. The prepared-input selector and optional settings import are shared above the steps. Launch only opensee-analysis; no separate settings-builder window is needed.

## Step 0: Excel and Robot inputs

The app now opens on Step 0, with settings in Step 1, batch analysis in Step 2 and the load-limit search in Step 3. Choose a saved Excel workbook, load its RSA_GROUP_MAPPING table, and review the mapped footing groups and Robot filenames. Select one or more mapping rows and use Select Robot file to choose a .rtd file for those rows. These overrides are recorded in the prepared input mapping snapshot; Excel is not modified. Other mappings retain their own model filenames.

Select the installed Interop.RobotOM.dll (autodetected when possible). Optionally filter supported combinations; blank reads all supported combinations. Read Robot & create inputs asks for an output JSON filename, runs the existing reaction viewer's read_robot.ps1, then uses its workbook preparation functions to join reactions with soil profiles and pier geometry. Extraction errors, missing groups, quantity discrepancies and warnings remain in the prepared JSON and on-screen findings. Successful inputs load into the integrated settings automatically. Inputs with findings remain available for review; solver validation still blocks applicable errors.

Requires openpyxl in the app interpreter and a ready, licensed Robot installation with current saved results. Extraction runs in a worker thread. The app prevents extraction and analysis from running concurrently. Existing prepared JSON files can still be loaded using the shared selector above the steps. No solver analysis starts automatically after extraction.

### Step 1 load combination envelope

The Load combination envelope tab uses the reaction viewer’s five controlling checks per footing: resultant shear, resultant bending, absolute torsion, positive-FZ compression and negative-FZ uplift. All six coincident reactions, source combination/node/model/group and exact tie count are displayed. Unit switching matches the reaction table; CSV export includes unit headings. Double-click a governing row to select it in the settings editor. Absent compression or uplift is shown as None found. The envelope includes only extracted reactions and retains preparation errors for review. Batch depth search continues to select all ties plus directional component extremes; this summary does not replace that selection or combine reactions from different cases.


### Pier projection above ground

In Step 1 > Analysis settings, set **Projection above ground (ft)** (`projection_height_ft` in settings JSON). The default is **1 ft (12 inches)**, including settings files that omit this field. Zero is allowed for a flush pier head; negative or non-finite heights are rejected.

Trial embedment remains the depth below ground. Total modeled pier length is embedment plus projection. The exposed beam has no soil springs, the applied reaction vector acts at the raised pier head, and head deflection is measured there. This introduces the exposed-length lever arm into the analysis. Supply head-level loads; do not also add that lever arm to the input moment. Ground and soil elevations remain unchanged. Batch depth searches and fixed-embedment load-limit searches retain the projection setting.
