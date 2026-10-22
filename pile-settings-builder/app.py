"""Desktop editor for OpenSeesPy pier settings. Run with Python + Tkinter."""
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Load by path so this reusable editor can coexist with other apps' model.py.
import importlib.util
_spec = importlib.util.spec_from_file_location('_pile_settings_model', Path(__file__).with_name('model.py'))
_settings_model = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_settings_model)
ROOT, build_settings, check_prepared, concrete_modulus, defaults, read_source, save_settings, soil_labels, soil_layer_details, suggested_soil_model = (
    getattr(_settings_model, key) for key in ('ROOT', 'build_settings', 'check_prepared', 'concrete_modulus', 'defaults', 'read_source', 'save_settings', 'soil_labels', 'soil_layer_details', 'suggested_soil_model'))


class SettingsEditor(ttk.Frame):
    def __init__(self, master, integrated=False):
        super().__init__(master)
        self.integrated = integrated
        self.document = None
        self.source_path = None
        self.piers = []
        self.soils = {}
        self.fields = {}
        self.prepared = False
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='Create pile analysis settings', font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        ttk.Label(outer, text='Review shared material and soil settings. Batch analysis selects reactions, both planes and trial depths automatically.' if integrated else 'Open results → choose footing and reaction → edit material and soils → save settings.json').pack(anchor='w', pady=(4, 12))
        bar = ttk.Frame(outer)
        if not integrated:
            bar.pack(fill='x')
        ttk.Button(bar, text='Open results / prepared inputs…', command=self.open_source).pack(side='left')
        self.source_label = ttk.Label(bar, text='No file loaded')
        self.source_label.pack(side='left', padx=12)
        tabs = self.tabs = ttk.Notebook(outer)
        tabs.pack(fill='both', expand=True, pady=12)
        selection = ttk.Frame(tabs, padding=12)
        analysis = ttk.Frame(tabs, padding=12)
        soils = ttk.Frame(tabs, padding=12)
        preview = ttk.Frame(tabs, padding=12)
        for frame, label in ((selection, '1 · Footing & reaction'), (analysis, '2 · Analysis settings'), (soils, '3 · Soil models'), (preview, '4 · JSON & validation')):
            tabs.add(frame, text=label)
        self.footing = tk.StringVar()
        self.footing_box = ttk.Combobox(selection, textvariable=self.footing, state='readonly')
        ttk.Label(selection, text='Footing').pack(anchor='w')
        self.footing_box.pack(anchor='w', pady=5)
        self.footing_box.bind('<<ComboboxSelected>>', self.select_footing)
        self.pier_info = ttk.Label(selection, text='', wraplength=1000)
        self.pier_info.pack(anchor='w', pady=8)
        ttk.Label(selection, text='Select one coincident reaction row. Scroll horizontally for all components.').pack(anchor='w')
        unit_controls = ttk.Frame(selection)
        unit_controls.pack(anchor='w', pady=5)
        ttk.Label(unit_controls, text='Load display units:').pack(side='left')
        self.units = tk.StringVar(value='kip / kip-ft')
        unit_box = ttk.Combobox(unit_controls, textvariable=self.units,
                               values=('kip / kip-ft', 'kN / kN-m', 'N / N-m'),
                               state='readonly', width=16)
        unit_box.pack(side='left', padx=8)
        unit_box.bind('<<ComboboxSelected>>', self.render_reactions)
        columns = ('node', 'case', 'case_name', 'group', 'model', 'FX', 'FY', 'FZ', 'MX', 'MY', 'MZ')
        table_frame = ttk.Frame(selection)
        table_frame.pack(fill='both', expand=True)
        self.reactions = ttk.Treeview(table_frame, columns=columns, show='headings', selectmode='browse')
        for key in columns:
            unit = ' (kip)' if key in ('FX', 'FY', 'FZ') else ' (kip-ft)' if key in ('MX', 'MY', 'MZ') else ''
            self.reactions.heading(key, text=key + unit)
            self.reactions.column(key, width=170 if key in ('model', 'group', 'case_name') else 95, stretch=False)
        self.reactions.grid(row=0, column=0, sticky='nsew')
        ybar = ttk.Scrollbar(table_frame, orient='vertical', command=self.reactions.yview)
        ybar.grid(row=0, column=1, sticky='ns')
        xbar = ttk.Scrollbar(table_frame, orient='horizontal', command=self.reactions.xview)
        xbar.grid(row=1, column=0, sticky='ew')
        self.reactions.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        ttk.Label(analysis, text='Example values are starting points. Set the material, trial depth, and load signs for your analysis.').grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 12))
        base = defaults()
        values = {**base, **base['material'], **base['load_signs'], **base['opensees']}
        definitions = [
            ('E_psi', 'Modulus of elasticity (psi)', None),
            ('embedment_ft', 'Trial embedment (ft)', None),
            ('projection_height_ft', 'Projection above ground (ft)', None),
            ('mesh_size_ft', 'Mesh size (ft)', None),
            ('plane', 'Plane: X = FX/MY; Y = FY/MX', ('X', 'Y')),
            ('lateral', 'Lateral load sign', ('1', '-1')),
            ('moment', 'Moment load sign', ('1', '-1')),
            ('axial', 'Axial load sign', ('1', '-1')),
            ('unit_weight_pcf', 'Material unit weight (lb/ft³)', None),
            ('poisson_ratio', 'Poisson ratio', None),
            ('max_iterations', 'Maximum iterations', None),
            ('load_steps', 'Load steps', None),
            ('energy_tolerance_lbf_ft', 'Energy tolerance (lbf-ft)', None),
            ('water_unit_weight_pcf', 'Water unit weight (lb/ft³)', None),
            ('drag_ratio', 'Drag ratio (0–1)', None),
            ('transformation', 'Transformation', ('Linear', 'PDelta')),
        ]
        for i, (key, label, choices) in enumerate(definitions):
            row, col = i % 8 + 1, (i // 8) * 2
            ttk.Label(analysis, text=label).grid(row=row, column=col, sticky='w', padx=(0, 12), pady=9)
            var = self.fields[key] = tk.StringVar(value=str(values[key]))
            widget = ttk.Combobox(analysis, textvariable=var, values=choices, state='readonly', width=20) if choices else ttk.Entry(analysis, textvariable=var, width=23)
            widget.grid(row=row, column=col+1, sticky='w', padx=(0, 24))
        calculator = ttk.LabelFrame(analysis, text='Normal-weight concrete: Ec = 57,000 × √f′c (psi)', padding=10)
        calculator.grid(row=9, column=0, columnspan=4, sticky='ew', pady=(10, 0))
        ttk.Label(calculator, text='Concrete f′c (psi)').pack(side='left', padx=(0, 10))
        self.concrete_strength = tk.StringVar()
        entry = ttk.Entry(calculator, textvariable=self.concrete_strength, width=18)
        entry.pack(side='left', padx=(0, 12))
        entry.bind('<Return>', self.calculate_concrete)
        ttk.Button(calculator, text='Calculate & use Ec', command=self.calculate_concrete).pack(side='left')
        ttk.Label(calculator, text='Updates the editable modulus field above.').pack(side='left', padx=12)
        ttk.Label(analysis, text='Boundary: free head, axially fixed tip. Static loading. Unit weight and Poisson ratio are retained but unused by the elastic beam.', wraplength=950).grid(row=10, column=0, columnspan=4, sticky='w', pady=20)
        ttk.Label(soils, text='Layer labels come from the Excel MODEL column. Each group below lists the layers with that label. Choose a spring model for the group; each layer keeps its own property values.', wraplength=1000).pack(anchor='w')
        ttk.Label(soils, text='To change a layer label, edit its MODEL cell in Excel, export prepared inputs again, and reopen them here.', wraplength=1000).pack(anchor='w', pady=(4, 0))
        addbar = ttk.Frame(soils)
        addbar.pack(fill='x', pady=10)
        ttk.Label(addbar, text='Exact source label (for raw reaction drafts):').pack(side='left', padx=(0, 8))
        self.new_soil = tk.StringVar()
        ttk.Entry(addbar, textvariable=self.new_soil, width=35).pack(side='left')
        ttk.Button(addbar, text='Add model mapping', command=self.add_soil).pack(side='left', padx=8)
        canvas = tk.Canvas(soils, highlightthickness=0)
        scroll = ttk.Scrollbar(soils, orient='vertical', command=canvas.yview)
        scroll.pack(side='right', fill='y')
        canvas.pack(fill='both', expand=True)
        canvas.configure(yscrollcommand=scroll.set)
        self.soil_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.soil_frame, anchor='nw')
        self.soil_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        self.preview = tk.Text(preview, wrap='word', font=('Consolas', 10))
        preview_scroll = ttk.Scrollbar(preview, orient='vertical', command=self.preview.yview)
        preview_scroll.pack(side='right', fill='y')
        self.preview.configure(yscrollcommand=preview_scroll.set)
        self.preview.pack(fill='both', expand=True)
        self.preview.configure(state='disabled')
        self.status = tk.StringVar(value='Open a source JSON file to begin.')
        ttk.Label(outer, textvariable=self.status, wraplength=1100).pack(anchor='w', pady=5)
        actions = ttk.Frame(outer)
        actions.pack(fill='x')
        ttk.Button(actions, text='Preview & validate', command=self.preview_settings).pack(side='left')
        if not integrated:
            ttk.Button(actions, text='Save settings.json…', command=self.save).pack(side='right')

    def calculate_concrete(self, event=None):
        try:
            modulus = concrete_modulus(self.concrete_strength.get())
        except ValueError as exc:
            messagebox.showerror('Check concrete strength', str(exc))
            return
        self.fields['E_psi'].set(str(modulus))
        self.set_preview('Modulus updated. Click Preview & validate to refresh the settings JSON.')
        self.status.set(f'Calculated Ec = {modulus:,.2f} psi. This value will be saved as material.E_psi.')

    def open_source(self):
        path = filedialog.askopenfilename(title='Open viewer results or prepared pier inputs', initialdir=ROOT, filetypes=[('JSON', '*.json')])
        if not path:
            return
        try:
            self.load_source(path)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            messagebox.showerror('Cannot open source', str(exc))

    def load_source(self, path):
            document, piers, prepared = read_source(path)
            self.document, self.piers, self.prepared = document, piers, prepared
            self.source_path = Path(path)
            self.source_label.configure(text=f'{Path(path).name} — {"prepared inputs" if prepared else "raw reactions (draft)"}')
            self.footing_box.configure(values=[p['footing'] for p in piers])
            self.footing_box.current(0)
            self.select_footing()

    def selected_pier(self):
        return self.piers[self.footing_box.current()]

    def render_reactions(self, event=None):
        selected = self.reactions.selection()
        force_unit, moment_unit = self.units.get().split(' / ')
        for key in self.reactions['columns']:
            unit = force_unit if key in ('FX', 'FY', 'FZ') else moment_unit if key in ('MX', 'MY', 'MZ') else ''
            self.reactions.heading(key, text=f'{key} ({unit})' if unit else key)
        if not self.piers:
            return
        self.reactions.delete(*self.reactions.get_children())
        for index, row in enumerate(self.selected_pier()['reactions']):
            displayed = dict(row)
            for key in ('FX', 'FY', 'FZ', 'MX', 'MY', 'MZ'):
                if isinstance(row.get(key), (int, float)):
                    factor = (4448.2216152605 * (0.3048 if key.startswith('M') else 1)
                              if force_unit == 'kip' else 1000 if force_unit == 'kN' else 1)
                    displayed[key] = f'{row[key] / factor:.6g}'
            self.reactions.insert('', 'end', iid=str(index), values=[displayed.get(k, '') for k in self.reactions['columns']])
        if event is not None and selected and self.reactions.exists(selected[0]):
            self.reactions.selection_set(selected[0])
            self.reactions.focus(selected[0])
            self.reactions.see(selected[0])

    def select_footing(self, event=None):
        pier = self.selected_pier()
        self.render_reactions()
        previous = {label: {k: v.get() for k, v in fields.items()} for label, fields in self.soils.items()} if self.integrated else {}
        self.soils = {}
        for widget in self.soil_frame.winfo_children():
            widget.destroy()
        labels = list(dict.fromkeys(label for p in self.piers for label in soil_labels(self.document, p))) if self.integrated else soil_labels(self.document, pier)
        for label in labels:
            self.add_soil_row(label)
            for key, value in previous.get(label, {}).items():
                self.soils[label][key].set(value)
        if self.integrated and self.reactions.get_children():
            self.reactions.selection_set(self.reactions.get_children()[0])
        if self.prepared:
            self.pier_info.configure(text=f"Diameter: {pier.get('diameter_ft')} ft · Minimum depth: {pier.get('minimum_embedment_ft')} ft · Water depth: {pier.get('water_table_depth_ft')} ft · Soil table: {pier.get('soil_table')}")
            if pier.get('minimum_embedment_ft') is not None:
                self.fields['embedment_ft'].set(str(pier['minimum_embedment_ft']))
        else:
            self.pier_info.configure(text='Raw reactions contain no pier geometry or soil profile. Use prepared inputs from the viewer for full validation.')
        self.status.set('Select a reaction row and choose soil models. Analysis values are editable example defaults.')
        self.set_preview('')

    def add_soil(self):
        label = self.new_soil.get().strip()
        if label and label not in self.soils:
            self.add_soil_row(label)
            self.new_soil.set('')

    def add_soil_row(self, label):
        box = ttk.LabelFrame(self.soil_frame, text=f'Source layer label: {label}', padding=10)
        box.pack(fill='x', pady=6)
        fields = self.soils[label] = {}
        content = ttk.Frame(box)
        content.pack(fill='x')
        if self.integrated:
            details = []
            seen_tables = set()
            for pier in self.piers:
                table = pier.get('soil_table')
                if table in seen_tables:
                    continue
                seen_tables.add(table)
                details.extend(f'{table} | {detail}' for detail in soil_layer_details(self.document or {}, pier, label))
        else:
            details = soil_layer_details(self.document or {}, self.selected_pier() if self.piers else {}, label)
        ttk.Label(content, text='Layers using this label (depths below ground):' if details else 'No source layers available for this label. This entry only maps a label to a spring model.').pack(anchor='w', pady=(0, 4))
        for detail in details:
            ttk.Label(content, text=detail, wraplength=900).pack(anchor='w', pady=(0, 4))
        controls_frame = ttk.Frame(content)
        controls_frame.pack(fill='x')
        definitions = [('model', 'Spring model for this label', '', ('API_clay', 'API_sand')),
                       ('cohesion', 'Clay cohesion', 'cohesion_ultimate', ('cohesion_ultimate', 'cohesion_factored')),
                       ('strain', 'Clay strain', 'e50', ('e50', 'e50_factored')),
                       ('J', 'Clay J (0.25–0.5)', '0.5', None),
                       ('modulus', 'Sand modulus', 'k_static', ('k_static', 'k_static_factored'))]
        controls = {}
        for i, (key, title, value, choices) in enumerate(definitions):
            initial = suggested_soil_model(label) if key == 'model' else value
            var = fields[key] = tk.StringVar(value=initial)
            ttk.Label(controls_frame, text=title).grid(row=i // 3 * 2, column=i % 3, sticky='w', padx=8)
            options = ('',) + choices if key == 'model' else choices
            widget = ttk.Combobox(controls_frame, textvariable=var, values=options, state='readonly', width=25) if choices else ttk.Entry(controls_frame, textvariable=var, width=27)
            widget.grid(row=i // 3 * 2 + 1, column=i % 3, padx=8, pady=(0, 8))
            controls[key] = widget
        target = ttk.Label(controls_frame, wraplength=900)
        target.grid(row=5, column=0, columnspan=3, sticky='w', padx=8, pady=(0, 6))
        def update(*args):
            target.configure(text={
                'API_clay': 'Suggested clay analog -> PySimple1 soilType 1. Verify selected Su, epsilon50, and J.',
                'API_sand': 'Suggested sand/gravel analog -> PySimple1 soilType 2. Verify selected friction angle and modulus.',
                '': 'Unmapped. Prepared-input validation will block analysis if this layer is within the trial embedment.',
            }[fields['model'].get()])
            for key in ('cohesion', 'strain', 'J', 'modulus'):
                active = fields['model'].get() == ('API_sand' if key == 'modulus' else 'API_clay')
                controls[key].configure(state=('normal' if key == 'J' else 'readonly') if active else 'disabled')
        fields['model'].trace_add('write', update)
        update()
        if label not in soil_labels(self.document or {}, self.selected_pier() if self.piers else {}):
            def remove():
                self.soils.pop(label)
                box.destroy()
            ttk.Button(controls_frame, text='Remove label', command=remove).grid(row=6, column=0, sticky='w', padx=8)

    def collect(self):
        if self.document is None:
            raise ValueError('Open a source JSON file first.')
        selected = self.reactions.selection()
        if not selected and self.integrated and self.reactions.get_children():
            selected = (self.reactions.get_children()[0],)
        if not selected:
            raise ValueError('Select a reaction row on the first tab.')
        pier = self.selected_pier()
        return build_settings(pier, pier['reactions'][int(selected[0])],
                              {k: v.get() for k, v in self.fields.items()},
                              {label: {k: v.get() for k, v in fields.items()} for label, fields in self.soils.items()})

    def set_preview(self, text):
        self.preview.configure(state='normal')
        self.preview.delete('1.0', 'end')
        self.preview.insert('1.0', text)
        self.preview.configure(state='disabled')

    def preview_settings(self):
        try:
            settings = self.collect()
            if self.prepared:
                try:
                    check_prepared(self.document, settings)
                    status = 'VALID: settings and selected prepared inputs passed the CLI checks. No analysis was run.'
                    warnings = [f"{i.get('source', '')}: {i.get('message', '')}" for i in self.document.get('issues', []) if i.get('footing', '') in ('', settings['footing'])]
                    if warnings:
                        status += '\nSource findings:\n' + '\n'.join(warnings)
                except (ValueError, KeyError, TypeError, OverflowError) as exc:
                    status = f'DRAFT — prepared-input validation failed:\n{exc}'
            else:
                status = 'DRAFT — raw reactions only. Validate with prepared pier inputs before analysis.'
                if self.document.get('warnings'):
                    status += '\nExtraction warnings: ' + str(self.document['warnings'])
            self.status.set(status.split('\n')[0])
            self.set_preview(status + '\n\n' + json.dumps(settings, indent=2, allow_nan=False))
            return settings, status
        except (ValueError, KeyError, TypeError) as exc:
            self.status.set(str(exc))
            messagebox.showerror('Check settings', str(exc))
            return None

    def save(self):
        result = self.preview_settings()
        if result is None:
            return
        settings, status = result
        path = filedialog.asksaveasfilename(title='Save settings draft' if status.startswith('DRAFT') else 'Save settings', initialdir=self.source_path.parent, initialfile='settings.json', defaultextension='.json', filetypes=[('JSON', '*.json')])
        if path:
            try:
                save_settings(path, settings, self.source_path)
                self.status.set(f'Saved {"draft" if status.startswith("DRAFT") else "settings"}: {path}')
            except (OSError, ValueError) as exc:
                messagebox.showerror('Cannot save settings', str(exc))


class SettingsBuilder(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Pile settings builder — OpenSeesPy')
        self.geometry('1180x820')
        self.minsize(950, 680)
        self.editor = SettingsEditor(self)
        self.editor.pack(fill='both', expand=True)


if __name__ == '__main__':
    SettingsBuilder().mainloop()
