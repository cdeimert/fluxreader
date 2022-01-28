from typing import Dict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from XGEN_flux_file_parsing import get_dataframes_from_XGEN_files, default_flux_data_folder
from input_dialogs import get_files_from_user
from flux_data_analysis import clean_up_flux_data
from plot_fluxes import plot_fluxes

growth = 'V1322o'

# Fromatted for easy pasting from the Excel sheet
target_flux_cells = ['Ga1', 'Al1', 'In1', 'Ga2', 'In2']
target_flux_str = '''
13.952
6.255
7.835
14.181
3.135
'''.strip().split('\n')

params = {
    'Ga1': {'Tip ratio (%)': 350},
    'Ga2': {'Tip ratio (%)': 250},
    'In1': {'Tip ratio (%)': 200},
    'In2': {'Tip ratio (%)': 200},
    'Sb': {'Cond (deg C)': 800, 'Crack (deg C)': 950, 'Valve (%)': 95},
    'As': {'Crack (deg C)': 950, 'Valve (%)': 98}
}


target_fluxes = {}
for tf, cl in zip(target_flux_str, target_flux_cells):
    target_fluxes[cl] = float(tf)

print(target_fluxes)

paths = get_files_from_user(initialdir=default_flux_data_folder)

data_summ, data_full = get_dataframes_from_XGEN_files(paths)

data_clean = clean_up_flux_data(data_summ)

data_clean['Growth'] = growth
data_clean['Flux gauge'] = 'MIG (nA)'

groups = data_clean.groupby('Cell type')

data: Dict[str, pd.DataFrame] = {}

for celltype, data_split in groups:

    data[celltype] = data_split

    for cell, pars in params.items():
        mask = data[celltype]['Cell'] == cell
        if any(mask):
            for par, val in pars.items():
                data[celltype].loc[mask, par] = val

if "GroupIII" in data:
    for cell, tf in target_fluxes.items():
        mask = data['GroupIII']['Cell'] == cell
        data['GroupIII'].loc[mask, 'Target'] = tf

if "As" in data:
    data['As']['Time open (min)'] = data['As']['Meas. num'] + 1

print_cols = {
    "GroupIII": ['Growth', 'Timestamp', 'Cell', 'Meas. num', 'Temp. (deg C)', 'Tip ratio (%)', 'Flux gauge', 'Reading', 'Background', 'Noise', 'Target'],
    "Sb": ['Growth', 'Timestamp', 'Meas. num', 'Temp. (deg C)', 'Cond (deg C)', 'Crack (deg C)', 'Valve (%)', 'Flux gauge', 'Reading', 'Background', 'Noise'],
    "As": ['Growth', 'Timestamp', 'Meas. num', 'Temp. (deg C)', 'Crack (deg C)', 'Valve (%)', 'Time open (min)', 'Flux gauge', 'Reading', 'Background', 'Noise'],
}

outstr = ''
for celltype in data:

    outstr += f"###### {celltype} ######\n"
    outstr += data[celltype].to_csv(sep='\t', na_rep='', columns=print_cols[celltype], index=False, line_terminator='\n')

    outstr += "\n\n\n"
    
with open("printout.txt", 'w') as outfile:
    outfile.write(outstr)

plot_fluxes(data_full)

plt.show()