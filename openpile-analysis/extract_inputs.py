"""File-based bridge to the existing Excel/Robot preparation routines."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'opensee-analysis'))
from preparation import config, read_mapping, parse_cases, extract_reactions, assemble_inputs


def process(request):
    if request['command'] == 'defaults':
        return dict(workbook=str(config.DEFAULT_WORKBOOK), sheet=config.MAPPING_SHEET_NAME,
                    table=config.MAPPING_TABLE_NAME, api=config.find_robot_api())
    workbook = Path(request['workbook']).resolve()
    mappings = read_mapping(workbook, request['sheet'], request['table'])
    if request['command'] == 'mapping':
        return dict(mappings=mappings, source={key: request[key] for key in ('workbook', 'sheet', 'table')})
    if request.get('snapshot') != mappings:
        raise ValueError('Workbook mapping changed. Load and review the mapping again.')
    overrides = request.get('models', {})
    pairs = set()
    for mapping in mappings:
        model = Path(overrides.get(str(mapping['row']), mapping['model']))
        if not model.is_absolute():
            model = workbook.parent / model
        model = model.resolve()
        if not model.is_file():
            raise ValueError(f'Robot model does not exist: {model}')
        mapping['model'] = str(model)
        mapping['exists'] = True
        pair = (str(model).casefold(), mapping['group'].casefold())
        if pair in pairs:
            raise ValueError('Duplicate Robot model/group assignment.')
        pairs.add(pair)
    cases = parse_cases(request.get('cases', ''))
    extraction = extract_reactions(mappings, request['api'], cases)
    return dict(document=assemble_inputs(workbook, mappings, extraction), extraction=extraction)


if __name__ == '__main__':
    try:
        request = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
        result = process(request)
        Path(sys.argv[2]).write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
