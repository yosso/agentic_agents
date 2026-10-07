"""Human-readable views of prepared inputs; no unit conversions or solver calls."""
from dataclasses import asdict

UNIT_KEYS = {
    'start': 'depth', 'end': 'depth', 'density': 'density',
    'cohesion_ultimate': 'cohesion', 'cohesion_factored': 'cohesion',
    'friction_angle': 'friction_angle', 'k_static': 'subgrade_modulus',
    'k_cyclic': 'subgrade_modulus', 'k_static_factored': 'subgrade_modulus',
    'e50': 'strain', 'e50_factored': 'strain',
}


def soil_report_rows(report):
    rows = []
    for profile in report.soil_profiles:
        marks = ', '.join(p.footing for p in report.piers if p.soil_table == profile.table_name) or 'Unassigned'
        for index, layer in enumerate(profile.layers, 1):
            for parameter, value in asdict(layer.properties).items():
                source = layer.cells.get(parameter, profile.table_name)
                raw = layer.raw_properties.get(parameter, value)
                findings = [i.message for i in report.issues if i.source == source]
                unit = profile.units.get(UNIT_KEYS.get(parameter), 'UNCONFIRMED') if parameter != 'model' else '—'
                if unit == 'UNCONFIRMED':
                    findings.append('Unit/convention must be confirmed.')
                if value is None and not findings:
                    findings.append('Not supplied' if parameter == 'k_cyclic' else 'Missing/invalid input')
                rows.append([marks, profile.boring_id, profile.table_name, index,
                             parameter, 'Missing' if raw is None else raw,
                             'Unavailable' if value is None else value, unit, source,
                             '; '.join(findings) or 'Read'])
    return rows


def markdown_report(report):
    def text(value):
        return str('Missing' if value is None else value).replace('|', '\\|').replace('\n', ' ')
    def table(headers, rows):
        return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                          '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                         ['| ' + ' | '.join(map(text, row)) + ' |' for row in rows])
    lines = ['# Prepared pier inputs and validation findings', '',
             f'Workbook: `{report.workbook}`', '',
             'Source values are retained in workbook units. This report does not establish solver readiness or run OpenSeesPy.', '',
             '## Assigned pier inputs', '',
             table(['Footing', 'Boring', 'Soil table', 'Fixed diameter (ft)', 'Minimum depth (ft)', 'Water depth (ft)', 'Allowable (in)', 'Reaction rows'],
                   [[p.footing, p.boring_id, p.soil_table, p.diameter_ft, p.minimum_embedment_ft,
                     p.water_table_depth_ft, p.allowable_deflection_in, len(p.reactions)] for p in report.piers]), '',
             '## Diameter-based criteria', '',
             table(['Footing', 'Table', 'Tip deflection (in)', 'Non-recoverable (in)', 'Minimum depth (ft)', 'Source cells'],
                   [[p.footing, p.diameter_criteria.get('table'), p.diameter_criteria.get('tip_deflection'),
                     p.diameter_criteria.get('nonrecoverable_deflection'), p.diameter_criteria.get('minimum_depth'),
                     p.diameter_criteria.get('source_cells')] for p in report.piers]), '',
             '## Pier input source cells', '',
             table(['Footing', 'Input', 'Source'], [[p.footing, key, cell] for p in report.piers for key, cell in p.source_cells.items()]), '',
             '## Extracted soil parameters', '',
             'START/END are depths in feet, positive downward from zero at the top of the hole. Layers follow worksheet order with shared boundaries.', '',
             table(['Footings', 'Boring', 'Table', 'Layer', 'Parameter', 'Source value', 'Parsed value', 'Units', 'Source cell', 'Finding'], soil_report_rows(report)), '',
             '## Validation findings', '',
             table(['Severity', 'Footing', 'Source', 'Finding'],
                   [[i.severity, i.footing or 'All / soil profile', i.source, i.message] for i in report.issues]), '',
             '## All extracted combination reactions', '',
             'Forces are N; moments are N-m. Original signs and complete node/combination vectors are preserved; no summation or envelope-only reduction.', '',
             table(['Footing', 'Model', 'Group', 'Node', 'Combination', 'Name', 'FX', 'FY', 'FZ', 'MX', 'MY', 'MZ'],
                   [[r.get(k) for k in ['mark', 'model', 'group', 'node', 'case', 'case_name', 'FX', 'FY', 'FZ', 'MX', 'MY', 'MZ']]
                    for p in report.piers for r in p.reactions]), '']
    return '\n'.join(lines)
