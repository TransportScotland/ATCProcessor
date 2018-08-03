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

from atcprocessor import processor
from atcprocessor.version import VERSION_TITLE


class ATCProcessorGUI(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super(ATCProcessorGUI, self).__init__(parent, padx=5, pady=5,
                                              *args, **kwargs)
        self.parent = parent

        # Keep variables within the main window for ease of access
        self.variables = {
            'input_folder': ('Input Folder', tk.StringVar()),
            'site_list': ('Site List File', tk.StringVar()),
            'path_to_csv': ('Thresholds File', tk.StringVar()),
            'output_folder': ('Output Folder', tk.StringVar()),
            'site_col': ('Site Name Column', tk.StringVar()),
            'count_col': ('Count Column', tk.StringVar()),
            'dir_col': ('Direction Column', tk.StringVar()),
            'date_col': ('Date Column', tk.StringVar()),
            'time_col': ('Time Column', tk.StringVar()),
            'std_range': ('Acceptable Standard Deviation range (±)',
                          tk.DoubleVar()),
            'combined_datetime': ('Date column includes Time?',
                                  tk.BooleanVar()),
            'hour_only': ('Time column provides hour only?', tk.BooleanVar()),
            'by_direction': ('Output graphs by direction?', tk.BooleanVar()),
            'valid_only': ('Restrict graphs to "Valid" data only?',
                           tk.BooleanVar()),
            'clean_data': ('Clean data?', tk.BooleanVar()),
            'outside_std_invalid': (
                'Mark values outside acceptable standard '
                'deviation range as invalid?', tk.BooleanVar()
            ),
        }

        # Defaults for advanced settings
        self.variables['std_range'][1].set(2.0)
        self.variables['combined_datetime'][1].set(False)
        self.variables['by_direction'][1].set(True)
        self.variables['hour_only'][1].set(True)
        self.variables['valid_only'][1].set(True)
        self.variables['clean_data'][1].set(True)
        self.variables['outside_std_invalid'][1].set(False)

        self.store = dict()
        self.store['File Inputs'] = FileInputs(
            self, section_name='File Inputs',
            inputs=(self.variables['input_folder'],
                    self.variables['site_list'],
                    self.variables['path_to_csv'],
                    self.variables['output_folder'])
        )
        self.store['File Inputs'].grid(row=0, column=0, sticky='WE')

        self.store['Columns'] = ColumnSelector(
            self, section_name='Choose Columns',
            inputs=(self.variables['site_col'],
                    self.variables['count_col'],
                    self.variables['dir_col'],
                    self.variables['date_col'],
                    self.variables['time_col']),
            folder_variable=self.variables['input_folder'][1]
        )

        self.store['Columns'].grid(row=1, column=0, sticky='WE')

        self.grid_columnconfigure(0, weight=1)

        self.clean_check = tk.Checkbutton(
            self, text=self.variables['clean_data'][0],
            variable=self.variables['clean_data'][1]
        )
        self.clean_check.grid(row=2, column=0, columnspan=2)

        self.run_button = tk.Button(self, text='Run',
                                    command=lambda: self.run())
        self.run_button.grid(row=3, column=0, columnspan=2)

        # Set up menu bar for advanced settings
        menu_bar = tk.Menu(parent)
        parent.config(menu=menu_bar)
        options = tk.Menu(menu_bar, tearoff=False)

        menu_bar.add_cascade(label='Options', menu=options)

        # Add options to menu bar.
        options.add_command(label='Advanced Settings',
                            command=lambda: self.show_advanced_settings())
        options.add_separator()
        options.add_command(label='Load Settings',
                            command=lambda: self.load_settings())
        options.add_command(label='Save Settings',
                            command=lambda: self.save_settings())

    def save_settings(self, use_dialogs=True, file_path=None):
        all_settings = {
            k: v[1].get() for k, v in self.variables.items()
        }

        if use_dialogs:
            res = filedialog.asksaveasfilename(
                defaultextension='.json',
                filetypes=[('JSON file', '*.json')]
            )
        else:
            res = file_path

        if res:
            with open(res, 'w') as f:
                json.dump(all_settings, f, indent=4)

            if use_dialogs:
                messagebox.showinfo(title='Settings saved!',
                                    message='Settings saved successfully.')

    def load_settings(self):
        res = filedialog.askopenfilename(
            filetypes=[('JSON file', '*.json')]
        )
        if res:
            with open(res, 'r') as f:
                all_settings = json.load(f)

            for k, v in all_settings.items():
                self.variables[k][1].set(v)

            messagebox.showinfo(title='Settings loaded!',
                                message='Settings loaded successfully.')

    def show_advanced_settings(self):
        AdvancedSettings(
            self.parent,
            inputs=(self.variables['combined_datetime'],
                    self.variables['hour_only'],
                    self.variables['std_range'],
                    self.variables['outside_std_invalid'],
                    self.variables['by_direction'],
                    self.variables['valid_only']),
            title='Advanced Settings'
        )

    def run(self):
        # TODO work out why the GUI suddenly changes size. Is this consistent?
        # TODO implement a progress bar
        params = {
            param: var.get() for param, (name, var) in self.variables.items()
        }

        try:
            thresh = processor.Thresholds(
                path_to_csv=params['path_to_csv'],
                site_list=params['site_list']
            )
        except FileNotFoundError:
            messagebox.showerror(
                title='File Missing',
                message='One of the site list and thresholds files is missing. '
                        'Please check these inputs'
            )
            return
        except ValueError as v:
            messagebox.showerror(
                title='Input Error',
                message='The following issue has been found with the inputs '
                        'chosen:\n{}'.format(v)
            )

        self.save_settings(
            use_dialogs=False,
            file_path=os.path.join(params['output_folder'], 'settings.json')
        )

        input_files = glob(os.path.join(params['input_folder'], '*.csv'))
        if input_files:
            for f in input_files:
                try:
                    c = processor.CountSite(
                        data=f, thresholds=thresh,
                        output_folder=params['output_folder'],
                        site_col=params['site_col'],
                        count_col=params['count_col'],
                        dir_col=params['dir_col'],
                        date_col=params['date_col'],
                        time_col=params['time_col'],
                        hour_only=params['hour_only']
                    )
                    if params['clean_data']:
                        c.clean_data(
                            std_range=params['std_range'],
                            outside_std_invalid=params['outside_std_invalid'])
                        c.summarise_cleaned_data()
                        c.cleaned_scatter()
                    c.facet_grids(valid_only=params['valid_only'],
                                  by_direction=params['by_direction'])
                    c.produce_cal_plots(valid_only=params['valid_only'],
                                        by_direction=params['by_direction'])

                except ValueError as v:
                    messagebox.showerror(
                        title='Input Error',
                        message='The following issue has been found with input '
                                'file [{}]:\n\n{}\n\nProcessing will terminate '
                                'here.'.format(f, v)
                    )
                    return

            messagebox.showinfo(title='Finished',
                                message='Processing complete')
        else:
            messagebox.showerror(
                title='No files found',
                message='No CSV files could be found in\n{}\nPlease check '
                        'the folder'.format(params['input_folder'])
            )


class FileInputs(tk.LabelFrame):
    def __init__(self, parent, section_name, inputs, *args, **kwargs):
        super(FileInputs, self).__init__(parent, text=section_name,
                                         padx=5, pady=5,
                                         *args, **kwargs)

        for i, (inp, var) in enumerate(inputs):
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
    def __init__(self, parent, section_name, inputs, folder_variable,
                 *args, **kwargs):
        super(ColumnSelector, self).__init__(parent, text=section_name,
                                             padx=5, pady=5,
                                             *args, **kwargs)

        self.folder_variable = folder_variable
        self.values = ['<Columns not loaded>']

        butt = tk.Button(self, text='Update Column Choices',
                         command=lambda: self.update_choices())
        butt.grid(row=0, column=0, columnspan=2)

        for i, (inp, var) in enumerate(inputs):
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


class AdvancedSettings(tk.Toplevel):
    def __init__(self, parent, inputs, title):
        super(AdvancedSettings, self).__init__(parent)
        self.title(title)

        validate_float = (parent.register(self.__validate_float), '%P')
        for i, (inp, var) in enumerate(inputs):
            if type(var) == tk.DoubleVar:
                lab = tk.Label(self, text=inp)
                ent = tk.Entry(self, textvariable=var, validate='all',
                               validatecommand=validate_float)

                lab.grid(row=i, column=0)
                ent.grid(row=i, column=1)

            if type(var) == tk.BooleanVar:
                chk = tk.Checkbutton(self, text=inp, variable=var)
                chk.grid(row=i, column=0, columnspan=2, sticky='W')

        close_button = tk.Button(self, text='Close',
                                 command=lambda: self.destroy())
        close_button.grid(row=i+1, column=0, columnspan=2)

        self.resizable(False, False)
        self.grab_set()

    @staticmethod
    def __validate_float(new_value):
        try:
            float(new_value)
            return True
        except ValueError:
            return False


if __name__ == "__main__":
    root = tk.Tk()
    ATCProcessorGUI(root).grid(row=0, column=0, sticky='NEWS')
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)
    root.resizable(True, False)
    root.title(VERSION_TITLE)
    root.mainloop()
