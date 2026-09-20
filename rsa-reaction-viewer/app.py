"""Small desktop viewer for Robot support-group counts and saved reactions."""
import csv
import json
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import config
from data import read_mapping, parse_cases, display_reaction, assess_group, controlling_combinations
from pier_designs import prepare_pier_designs, Issue


class Viewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Robot • Support reactions')
        self.geometry('1320x820')
        self.minsize(980, 650)
        self.mappings, self.reactions = [], []
        self.messages = queue.Queue()
        self.busy = False
        self.extraction = None
        self.preparation = None
        self.workbook = tk.StringVar(value=str(config.DEFAULT_WORKBOOK))
        self.sheet = tk.StringVar(value=config.MAPPING_SHEET_NAME)
        self.table = tk.StringVar(value=config.MAPPING_TABLE_NAME)
        self.api = tk.StringVar(value=config.find_robot_api())
        self.cases = tk.StringVar()
        self.units = tk.StringVar(value='kip / kip-ft')
        self.filter = tk.StringVar()
        self.status = tk.StringVar(value='Load the saved workbook mapping to begin.')
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('Treeview', rowheight=25)
        style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'))
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='Robot support reactions', style='Title.TLabel').pack(anchor='w')
        ttk.Label(outer, text='Excel group mapping → Robot support nodes → saved global reactions').pack(anchor='w', pady=(2, 12))
        form = ttk.Frame(outer)
        form.pack(fill='x')
        form.columnconfigure(1, weight=1)
        for row, (label, variable) in enumerate([('Workbook', self.workbook), ('Mapping sheet', self.sheet),
                                                ('Mapping table', self.table), ('Robot API DLL', self.api)]):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky='w', padx=(0, 10), pady=3)
            ttk.Entry(form, textvariable=variable).grid(row=row, column=1, sticky='ew', pady=3)
        ttk.Button(form, text='Browse…', command=self.browse).grid(row=0, column=2, padx=(8, 0))
        toolbar = ttk.Frame(outer)
        toolbar.pack(fill='x', pady=10)
        self.load_button = ttk.Button(toolbar, text='1. Load mapping', command=self.load)
        self.load_button.pack(side='left')
        ttk.Label(toolbar, text='Combinations:').pack(side='left', padx=(16, 5))
        ttk.Entry(toolbar, textvariable=self.cases, width=20).pack(side='left')
        ttk.Label(toolbar, text='Blank = all supported combinations').pack(side='left', padx=6)
        self.read_button = ttk.Button(toolbar, text='2. Read Robot models', command=self.read, state='disabled')
        self.read_button.pack(side='right')
        self.progress = ttk.Progressbar(outer, mode='indeterminate')
        self.progress.pack(fill='x')
        tabs = ttk.Notebook(outer)
        tabs.pack(fill='both', expand=True, pady=10)
        group_frame = ttk.Frame(tabs, padding=6)
        reaction_frame = ttk.Frame(tabs, padding=6)
        controlling_frame = ttk.Frame(tabs, padding=6)
        log_frame = ttk.Frame(tabs, padding=6)
        prepare_frame = ttk.Frame(tabs, padding=6)
        tabs.add(group_frame, text='Groups & node quantities')
        tabs.add(reaction_frame, text='Node reactions')
        tabs.add(controlling_frame, text='Controlling combinations')
        tabs.add(prepare_frame, text='Prepare pier designs')
        tabs.add(log_frame, text='Read log')
        ttk.Label(group_frame, text='Red rows require review. Expected = Excel FOOTING QTY; Nodes / Supports = Robot. Select a row for the source cell and details.').pack(anchor='w', pady=(0, 6))
        self.group_details = tk.StringVar()
        ttk.Label(group_frame, textvariable=self.group_details, wraplength=1150).pack(anchor='w', pady=(0, 6))
        self.group_findings = {}
        self.groups = self.grid_table(group_frame, ['Footing', 'Model', 'Group', 'Expected', 'Nodes', 'Supports', 'Reaction rows', 'Status', 'Node IDs'])
        self.groups.tag_configure('review', background='#ffe0df', foreground='#8b1616')
        self.groups.bind('<<TreeviewSelect>>', self.show_group_details)
        controls = ttk.Frame(reaction_frame)
        controls.pack(fill='x', pady=(0, 6))
        ttk.Label(controls, text='Units').pack(side='left')
        unit_box = ttk.Combobox(controls, textvariable=self.units, values=['kip / kip-ft', 'kN / kN-m', 'N / N-m'], width=16, state='readonly')
        unit_box.pack(side='left', padx=6)
        unit_box.bind('<<ComboboxSelected>>', lambda _: self.render_reactions())
        ttk.Label(controls, text='Filter (footing, group, node, combination)').pack(side='left', padx=(12, 6))
        ttk.Entry(controls, textvariable=self.filter, width=26).pack(side='left')
        self.filter.trace_add('write', lambda *_: self.render_reactions())
        ttk.Button(controls, text='Export visible CSV…', command=self.export).pack(side='right')
        self.reaction_columns = ['Footing', 'Model', 'Group', 'Node', 'Combination', 'Combination name', 'FX', 'FY', 'FZ', 'MX', 'MY', 'MZ']
        self.values = self.grid_table(reaction_frame, self.reaction_columns)
        ttk.Label(reaction_frame, text='Global support reactions as reported by Robot. Signs preserved; no sums or conversion to applied footing loads.').pack(anchor='w', pady=5)
        ttk.Label(controlling_frame, text='Per footing group A, B, C, etc.: maximum shear √(Fx²+Fy²), bending √(Mx²+My²), |Mz|, compression (+Fz), and uplift (−Fz). Z is vertical.', wraplength=1150).pack(anchor='w', pady=5)
        ttk.Label(controlling_frame, text='Each row retains all six reactions from its governing node/combination. Exact ties show the first source and tie count. This is a load envelope, not a capacity or deflection check.', wraplength=1150).pack(anchor='w', pady=5)
        control_units = ttk.Combobox(controlling_frame, textvariable=self.units, values=['kip / kip-ft', 'kN / kN-m', 'N / N-m'], width=16, state='readonly')
        control_units.pack(anchor='w', pady=5)
        control_units.bind('<<ComboboxSelected>>', lambda _: self.render_reactions())
        self.controllers = self.grid_table(controlling_frame, ['Footing', 'Criterion', 'Value', 'Units', 'Combination', 'Combination name', 'Node', 'Model', 'Group', 'Ties', 'FX', 'FY', 'FZ', 'MX', 'MY', 'MZ'])
        self.controllers.column('Criterion', width=190)
        ttk.Label(controlling_frame, text='Based only on successfully extracted combinations; the Node reactions text filter does not change this envelope. Review group mismatches and skipped/failed reads in the other tabs.', wraplength=1150).pack(anchor='w', pady=5)
        self.log = tk.Text(log_frame, wrap='word', height=8, state='disabled')
        self.log.pack(fill='both', expand=True)
        prep_controls = ttk.Frame(prepare_frame)
        prep_controls.pack(fill='x')
        ttk.Button(prep_controls, text='Prepare & validate inputs', command=self.prepare).pack(side='left')
        ttk.Button(prep_controls, text='Export preparation JSON…', command=self.export_preparation).pack(side='left', padx=8)
        self.preparation_status = tk.StringVar(value='Read Robot combinations, then prepare the saved workbook inputs. OpenSeesPy is not run.')
        ttk.Label(prepare_frame, textvariable=self.preparation_status, wraplength=1150).pack(anchor='w', pady=8)
        self.prepared = self.grid_table(prepare_frame, ['Footing', 'Boring', 'Soil table', 'Layers', 'Diameter (ft)', 'Minimum depth (ft)', 'Water depth (ft)', 'Allowable (in)', 'Combinations/node rows'])
        self.validation = self.grid_table(prepare_frame, ['Severity', 'Footing', 'Source', 'Finding'])
        self.validation.column('Source', width=270)
        self.validation.column('Finding', width=800)
        self.validation.tag_configure('error', background='#ffe0df', foreground='#8b1616')
        ttk.Label(outer, textvariable=self.status, wraplength=1200).pack(anchor='w')
        ttk.Label(outer, text='Save Excel changes first. Open Robot: reads only its current model. Close Robot for multi-file reads. No models are recalculated or saved.').pack(anchor='w', pady=(5, 0))
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(150, self.poll)

    def grid_table(self, parent, columns):
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=columns, show='headings', selectmode='browse')
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=220 if col in ['Model', 'Group', 'Status', 'Combination name', 'Node IDs'] else 95, stretch=False)
        tree.grid(row=0, column=0, sticky='nsew')
        x = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
        y = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(xscrollcommand=x.set, yscrollcommand=y.set)
        x.grid(row=1, column=0, sticky='ew')
        y.grid(row=0, column=1, sticky='ns')
        return tree

    def browse(self):
        filename = filedialog.askopenfilename(filetypes=[('Excel workbook', '*.xlsm *.xlsx')])
        if filename:
            self.workbook.set(filename)

    def load(self):
        self.clear_preparation()
        self.extraction = None
        self.group_details.set('')
        self.group_findings.clear()
        self.mappings = []
        self.reactions = []
        self.groups.delete(*self.groups.get_children())
        self.render_reactions()
        self.read_button.configure(state='disabled')
        try:
            self.mappings = read_mapping(self.workbook.get(), self.sheet.get(), self.table.get())
            for item in self.mappings:
                iid = self.groups.insert('', 'end', values=[item['mark'], item['model'], item['group'], item['expected'], '', '', '',
                                                      'Not checked' if item['exists'] else 'Model file not found', ''],
                                         tags=() if item['exists'] else ('review',))
                self.group_findings[iid] = f"Excel row {item['row']}: {config.MODEL_COLUMN} = {item['model']}. " + ('Ready to check against Robot.' if item['exists'] else 'File not found; check the workbook filename/path.')
            self.status.set(f'{len(self.mappings)} group mappings loaded. Expected quantities come from Excel; actual counts come from Robot.')
            self.read_button.configure(state='normal')
        except Exception as error:
            self.status.set(str(error))
            messagebox.showerror('Cannot load mapping', str(error))

    def read(self):
        self.clear_preparation()
        self.extraction = None
        try:
            cases = parse_cases(self.cases.get())
            if not Path(self.api.get()).is_file():
                raise ValueError('Select an installed Robot Interop.RobotOM.dll.')
            request = dict(api=self.api.get(), mappings=self.mappings, cases=cases)
        except Exception as error:
            messagebox.showerror('Cannot read models', str(error))
            return
        self.busy = True
        self.load_button.configure(state='disabled')
        self.read_button.configure(state='disabled')
        self.reactions = []
        self.render_reactions()
        self.groups.delete(*self.groups.get_children())
        self.group_findings.clear()
        self.group_details.set('')
        self.status.set('Opening Robot and reading mapped groups. Large models may take several minutes…')
        self.progress.start()
        threading.Thread(target=self.worker, args=(request,), daemon=True).start()

    def worker(self, request):
        try:
            with tempfile.TemporaryDirectory(prefix='rsa-viewer-') as temp:
                request_path, result_path = Path(temp) / 'request.json', Path(temp) / 'result.json'
                request_path.write_text(json.dumps(request), encoding='utf-8')
                process = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                    '-File', str(config.APP_DIR / 'read_robot.ps1'), '-RequestPath', str(request_path), '-ResultPath', str(result_path)],
                    capture_output=True, text=True, errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
                if not result_path.exists():
                    raise RuntimeError(process.stderr or process.stdout or f'Robot reader exited {process.returncode}')
                result = json.loads(result_path.read_text(encoding='utf-8-sig'))
                self.messages.put(result)
        except Exception as error:
            self.messages.put(dict(error=str(error), groups=[], reactions=[], warnings=[]))

    def poll(self):
        try:
            result = self.messages.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            self.extraction = result
            self.progress.stop()
            self.load_button.configure(state='normal')
            self.read_button.configure(state='normal')
            self.groups.delete(*self.groups.get_children())
            self.group_findings.clear()
            issues = []
            review_count = 0
            for group in result.get('groups', []):
                mapping = next(m for m in self.mappings if m['model'] == group['model'] and m['group'] == group['group'] and m['mark'] == group['mark'])
                verdict, findings, source = assess_group(group, mapping)
                description = f"Footing {group['mark']} / {group['group']} / {group['model']}: " + (' '.join(findings) or f'Quantities match at {source}.')
                if findings:
                    review_count += 1
                    issues.append(description)
                values = ([group.get(k, '') for k in
                    ['mark', 'model', 'group', 'expected', 'node_count', 'support_count', 'result_rows', 'status']] +
                    [', '.join(map(str, group.get('nodes', [])))])
                values[7] = verdict + (': ' + ' '.join(findings) if findings else '')
                iid = self.groups.insert('', 'end', values=values, tags=('review',) if findings else ())
                self.group_findings[iid] = description
                if findings and not self.groups.selection():
                    self.groups.selection_set(iid)
                    self.groups.see(iid)
            self.show_group_details()
            self.reactions = result.get('reactions', [])
            self.render_reactions()
            messages = ([result['error']] if result.get('error') else []) + result.get('warnings', []) + issues
            self.log.configure(state='normal')
            self.log.delete('1.0', 'end')
            self.log.insert('end', '\n\n'.join(messages) or 'Read completed without reported issues.')
            self.log.configure(state='disabled')
            self.status.set(result.get('error') or f'{len(result.get("groups", []))} groups • {review_count} require review • {len(self.reactions)} reaction rows • {len(messages)} notices. Select highlighted rows for the mismatched input.')
        self.after(150, self.poll)

    def show_group_details(self, _event=None):
        selected = self.groups.selection()
        self.group_details.set(self.group_findings.get(selected[0], '') if selected else '')

    def clear_preparation(self):
        self.preparation = None
        self.prepared.delete(*self.prepared.get_children())
        self.validation.delete(*self.validation.get_children())
        self.preparation_status.set('Inputs not yet prepared. OpenSeesPy is not run.')

    def prepare(self):
        if self.busy:
            messagebox.showinfo('Reading Robot', 'Wait for extraction to finish first.')
            return
        self.clear_preparation()
        try:
            report = prepare_pier_designs(self.workbook.get(), self.reactions)
            if not self.extraction:
                report.issues.append(Issue('ERROR', '', 'Robot extraction', 'Read Robot combinations before validating the joined inputs.'))
            else:
                if self.extraction.get('error'):
                    report.issues.append(Issue('ERROR', '', 'Robot extraction', self.extraction['error']))
                for group in self.extraction.get('groups', []):
                    if group.get('status') != 'OK':
                        report.issues.append(Issue('ERROR', group.get('mark', ''), 'Robot group', group.get('status', 'Not checked')))
                for warning in self.extraction.get('warnings', []):
                    report.issues.append(Issue('WARNING', '', 'Robot extraction', warning))
            self.preparation = report
            profiles = {p.table_name: p for p in report.soil_profiles}
            for pier in report.piers:
                profile = profiles.get(pier.soil_table)
                self.prepared.insert('', 'end', values=[pier.footing, pier.boring_id, pier.soil_table or 'UNRESOLVED',
                    len(profile.layers) if profile else 0, pier.diameter_ft, pier.minimum_embedment_ft,
                    pier.water_table_depth_ft, pier.allowable_deflection_in, len(pier.reactions)])
            for issue in report.issues:
                self.validation.insert('', 'end', values=[issue.severity, issue.footing, issue.source, issue.message],
                    tags=('error',) if issue.severity == 'ERROR' else ())
            errors = sum(i.severity == 'ERROR' for i in report.issues)
            self.preparation_status.set(f'{len(report.piers)} piers / {len(report.soil_profiles)} boring tables / {errors} errors. Raw soil units retained; no OpenSeesPy analysis performed.')
        except Exception as error:
            messagebox.showerror('Preparation failed', str(error))

    def export_preparation(self):
        if self.preparation is None:
            messagebox.showinfo('Prepare inputs', 'Prepare and validate inputs first.')
            return
        filename = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('Preparation JSON', '*.json')])
        if filename:
            try:
                Path(filename).write_text(json.dumps(self.preparation.to_dict(), indent=2, allow_nan=False), encoding='utf-8')
            except (OSError, ValueError) as error:
                messagebox.showerror('Export failed', str(error))

    def visible_rows(self):
        query = self.filter.get().casefold().strip()
        for row in self.reactions:
            identifiers = [row[k] for k in ['mark', 'model', 'group', 'node', 'case', 'case_name']]
            if not query or query in ' '.join(map(str, identifiers)).casefold():
                yield identifiers + display_reaction(row, self.units.get())

    def render_reactions(self):
        if not hasattr(self, 'values'):
            return
        self.values.delete(*self.values.get_children())
        force, moment = self.units.get().split(' / ')
        for component in ['FX', 'FY', 'FZ', 'MX', 'MY', 'MZ']:
            self.values.heading(component, text=f'{component} ({force if component.startswith("F") else moment})')
        for row in self.visible_rows():
            self.values.insert('', 'end', values=row[:6] + [f'{x:.5g}' for x in row[6:]])
        self.render_controllers()

    def render_controllers(self):
        self.controllers.delete(*self.controllers.get_children())
        force, moment = self.units.get().split(' / ')
        for component in ('FX', 'FY', 'FZ', 'MX', 'MY', 'MZ'):
            self.controllers.heading(component, text=f'{component} ({force if component.startswith("F") else moment})')
        for item in controlling_combinations(self.reactions):
            row = item['reaction']
            component = item['component']
            if row is None:
                self.controllers.insert('', 'end', values=[item['mark'], item['criterion'], 'None found', force, '—', 'No qualifying combination', '', '', '', 0] + [''] * 6)
                continue
            components = display_reaction(row, self.units.get())
            if component == 'H':
                value = (components[0] ** 2 + components[1] ** 2) ** 0.5
            elif component == 'MH':
                value = (components[3] ** 2 + components[4] ** 2) ** 0.5
            elif component == 'MZ':
                value = abs(components[5])
            else:
                value = components[2]
            self.controllers.insert('', 'end', values=[item['mark'], item['criterion'], f'{value:.5g}',
                moment if component.startswith('M') else force, row['case'], row['case_name'], row['node'],
                row['model'], row['group'], item['ties']] + [f'{v:.5g}' for v in components])

    def export(self):
        rows = list(self.visible_rows())
        if not rows:
            messagebox.showinfo('Export', 'No visible reaction rows to export.')
            return
        filename = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV', '*.csv')])
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8-sig') as stream:
                    writer = csv.writer(stream)
                    writer.writerow([self.values.heading(c)['text'] for c in self.reaction_columns])
                    # Prevent text labels being interpreted as Excel formulas.
                    writer.writerows([("'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@')) else v)
                                      for v in row] for row in rows)
                self.status.set(f'Exported {len(rows)} rows to {filename}')
            except OSError as error:
                messagebox.showerror('Export failed', str(error))

    def close(self):
        if self.busy:
            messagebox.showinfo('Reading Robot', 'Wait for the current read to finish before closing.')
        else:
            self.destroy()


if __name__ == '__main__':
    Viewer().mainloop()
