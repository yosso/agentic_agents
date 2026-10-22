from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DEFAULT_WORKBOOK = APP_DIR.parent / 'inputs' / 'DVLP_FTG_MTL_QTY.xlsm'
MAPPING_SHEET_NAME = 'INPUT TABLES'
MAPPING_TABLE_NAME = 'RSA_GROUP_MAPPING'
MARK_COLUMN = 'MARK'
QUANTITY_COLUMN = 'FOOTING QTY'
GROUP_COLUMN = 'GROUP NAME'
MODEL_COLUMN = 'ROBOT FILE NAME'

SOIL_SHEET_NAME = 'GEOTECH PARAMETERS'
SOIL_TABLE_PREFIX = 'tblSOIL_BORING_'
ASSIGNMENT_SHEET_NAME = 'INPUT TABLES'
ASSIGNMENT_TABLE_NAME = 'tblBoringAssignment'
# Optional expected IDs, checked against the numeric table suffix (not overrides).
SOIL_BORING_IDS = {}
# Prepared units; E50/FE50 percentage points are converted to unitless fractions.
SOIL_UNITS = {
    'depth': 'ft', 'density': 'lb/ft^3', 'cohesion': 'lb/ft^2',
    'friction_angle': 'degrees', 'subgrade_modulus': 'lb/in^3', 'strain': 'unitless',
}
DEFLECTION_TABLE_NAME = 'tblDEFLECTION_SIZE'
# Confirmed allowable top-of-pier deflection criterion.
ALLOWABLE_DEFLECTION_COLUMN = 'NON-RECOVERABLE (IN)'

def find_robot_api():
    installations = Path('C:/Program Files/Autodesk').glob(
        'Robot Structural Analysis Professional */Exe/Interop.RobotOM.dll')
    return str(next(iter(sorted(installations, reverse=True)), ''))
