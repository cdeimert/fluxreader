import re
from pathlib import Path
import datetime as dtm
from typing import List, Dict, Tuple

import numpy as np
import pandas as pd


default_flux_data_folder = Path(r"V:\Growths\XGEN data\Flux data")

filename_regex = re.compile(
    r'FluxReadingCell(?P<port>\d\d?)_01_(?P<timestamp>\d{8}_\d{6}).txt$'
)


def parse_flux_filename(fpath: Path):
    match = filename_regex.match(fpath.name)

    if match:
        port = int(match['port'])
        timestamp_str = match['timestamp']

        timestamp = dtm.datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')

        return port, timestamp
    else: 
        raise ValueError(f"Unrecognized filename format: '{fpath}'")


class XGEN_flux_reading():
    flux_line_pattern = re.compile(
        r'^(?P<type>Fluxcal   |Background), Cell, (?P<cell>\d+), '
        r'Reading, (?P<num>\d+), Temp, (?P<temp>\d+\.\d+), '
        r'Average, (?P<avg>\d+\.\d+), Readings(?P<vals>(, -?\d+\.\d+ ){24})$'
    )

    def __init__(self, line: str, timestamp: dtm.datetime, num: int):

        self.timestamp = timestamp

        match = self.flux_line_pattern.match(line)

        if not match:
            raise ValueError(f"Unexpected line format:\n'{line}'")

        self.num = num
        # Note: reading number is unreliable in the XGEN flux files. Seems to
        # stop counting at 10. Has to be set artificially.

        self.meastype = match['type'].strip()
        self.port = int(match['cell'])
        self.temp = float(match['temp'])
        self.avg = float(match['avg'])

        vals_str = match['vals'].split(',')[1:]

        self.vals = np.array([float(val) for val in vals_str])

        self.vals_reduced = self.calc_vals_reduced()

        self.noise = np.std(self.vals_reduced)

    def calc_vals_reduced(self):
        ''' Create reduced array which is missing the highest two and
        lowest two values. This reduced array is what XGEN uses to
        calculate averages.'''

        vals_reduced = list(self.vals)
        for i in range(2):
            vals_reduced.remove(max(vals_reduced))
            vals_reduced.remove(min(vals_reduced))

        return vals_reduced

    def confirm_avg(self):
        MIG_current = np.average(self.vals_reduced)

        if (MIG_current - self.avg)/self.avg > 1e-12:
            raise ValueError(
                f"Average reading in file ({self.avg}) does not match calculated"
                f" average ({MIG_current})"
            )

    def to_dataframes(self):

        basic_info = {
            'Timestamp': self.timestamp,
            'Port': self.port,
            'Meas. num': self.num,
        }

        data_summ = pd.DataFrame({
            **basic_info,
            'Meas. type': self.meastype,
            'Temp. (deg C)': self.temp,
            'Avg. reading': [self.avg],
            'Noise': [self.noise],
        })

        data_full = pd.DataFrame({
            **basic_info,
            'i': pd.RangeIndex(len(self.vals)),
            'Reading val': self.vals,
        })

        return data_summ, data_full


def get_readings_from_XGEN_files(fpaths: List[Path]):

    readings = []

    for fpath in fpaths:

        _, timestamp = parse_flux_filename(fpath)

        num = 0

        with open(fpath, 'r') as ffile:
            for line in ffile:
                if line.strip():
                    reading = XGEN_flux_reading(line, timestamp, num)
                    num += 1

                    readings.append(reading)

    return readings


def readings_to_dataframes(readings: List[XGEN_flux_reading]):

    ds_list = []
    df_list = []

    for reading in readings:
        ds, df = reading.to_dataframes()

        ds_list.append(ds)
        df_list.append(df)

    data_summ = pd.concat(ds_list, ignore_index=True)
    data_full = pd.concat(df_list, ignore_index=True)

    return data_summ, data_full


def get_dataframes_from_XGEN_files(fpaths: List[Path]) -> Tuple[pd.DataFrame, pd.DataFrame]:

    readings = get_readings_from_XGEN_files(fpaths)
    data_summ, data_full = readings_to_dataframes(readings)

    return data_summ, data_full


if __name__ == '__main__':

    from input_dialogs import get_files_from_user

    path = None
    #path = default_flux_data_folder / "FluxReadingCell1_01_20211216_154309.txt"
    paths = [path]

    if not path:
        paths = get_files_from_user(
            initialdir=default_flux_data_folder
        )

    ds, df = get_dataframes_from_XGEN_files(paths)

    print(ds)
    #print(ds.loc[:, 'port'])