# Robot support reaction viewer

A small Windows desktop app displaying Robot group node quantities and individual support reactions. Located in its own folder; it does not edit the Excel workbook or Robot models.

## Start

Requires Python with Tkinter, Windows PowerShell, and a licensed installation of Autodesk Robot. Set up the viewer's virtual environment once, from the repository root:

```powershell
python -m venv rsa-reaction-viewer/.venv
rsa-reaction-viewer/.venv/Scripts/python -m pip install -r rsa-reaction-viewer/requirements.txt
```

Double-click `start.bat` in this folder, or run the following from the repository root. No environment activation is needed:

```powershell
rsa-reaction-viewer/.venv/Scripts/python rsa-reaction-viewer/app.py
```

In VS Code, use **Ctrl+Shift+P → Python: Select Interpreter → Enter interpreter path** and select `rsa-reaction-viewer/.venv/Scripts/python.exe` in this repository.

1. Save workbook edits in Excel. The app reads the saved file, not unsaved Excel cells.
2. Select the workbook and click **Load mapping**.
3. Leave Combinations blank for all supported load combinations, or enter combination numbers/ranges such as `20, 30-36`.
4. Click **Read Robot models**. Review group quantities, node lists, and read notices.
5. View/filter reactions, select units, and export the visible rows to CSV.

Settings default to `../inputs/DVLP_FTG_MTL_QTY.xlsm`, sheet `INPUT TABLES`, table `RSA_GROUP_MAPPING`. These match the currently saved workbook. Change defaults and column names in `config.py`; sheet and table names can also be changed in the app. The viewer does not import the workbook-editing script.

## Mapping columns

| Column | Meaning |
| --- | --- |
| MARK | Footing callout |
| FOOTING QTY | Expected quantity, compared with actual unique group nodes |
| GROUP NAME | Exact node-group name in Robot |
| ROBOT FILE NAME | Absolute path or path relative to the workbook; `.rtd` is added if no extension is supplied |

Separate files may supply different mappings. Identical node numbers in different models remain distinct. Group node count includes all members; support count excludes non-support nodes and flags the discrepancy. The viewer does not infer that every node corresponds to a physical footing; the counts make that assumption reviewable.

## Robot access and results

The PowerShell bridge uses the installed `Interop.RobotOM.dll`. With no Robot process running, it creates a hidden session and opens each mapped file sequentially, then closes its own session without saving. If Robot is already running and exposes its active COM object, it reads only the matching open project, without switching models, closing it, or altering its visibility. A running but inaccessible Robot session produces an actionable error. Finish startup/license dialogs or close Robot before trying again. Do not edit an attached model during extraction.

Reactions come from `Structure.Results.Nodes.Reactions.Value(node, case)` in global axes, retaining all six components and source file/group/node/case identifiers. Raw API units are N and N-m; display options are N/N-m, kN/kN-m, and kip/kip-ft. Robot reaction signs are retained; the app does not negate them into applied footing loads or sum supports.

The API units and basic reaction call follow Autodesk's [Getting Started Robot API guide](https://forums.autodesk.com/autodesk/attachments/autodesk/robot-structural-analysis-forum-en/1707/1/Getting%20Started%20Guide%20Robot%20API.pdf). Group, selection, result-status and case interfaces were checked against the locally installed Robot 2026 interop assembly.

The reader extracts only ordinary linear load combinations. Simple load cases are always excluded, including when their numbers are explicitly entered; explicitly requested load cases produce a notice. Dynamic, mobile, code-envelope, buckling, and incremental case types are explicitly skipped with notices; these require further component-specific result handling. Missing/out-of-date results are not displayed as valid reactions. The reader does not run analysis. Missing groups/files, unsupported cases, non-support nodes and failed reaction queries remain visible in status/logs; zero values are not substituted for failures.

Expected quantities are loaded from Excel; actual quantities are obtained only after Robot reads the group. Multiple group memberships remain separate mapping rows, not an aggregate total.

Rows requiring review are highlighted red and labeled REVIEW. Selecting a row shows the workbook/table, quantity cell, Excel quantity, Robot quantity, and difference. The first flagged row is selected automatically. Matching rows are labeled MATCH; unread mappings remain Not checked. Missing files/groups or failed reads are flagged without treating an unavailable quantity as zero. These checks flag the input for review; they do not automatically change the workbook or establish whether Excel or the model is correct.

## Verification

## Prepare pier designs

Soil extraction/reporting can be used before Robot extraction: click **Prepare & validate inputs** with the saved workbook selected. Missing reactions will be reported, but soil profiles still appear. The preparation tab has **Assigned pier inputs**, **Soil parameters & source cells**, and **Validation findings** sub-tabs. Each soil parameter shows its footing assignment, boring/table, layer, source value, parsed value, declared unit, source cell, and findings. Unknown units and unavailable values remain visible for review.

**Export readable report** writes a Markdown report containing pier inputs and their source cells, all soil layer parameters, validation findings, and every available node/combination reaction vector. JSON export also retains the raw soil properties. The report is a snapshot of preparation, not a solver result.

After reading combinations, use **Prepare pier designs → Prepare & validate inputs**. The reader joins `INPUT TABLES!tblBoringAssignment` to each `tblSOIL_BORING_*` table on `GEOTECH PARAMETERS`, using the numeric table suffix as its boring ID: `tblSOIL_BORING_03` identifies boring 3 (`SB3`). The BORING/NUMBER cell above the table is cross-checked and any disagreement is flagged as an error. Numeric IDs and zero-padded SB IDs are normalized when joining assignments. Names and optional expected-ID checks are configured in `config.py`.

The report retains source cells, raw soil properties, both ultimate/factored parameters, saved formula values, and all six reaction components for every extracted node/combination. It checks required fields, numeric values, layer continuity, missing/ambiguous boring assignments, soil-unit declarations, and missing reactions. Extraction errors and quantity discrepancies remain blockers in the app. Blank water depth is not interpreted as zero; missing inputs require correction or an explicit future policy. Cyclic modulus `-` is retained as unavailable, not zero.

Confirmed source units are recorded in `SOIL_UNITS`: depths in ft, density in lb/ft^3, cohesion in kip/ft^2, subgrade moduli in lb/in^3, friction angle in degrees, and prepared strain as unitless fractions. Plain numeric E50 and FE50 worksheet values are percentage points and are divided by 100 (1.5 becomes 0.015); Excel percentage-formatted cells already store fractions and are retained as stored. Raw source values remain available in the export and readable report. Reprepare and re-export existing inputs to apply this conversion. The confirmed 12-field schema reads static modulus, cyclic modulus, factored static modulus (`fKh`), epsilon 50, and factored epsilon 50 in columns 8 through 12. No factored cyclic modulus is required. Depths increase downward from zero at the top of the hole. The first layer starts at zero, each END exceeds START, and each following START equals the preceding END; negative depths and discontinuities are flagged. Apart from the E50/FE50 percentage-to-fraction conversion, no soil-unit conversions, spring selection, reinforcement/material assumptions, or OpenSeesPy analysis are performed. `input_valid` reports the implemented preparation checks only; exported `solver_ready` remains false until model and solver validation are implemented. The named `tblDEFLECTION_SIZE` table supplies minimum embedment by exact diameter match. Both deflection columns and source cells are reported. `ALLOWABLE_DEFLECTION_COLUMN` is confirmed as `NON-RECOVERABLE (IN)`; the matched value is used as the allowable top-of-pier deflection. Assignment differences are flagged.

Export the preparation JSON from the tab, or run `python pier_designs.py --reactions live-results.json --output prepared-inputs.json`. The JSON contains pier records, soil profiles, and source-specific findings. The workbook is never saved by this reader.

The **Controlling combinations** tab shows five governing checks for each footing callout (A, B, C, etc.), across its extracted nodes/models: maximum shear `sqrt(FX²+FY²)`, maximum bending moment `sqrt(MX²+MY²)`, maximum torsion magnitude `abs(MZ)`, maximum positive FZ (compression), and most negative FZ (uplift). Global Z is vertical. Uplift is displayed with its negative sign; torsion magnitude is displayed alongside the original signed MZ. If no compression or uplift exists in the extracted data, its row says “None found” without inventing a governing combination. Each row includes the governing combination, node, model/group, and all six coincident reactions. Different checks can be controlled by different combinations. Exact ties show a count and the first source in deterministic order. No node reactions are summed. The text filter does not restrict the envelope; extraction selections do. These are load extremes, not capacity/deflection checks, and remain subject to extraction and quantity notices.

The combinations-only revision was verified live against the supplied model: 432 reaction rows for combinations 20, 21, and 30–36, with no extraction warnings. Individual load cases were excluded. The existing footing C quantity mismatch remains flagged. Seven automated checks passed.

Run `python -m unittest -v` in this folder. Checks cover mapping joins across model files, duplicate/incomplete mappings, relative filenames, unit conversions, case filters, and preservation of the input workbook. Real Robot extraction additionally requires a ready, licensed API session and current saved results. The tests do not establish engineering correctness of a model.

Before the combinations-only revision, live verification on September 20, 2026 with `FP1_RIGID_BUS_VERSION_B_EXPANSION.rtd` and Robot 2026 returned 912 node/case reaction rows across 19 cases, with no skipped-case notices. A had 21/21 expected nodes, B had 20/20, and C had 7/8. All 48 group nodes were supports. The C quantity discrepancy is reported for review, not corrected automatically. Desktop checks confirmed all 912 rows render, filtering to C yields 133 rows, and unit switching works. Five automated tests passed. These counts reflect the model/workbook at verification time.
