# Pier workbook inspection

Source: `inputs/TEST_SUB_LAT_PILE_PY.xlsm`. Inspected worksheet formulas, saved values, workbook metadata, and extracted VBA source. No macros were executed and the workbook was not modified or recalculated. Saved results are not independently validated calculations.

## Workbook structure

| Sheet | Role |
| --- | --- |
| INPUT_CALCS | Soil tables, current pier inputs, calculation call, response array, and summaries |
| Function Index | Function arguments, output columns, units, and limitations |
| Examples | Example analysis and comparison data; saved calculation outputs contain errors |
| SoilProps | Soil reference data and p–y curve examples |
| About | Attribution, license, and version history |

The workbook also lists a very-hidden `mLPile` sheet without a valid worksheet relationship. The reader warned about this entry; `mLPile` VBA source was nevertheless extracted successfully. Avoid rewriting the original with a general-purpose spreadsheet library until its special features have been accounted for.

## Inputs and outputs

| Input on INPUT_CALCS | Location | Current contents / purpose |
| --- | --- | --- |
| Soil parameter tables | SB_INPUT, SB_02, SB_03 | Layer depths, soil model, density, cohesion, friction angle, stiffness, and strain parameters |
| Solver soil table | SB_INPUT_1, C39:G46 | Layer names followed by seven rows of solver properties |
| Segment definition | O41:P41 | 108 inches and 48 subdivisions |
| Loads | R41:R47 | Head shear, head moment, axial loads at top/bottom, zero-axial depth, cycles, and water-table depth |
| Section | U39:U51 | Section extent, 30-inch diameter, circular section option C, reinforcement, and material properties |
| Iteration settings | Y39:Y43 | Intended defaults override; see argument issue below |

The current load values include 1,800 lb head shear, 85,200 lb-in head moment, and 2,100 lb axial loads at both ends.

`INPUT_CALCS!N56` calls `LatPile`, returning 49 rows in `N56:S104`:

| Column | Meaning | Mapping to future workflow |
| --- | --- | --- |
| N | Node position, zero at head and negative downward | Response location / depth |
| O | Lateral deflection | Head deflection from the head row; full profile retained separately |
| P | Bending moment | Signed moment envelope and governing location |
| Q | Shear force | Signed shear envelope and governing location |
| R | Pile flexural stiffness EI | Diagnostic / comparison data |
| S | Soil spring stiffness | Diagnostic / comparison data |

The active sheet labels imply inches, lb, and lb-in for the displacement/force responses. Their validity depends on resolving the section-unit issue below. The units printed for EI in the Function Index should also be checked against the implementation before reuse.

Saved values for this case include head deflection 0.330043 in, maximum moment 151,601.235 lb-in (12.6334 kip-ft), and shear extrema -4,146.947 lb and +1,800.000 lb. These describe the saved file only, not a rerun or an accepted design.

## VBA responsibilities

Extracted source is in `vba/` beside this report.

- `mLPile.bas`: `LatPile` assembles the analysis, iterates soil and section stiffness, and returns response arrays.
- `SmithP43.bas`: `BoEF` assembles and solves the beam model and recovers forces. Although the Function Index calls the analysis finite difference, this module identifies a finite-element source and contains element assembly and integration routines.
- `mPYCurves.bas`: soil response, effective-depth calculations, and p–y curves.
- `mCirc.bas` and `mEstress.bas`: circular/rectangular section response and stiffness calculations.
- Remaining numerical modules support interpolation and equation solving.

The Function Index states that steel yielding and concrete crushing are not included in the analysis and calls for separate stress checks. Do not treat these response calculations as evidence of a complete pier capacity check.

## Findings to resolve before benchmarking

1. **Defaults argument mismatch.** `N56` contains `=LatPile(SEGMENTS,LOADS,SB_INPUT_1[],SECTION_TABLE,DEFAULT_TABLE)`. In `mLPile.bas:12`, the fifth argument is `PYCurveA`; `DefaultA` is sixth. The intended defaults therefore do not reach the iteration-settings argument. A corrected call would need to omit the optional p–y argument or supply it separately; confirm this in a working copy before recalculation.

2. **Verify units in the C/R section-stiffness updates.** The intended workflow always supplies `C` (circular) or `R` (rectangular); EI is calculated from section geometry and material properties, never supplied as a fixed input. The initial gross-section EI calculation uses diameter for C or width and depth for R, together with the material modulus, and is consistent with compatible geometry/modulus units. The remaining concern is the subsequent section-response calculation: `mLPile.bas:179` onward applies metric conversions before calling the circular/rectangular response routines. Validate those conversions for the workbook's inch/psi inputs. This finding concerns the later stiffness updates, not the validity of C/R or the initial geometry-based EI calculation.

3. **Section-stiffness convergence check is ineffective.** The update to `PStiffDiff` in `mLPile.bas` uses `Abs(FSA(i, 2) - FSA(i, 2))`, which is always zero. It does not compare the old and new stiffness.

4. **No explicit convergence status in the default output.** `LatPile` exits its loop either on tolerance conditions or the iteration limit, then returns the response array. It does not expose which exit condition occurred. Also, `YNorm` divides by the signed sum of displacements; cancellation or a negative sum warrants review.

5. **Summary formulas need review.** `Q49` and `Q51` use `MAXA` over profiles rather than a signed force envelope or explicit head displacement. `Q50` has an IF without a false branch and places the apparent positive-shear alternative inside MINA. The saved negative-governing shear does not establish that the positive-governing case works.

6. **Saved errors exist.** The active sheet contains five `#DIV/0!` cells in soil-table totals; the Examples sheet contains 372 error-valued cells. These are saved errors, not errors caused by running this inspection. Their effect on any selected benchmark must be traced.

7. **Proposed batch inputs are not established here.** The inspected tables do not provide the planned pier-to-diameter and diameter-to-allowable-deflection lookup tables. The visible calculation is one trial length and load set, not the proposed multi-pier depth-sizing workflow.

## Use in the proposed workflow

OpenSeesPy is the planned analysis engine. This workbook is a reference for inputs and optional comparison cases; repairing or porting its VBA solver is not a prerequisite for the new implementation.

Reuse the input categories and six-column response layout as a starting point for the data contract. Keep the workflow's fixed Excel diameter and allowable-deflection lookup, adding explicit pier/load-case IDs, units, and solver status.

Before comparing with OpenSeesPy, establish a reproducible workbook case with verified units, function arguments, convergence, and force extraction. Compare the full deflection, shear, and moment profiles under matched modeling assumptions. Use a separate independently known benchmark as well; agreement with this workbook alone would not validate either implementation.

The About sheet identifies GPL version 2 or later and Interactive Design Services attribution. Preserve its licensing and attribution when reusing extracted source.
