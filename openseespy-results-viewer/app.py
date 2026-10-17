"""Desktop viewer for OpenSeesPy pier CLI results; Python + Tkinter only."""
import argparse
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from model import load_results

ROOT = Path(__file__).resolve().parents[1]


class ResultsViewer(tk.Tk):
    def __init__(self, folder=None):
        super().__init__()
        self.title('OpenSeesPy pile results viewer')
        self.geometry('1350x900')
        self.minsize(1000, 700)
        self.result = None
        bar = ttk.Frame(self, padding=12)
        bar.pack(fill='x')
        ttk.Button(bar, text='Open results folder...', command=self.open_folder).pack(side='left')
        self.location = ttk.Label(bar, text='Choose a CLI result folder containing a converged analysis.')
        self.location.pack(side='left', padx=12)
        self.overview = ttk.Label(self, padding=12, wraplength=1250)
        self.overview.pack(fill='x')
        tabs = ttk.Notebook(self)
        tabs.pack(fill='both', expand=True, padx=12, pady=8)
        plots = ttk.Frame(tabs)
        tabs.add(plots, text='Deflection, shear & moment')
        ttk.Label(plots, text='Depth increases downward (ft). Shear and moment: i-end local resisting force, with j-end sign reversed. Each element is plotted separately to retain jumps.', wraplength=1200, padding=8).pack(fill='x')
        self.canvas = tk.Canvas(plots, background='white', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', lambda _: self.draw())
        self.inputs = self.text_tab(tabs, 'Inputs & soil layers')
        self.findings = self.text_tab(tabs, 'Summary & validation')
        self.status = ttk.Label(self, text='Imperial plots: in, kip, kip-ft; depth in ft.', padding=10)
        self.status.pack(fill='x')
        if folder:
            self.after(100, lambda: self.open_folder(folder))

    def text_tab(self, tabs, title):
        frame = ttk.Frame(tabs)
        tabs.add(frame, text=title)
        text = tk.Text(frame, wrap='word', font=('Consolas', 10))
        scroll = ttk.Scrollbar(frame, orient='vertical', command=text.yview)
        scroll.pack(side='right', fill='y')
        text.pack(fill='both', expand=True)
        text.configure(yscrollcommand=scroll.set, state='disabled')
        return text

    def set_text(self, widget, text):
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', text)
        widget.configure(state='disabled')

    def open_folder(self, folder=None):
        folder = folder or filedialog.askdirectory(initialdir=ROOT / 'openseespy-cli/results', title='Open CLI results folder')
        if not folder:
            return
        try:
            result = load_results(folder)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            messagebox.showerror('Cannot open results', str(exc))
            return
        self.result = result
        p, s = result['plan'], result['summary']
        self.location.configure(text=str(result['folder']))
        depth = p.get('embedment_ft', p.get('embedment_m', 0)/.3048)
        diameter = p.get('diameter_ft', p.get('diameter_m', 0)/.3048)
        head = result['curves']['Deflection [in]'][0][0][0]
        self.overview.configure(text=f"Footing {p.get('footing')} | Plane {p.get('plane')} | Diameter {diameter:g} ft | Embedment {depth:g} ft | Head deflection {head:.6g} in | {s['status']}\nNo design acceptance is established by these results.")
        self.set_text(self.inputs, 'ANALYSIS INPUTS\nUnits are identified by field suffixes; original source records retain their declared units.\n\n' + json.dumps(p, indent=2))
        self.set_text(self.findings, 'SUMMARY\n' + json.dumps(s, indent=2) + '\n\nVALIDATION\n' + json.dumps(result['validation'], indent=2))
        self.draw()

    def draw(self):
        c = self.canvas
        c.delete('all')
        if not self.result:
            c.create_text(30, 30, anchor='nw', text='Open a converged results folder to display plots.', fill='#526175')
            return
        width, height = c.winfo_width(), c.winfo_height()
        if width < 200 or height < 200:
            return
        max_depth = max(z for curves in self.result['curves'].values() for segment in curves for _, z in segment)
        max_depth = max(max_depth, .001)
        for index, (title, segments) in enumerate(self.result['curves'].items()):
            panel = width / 3
            left, right = panel*index+65, panel*(index+1)-25
            top, bottom = 65, height-65
            values = [x for segment in segments for x, _ in segment]
            lo, hi = min(0, min(values)), max(0, max(values))
            span = hi-lo or 1
            lo, hi = lo-span*.12, hi+span*.12
            def xy(x, z):
                return left+(x-lo)/(hi-lo)*(right-left), top+z/max_depth*(bottom-top)
            c.create_text((left+right)/2, 24, text=title, font=('Segoe UI', 12, 'bold'))
            for tick in range(6):
                z = max_depth*tick/5
                y = xy(0, z)[1]
                c.create_line(left, y, right, y, fill='#e2e8f0')
                c.create_text(left-8, y, anchor='e', text=f'{z:.3g}', fill='#526175')
                xvalue = lo+(hi-lo)*tick/5
                x = xy(xvalue, 0)[0]
                c.create_text(x, bottom+18, text=f'{xvalue:.3g}', fill='#526175')
            c.create_text(left-40, (top+bottom)/2, text='Depth [ft]', angle=90)
            c.create_rectangle(left, top, right, bottom, outline='#94a3b8')
            c.create_line(*xy(0, 0), *xy(0, max_depth), fill='#64748b', dash=(3, 3))
            for depth, name in self.result['boundaries']:
                if 0 < depth < max_depth:
                    y = xy(0, depth)[1]
                    c.create_line(left, y, right, y, fill='#b9a788', dash=(5, 4))
            for segment in segments:
                points = [coordinate for x, z in segment for coordinate in xy(x, z)]
                if len(points) >= 4:
                    c.create_line(*points, fill=('#2563eb', '#0f766e', '#9333ea')[index], width=2)
            peak = max(values, key=abs)
            c.create_text((left+right)/2, bottom+43, text=f'Max |response|: {abs(peak):.6g}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path)
    args = parser.parse_args()
    ResultsViewer(args.results).mainloop()
