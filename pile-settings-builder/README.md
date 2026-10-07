# Pile settings builder

Small Windows desktop app that creates `settings.json` for the adjacent OpenSeesPy pier CLI. Requires Python with Tkinter (included with the usual Windows Python installation). No pip dependencies or virtual environment are required. Keep this folder alongside `openseespy-cli` and `rsa-reaction-viewer`, whose example settings and validation code it uses.

Double-click `start.bat`, or run from the repository root:

```powershell
python pile-settings-builder/app.py
```

1. **Open results / prepared inputs**. Prefer the viewer's prepared-inputs export, which contains `piers`, `soil_profiles`, and reactions. `openseespy-cli/settings/test_01.json` is this kind of input despite its filename. The synthetic `openseespy-cli/examples/prepared.json` is also available for trying the app.
2. Choose a footing and select one reaction row. The table retains the exact model, group, node and combination identifiers. Forces are displayed in N and moments in N-m, as exported by the viewer.
3. Edit the analysis settings. Elastic modulus is entered in **psi**, material and water unit weights in **lb/ft³**, and energy tolerance in **lbf-ft**. Saved settings use `E_psi`, `unit_weight_pcf`, `water_unit_weight_pcf`, and `energy_tolerance_lbf_ft`; the CLI converts these to its internal units. Example defaults preserve their previous physical values. Trial depth starts at the selected pier's minimum depth when available; the other initial values come from the CLI example and must be set for the intended analysis. The app does not infer load signs or material properties from reactions.
4. Review the suggested analog for each soil label. Unambiguous clay labels suggest `API_clay` (OpenSeesPy `PySimple1` soilType 1); sand/gravel labels suggest `API_sand` (soilType 2). These are approximate lateral spring backbones, not exact equivalents. The extracted layer values and source rows are shown for review. Ambiguous labels and materials such as limestone remain unmapped; choose a reviewed proxy only when justified, or extend the solver with a suitable model. Clay uses a cohesion field, strain field and J; sand uses a static modulus field. Switching footing resets soil choices and the trial depth.
5. Click **Preview & validate**, then open the JSON & validation tab. The app invokes the existing OpenSeesPy CLI input validator without running an analysis or requiring OpenSeesPy to be installed.
6. **Save settings.json** to a separate file. The source JSON cannot be overwritten. Unmapped soil types are omitted from `soil_models`, allowing the settings to be saved as a draft; prepared-input validation reports the first unmapped layer within the trial embedment. Findings are displayed in the preview and are not inserted into the settings schema.

The viewer's raw `live-results.json` / `results.json` is also supported. It provides footing marks and reactions, but no soil profiles or pier geometry. Add the exact soil labels manually and save a draft. Open prepared inputs for full validation; raw reaction drafts cannot be declared validated by this app. Solver summaries and existing settings files are not source-results formats.

Missing water depths, upstream preparation errors and invalid strain values remain validation failures. This editor does not modify or reinterpret source data. Fix the workbook/prepared inputs and reopen the source. Saving settings does not run the solver or establish design acceptance.

For normal-weight concrete, the **Analysis settings** tab includes a **Concrete f′c (psi)** input. Enter the strength and click **Calculate & use Ec** (or press Enter) to fill the modulus field using `Ec = 57000 × sqrt(f′c)`. For example, 4,000 psi produces approximately 3,604,997 psi. The modulus remains editable and is saved as `material.E_psi`; the strength input is a calculator input and is not saved. After changing strength, calculate again to update Ec.

To validate a saved file with the CLI, from the repository root:

```powershell
python openseespy-cli/cli.py validate --inputs openseespy-cli/examples/prepared.json --settings path/to/settings.json --output openseespy-cli/results/new-validation
```

Use the same prepared inputs used to create the settings and a new output folder.

Run the builder tests:

```powershell
python -m unittest discover -s pile-settings-builder -v
```
