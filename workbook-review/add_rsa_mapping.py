"""Add an RSA mapping sheet without rewriting existing worksheet/VBA parts."""
from pathlib import Path
from datetime import datetime
import hashlib
import os
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, quoteattr

MAPPING_SHEET_NAME = 'INPUT TABLES'
MAPPING_TABLE_NAME = 'RSA_GROUP_MAPPINGg'

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'inputs/DVLP_FTG_MTL_QTY.xlsm'
ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
rel_ns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

def append_element(raw, local_name, element):
    text = raw.decode('utf-8')
    pattern = rf'</(?:\w+:)?{local_name}\s*>'
    result, count = re.subn(pattern, lambda m: element + m.group(), text)
    if count != 1:
        raise ValueError(f'Expected one closing {local_name} tag')
    return result.encode('utf-8')

original_hash = hashlib.sha256(source.read_bytes()).digest()
with zipfile.ZipFile(source) as archive:
    entries = archive.infolist()
    parts = {e.filename: archive.read(e.filename) for e in entries}
    archive_comment = archive.comment

workbook = ET.fromstring(parts['xl/workbook.xml'])
if any(s.attrib['name'] == MAPPING_SHEET_NAME for s in workbook.find(f'{{{ns}}}sheets')):
    raise SystemExit(f'{MAPPING_SHEET_NAME} already exists; no changes made.')
sheet_id = max(int(s.attrib['sheetId']) for s in workbook.find(f'{{{ns}}}sheets')) + 1
sheet_number = max(int(m.group(1)) for p in parts if (m := re.fullmatch(r'xl/worksheets/sheet(\d+)\.xml', p))) + 1
table_number = max([int(m.group(1)) for p in parts if (m := re.fullmatch(r'xl/tables/table(\d+)\.xml', p))] or [0]) + 1
table_id = max([int(ET.fromstring(v).attrib['id']) for p, v in parts.items() if re.fullmatch(r'xl/tables/table\d+\.xml', p)] or [0]) + 1
relationships = ET.fromstring(parts['xl/_rels/workbook.xml.rels'])
used_ids = {r.attrib['Id'] for r in relationships}
rid_num = 1
while f'rId{rid_num}' in used_ids:
    rid_num += 1
rid = f'rId{rid_num}'
sheet_path = f'xl/worksheets/sheet{sheet_number}.xml'
table_path = f'xl/tables/table{table_number}.xml'

updates = {}
updates['xl/workbook.xml'] = append_element(parts['xl/workbook.xml'], 'sheets', f'<sheet xmlns="{ns}" xmlns:r="{rel_ns}" name={quoteattr(MAPPING_SHEET_NAME)} sheetId="{sheet_id}" r:id="{rid}"/>')
updates['xl/_rels/workbook.xml.rels'] = append_element(parts['xl/_rels/workbook.xml.rels'], 'Relationships', f'<Relationship xmlns="http://schemas.openxmlformats.org/package/2006/relationships" Id="{rid}" Type="{rel_ns}/worksheet" Target="worksheets/sheet{sheet_number}.xml"/>')
updates['[Content_Types].xml'] = append_element(parts['[Content_Types].xml'], 'Types', f'<Override xmlns="http://schemas.openxmlformats.org/package/2006/content-types" PartName="/{sheet_path}" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override xmlns="http://schemas.openxmlformats.org/package/2006/content-types" PartName="/{table_path}" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>')

headers = ['STRUCTURE/EQUIPMENT', 'RSA MODEL ID', 'RSA MODEL FILE', 'RSA SUPPORT GROUP', 'FTG MARK', 'NOTES']
def cell(address, value):
    return f'<c r="{address}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'

instructions = [
    'Structure / Robot support-group / footing-callout mapping',
    'One row per structure, Robot model, support-node group, and footing callout.',
    'Read support nodes from the specified group in the specified Robot model.',
    'Use a stable model ID and a model file path relative to this workbook, or an absolute path.',
    'Repeated footing marks may represent shared designs. Do not sum different supports automatically.',
]
rows = ''.join(f'<row r="{i}">{cell(f"A{i}", text)}</row>' for i, text in enumerate(instructions, 1))
rows += '<row r="7">' + ''.join(cell(f'{chr(65+i)}7', h) for i, h in enumerate(headers)) + '</row><row r="8"/>'
updates[sheet_path] = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="{ns}" xmlns:r="{rel_ns}"><dimension ref="A1:F8"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="7" topLeftCell="A8" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><sheetFormatPr defaultRowHeight="15"/><cols><col min="1" max="1" width="24" customWidth="1"/><col min="2" max="2" width="55" customWidth="1"/><col min="3" max="4" width="20" customWidth="1"/><col min="5" max="6" width="50" customWidth="1"/></cols><sheetData>{rows}</sheetData><tableParts count="1"><tablePart r:id="rId1"/></tableParts></worksheet>'''.encode()
columns = ''.join(f'<tableColumn id="{i}" name="{h}"/>' for i, h in enumerate(headers, 1))
updates[table_path] = f'<table xmlns="{ns}" id="{table_id}" name={quoteattr(MAPPING_TABLE_NAME)} displayName={quoteattr(MAPPING_TABLE_NAME)} ref="A7:F8" totalsRowShown="0"><autoFilter ref="A7:F8"/><tableColumns count="6">{columns}</tableColumns><tableStyleInfo name="TableStyleMedium2" showFirstColumn="0" showLastColumn="0" showRowStripes="1" showColumnStripes="0"/></table>'.encode()
updates[f'xl/worksheets/_rels/sheet{sheet_number}.xml.rels'] = f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="{rel_ns}/table" Target="../tables/table{table_number}.xml"/></Relationships>'.encode()

candidate = source.with_name(source.stem + '_with_RSA_mapping.xlsm')
if candidate.exists():
    raise FileExistsError(candidate)
with zipfile.ZipFile(candidate, 'w', zipfile.ZIP_DEFLATED) as archive:
    archive.comment = archive_comment
    for entry in entries:
        archive.writestr(entry, updates.get(entry.filename, parts[entry.filename]))
    for name, data in updates.items():
        if name not in parts:
            archive.writestr(name, data)
with zipfile.ZipFile(candidate) as archive:
    assert archive.testzip() is None
    for name, data in parts.items():
        if name not in updates:
            assert archive.read(name) == data, name
    for name in updates:
        ET.fromstring(archive.read(name))
import openpyxl
check = openpyxl.load_workbook(candidate, read_only=False)
assert check[MAPPING_SHEET_NAME].tables[MAPPING_TABLE_NAME].ref == 'A7:F8'
assert [c.value for c in check[MAPPING_SHEET_NAME][7]] == headers
check.close()
if hashlib.sha256(source.read_bytes()).digest() != original_hash:
    raise RuntimeError(f'Source changed during preparation. Candidate retained: {candidate}')
backup = ROOT / 'workbook-review' / 'backups' / (source.stem + datetime.now().strftime('_%Y%m%d_%H%M%S_before_RSA_mapping.xlsm'))
backup.parent.mkdir(exist_ok=True)
shutil.copy2(source, backup)
try:
    os.replace(candidate, source)
    print(f'Updated: {source}')
except PermissionError:
    print(f'Workbook is locked. Prepared copy: {candidate}')
print(f'Backup: {backup}')
print('Verified new table and byte-for-byte preservation of all unchanged archive parts, including VBA and drawings.')
