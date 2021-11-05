import re
import os
import datetime as dtm
from typing import List, Dict, Tuple
from copy import copy, deepcopy

import numpy as np

from cells import Cell, cells
from input_dialogs import get_cell_pars_from_user, ask_yes_no, show_error_and_exit

this_dir = os.path.dirname(os.path.abspath(__file__))
default_save_folder = os.path.join(this_dir, 'FluxDataPy')

class MIGReading():
    def __init__(
        self,
        timestamp: dtm.datetime,
        MIG_current: float,
        signal_to_noise: float=None
    ) -> None:

        self.timestamp = timestamp
        self.MIG_current = MIG_current
        self.signal_to_noise = signal_to_noise


class BkgrndMIGReading(MIGReading):
    def __init__(
        self, 
        timestamp: dtm.datetime,
        MIG_current: float,
        signal_to_noise: float=None,
        reading_num: int=None
    ):
        super().__init__(timestamp, MIG_current, signal_to_noise)

        self.reading_num = reading_num


class FluxMIGReading(MIGReading):
    def __init__(
        self, 
        timestamp: dtm.datetime,
        cell: Cell, 
        cell_par_vals: Dict[str, float], 
        MIG_current: float,
        signal_to_noise: float=None, 
        reading_num: int=None
    ):

        super().__init__(timestamp, MIG_current, signal_to_noise)

        self.cell = cell
        self.cell_par_vals = cell_par_vals
        self.reading_num = reading_num

    def subtract_background(
        self, background: 'BkgrndMIGReading'
    ) -> 'MIGReading':

        if self.timestamp != background.timestamp:
            raise ValueError(
                "Reading and background have incompatible timestamps"
            )

        cell = copy(self.cell)
        timestamp = copy(self.timestamp)
        cell_par_vals = copy(self.cell_par_vals)
        MIG_current = self.MIG_current - background.MIG_current
        
        if self.signal_to_noise and background.signal_to_noise:
            noise = self.MIG_current/self.signal_to_noise
            bg_noise = background.MIG_current/background.signal_to_noise
            signal_to_noise = MIG_current/np.sqrt(noise**2 + bg_noise**2)
        else:
            signal_to_noise = None

        signal_to_background = self.MIG_current/background.MIG_current

        if background.reading_num and self.reading_num:
            if self.timestamp == background.timestamp:
                num_meas_between = background.reading_num - self.reading_num
            else:
                num_meas_between = None
        else:
            num_meas_between = None

        return CorrMIGReading(
            timestamp, cell, cell_par_vals, MIG_current,
            signal_to_noise, signal_to_background, num_meas_between
        )

class CorrMIGReading(MIGReading):
    def __init__(
        self, 
        timestamp: dtm.datetime,
        cell: Cell, 
        cell_par_vals: Dict[str, float], 
        MIG_current: float,
        signal_to_noise: float=None, 
        signal_to_background: float=None, 
        num_meas_between: int=None
    ):

        super().__init__(timestamp, MIG_current, signal_to_noise)

        self.cell = cell
        self.cell_par_vals = cell_par_vals
        self.signal_to_background = signal_to_background
        self.num_meas_between = num_meas_between

    def print_to_str(self):
        out_str = f"{self.timestamp}, "
        out_str += f"Cell={self.cell.name}, "
        for par, val in self.cell_par_vals.items():
            if val:
                out_str += f'{par}={val:g}, '
            else:
                out_str += f'{par}=?, '
        out_str += f"MIG (nA)={self.MIG_current:.4f}, "
        out_str += f"Sig-to-noise={self.signal_to_noise:.2f}, "
        out_str += f"Sig-to-bg={self.signal_to_background:.2f}, "
        out_str += f"# meas between sig and bg={self.num_meas_between}"

        return out_str


filename_regex = re.compile(
    r'FluxReadingCell(?P<port>\d\d?)_01_(?P<timestamp>\d{8}_\d{6}).txt$'
)


def parse_flux_filename(fname):
    match = filename_regex.match(os.path.basename(fname))

    if match:
        port = int(match['port'])
        timestamp_str = match['timestamp']

        timestamp = dtm.datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')

        if port == 0:
            show_error_and_exit(
                f"Invalid file '{fname}'. Cell0 is a manual measurement that"
                " cannot be parsed automatically."
            )

        cell = cells.find_by_port(port)

        return cell, timestamp
    else: 
        raise show_error_and_exit(f"Unrecognized filename format: '{fname}'")


flux_line_pattern = re.compile(
    r'^(?P<type>Fluxcal   |Background), Cell, (?P<cell>\d+), '
    r'Reading, (?P<num>\d+), Temp, (?P<temp>\d+\.\d+), '
    r'Average, (?P<avg>\d+\.\d+), Readings(?P<vals>(, \d+\.\d+ ){24})$'
)


def parse_flux_line(line):
    match = flux_line_pattern.match(line)

    if match:
        meas_type = match['type'].strip()
        port = int(match['cell'])
        temp = float(match['temp'])
        avg = float(match['avg'])
        num = int(match['num'])
        vals = match['vals'].split(',')[1:]

        vals = np.array([float(val) for val in vals])

    else:
        raise ValueError(f"Unexpected line format:\n'{line}'")

    return meas_type, port, temp, num, vals


def create_reading_from_XGEN_line(
    line: str, timestamp: dtm.datetime
) -> MIGReading:
    
    match = flux_line_pattern.match(line)

    if match:
        meas_type = match['type'].strip()
        port = int(match['cell'])
        temp = float(match['temp'])
        avg = float(match['avg'])
        reading_num = int(match['num'])
        vals = match['vals'].split(',')[1:]

        vals = np.array([float(val) for val in vals])

    else:
        raise ValueError(f"Unexpected line format:\n'{line}'")

    cell = cells.find_by_port(port)
    cell_par_vals = {par: None for par in cell.pars}
    cell_par_vals['Temp (°C)'] = temp

    # Create reduced array which is missing the highest two and lowest two
    # values. This reduced array is what XGEN uses to calculate averages.
    vals_reduced = list(vals)
    for i in range(2):
        vals_reduced.remove(max(vals_reduced))
        vals_reduced.remove(min(vals_reduced))

    MIG_current = np.average(vals_reduced)

    if (MIG_current - avg)/avg > 1e-12:
        raise ValueError(
            f"Average reading in file ({avg}) does not match calculated"
            f" average ({MIG_current})"
        )

    signal_to_noise = MIG_current/np.std(vals_reduced)

    if meas_type == 'Background':
        return BkgrndMIGReading(
            timestamp, MIG_current, signal_to_noise, reading_num
        )
    elif meas_type == 'Fluxcal':
        return FluxMIGReading(
            timestamp, cell, cell_par_vals, MIG_current,
            signal_to_noise, reading_num
        )
    else:
        raise ValueError(f"Unexpected measurement type '{meas_type}'")


def get_readings_from_XGEN_file(fname):

    _, timestamp = parse_flux_filename(fname)

    readings: List[MIGReading] = []
    with open(fname, 'r') as ffile:
        for line in ffile:
            if line.strip():
                readings.append(create_reading_from_XGEN_line(line, timestamp))

    return readings

def subtract_background_simple(
    readings: List[MIGReading]
) -> List[MIGReading]:

    fluxes: List[Tuple[int, FluxMIGReading]] = []
    backgrounds: List[Tuple[int, BkgrndMIGReading]] = []

    for i, rd in enumerate(readings):
        if isinstance(rd, BkgrndMIGReading):
            backgrounds.append([i, rd])
        elif isinstance(rd, FluxMIGReading):
            fluxes.append([i, rd])
        else:
            raise ValueError("Unexpected reading type.")

    corrected_readings = []

    # Search for the next background reading after the flux reading
    for i, flux in fluxes:
        found_bg = False
        for j, bg in backgrounds:
            if j > i:
                corrected_reading = flux.subtract_background(bg)
                corrected_readings.append(corrected_reading)
                found_bg = True
                break

        if not found_bg:
            print(
                "Warning: could not find background reading. "
                f"Skipping measurement {i}."
            )

    return corrected_readings

def get_corrected_readings_from_XGEN_file(fname, prompt_missing=True):

    readings = get_readings_from_XGEN_file(fname)

    corrected_readings = subtract_background_simple(readings)

    if prompt_missing:
        corrected_readings = prompt_for_missing_par_vals(corrected_readings)

    return corrected_readings


def prompt_for_missing_par_vals(
    readings: List[CorrMIGReading]
) -> List[CorrMIGReading]:
    '''Assumes all readings correspond to the same timestamp and cell.'''

    missing_pars = []
    for rd in readings:
        for par, val in rd.cell_par_vals.items():
            if (par not in missing_pars) and (val is None):
                missing_pars.append(par)

    if missing_pars:
        vals = get_cell_pars_from_user(
            missing_pars, len(readings), readings[0].cell,
            readings[0].timestamp
        )

        if vals:
            for key in vals:
                for reading, val in zip(readings, vals[key]):
                    reading.cell_par_vals[key] = val

    return readings


def generate_header(cellname: str) -> str:

    cell = cells.find_by_name(cellname)

    header = "Timestamp"
    for par in cell.pars:
        header += f", {par}"

    header += ", MIG (nA), Signal-to-noise, Signal-to-background"
    header += ", Num meas between sig and BG"

    return header


def print_line(reading: CorrMIGReading) -> str:

    out_str = f"\n"
    out_str += dtm.datetime.strftime(reading.timestamp, '%Y-%m-%d %H:%M:%S')
    for _, val in reading.cell_par_vals.items():
        out_str += ", "
        if val:
            out_str += f"{val:g}"

    out_str += f", {reading.MIG_current:g}, {reading.signal_to_noise}"
    out_str += f", {reading.signal_to_background:g}"
    out_str += f", {reading.num_meas_between}"

    return out_str


def read_float(s: str):
    if s:
        return float(s)
    else:
        return None

def load_readings(
    cellnames: List[str], folder: str = default_save_folder
) -> List[CorrMIGReading]:

    readings: List[CorrMIGReading] = []

    for cellname in cellnames:

        filepath = os.path.join(folder, f"{cellname}.txt")

        cell = cells.find_by_name(cellname)

        if not os.path.exists(filepath):
            return []

        with open(filepath, 'r', encoding='utf8') as fl:
            header = fl.readline().strip()

            if header != generate_header(cellname):
                raise ValueError("Unexpected file header.")

            valnames = header.split(', ')


            for line in fl:
                vals = line.strip().split(', ')

                valdict = {name: val for name, val in zip(valnames, vals)}

                timestamp = dtm.datetime.strptime(
                    valdict['Timestamp'], '%Y-%m-%d %H:%M:%S'
                )
                MIG_current = read_float(valdict['MIG (nA)'])
                signal_to_noise = read_float(valdict['Signal-to-noise'])
                signal_to_background = read_float(
                    valdict['Signal-to-background']
                )
                num_meas_between = read_float(
                    valdict['Num meas between sig and BG']
                )

                cell_par_vals = {
                    par: read_float(valdict[par]) for par in cell.pars
                }

                readings.append(
                    CorrMIGReading(
                        timestamp, cell, cell_par_vals, MIG_current,
                        signal_to_noise, signal_to_background, num_meas_between
                    )
                )

    return readings


def split_readings_by_timestamp(
    readings: List[CorrMIGReading]
) -> Dict[str, List[CorrMIGReading]]:

    readings_by_timestamp: Dict[dtm.datetime, List[CorrMIGReading]] = {}
    for reading in readings:
        timestamp = reading.timestamp
        if timestamp not in readings_by_timestamp:
            readings_by_timestamp[timestamp] = []

        readings_by_timestamp[timestamp].append(reading)

    return readings_by_timestamp


def split_readings_by_cellname(
    readings: List[CorrMIGReading]
) -> Dict[str, List[CorrMIGReading]]:

    readings_by_cellname: Dict[str, List[CorrMIGReading]] = {}

    for reading in readings:
        cellname = reading.cell.name

        if cellname not in readings_by_cellname:
            readings_by_cellname[cellname] = []

        readings_by_cellname[cellname].append(reading)

    return readings_by_cellname


def get_cellnames_from_readings(
    readings: List[CorrMIGReading]
) -> List[str]:

    cellnames = []
    for reading in readings:
        if reading.cell.name not in cellnames:
            cellnames.append(reading.cell.name)

    return cellnames


def split_readings(
    readings: List[CorrMIGReading]
) -> Dict[str, Dict[str, List[CorrMIGReading]]]:
    '''Returns readings split by cell and timestamp.'''

    readings_by_cell = split_readings_by_cellname(readings)

    readings_split = {}

    for cell in readings_by_cell:
        readings_split[cell] = split_readings_by_timestamp(
            readings_by_cell[cell]
        )

    return readings_split


def unsplit_readings(
    readings: Dict[str, Dict[str, List[CorrMIGReading]]]
) -> List[CorrMIGReading]:

    unsplit_readings: List[CorrMIGReading] = []

    for cellname in readings:
        for timestamp in readings[cellname]:
            unsplit_readings += readings[cellname][timestamp]

    return unsplit_readings


def unsplit_readings_by_timestamp(
    readings_by_timestamp: Dict[dtm.datetime, List[CorrMIGReading]], sort=True
) -> List[CorrMIGReading]:

    timestamp_list = list(readings_by_timestamp.keys())
    
    if sort:
        timestamp_list.sort()

    readings: List[CorrMIGReading] = []
    for ts in timestamp_list:
        readings += readings_by_timestamp[ts]

    return readings


def merge_readings(
    new_readings: List[CorrMIGReading], old_readings: List[CorrMIGReading],
    overwrite_old: bool=False
) -> List[CorrMIGReading]:

    new_rdngs_splt = split_readings(new_readings)
    olds_rdngs_splt = split_readings(old_readings)

    merged_rdngs_splt = {
        cl: olds_rdngs_splt[cl].copy() for cl in olds_rdngs_splt
    }

    for cell in new_rdngs_splt:

        if cell not in merged_rdngs_splt:
            merged_rdngs_splt[cell] = new_rdngs_splt[cell].copy()
        else:
            for timestamp, reading_list in new_rdngs_splt[cell].items():
                if (timestamp not in merged_rdngs_splt[cell]) or overwrite_old:
                    merged_rdngs_splt[cell][timestamp] = reading_list

    return unsplit_readings(merged_rdngs_splt)


def write_readings(
    readings: List[CorrMIGReading], folder: str=default_save_folder,
    delete_old_data_first: bool=False, sort: bool=True
):

    readings_split = split_readings(readings)

    filepaths = {
        cellname: os.path.join(folder, f"{cellname}.txt")
        for cellname in readings_split
    }

    for cellname in readings_split:
        if os.path.exists(filepaths[cellname]) and not delete_old_data_first:
            raise ValueError(
                f"Data file '{filepaths[cellname]}' already exists!"
                " Set delete_old_data_first=True if you want to overwrite."
            )

    for cellname in readings_split:

        timestamps = list(readings_split[cellname])
        if sort:
            timestamps.sort()

        header = generate_header(cellname)

        with open(filepaths[cellname], 'w', encoding='utf8') as f:
            f.write(header)
            for timestamp in timestamps:
                for reading in readings_split[cellname][timestamp]:
                    f.write(print_line(reading))


def check_timestamp_conflicts(
    readings1: List[CorrMIGReading], readings2: List[CorrMIGReading]
) -> bool:
    readings1_split = split_readings(readings1)
    readings2_split = split_readings(readings2)

    for cell in readings1_split:
        if cell in readings2_split:
            for timestamp in readings1_split[cell]:
                if timestamp in readings2_split[cell]:
                    return True

    return False


def save_readings(
    readings: List[CorrMIGReading], folder: str=default_save_folder,
    prompt_overwrite: bool=True, default_overwrite: bool=False
):

    if not os.path.exists(folder):
        os.makedirs(folder)

    cellnames = get_cellnames_from_readings(readings)

    old_readings = load_readings(cellnames, folder)

    overwrite = default_overwrite
    if prompt_overwrite:
        conflict = check_timestamp_conflicts(readings, old_readings)
        if conflict:
            overwrite = ask_yes_no(
                "Warning: trying to save data for cell(s) and timestamp(s)"
                " that have already been saved. Do you want to overwrite old"
                " entries? (Press no to skip writing data that conflicts with"
                " existing data."
                " New data with non-conflicting cell/timestamp will still be"
                " saved.)"
            )

    merged_readings = merge_readings(readings, old_readings, overwrite)
    
    write_readings(merged_readings, folder, delete_old_data_first=True)


if __name__ == '__main__':
    readings = get_corrected_readings_from_XGEN_file(
        "FluxData\\FluxReadingCell11_01_20210203_113938.txt"
    )

    save_readings(readings)

    # for reading in readings:
    #     out_str = reading.print_to_str()
    #     print(out_str)



    # load_readings('Sb')