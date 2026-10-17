"""Shared Excel/Robot extraction and prepared-input assembly."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from model import ROOT

sys.path.insert(0, str(ROOT/'rsa-reaction-viewer'))
import config
from data import read_mapping, parse_cases, assess_group
from pier_designs import prepare_pier_designs, Issue


def extract_reactions(mappings, api, cases):
    if not Path(api).is_file():
        raise ValueError('Select an installed Interop.RobotOM.dll.')
    if not mappings:
        raise ValueError('Load the Excel mapping first.')
    with tempfile.TemporaryDirectory(prefix='opensee-inputs-') as folder:
        root=Path(folder)
        request=root/'request.json'
        result=root/'results.json'
        request.write_text(json.dumps(dict(api=api,mappings=mappings,cases=cases)),encoding='utf-8')
        completed=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
                                  '-File',str(config.APP_DIR/'read_robot.ps1'),'-RequestPath',str(request),'-ResultPath',str(result)],
                                 capture_output=True,text=True,errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if not result.exists():
            raise RuntimeError(completed.stderr or completed.stdout or f'Robot reader exited {completed.returncode}')
        return json.loads(result.read_text(encoding='utf-8-sig'))


def assemble_inputs(workbook, mappings, extraction):
    report=prepare_pier_designs(workbook,extraction.get('reactions',[]))
    if extraction.get('error'):
        report.issues.append(Issue('ERROR','','Robot extraction',str(extraction['error'])))
    groups=extraction.get('groups',[])
    for mapping in mappings:
        matches=[g for g in groups if all(g.get(k)==mapping[k] for k in ('mark','model','group'))]
        if len(matches)!=1:
            report.issues.append(Issue('ERROR',mapping['mark'],'Robot group','Missing or ambiguous extraction group.'))
            continue
        verdict,findings,source=assess_group(matches[0],mapping)
        for finding in findings:
            report.issues.append(Issue('ERROR',mapping['mark'],source,finding))
    for warning in extraction.get('warnings',[]):
        report.issues.append(Issue('WARNING','','Robot extraction',str(warning)))
    document=report.to_dict()
    document['mapping_snapshot']=copy.deepcopy(mappings)
    return document
