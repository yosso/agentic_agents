# Input workbook mapping

Source: `inputs/DVLP_FTG_MTL_QTY.xlsm`. Read-only inspection of saved worksheet values, formulas, table definitions, and named ranges. No macros executed, formulas recalculated, or workbook changes made. The adjacent `~$` file is an Excel lock file and was not used.

| Workflow data | Workbook source | Details |
| --- | --- | --- |
| Pier assignments and specified diameters | INPUT TABLES: tblBoringAssignment, A36:I41 | Footing mark, boring, diameter in ft, minimum embedment in ft, water-table depth in ft, allowable deflection in inches; G:I hold depth/moment/shear results |
| Soil profiles | GEOTECH PARAMETERS: tblSOIL_BORING_01, C7:N10; tblSOIL_BORING_02, C17:N22; tblSOIL_BORING_03, C27:N32 | Boring IDs SB1, SB2, SB3 are in D6, D16, D26; tables contain layer bounds and soil properties |
| Diameter-based criteria | DP WORKFLOW and GUIDELINES: B67:E75 | Ordinary cell range, not a named Excel table; diameter in ft, tip deflection in inches, non-recoverable deflection in inches, minimum embedment |
| Existing load records | INPUT TABLES: tblREACTIONS, A48:F55 | Structure/equipment, load case, axial kip, resultant shear kip, resultant moment kip-ft, footing mark |
| Structure-to-footing mapping | INPUT TABLES: ProjectStrTable, A7:I20 | Used by the load table's footing-mark lookup |
| Anchor-pattern diameter calculation | Individual FTG ... (DP) sheets, including FTG A (DP)!J7:J11 | J11 calls the VBA function roundpierdia; the saved value for footing A is 30 inches |

## Current populated case

`tblBoringAssignment` has one populated footing row: A, boring SB1, diameter 2.5 ft, minimum embedment 6 ft, blank water-table depth, allowable deflection 0.3564 in, and saved design embedment 9 ft. The saved moment and shear results are 12.6334 kip-ft and 4.14695 kip.

The complete load row is load case 1 for `7-1 161KV A-FRAME DEADEND`, mapped to footing A: axial 2.1 kip, resultant shear 1.8 kip, resultant moment 7.1 kip-ft. Other load rows are incomplete. The future RSA import must preserve model, pier/support, load-case, direction, and sign information; this existing table only exposes resultants for shear and moment.

## Items to settle before automated analysis

- **Deflection criterion and row match:** the guideline table's 2.5-ft row gives 0.9 in tip deflection and 0.297 in non-recoverable deflection. The assignment's 0.3564 in equals the 3-ft row's non-recoverable value. Confirm which column governs the top-of-pier check and whether the assignment value is an intentional override. The label “tip” also needs an explicit mapping to the intended response location.
- **Minimum depth:** footing A specifies 6 ft, while the 2.5-ft guideline row evaluates to 10 ft. Its saved design depth is 9 ft. Establish precedence between the assignment and guideline values.
- **Water-table depth:** footing A's field is blank. Its meaning must be explicit; the importer must not silently turn it into zero.
- **Soil units:** the cohesion header says KSF while entries include 1000, 1300, and 200000. Verify source units rather than infer conversion from magnitudes. Density, subgrade-reaction modulus, and strain columns also need explicit units and conventions.
- **Named-range scope:** global COHESION_PHI and PHI_K names contain #REF!, but valid sheet-local versions exist on GEOTECH PARAMETERS, pointing to H2 and K2. PHI_EPSILON is also local, pointing to N2. An importer must respect sheet-local name resolution rather than assume these formulas use the broken global names.
- **Formula and VBA values:** saved formula results, including roundpierdia, are snapshots. Reading the workbook does not execute VBA or recalculate formulas. Input freshness needs an explicit check in implementation.

## Integration plan

An `RSA GROUP MAPPING` sheet with table `tblRSAGroupMapping` has been added to the prepared copy `inputs/DVLP_FTG_MTL_QTY_with_RSA_mapping.xlsm`. The original workbook was locked by Excel and remains unchanged. A backup of the inspected original is in `workbook-review/backups/`.

The mapping columns are `STRUCTURE/EQUIPMENT`, `RSA MODEL ID`, `RSA MODEL FILE`, `RSA SUPPORT GROUP`, `FTG MARK`, and `NOTES`. Use one row per structure/model/support-group/footing-callout assignment. Match structure labels to `ProjectStrTable[STRUCTURE/EQUIPMENT]`; FTG MARK joins `tblBoringAssignment`. Read support-node membership from the specified group in the specified Robot file. Different assignments may reference different files, including for the same footing callout. The table remains blank pending actual assignments.

The reader must validate model-file associations, group existence and support membership, overlapping groups, conflicting mappings, and footing-callout matches. Preserve model, group, node, and load-case identifiers. Keep individual support reactions and complete load cases separate; do not automatically sum reactions across groups or models.

Use `read_design_inputs()` to read these existing ranges. Use `prepare_pier_designs()` to join footing marks to boring IDs, validate units and required fields, resolve the selected diameter-based criterion, and record any approved overrides. Keep diameters fixed during OpenSeesPy depth sizing. Define the output destination before implementing writes; the assignment table already has columns for design depth, maximum moment, and maximum shear.

The high-level workflow remains unchanged. Automated analysis is pending resolution of the input ambiguities above and the planned OpenSeesPy model/output validation.
