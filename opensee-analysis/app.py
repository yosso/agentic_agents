"""Desktop batch embedment sizing for the adjacent OpenSeesPy CLI."""
import argparse
import json
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from model import ROOT, batch, read_json, select_cases, starting_depth
from capacity import capacity_search
from input_screen import InputPreparation
from envelope import EnvelopeView
import importlib.util
_spec = importlib.util.spec_from_file_location('_integrated_settings_editor', ROOT/'pile-settings-builder/app.py')
_builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_builder)


class AnalysisApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('OpenSeesPy footing analysis & depth sizing')
        self.geometry('1200x850')
        self.minsize(950, 650)
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.running = False
        self.fields = {'inputs': tk.StringVar()}
        shared = ttk.Frame(self, padding=12)
        shared.pack(fill='x')
        ttk.Label(shared, text='Prepared inputs JSON:').pack(side='left')
        source_entry = ttk.Entry(shared, textvariable=self.fields['inputs'])
        source_entry.pack(side='left', fill='x', expand=True, padx=8)
        source_entry.bind('<FocusOut>', lambda event: self.normalize_path(self.fields['inputs']))
        ttk.Button(shared, text='Browse...', command=lambda: self.browse('inputs')).pack(side='left')
        ttk.Button(shared, text='Load / refresh', command=self.load_footings).pack(side='left', padx=6)
        ttk.Button(shared, text='Import settings (optional)...', command=self.import_settings).pack(side='left')
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill='both', expand=True)
        panel = ttk.Frame(self.tabs, padding=14)
        self.tabs.add(panel, text='Step 2 · Batch analysis')
        self.editor = _builder.SettingsEditor(self.tabs, integrated=True)
        self.envelope = EnvelopeView(self.editor.tabs, self.editor)
        self.editor.tabs.add(self.envelope, text='Load combination envelope')
        self.tabs.insert(0, self.editor, text='Step 1 · Settings')
        self.preparation = InputPreparation(self.tabs, self.prepared_ready, lambda: self.running)
        self.tabs.insert(0, self.preparation, text='Step 0 · Excel & Robot inputs')
        self.tabs.select(self.preparation)
        ttk.Label(panel, text='Footing deflection & embedment search', font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        ttk.Label(panel, text='Uses all tied extreme load vectors for each selected footing. Diameter stays fixed; depth increases until the configured deflection check passes.', wraplength=1100).pack(anchor='w', pady=6)
        paths = ttk.Frame(panel)
        paths.pack(fill='x')
        definitions = [('output', 'New output folder', str(ROOT/'opensee-analysis/results/new-run')),
                       ('python', 'Solver Python interpreter', str(ROOT/'openseespy-cli/.venv/Scripts/python.exe'))]
        for row, (key, title, default) in enumerate(definitions):
            self.fields[key] = tk.StringVar(value=default)
            ttk.Label(paths, text=title).grid(row=row, column=0, sticky='w', pady=4)
            entry = ttk.Entry(paths, textvariable=self.fields[key])
            entry.grid(row=row, column=1, sticky='ew', padx=8)
            entry.bind('<FocusOut>', lambda event, variable=self.fields[key]: self.normalize_path(variable))
            ttk.Button(paths, text='Browse...', command=lambda k=key: self.browse(k)).grid(row=row, column=2)
        paths.columnconfigure(1, weight=1)
        ttk.Label(panel, text='Review material, soil mappings, load signs and solver controls in Step 1. Those settings apply to the selected footings; reaction cases are selected automatically. Depth starts at the greater of the Step 1 trial embedment and the workbook minimum for each footing.', wraplength=1100).pack(anchor='w', pady=8)
        controls = ttk.Frame(panel)
        controls.pack(fill='x', pady=6)
        self.increment = tk.StringVar(value='1')
        self.maximum = tk.StringVar(value='60')
        self.mode = tk.StringVar(value='resultant')
        for title, variable in [('Depth increment (ft)', self.increment), ('Maximum depth (ft)', self.maximum)]:
            ttk.Label(controls, text=title).pack(side='left', padx=(0, 6))
            ttk.Entry(controls, textvariable=variable, width=8).pack(side='left', padx=(0, 16))
        ttk.Label(controls, text='Deflection check:').pack(side='left')
        ttk.Combobox(controls, textvariable=self.mode, values=('directional', 'resultant'), state='readonly', width=14).pack(side='left', padx=6)
        ttk.Label(panel, text='Directional: each plane ≤ allowable. Resultant: √(X² + Y²) ≤ allowable. Uses absolute head displacement; does not evaluate residual deflection or full design acceptance.', wraplength=1100).pack(anchor='w', pady=4)
        footings = ttk.Frame(panel)
        footings.pack(fill='x', pady=8)
        self.list = tk.Listbox(footings, selectmode='extended', exportselection=False, height=5)
        self.list.pack(side='left', fill='x', expand=True)
        ttk.Button(footings, text='Load / refresh footings', command=self.load_footings).pack(side='left', padx=8)
        ttk.Button(footings, text='Select all', command=lambda: self.list.selection_set(0, 'end')).pack(side='left')
        actions = ttk.Frame(panel)
        actions.pack(fill='x')
        self.run_button = ttk.Button(actions, text='Run selected footings', command=self.start)
        self.run_button.pack(side='left')
        self.cancel_button = ttk.Button(actions, text='Cancel after current solver run', command=self.stop.set, state='disabled')
        self.cancel_button.pack(side='left', padx=8)
        self.status = tk.StringVar(value='Open prepared inputs, then review the integrated settings in Step 1.')
        ttk.Label(panel, textvariable=self.status, wraplength=1100).pack(anchor='w', pady=8)
        columns = ('footing', 'status', 'depth', 'deflection', 'allowable', 'shear', 'moment')
        self.table = ttk.Treeview(panel, columns=columns, show='headings', height=7)
        for key, title in zip(columns, ('Footing', 'Status', 'Depth (ft)', 'Deflection (in)', 'Allowable (in)', 'Max shear (kip)', 'Max moment (kip-ft)')):
            self.table.heading(key, text=title)
            self.table.column(key, width=145)
        self.table.pack(fill='x')
        self.log = tk.Text(panel, height=8, wrap='word', state='disabled')
        self.log.pack(fill='both', expand=True, pady=8)
        capacity_panel = ttk.Frame(self.tabs, padding=16)
        self.tabs.add(capacity_panel, text='Step 3 · Load limit at default embedment')
        ttk.Label(capacity_panel, text='Load limit at allowable deflection', font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        ttk.Label(capacity_panel, text='Select a footing and coincident reaction in Step 1. The search fixes depth at the workbook minimum and scales all six reaction components together, retaining their proportions. Combined head deflection = √(X² + Y²).', wraplength=1100).pack(anchor='w', pady=10)
        ttk.Label(capacity_panel, text='Reports a displacement-limited load along this case’s loading path. Applied shear/moment and internal force maxima are separate quantities; this is not a structural strength check.', wraplength=1100).pack(anchor='w', pady=8)
        settings_row = ttk.Frame(capacity_panel)
        settings_row.pack(fill='x', pady=8)
        self.capacity_max = tk.StringVar(value='1024')
        self.capacity_tolerance = tk.StringVar(value='0.01')
        for title, variable in [('Maximum load multiplier', self.capacity_max), ('Relative bracket tolerance', self.capacity_tolerance)]:
            ttk.Label(settings_row, text=title).pack(side='left', padx=(0, 6))
            ttk.Entry(settings_row, textvariable=variable, width=10).pack(side='left', padx=(0, 18))
        self.capacity_output = tk.StringVar(value=str(ROOT/'opensee-analysis/results/capacity-new-run'))
        ttk.Label(capacity_panel, text='New capacity output folder:').pack(anchor='w')
        capacity_path_entry = ttk.Entry(capacity_panel, textvariable=self.capacity_output)
        capacity_path_entry.pack(fill='x', pady=6)
        capacity_path_entry.bind('<FocusOut>', lambda event: self.normalize_path(self.capacity_output))
        self.capacity_button = ttk.Button(capacity_panel, text='Search selected case at workbook minimum depth', command=self.start_capacity)
        self.capacity_button.pack(anchor='w', pady=8)
        ttk.Button(capacity_panel, text='Cancel after current solver run', command=self.stop.set).pack(anchor='w')
        ttk.Label(capacity_panel, textvariable=self.status, wraplength=1100).pack(anchor='w', pady=8)
        ttk.Button(capacity_panel, text='Open saved capacity-summary.json...', command=self.open_capacity_report).pack(anchor='w', pady=(0, 6))
        self.capacity_overview = ttk.Label(capacity_panel, wraplength=1100)
        self.capacity_overview.pack(anchor='w', pady=(0, 6))
        result_tabs = ttk.Notebook(capacity_panel)
        result_tabs.pack(fill='both', expand=True)
        self.capacity_summary = self.result_table(result_tabs, 'Load limit', ('Search', 'Result', 'Value', 'Units'))
        self.capacity_forces = self.result_table(result_tabs, 'Internal force maxima', ('Search', 'Quantity', 'Absolute maximum', 'Units', 'Depth (ft)', 'Plane', 'Element', 'End', 'Result folder'))
        self.capacity_trials = self.result_table(result_tabs, 'Search trials', ('Search', 'Trial', 'Multiplier', 'Deflection (in)', 'Check', 'Applied shear (kip)', 'Applied moment (kip-ft)', 'X deflection (in)', 'Y deflection (in)'))
        raw_frame = ttk.Frame(result_tabs)
        result_tabs.add(raw_frame, text='JSON details')
        self.capacity_text = tk.Text(raw_frame, wrap='word', state='disabled')
        raw_scroll = ttk.Scrollbar(raw_frame, orient='vertical', command=self.capacity_text.yview)
        raw_scroll.pack(side='right', fill='y')
        self.capacity_text.pack(fill='both', expand=True)
        self.capacity_text.configure(yscrollcommand=raw_scroll.set)
        self.editor.fields['embedment_ft'].trace_add('write', lambda *_: self.refresh_footing_depths())
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(150, self.poll)

    def prepared_ready(self, path, errors):
        self.fields['inputs'].set(str(Path(path)))
        self.load_footings()
        self.status.set(f'Prepared inputs loaded. {errors} source errors; review Step 0 findings and Step 1 settings.')
        if not errors:
            self.tabs.select(self.editor)

    def result_table(self, tabs, title, columns):
        frame = ttk.Frame(tabs)
        tabs.add(frame, text=title)
        tree = ttk.Treeview(frame, columns=columns, show='headings')
        for column in columns:
            tree.heading(column, text=column)
            tree.column(column, width=160, stretch=False)
        tree.grid(row=0, column=0, sticky='nsew')
        vertical = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
        horizontal.grid(row=1, column=0, sticky='ew')
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        return tree

    def open_capacity_report(self):
        if self.running:
            return
        path = filedialog.askopenfilename(title='Open capacity report', filetypes=[('JSON', '*.json')])
        if path:
            try:
                report = read_json(path)
                if not all(key in report for key in ('footing', 'depth_ft', 'allowable_in', 'searches')):
                    raise ValueError('Select a capacity-summary.json report.')
                self.render_capacity_report(report)
            except Exception as exc:
                messagebox.showerror('Cannot open report', str(exc))

    def render_capacity_report(self, report):
        def display(value):
            if value is None:
                return '—'
            return f'{value:.6g}' if isinstance(value, (int, float)) else str(value)
        self.capacity_overview.configure(text=f"Footing {report['footing']} | Fixed embedment {report['depth_ft']:g} ft | Allowable combined deflection {report['allowable_in']:g} in")
        for tree in (self.capacity_summary, self.capacity_forces, self.capacity_trials):
            tree.delete(*tree.get_children())
        metrics = [('status', 'Search status', ''), ('lower_passing_factor', 'Passing multiplier', '×'),
                   ('upper_failing_factor', 'Failing multiplier', '×'), ('passing_deflection_in', 'Passing combined deflection', 'in'),
                   ('upper_deflection_in', 'Failing combined deflection', 'in'), ('applied_shear_kip', 'Applied resultant shear at passing load', 'kip'),
                   ('applied_moment_kip_ft', 'Applied resultant moment at passing load', 'kip-ft'), ('message', 'Finding', '')]
        for search in report['searches']:
            path = search['path']
            for key, label, unit in metrics:
                if key in search:
                    self.capacity_summary.insert('', 'end', values=(path, label, display(search[key]), unit))
            for quantity, force in search.get('internal_force_envelopes', {}).items():
                if force:
                    self.capacity_forces.insert('', 'end', values=(path, quantity.title(), display(force['absolute_value']), force['unit'], display(force['depth_ft']), force['plane'], force['element'], force['end'], force['results_folder']))
            for index, trial in enumerate(search.get('trials', []), 1):
                responses = {r['plane']: r['head_deflection_in'] for r in trial.get('cases', [])}
                check = ('Pass' if trial['passed'] else 'Exceeds allowable') if 'passed' in trial else 'Incomplete'
                self.capacity_trials.insert('', 'end', values=(path, index, display(trial.get('factor')), display(trial.get('deflection_in')), check,
                                                               display(trial.get('applied_shear_kip')), display(trial.get('applied_moment_kip_ft')),
                                                               display(responses.get('X')), display(responses.get('Y'))))
        for note in report.get('limitations', []):
            self.capacity_summary.insert('', 'end', values=('', 'Limitation', note, ''))
        self.capacity_text.configure(state='normal')
        self.capacity_text.delete('1.0', 'end')
        self.capacity_text.insert('1.0', json.dumps(report, indent=2))
        self.capacity_text.configure(state='disabled')

    def normalize_path(self, variable):
        value = variable.get().strip()
        if value:
            variable.set(os.path.normpath(value))

    def browse(self, key):
        if self.running:
            return
        if key == 'output':
            parent = filedialog.askdirectory(title='Choose parent for a NEW result folder')
            path = str(Path(parent)/'new-run') if parent else ''
        else:
            path = filedialog.askopenfilename(title=key, filetypes=[('JSON', '*.json')] if key != 'python' else [('Python executable', '*.exe')])
        if path:
            self.fields[key].set(os.path.normpath(path))
            if key == 'inputs':
                self.load_footings()

    def load_footings(self):
        if self.running:
            return
        try:
            self.document = read_json(self.fields['inputs'].get())
            self.piers = self.document['piers']
            self.editor.load_source(self.fields['inputs'].get())
            self.envelope.load(self.document)
            self.refresh_footing_depths()
            self.list.selection_set(0, 'end')
        except Exception as exc:
            messagebox.showerror('Cannot load footings', str(exc))

    def refresh_footing_depths(self):
        if not hasattr(self, 'piers'):
            return
        selected = self.list.curselection()
        self.list.delete(0, 'end')
        for p in self.piers:
            try:
                start = f"{starting_depth(p, self.editor.fields['embedment_ft'].get()):g} ft"
            except (ValueError, TypeError, KeyError):
                start = 'enter a valid trial depth in Step 1'
            cases = select_cases(p)
            self.list.insert('end', f"{p['footing']} | {len(cases)} extreme vectors | workbook min {p['minimum_embedment_ft']} ft | batch start {start} | allowable {p['allowable_deflection_in']} in")
        for index in selected:
            if index < len(self.piers):
                self.list.selection_set(index)

    def import_settings(self):
        if self.running:
            return
        path = filedialog.askopenfilename(title='Import existing settings', filetypes=[('JSON', '*.json')])
        if not path:
            return
        try:
            settings = read_json(path)
            settings.setdefault('projection_height_ft', 1)
            values = {**settings, **settings['material'], **settings['load_signs'], **settings['opensees']}
            for key, variable in self.editor.fields.items():
                if key in values:
                    variable.set(str(values[key]))
            for label, mapping in settings['soil_models'].items():
                if label not in self.editor.soils:
                    self.editor.add_soil_row(label)
                for key, value in mapping.items():
                    if key in self.editor.soils[label]:
                        self.editor.soils[label][key].set(str(value))
            self.status.set('Settings imported. Review Step 1 before running.')
        except Exception as exc:
            messagebox.showerror('Cannot import settings', str(exc))

    def start(self):
        if self.preparation.busy:
            messagebox.showinfo('Reading Robot', 'Wait for input preparation to finish first.')
            return
        if self.running:
            return
        try:
            # Refresh source to ensure list selections still reference the displayed file.
            document = read_json(self.fields['inputs'].get())
            if not hasattr(self, 'document') or document != self.document:
                self.load_footings()
                return
            marks = [self.piers[i]['footing'] for i in self.list.curselection()]
            if not marks:
                raise ValueError('Select at least one footing.')
            options = {k: v.get() for k, v in self.fields.items()}
            options.update(increment=float(self.increment.get()), max_depth=float(self.maximum.get()), mode=self.mode.get(), footings=marks)
            options['template'] = self.editor.collect()
            if Path(options['output']).exists():
                raise ValueError('Output folder already exists. Enter a new folder name.')
        except Exception as exc:
            messagebox.showerror('Check inputs', str(exc))
            return
        self.running = True
        self.stop.clear()
        self.run_button.configure(state='disabled')
        self.capacity_button.configure(state='disabled')
        self.cancel_button.configure(state='normal')
        self.table.delete(*self.table.get_children())
        def work():
            try:
                report = batch(**options, progress=lambda m: self.events.put(('progress', m)), cancelled=self.stop.is_set)
                self.events.put(('done', report))
            except Exception as exc:
                self.events.put(('error', str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def start_capacity(self):
        if self.preparation.busy:
            messagebox.showinfo('Reading Robot', 'Wait for input preparation to finish first.')
            return
        if self.running:
            return
        try:
            document = read_json(self.fields['inputs'].get())
            if not hasattr(self, 'document') or document != self.document:
                raise ValueError('Load / refresh prepared inputs using the shared selector above first.')
            settings = self.editor.collect()
            options = dict(inputs=self.fields['inputs'].get(), template=settings,
                           output=self.capacity_output.get(), python=self.fields['python'].get(),
                           max_factor=float(self.capacity_max.get()), tolerance=float(self.capacity_tolerance.get()))
            if Path(options['output']).exists():
                raise ValueError('Choose a new capacity output folder.')
        except Exception as exc:
            messagebox.showerror('Check capacity inputs', str(exc))
            return
        self.running = True
        self.stop.clear()
        self.run_button.configure(state='disabled')
        self.capacity_button.configure(state='disabled')
        self.cancel_button.configure(state='normal')
        def work():
            try:
                report = capacity_search(**options, progress=lambda m: self.events.put(('progress', m)), cancelled=self.stop.is_set)
                self.events.put(('capacity_done', report))
            except Exception as exc:
                self.events.put(('error', str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        while not self.events.empty():
            kind, value = self.events.get()
            if kind == 'progress':
                self.status.set(value)
                self.log.configure(state='normal')
                self.log.insert('end', value+'\n')
                self.log.see('end')
                self.log.configure(state='disabled')
            else:
                self.running = False
                self.run_button.configure(state='normal')
                self.capacity_button.configure(state='normal')
                self.cancel_button.configure(state='disabled')
                if kind == 'error':
                    self.status.set(value)
                    messagebox.showerror('Analysis stopped', value)
                elif kind == 'capacity_done':
                    self.render_capacity_report(value)
                    self.status.set('Load search finished. See capacity-summary.json and trial result folders.')
                else:
                    for row in value['footings']:
                        def display(key):
                            v = row.get(key)
                            return f'{v:.6g}' if isinstance(v, (int, float)) else v or ''
                        self.table.insert('', 'end', values=[display(k) for k in ('footing', 'status', 'accepted_depth_ft', 'checked_deflection_in', 'allowable_in', 'max_shear_kip', 'max_moment_kip_ft')])
                        if row.get('status') != 'deflection_pass':
                            self.log.configure(state='normal')
                            self.log.insert('end', f"{row['footing']}: {row.get('message', '')}\n")
                            self.log.configure(state='disabled')
                    self.status.set('Batch finished. See batch-summary.json and footings.csv in the output folder.')
        self.after(150, self.poll)

    def close(self):
        if self.preparation.busy:
            messagebox.showinfo('Reading Robot', 'Wait for input preparation to finish before closing.')
            return
        if self.running:
            self.stop.set()
            self.status.set('Cancellation requested. Wait for the current solver run, then close.')
        else:
            self.destroy()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path)
    parser.add_argument('--settings', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--increment', type=float, default=1)
    parser.add_argument('--max-depth', type=float, default=60)
    parser.add_argument('--check', choices=('directional', 'resultant'), default='resultant')
    parser.add_argument('--python', type=Path)
    args = parser.parse_args()
    if args.inputs:
        if not args.settings or not args.output:
            parser.error('--settings and --output are required with --inputs')
        report = batch(args.inputs, args.settings, args.output, args.increment, args.max_depth, args.check, args.python, progress=print)
        print(json.dumps(report, indent=2))
        raise SystemExit(0 if all(r['status'] == 'deflection_pass' for r in report['footings']) else 2)
    AnalysisApp().mainloop()
