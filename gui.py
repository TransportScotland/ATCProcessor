import os
from collections import defaultdict
from glob import glob
import json
try:
    import tkinter as tk
    from tkinter import filedialog, ttk, messagebox
except ImportError:
    import Tkinter as tk
    import tkFileDialog as filedialog
    import ttk
    import tkMessageBox as messagebox

from atcprocessor.processor import CountSite, Thresholds
from atcprocessor.version import VERSION_TITLE


class ATCProcessorGUI(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super(ATCProcessorGUI, self).__init__(parent, padx=5, pady=5,
                                              *args, **kwargs)

        self.store = dict()

        self.store['File Inputs'] = FileInputs(
            self, section_name='File Inputs',
            input_names=('Input Folder', 'Site List File', 'Thresholds File',
                         'Output Folder')
        )
        self.store['File Inputs'].grid(row=0, column=0, sticky='WE')

        columns_to_choose = (
            'Site Name Column', 'Count Column', 'Direction Column',
            'Date Column', 'Time Column'
        )

        self.store['Columns'] = ColumnSelector(
            self, section_name='Choose Columns', input_names=columns_to_choose,
            folder_variable=self.store['File Inputs'].variables['Input Folder']
        )

        self.store['Columns'].grid(row=1, column=0, sticky='WE')

        self.grid_columnconfigure(0, weight=1)

        self.run_button = tk.Button(self, text='Run',
                                    command=lambda: self.run())
        self.run_button.grid(row=2, column=0, columnspan=2)

        # Set up menu bar for advanced settings
        menu_bar = tk.Menu(parent)
        parent.config(menu=menu_bar)
        options = tk.Menu(menu_bar, tearoff=False)

        menu_bar.add_cascade(label='Options', menu=options)

        # TODO set up advanced settings
        # options.add_command(label='Advanced Settings')
        # options.add_separator()
        options.add_command(label='Load Settings',
                            command=lambda: self.load_settings())
        options.add_command(label='Save Settings',
                            command=lambda: self.save_settings())

    def save_settings(self):
        all_settings = {
            name: {k: v.get() for k, v in widget.variables.items()}
            for name, widget in self.store.items()
        }

        res = filedialog.asksaveasfilename(
            defaultextension='.json',
            filetypes=[('JSON file', '*.json')]
        )
        if res:
            with open(res, 'w') as f:
                json.dump(all_settings, f, indent=4)

            messagebox.showinfo(title='Settings saved!',
                                message='Settings saved successfully.')

    def load_settings(self):
        res = filedialog.askopenfilename(
            filetypes=[('JSON file', '*.json')]
        )
        if res:
            with open(res, 'r') as f:
                all_settings = json.load(f)

            for name, widget in self.store.items():
                for k, v in all_settings[name].items():
                    widget.variables[k].set(v)

            messagebox.showinfo(title='Settings loaded!',
                                message='Settings loaded successfully.')

    def run(self):
        # TODO work out why the GUI suddenly changes size. Is this consistent?
        # TODO get the variables in a neater way
        thresh = Thresholds(
            path_to_csv=self.store['File Inputs'].variables['Thresholds File'].get(),
            site_list=self.store['File Inputs'].variables['Site List File'].get()
        )

        input_folder = self.store['File Inputs'].variables['Input Folder'].get()
        output_folder = self.store['File Inputs'].variables['Output Folder'].get()

        site_col = self.store['Columns'].variables['Site Name Column'].get()
        count_col = self.store['Columns'].variables['Count Column'].get()
        dir_col = self.store['Columns'].variables['Direction Column'].get()
        date_col = self.store['Columns'].variables['Date Column'].get()
        time_col = self.store['Columns'].variables['Time Column'].get()

        for f in glob(os.path.join(input_folder, '*.csv')):
            c = CountSite(data=f, output_folder=output_folder,
                          site_col=site_col, count_col=count_col,
                          dir_col=dir_col, date_col=date_col, time_col=time_col,
                          thresholds=thresh)

            c.clean_data()
            c.summarise_cleaned_data()
            c.cleaned_scatter()
            # TODO work out why FacetGrid plots are not working
            c.facet_grids()
            c.produce_cal_plots()

        messagebox.showinfo(title='Finished',
                            message='Processing complete')


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
        self.values = ['<Columns not loaded>']

        butt = tk.Button(self, text='Update Column Choices',
                         command=lambda: self.update_choices())
        butt.grid(row=0, column=0, columnspan=2)

        for i, (inp, var) in enumerate(self.variables.items()):
            lab = tk.Label(self, text=inp)
            choice = ttk.Combobox(self, values=self.values,
                                  textvariable=var, width=50)

            choice.configure(
                postcommand=lambda choice=choice: self.combo_update(box=choice)
            )

            lab.grid(row=i+1, column=0, sticky='W')
            choice.grid(row=i+1, column=1, sticky='WE')

    def combo_update(self, box):
        box['values'] = self.values

    def update_choices(self):
        # TODO validate that a file exists.
        files = glob(os.path.join(self.folder_variable.get(), '*.csv'))
        if files:
            with open(files[0], 'r') as f:
                columns = f.readline().split(',')

            # Line will probably end with a carriage return
            # TODO consider a single-line file (i.e. no data). What happens?
            if columns[-1].endswith('\n'):
                columns[-1] = columns[-1][:-1]
            self.values = columns
        else:
            messagebox.showerror(title='No CSV files found',
                                 message='No CSV files could be found in the '
                                         'chosen folder. Please check your '
                                         'inputs.')


if __name__ == "__main__":
    root = tk.Tk()
    ATCProcessorGUI(root).grid(row=0, column=0, sticky='NEWS')
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)
    root.resizable(True, False)
    root.title(VERSION_TITLE)
    root.mainloop()
