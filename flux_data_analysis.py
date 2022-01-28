from pathlib import Path
import pandas as pd

from XGEN_flux_file_parsing import get_dataframes_from_XGEN_files, default_flux_data_folder
from input_dialogs import get_files_from_user

thisdir = Path(__file__).parent.resolve()

def add_cell_info(data_summ: pd.DataFrame):
    cell_info = pd.read_csv(thisdir / 'cell_info.csv')

    return data_summ.merge(cell_info, on='Port')


def merge_backgrounds(data_summ: pd.DataFrame):
    '''Tries to add a background measurement for each Fluxcal measurement.
    Important! Assumes that if there is a flux measurement followed by a
    background measurement under the same cell+timestamp, then that background
    corresponds to that flux measurement.
    
    If there are two+ background measurements in a row, only the first one will
    be used.'''

    grouped = data_summ.groupby('Meas. type')

    flx = grouped.get_group('Fluxcal')
    bg = grouped.get_group('Background')

    flx = flx.drop('Meas. type', axis=1)
    bg = bg.drop('Meas. type', axis=1)

    flx['BG num'] = flx['Meas. num'] + 1

    cols = ['Timestamp', 'Port', 'Temp. (deg C)']
    left_on = cols + ['BG num']
    right_on = cols + ['Meas. num']

    merged = flx.merge(bg, left_on=left_on, right_on=right_on, how='left', suffixes=['', ' (BG)'])

    mask = ~merged['Noise (BG)'].isna()

    merged.loc[mask, 'Noise'] = (merged.loc[mask, 'Noise'] + merged.loc[mask, 'Noise (BG)'])/2


    merged.drop(['BG num', 'Meas. num (BG)', 'Noise (BG)'], axis=1, inplace=True)

    merged.rename(
        columns={
            'Avg. reading': 'Reading',
            'Avg. reading (BG)': 'Background',
        }, 
        inplace=True
    )

    return merged


def renumber_measurements(data_summ: pd.DataFrame):
    groups = data_summ.groupby(['Timestamp', 'Port', 'Temp. (deg C)'])

    newrows = []

    for name, group in groups:
        group['Meas. num'] = [n for n in range(len(group.index))]

        newrows.append(group)

    return pd.concat(newrows, ignore_index=True)


def clean_up_flux_data(data_summ):

    dc = merge_backgrounds(data_summ)
    dc = renumber_measurements(dc)
    dc = add_cell_info(dc)

    return dc


if __name__ == '__main__':

    path = None
    #path = default_flux_data_folder / "FluxReadingCell1_01_20211216_154309.txt"
    paths = [path]

    if not path:
        paths = get_files_from_user(
            initialdir=default_flux_data_folder
        )

    data_summ, data_full = get_dataframes_from_XGEN_files(paths)
    #add_cell_info(data_summ)
    print(clean_up_flux_data(data_summ))