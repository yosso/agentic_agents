"""Controlling combinations using the reaction viewer's envelope rules."""
import csv
import tkinter as tk
from tkinter import ttk, filedialog
from preparation import config
from data import controlling_combinations, display_reaction


class EnvelopeView(ttk.Frame):
    def __init__(self, master, editor):
        super().__init__(master, padding=10)
        self.editor = editor
        self.units = editor.units
        self.rows = []
        self.sources = {}
        ttk.Label(self, text='Per footing: maximum resultant shear, resultant bending, |torsion|, compression (+FZ), and uplift (−FZ). Each extreme retains its complete coincident reaction vector.', wraplength=1100).pack(anchor='w')
        ttk.Label(self, text='Exact ties show one deterministic source and their count. Double-click a row to select its footing and reaction for review or the load-limit search. This envelope does not establish the governing deflection.', wraplength=1100).pack(anchor='w', pady=6)
        bar = ttk.Frame(self)
        bar.pack(fill='x', pady=5)
        ttk.Label(bar, text='Display units:').pack(side='left')
        ttk.Combobox(bar, textvariable=self.units, values=('kip / kip-ft','kN / kN-m','N / N-m'), state='readonly', width=16).pack(side='left', padx=8)
        ttk.Button(bar, text='Export envelope CSV...', command=self.export).pack(side='left')
        columns=('Footing','Criterion','Value','Units','Combination','Combination name','Node','Model','Group','Ties','FX','FY','FZ','MX','MY','MZ')
        self.columns=columns
        frame=ttk.Frame(self)
        frame.pack(fill='both',expand=True)
        self.table=ttk.Treeview(frame, columns=columns, show='headings')
        for key in columns:
            self.table.heading(key,text=key)
            self.table.column(key,width=190 if key in ('Criterion','Model','Combination name') else 100,stretch=False)
        self.table.grid(row=0,column=0,sticky='nsew')
        vertical=ttk.Scrollbar(frame,orient='vertical',command=self.table.yview)
        vertical.grid(row=0,column=1,sticky='ns')
        horizontal=ttk.Scrollbar(frame,orient='horizontal',command=self.table.xview)
        horizontal.grid(row=1,column=0,sticky='ew')
        self.table.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
        frame.columnconfigure(0,weight=1)
        frame.rowconfigure(0,weight=1)
        self.table.bind('<Double-1>',self.choose)
        self.status=ttk.Label(self,text='Load prepared inputs to see controlling combinations.',wraplength=1100)
        self.status.pack(anchor='w',pady=8)
        self.units.trace_add('write',lambda *args:self.render())

    def load(self,document):
        self.document=document
        reactions=[dict(row,mark=pier['footing']) for pier in document['piers'] for row in pier['reactions']]
        self.rows=controlling_combinations(reactions)
        self.render()
        issues=document.get('issues',[])
        errors=sum(i['severity']=='ERROR' for i in issues)
        self.status.configure(text=f'{len(reactions)} extracted reaction rows | {len(document["piers"])} footings | {errors} preparation errors. Review Step 0 findings; only extracted combinations are represented.')

    def render(self):
        self.table.delete(*self.table.get_children())
        self.sources={}
        force,moment=self.units.get().split(' / ')
        for key in ('FX','FY','FZ','MX','MY','MZ'):
            self.table.heading(key,text=f'{key} ({force if key.startswith("F") else moment})')
        for item in self.rows:
            row=item['reaction']
            component=item['component']
            unit=moment if component.startswith('M') else force
            if row is None:
                values=[item['mark'],item['criterion'],'None found',unit,'—','No qualifying combination','','','',0]+['']*6
            else:
                components=display_reaction(row,self.units.get())
                value=((components[0]**2+components[1]**2)**.5 if component=='H' else
                       (components[3]**2+components[4]**2)**.5 if component=='MH' else
                       abs(components[5]) if component=='MZ' else components[2])
                values=[item['mark'],item['criterion'],f'{value:.6g}',unit,row['case'],row.get('case_name',''),row['node'],row['model'],row['group'],item['ties']]+[f'{v:.6g}' for v in components]
            iid=self.table.insert('','end',values=values)
            self.sources[iid]=(item['mark'],row)
        if self.editor.piers:
            self.editor.render_reactions(event=True)

    def choose(self,event=None):
        selected=self.table.selection()
        if not selected:return
        mark,row=self.sources[selected[0]]
        if row is None:return
        index=next(i for i,p in enumerate(self.editor.piers) if p['footing']==mark)
        self.editor.footing_box.current(index)
        self.editor.select_footing()
        reaction_index=next(i for i,r in enumerate(self.editor.piers[index]['reactions']) if all(r[k]==row[k] for k in ('model','group','node','case')))
        self.editor.reactions.selection_set(str(reaction_index))
        self.editor.reactions.see(str(reaction_index))
        self.editor.tabs.select(0)

    def export(self):
        if not self.rows:return
        path=filedialog.asksaveasfilename(title='Export load envelope',initialfile='load-envelope.csv',defaultextension='.csv',filetypes=[('CSV','*.csv')])
        if not path:return
        with open(path,'w',newline='',encoding='utf-8-sig') as stream:
            writer=csv.writer(stream)
            writer.writerow([self.table.heading(key)['text'] for key in self.columns])
            writer.writerows(self.table.item(iid,'values') for iid in self.table.get_children())
