from collections import defaultdict
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

        inps = FileInputs(self, name='File Inputs')
        inps.grid(row=1, column=0, sticky='WE')

        self.grid_columnconfigure(0, weight=1)


class FileInputs(tk.LabelFrame):
    def __init__(self, parent, name, *args, **kwargs):
        super(FileInputs, self).__init__(parent, text=name, padx=5, pady=5,
                                         *args, **kwargs)

        self.variables = {'Input Folder': tk.StringVar(),
                          'Site List': tk.StringVar(),
                          'Thresholds': tk.StringVar()}

        self.widgets = defaultdict(dict)

        for i, (inp, var) in enumerate(self.variables.items()):
            self.widgets[inp]['label'] = tk.Label(self, text=inp)
            self.widgets[inp]['entry'] = tk.Entry(self, width=60,
                                                  textvariable=var)
            self.widgets[inp]['button'] = tk.Button(
                self, text='Browse',
                command=lambda: self.browse_for_input(
                    inp, var, self.widgets[inp]['entry']
                )
            )

            self.widgets[inp]['label'].grid(row=i, column=0, sticky='W')
            self.widgets[inp]['entry'].grid(row=i, column=1, sticky='WE')
            self.widgets[inp]['button'].grid(row=i, column=2, sticky='WE')

        self.grid_columnconfigure(1, weight=1)

    @staticmethod
    def browse_for_input(reference, variable, entry):
        print(reference)
        if 'folder' in reference.lower():
            print('YES')
            res = filedialog.askdirectory()
        else:
            res = filedialog.askopenfilename()

        if res:
            variable.set(res.replace('/', '\\'))
            entry.xview_moveto(1.0)


if __name__ == "__main__":
    root = tk.Tk()
    ATCProcessorGUI(root).grid(row=0, column=0, sticky='NEWS')
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)
    root.resizable(True, False)
    root.title(VERSION_TITLE)
    root.mainloop()
