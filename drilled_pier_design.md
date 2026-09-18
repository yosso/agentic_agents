# Drilled Pier Design
## 1. Goal
Size the embedment depth and obtain the maximum shear and moment on the drilled pier from the applied loading

## 2. How it is currentlly done
1. We obtain all of the load cases for each pier
2. We use a program called Allpile to obtain the depth which will keep the pier deflection below the deflection criteria
3. We use the same program to obtain the maximum shear and moment seen by the concrete
4. We next take the depth and loading and place into an excel worksheet to track and create the data required to create the drawings.

## 3. How will I do it?

This overview shows the main functions and the data each function produces. Ovals represent functions; rectangles represent their outputs. Detailed checks and depth iterations are handled inside the functions.

```mermaid
flowchart TD
    LOADS(["read_rsa_loads()"])
    LOAD_DATA["Pier loads<br/>Model, pier ID, and load cases / combinations"]
    INPUTS(["read_design_inputs()"])
    INPUT_DATA["Design inputs<br/>Excel soil parameters, pier assignments, starting diameters,<br/>anchor-pattern criteria, deflection rule, and analysis settings"]
    ASSEMBLE(["prepare_pier_designs()"])
    PIER_DATA["Validated inputs for each pier<br/>Loads, assigned soil profile, diameter meeting anchor minimum,<br/>allowable deflection, and analysis settings"]
    SIZE(["size_embedment_depth()"])
    ANALYSIS_DATA["Depth-sizing results for each pier<br/>Accepted depth, top deflection, allowable deflection,<br/>analysis responses, and success / failure status"]
    FORCES(["summarize_pier_results()"])
    RESULT_DATA["Pier results table<br/>Diameter, embedment depth, deflection, maximum shear and moment,<br/>governing cases and locations, source IDs, and status"]
    EXPORT(["export_results_to_excel()"])
    WORKBOOK["Updated Excel workbook<br/>Design tracking and drawing data"]

    LOADS --> LOAD_DATA
    INPUTS --> INPUT_DATA
    LOAD_DATA --> ASSEMBLE
    INPUT_DATA --> ASSEMBLE
    ASSEMBLE --> PIER_DATA
    PIER_DATA --> SIZE
    SIZE --> ANALYSIS_DATA
    ANALYSIS_DATA --> FORCES
    FORCES --> RESULT_DATA
    RESULT_DATA --> EXPORT
    EXPORT --> WORKBOOK
```

`size_embedment_depth()` builds and runs the OpenSeesPy models, checks top deflection for the applicable load cases / combinations, and adjusts depth within the configured search limits. It returns the first passing trial depth or an explicit failure / unresolved status. `summarize_pier_results()` extracts the shear and moment envelopes for accepted designs and carries unsuccessful pier statuses into the results table.

The diameter-based deflection rule, anchor-pattern minimum diameter criteria, and depth search settings still need to be defined. Specify whether deflection is checked by direction or as a resultant.
