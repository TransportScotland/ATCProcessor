import os
from collections import defaultdict
from glob import glob
try:
    import tkinter as tk
    from tkinter import filedialog, ttk, messagebox
except ImportError:
    import Tkinter as tk
    import tkFileDialog as filedialog
    import ttk
    import tkMessageBox as messagebox

from atcprocessor.processor import CountSite
from atcprocessor.version import VERSION_TITLE


class ATCProcessorGUI(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super(ATCProcessorGUI, self).__init__(parent, padx=5, pady=5,
                                              *args, **kwargs)

        inps = FileInputs(
            self, section_name='File Inputs',
            input_names=('Input Folder', 'Site List', 'Thresholds')
        )
        inps.grid(row=1, column=0, sticky='WE')

        cols = ColumnSelector(self, section_name='Choose Columns',
                              input_names=('Option 1', 'Option 2'),
                              folder_variable=inps.variables['Input Folder'])

        cols.grid(row=2, column=0, sticky='WE')
        self.grid_columnconfigure(0, weight=1)


class FileInputs(tk.LabelFrame):
    def __init__(self, parent, section_name, input_names, *args, **kwargs):
        super(FileInputs, self).__init__(parent, text=section_name,
                                         padx=5, pady=5,
                                         *args, **kwargs)

        self.variables = {inp: tk.StringVar() for inp in input_names}

        for i, (inp, var) in enumerate(self.variables.items()):
            lab = tk.Label(self, text=inp)
            ent = tk.Entry(self, width=60, textvariable=var)

            folder_browser = 'folder' in inp.lower()
            butt = tk.Button(
                self, text='Browse',
                command=lambda var=var, ent=ent, folder_browser=folder_browser:
                        self.browse_for_input(var, ent, folder_browser)
            )

            lab.grid(row=i, column=0, sticky='W')
            ent.grid(row=i, column=1, sticky='WE')
            butt.grid(row=i, column=2, sticky='WE')

        self.grid_columnconfigure(1, weight=1)

    @staticmethod
    def browse_for_input(variable, entry, folder=False):
        if folder:
            res = filedialog.askdirectory()
        else:
            res = filedialog.askopenfilename()

        if res:
            variable.set(res.replace('/', '\\'))
            entry.xview_moveto(1.0)


class ColumnSelector(tk.LabelFrame):
    def __init__(self, parent, section_name, input_names, folder_variable,
                 *args, **kwargs):
        super(ColumnSelector, self).__init__(parent, text=section_name,
                                             padx=5, pady=5,
                                             *args, **kwargs)

        self.variables = {inp: tk.StringVar() for inp in input_names}
        self.folder_variable = folder_variable
        self.values = []

        butt = tk.Button(self, text='Update Column Choices',
                         command=lambda: self.update_choices())
        butt.grid(row=0, column=0, columnspan=2)

        for i, (inp, var) in enumerate(self.variables.items()):
            lab = tk.Label(self, text=inp)
            choice = ttk.Combobox(self, values=self.values,
                                  textvariable=var)

            choice.configure(postcommand=lambda choice=choice: self.combo_update(box=choice))

            lab.grid(row=i+1, column=0)
            choice.grid(row=i+1, column=1)

    def combo_update(self, box):
        box['values'] = self.values

    def update_choices(self):
        # TODO make this read from a file. The first in
        first_file = glob(os.path.join(self.folder_variable.get(), '*.csv'))[0]
        with open(first_file, 'r') as f:
            columns = f.readline().split(',')
        self.values = columns


if __name__ == "__main__":
    root = tk.Tk()
    ATCProcessorGUI(root).grid(row=0, column=0, sticky='NEWS')
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)
    root.resizable(True, False)
    root.title(VERSION_TITLE)
    root.mainloop()
