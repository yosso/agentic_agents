"""Integrated Excel/Robot input preparation screen."""
import copy
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from preparation import config,read_mapping,parse_cases,extract_reactions,assemble_inputs
from model import write_json


class InputPreparation(ttk.Frame):
    def __init__(self,master,on_ready,analysis_busy=lambda:False):
        super().__init__(master,padding=14)
        self.on_ready=on_ready
        self.analysis_busy=analysis_busy
        self.mappings=[]
        self.events=queue.Queue()
        self.busy=False
        self.variables={}
        ttk.Label(self,text='Excel & Robot → prepared footing inputs',font=('Segoe UI',18,'bold')).pack(anchor='w')
        ttk.Label(self,text='Select the saved Excel workbook, load footing/group mappings, and select a Robot file for each mapping as needed. Existing saved Robot results are read; models and workbook are not saved or recalculated.',wraplength=1100).pack(anchor='w',pady=8)
        form=ttk.Frame(self)
        form.pack(fill='x')
        definitions=[('workbook','Excel workbook',str(config.DEFAULT_WORKBOOK)),('sheet','Mapping sheet',config.MAPPING_SHEET_NAME),
                     ('table','Mapping table',config.MAPPING_TABLE_NAME),('api','Robot API DLL',config.find_robot_api()),
                     ('cases','Combinations (blank = all supported)','')]
        for index,(key,title,default) in enumerate(definitions):
            self.variables[key]=tk.StringVar(value=default)
            ttk.Label(form,text=title).grid(row=index,column=0,sticky='w',pady=4)
            ttk.Entry(form,textvariable=self.variables[key]).grid(row=index,column=1,sticky='ew',padx=8)
            if key in ('workbook','api'):
                ttk.Button(form,text='Browse...',command=lambda k=key:self.browse(k)).grid(row=index,column=2)
        form.columnconfigure(1,weight=1)
        actions=ttk.Frame(self)
        actions.pack(fill='x',pady=10)
        ttk.Button(actions,text='Load Excel mapping',command=self.load).pack(side='left')
        ttk.Button(actions,text='Select Robot file for selected mappings...',command=self.robot_file).pack(side='left',padx=8)
        self.read_button=ttk.Button(actions,text='Read Robot & create inputs',command=self.start)
        self.read_button.pack(side='left')
        columns=('Footing','Group','Expected','Robot file','Excel source')
        self.mapping_table=ttk.Treeview(self,columns=columns,show='headings',height=7,selectmode='extended')
        for column in columns:
            self.mapping_table.heading(column,text=column)
            self.mapping_table.column(column,width=180)
        self.mapping_table.pack(fill='x')
        self.status=tk.StringVar(value='Load the saved Excel mapping to begin.')
        ttk.Label(self,textvariable=self.status,wraplength=1100).pack(anchor='w',pady=8)
        self.progress=ttk.Progressbar(self,mode='indeterminate')
        self.progress.pack(fill='x')
        self.findings=tk.Text(self,wrap='word',state='disabled')
        self.findings.pack(fill='both',expand=True,pady=8)
        self.after(150,self.poll)

    def browse(self,key):
        if self.busy:return
        path=filedialog.askopenfilename(filetypes=[('Excel workbook','*.xlsm *.xlsx')] if key=='workbook' else [('Robot API','*.dll')])
        if path:self.variables[key].set(str(Path(path)))

    def load(self):
        if self.busy:return
        try:
            self.mappings=read_mapping(self.variables['workbook'].get(),self.variables['sheet'].get(),self.variables['table'].get())
            self.mapping_source=tuple(self.variables[k].get() for k in ('workbook','sheet','table'))
            self.render()
            self.status.set(f'{len(self.mappings)} mappings loaded. Select rows to change their Robot file without editing Excel.')
        except Exception as exc:messagebox.showerror('Cannot load mapping',str(exc))

    def render(self):
        self.mapping_table.delete(*self.mapping_table.get_children())
        for index,mapping in enumerate(self.mappings):
            self.mapping_table.insert('','end',iid=str(index),values=(mapping['mark'],mapping['group'],mapping['expected'],mapping['model'],mapping['source']))

    def robot_file(self):
        if self.busy:return
        selected=self.mapping_table.selection()
        if not selected:
            messagebox.showinfo('Select mappings','Select one or more mapping rows first.')
            return
        path=filedialog.askopenfilename(filetypes=[('Robot model','*.rtd')])
        if path:
            for index in selected:
                self.mappings[int(index)].update(model=str(Path(path).resolve()),exists=True)
            self.render()

    def start(self):
        if self.analysis_busy():
            messagebox.showinfo('Analysis running','Wait for the current analysis to finish first.')
            return
        if self.busy:return
        try:
            if not self.mappings or self.mapping_source!=tuple(self.variables[k].get() for k in ('workbook','sheet','table')):
                raise ValueError('Load the current Excel mapping first.')
            mappings=copy.deepcopy(self.mappings)
            identities=[(m['model'].casefold(),m['group'].casefold()) for m in mappings]
            if len(set(identities))!=len(identities):
                raise ValueError('Robot file selection created duplicate model/group mappings.')
            for mapping in mappings:
                if not Path(mapping['model']).is_file():raise ValueError(f"Robot model not found: {mapping['model']}")
            cases=parse_cases(self.variables['cases'].get())
            api=self.variables['api'].get()
            if not Path(api).is_file():raise ValueError('Select an installed Robot API DLL.')
            workbook=self.variables['workbook'].get()
            output=filedialog.asksaveasfilename(title='Save new prepared inputs JSON',initialdir=Path(workbook).parent,initialfile='prepared-inputs.json',defaultextension='.json',filetypes=[('JSON','*.json')])
            if not output:return
        except Exception as exc:
            messagebox.showerror('Cannot prepare inputs',str(exc));return
        self.busy=True
        self.read_button.configure(state='disabled')
        self.progress.start()
        self.status.set('Reading Robot models and preparing Excel soil/footing inputs...')
        def worker():
            try:
                extraction=extract_reactions(mappings,api,cases)
                document=assemble_inputs(workbook,mappings,extraction)
                write_json(output,document)
                self.events.put(('ready',(output,document)))
            except Exception as exc:self.events.put(('error',str(exc)))
        threading.Thread(target=worker,daemon=True).start()

    def poll(self):
        while not self.events.empty():
            kind,value=self.events.get()
            self.busy=False
            self.progress.stop()
            self.read_button.configure(state='normal')
            if kind=='error':
                self.status.set(value)
                messagebox.showerror('Input preparation failed',value)
            else:
                path,document=value
                issues=document.get('issues',[])
                errors=sum(i['severity']=='ERROR' for i in issues)
                self.findings.configure(state='normal')
                self.findings.delete('1.0','end')
                self.findings.insert('1.0',f"Saved: {path}\n{len(document['piers'])} footings | {len(document['soil_profiles'])} soil profiles\n\n"+'\n'.join(f"{i['severity']} | {i.get('footing','')} | {i['source']} | {i['message']}" for i in issues))
                self.findings.configure(state='disabled')
                self.status.set(f'Prepared inputs saved with {errors} errors. Review findings before analysis.')
                if document['piers'] and document['soil_profiles']:
                    self.on_ready(path,errors)
        self.after(150,self.poll)
