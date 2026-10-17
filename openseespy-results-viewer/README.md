# OpenSeesPy results viewer

A Windows desktop viewer for the adjacent OpenSeesPy pile CLI. Uses Python and Tkinter only; no pip installation is needed.

Double-click `start.bat`, then select a result folder, or run from the repository root:

```powershell
python openseespy-results-viewer/app.py --results openseespy-cli/results/20261002-run-02
```

The folder must contain `analysis-inputs.json`, `summary.json`, `validation.json`, `displacements.csv`, and `forces.csv` from a validated, converged analysis. Files are read without modification.

The first tab plots deflection in inches, shear in kips, and moment in kip-ft against depth in feet, increasing downward. Dashed horizontal lines mark soil layer boundaries. Each plot shows its absolute maximum. Resize the window to resize the plots.

Shear and moment use the i-end local resisting force convention, with j-end signs reversed. Each element is plotted separately to retain force jumps at nodes; values are not averaged across elements. These signs describe the solver's local axes, not an independently established structural design sign convention.

The inputs tab shows the complete exported analysis inputs, including loads, geometry, material, soil layer parameters, source cells, reaction selection, and original settings. The summary tab includes solver status, response maxima, warnings and validation findings. Legacy SI CSV files are converted to imperial units for plotting; their input JSON retains its original units.

Saving results does not establish design acceptance; this app displays the solver's existing analysis.

Run checks from the repository root:

```powershell
python -m unittest discover -s openseespy-results-viewer -v
```
