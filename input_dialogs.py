
# Adapted from https://stackoverflow.com/questions/50573260/simpledialog-simpledialog-in-python-with-2-inputsh

from typing import List, Dict, Tuple
from tkinter import (
    Tk, TOP, BOTH, X, N, LEFT, RIGHT, messagebox, filedialog, TclError, Toplevel
)
from tkinter.ttk import Frame, Label, Entry, Button
import datetime as dtm
from copy import deepcopy

from cells import Cell, cells


class MultiFieldDialog(Frame):
    def __init__(
        self, field_names: List[str], message: str, 
        default_vals: Dict[str, str]=None, prefix: str=''
    ) -> None:
        super().__init__()

        self.message_text = message
        self.field_names = field_names

        self.field_vals = {name: "" for name in self.field_names}

        self.default_vals = {name: "" for name in self.field_names}
        if default_vals:
            for name, val in default_vals.items():
                if val:
                    self.default_vals[name] = val

        self.prefix = prefix

        self.initUI()

    def initUI(self):

        self.master.title("Request values")
        self.pack(fill=BOTH, expand=True)

        message_frame = Frame(self)
        message_frame.pack(fill=X)
        message = Label(message_frame, text=self.message_text)
        message.pack(side=LEFT, padx=5, pady=5)

        self.field_frames: Dict[str, Frame] = {}
        self.labels: Dict[str, Label] = {}
        self.entries: Dict[str, Entry] = {}

        for name in self.field_names:
            self.field_frames[name] = Frame(self)
            self.field_frames[name].pack(fill=X)

            self.labels[name] = Label(
                self.field_frames[name], text=f"{self.prefix}{name}:"
            )
            self.labels[name].pack(side=LEFT, padx=5, pady=5)

            self.entries[name] = Entry(
                self.field_frames[name], textvariable=self.field_vals[name]
            )
            self.entries[name].pack(fill=X, padx=5, expand=True)
            self.entries[name].delete(0, 'end')
            self.entries[name].insert(0, self.default_vals[name])

        main_frame = Frame(self)
        main_frame.pack(fill=X)

        btn = Button(main_frame, text="Submit", command=self.on_submit)
        btn.pack(padx=5, pady=10)

    def on_submit(self):

        for name in self.field_names:
            self.field_vals[name] = str(self.entries[name].get())

        self.quit()

    def show_invalid_input_string_error(self, field_name):
        messagebox.showerror(
            parent=self,
            title='Error',
            message = (
                f"Could not parse input '{self.field_vals[field_name]}' for"
                f" {self.prefix}{field_name}. Please try again."
            )
        )


class CellParsDialog(MultiFieldDialog):

    def __init__(
        self, pars: List[str], num_readings: int, cell: Cell,
        timestamp: dtm.datetime, default_vals: Dict[str, float]=None
    ):

        message = (
            f"Found {num_readings} reading(s) for {cell.name}"
            f" (cell {cell.port}) with timestamp {timestamp}."
            f"\n\nSome cell parameters must be entered manually:"
            " please enter them below."
            "\nType either a single value (will be used for all reading(s))"
            f" or a comma-separated list.\nLeave unknown values blank."
        )

        # Uses default values defined by the cell, then overwrites any defaults
        # that are supplied directly as an argument
        defaults = {name: val for name, val in cell.par_defaults.items()}

        if default_vals:
            for name, val in default_vals.items():
                defaults[name] = val

        super().__init__(
            field_names=pars, message=message, 
            default_vals=defaults, prefix=f"{cell.name} "
        )

        self.num_readings = num_readings

        # self.field_names stores the string value of each entry.
        # self.parsed_outputs stores the value converted to a list of floats.
        self.parsed_field_vals: Dict[str, List[float]] = None

    def on_submit(self, event=None):

        self.field_vals = {
            name: self.entries[name].get() for name in self.field_names
        }

        parsed_vals = {
            name: [] for name in self.field_names
        }

        for name in self.field_names:
            try:
                 parsed_vals[name] = self.parse_vals_string(
                     self.field_vals[name]
                )
            except self.InvalidLengthError as e:
                self.show_invalid_length_error(name, e.lengthval)
                return
            except ValueError:
                self.show_invalid_input_string_error(name)
                return

        self.parsed_field_vals = parsed_vals

        self.quit()

    def parse_vals_string(self, vals_string: str):
        if not vals_string:
            return [None]*self.num_readings

        vals: List[float] = []
        for val in vals_string.split(','):
            if val.strip():
                vals.append(float(val))
            else:
                vals.append(None)

        # If a single value is given, repeat it for all readings
        if len(vals) == 1:
            vals *= self.num_readings

        # Check that #vals given = #readings
        if len(vals) != self.num_readings:
            raise self.InvalidLengthError(len(vals))
        
        return vals

    class InvalidLengthError(ValueError):
        def __init__(self, lengthval: int) -> None:
            super().__init__()

            self.lengthval = lengthval

    def show_invalid_length_error(self, field_name, lengthval):
        messagebox.showerror(
            parent=self,
            title="Error",
            message=(
                f"Number of values given for {self.prefix}{field_name}"
                f" ({lengthval}) is incompatible with"
                f" number of readings ({self.num_readings}). Please try again."
            )
        )


class FluxMeasurementDialog(MultiFieldDialog):
    def __init__(self, cell_names: List[str], timestamp: dtm.datetime):

        field_names = ['Growth number']
        field_names += [f'{name} target MIG (nA)' for name in cell_names]

        message = "Calculating flux calibration for group III cell(s) "
        message += ', '.join(cell_names)
        message += f'.\nTimestamp for flux measurements: {timestamp}\n\n'
        message += "Please enter growth number and target MIG readings.\n"

        super().__init__(field_names, message)

        # self.field_names stores the string value of each entry.
        # self.parsed_outputs stores the value converted to a list of floats.
        self.parsed_field_vals: Dict[str, List[float]] = {
            name: None for name in self.field_names
        }

    def on_submit(self, event=None):

        self.field_vals = {
            name: self.entries[name].get() for name in self.field_names
        }

        parsed_vals = {
            name: None for name in self.field_names
        }

        parsed_vals['Growth number'] = self.field_vals['Growth number']

        for name in self.field_vals:
            if not self.field_vals[name]:
                self.show_empty_input_string_error(name)
                return

        for name in self.field_vals:
            if name == 'Growth number':
                parsed_vals[name] = self.field_vals[name]
            else:
                try:
                    parsed_vals[name] = float(self.field_vals[name])
                except ValueError:
                    self.show_invalid_input_string_error(name)
                    return                    

        self.parsed_field_vals = parsed_vals

        self.quit()

    def show_empty_input_string_error(self, field_name):
        messagebox.showerror(
            parent=self,
            title="Error",
            message=(
                f"Value for {self.prefix}{field_name} cannot be empty."
                " Please try again."
            )
        )

def get_files_from_user(initialdir=None) -> List[str]:

    root = Tk()
    root.withdraw()

    filenames = filedialog.askopenfilenames(
        initialdir=initialdir
    )
    root.destroy()

    return filenames


def ask_yes_no(message:str) -> bool:
    
    root = Tk()
    root.withdraw()

    answer = messagebox.askyesno(title='User input', message=message)

    root.destroy()

    return answer


def show_error_and_exit(message:str):
    root = Tk()
    root.withdraw()

    messagebox.showerror(
        title='Error', message=message+"\nTerminating program..."
    )

    root.destroy()
    exit()


def prompt_flux_measurement(
    cell_names: List[str], timestamp: dtm.datetime
) -> Tuple[str, Dict[str, float]]:

    root = Tk()
    app = FluxMeasurementDialog(cell_names, timestamp)

    root.eval(f'tk::PlaceWindow . center')
    root.lift()
    root.grab_set()
    root.focus_force()
    root.bind('<Return>', app.on_submit)

    root.mainloop()

    try:
        root.destroy()
    except TclError:
        pass

    for _, val in app.parsed_field_vals.items():
        if not val:
            raise ValueError("Failed to get values from user.")

    growth_num: str = app.parsed_field_vals['Growth number']

    target_MIGs: Dict[str, float] = {
        name: app.parsed_field_vals[f'{name} target MIG (nA)']
        for name in cell_names
    }

    return growth_num, target_MIGs


def get_cell_pars_from_user(
    pars: List[str], num_rd: int, cell: Cell, timestamp: dtm.datetime, 
    defaults: Dict[str, str]=None,
):

    root = Tk()
    app = CellParsDialog(pars, num_rd, cell, timestamp, defaults)

    root.eval(f'tk::PlaceWindow . center')
    root.lift()
    root.grab_set()
    root.focus_force()
    root.bind('<Return>', app.on_submit)


    root.mainloop()

    try:
        root.destroy()
    except TclError:
        pass

    return app.parsed_field_vals

if __name__ == '__main__':
    # Example usage
    pars = ['par1', 'par2', 'long input name', 'par4', 'par5', 'par6']
    defaults = {'par2': 'par2 default', 'par5': 'par2 default'}
    num_readings = 4
    cell = cells.find_by_name('Ga1')
    output = get_cell_pars_from_user(
        pars, num_readings, cell, dtm.datetime.now(), defaults
    )
    print(output)

