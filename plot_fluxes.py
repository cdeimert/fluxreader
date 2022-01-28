from pathlib import Path
import pandas as pd

from XGEN_flux_file_parsing import get_dataframes_from_XGEN_files, default_flux_data_folder
from input_dialogs import get_files_from_user

import matplotlib.pyplot as plt
from qncmbe.plotting import styles as pltsty

pltsty.use('qncmbe')

thisdir = Path(__file__).parent.resolve()

def plot_fluxes(data_full: pd.DataFrame):

    cell_info = pd.read_csv(thisdir / 'cell_info.csv', index_col='Port')

    groups = data_full.groupby(['Port', 'Timestamp'])

    for info, data in groups:

        port, ts = info

        cell = cell_info.loc[port, 'Cell']

        fig, ax = plt.subplots()
        ax.set_title(f'{cell}, {ts}')

        subgroups = data.groupby(['Meas. num'])

        lw = data['Reading val'].min()
        hi = data['Reading val'].max()*1.2

        n = 0
        for _, subdata in subgroups:
            
            ax.plot(n + subdata['i'], subdata['Reading val'], '-', color='C0')
            
            if n > 0:
                ax.plot([n]*2, [lw, hi], ':', color=[0.3]*3)

            n += len(subdata.index)-1

        ax.set_ylim([lw, hi])
        ax.set_ylabel("MIG (nA)")
        ax.set_xlabel("i")


if __name__ == "__main__":
    path = None
    #path = default_flux_data_folder / "FluxReadingCell1_01_20211216_154309.txt"
    paths = [path]

    if not path:
        paths = get_files_from_user(
            initialdir=default_flux_data_folder
        )

    data_summ, data_full = get_dataframes_from_XGEN_files(paths)

    plot_fluxes(data_full)

    plt.show()