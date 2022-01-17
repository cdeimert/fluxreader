import atexit
from typing import List
import os
import datetime as dtm
import numpy as np

from cells import Cell
from XGEN_flux_file_parsing import (
    CorrMIGReading, parse_flux_filename, get_corrected_readings_from_XGEN_file,
    save_readings, default_save_folder_base
)
from input_dialogs import get_files_from_user, prompt_flux_measurement, show_error_and_exit

atexit.register(lambda: input("\nFinished. Press any key to exit..."))

print("Collecting flux data and running group III calibrations...\n")
print("Please select the XGEN FluxData files that you want to use.\n")

outdir_calib = os.path.join(default_save_folder_base, 'Flux calibs')

def uniquify(path):
    filename, extension = os.path.splitext(path)
    counter = 1

    while os.path.exists(path):
        path = f"{filename}-({counter}){extension}"
        counter += 1

    return path

def print_grpIII_flux_reading(
    growth_num: str, timestamp: dtm.datetime, cell: Cell, 
    target_MIG: float, readings: List[CorrMIGReading]
) -> str:

    message = (
        f"---- Flux calibration from XGEN ----\n\n"
        f"Cell: {cell.name}\n"
        f"Growth: {growth_num}\n"
        f"Timestamp: {timestamp}\n"
    )

    message += "\n"
    for par, val in readings[0].cell_par_vals.items():
        if val:
            message += f"{cell.name} {par}: {val:g}\n"

    message += f"\nFound {len(readings)} MIG readings:\n"

    min_sig_to_bg = np.inf
    min_sig_to_noise = np.inf
    for reading in readings:
        min_sig_to_noise = min(min_sig_to_noise, reading.signal_to_noise)
        min_sig_to_bg = min(min_sig_to_bg, reading.signal_to_background)
        message += (
            f"{reading.MIG_current:.6g} nA ("
            f"sig/noise={reading.signal_to_noise:.4g}, "
            f"sig/bg={reading.signal_to_background:.4g})\n"
        )

    last_MIG_a = readings[-2].MIG_current
    last_MIG_b = readings[-1].MIG_current

    I_vals = np.array([r.MIG_current for r in readings])
    dev_readings = np.std(I_vals)/np.average(I_vals)

    avg_last_2 = 0.5*(last_MIG_a + last_MIG_b)
    diff_last_2 = abs(last_MIG_a - last_MIG_b)/avg_last_2

    message += (
        f"\nAverage of last two (nA): {avg_last_2:.6g}\n"
        f"Diff. between last two: {diff_last_2*100:.4g}%\n"
    )

    message += f"\nTarget MIG (nA): {target_MIG}\n"

    ratio = avg_last_2/target_MIG

    message += (
        f"\nDeviation from target: {(ratio-1)*100:.4g}%\n"
        f"A coef correction: {ratio:.12g}\n"
    )

    short_message = (
        f"{cell.name} correction: {ratio:.12g} ({(ratio-1)*100:.4g}%)"
        f"\n(Min sig-to-noise: {min_sig_to_noise:.4g}"
        f", Min sig-to-bg: {min_sig_to_bg:.4g}"
        f", Variation: {dev_readings*100:.4g}%)"
    )

    return message, short_message
    

filenames = get_files_from_user(
    initialdir=r"V:\Growths\XGEN data\Flux data"
)

if not filenames:
    exit()

all_readings = []

grpIII_cellnames: List[str] = []

filenames = list(filenames)
filenames.sort()

_, timestamp0 = parse_flux_filename(filenames[0])

for filename in filenames:
    cell, timestamp = parse_flux_filename(filename)

    for name in ['Ga', 'In', 'Al']:
        if name in cell.name:
            grpIII_cellnames.append(cell.name)
            break

    if timestamp != timestamp0:
        show_error_and_exit(
            "Selected flux files do not all have the same timestamp."
            " For automated flux calibration, all files must have the same"
            " timestamp."
        )

if grpIII_cellnames:
    growth_num, target_MIGs = prompt_flux_measurement(
        grpIII_cellnames, timestamp0
    )

summary_message = ""

for filename in filenames:

    cell, timestamp = parse_flux_filename(filename)

    readings = get_corrected_readings_from_XGEN_file(filename)

    if cell.name in grpIII_cellnames:
        for reading in readings:
            for par, val in reading.cell_par_vals.items():
                if val != readings[0].cell_par_vals[par]:
                    show_error_and_exit(
                        "Cannot perform automated flux calibration when "
                        "Group III cell parameters are not the same for each "
                        "reading."
                    )
        message, short_message = print_grpIII_flux_reading(
            growth_num, timestamp, cell, target_MIGs[cell.name], readings
        )

        print(message)
        summary_message += '\n' + short_message + '\n'

        outfolder = os.path.join(outdir_calib, cell.name)
        os.makedirs(outfolder, exist_ok=True)

        outfilepath = os.path.join(outfolder, f"{growth_num}.txt")
        outfilepath = uniquify(outfilepath)

        with open(outfilepath, 'w', encoding='utf8') as outfile:
            outfile.write(message)

        print(
            f"(This message has been saved to '{os.path.abspath(outfilepath)}')"
        )

    all_readings += readings

print("\nSaving collected data...")
save_readings(all_readings)


if grpIII_cellnames:
    outfolder = os.path.join(outdir_calib, "Summaries")
    os.makedirs(outfolder, exist_ok=True)

    outfilepath = os.path.join(outfolder, f"{growth_num}.txt")
    outfilepath = uniquify(outfilepath)

    with open(outfilepath, 'w', encoding='utf8') as outfile:
        outfile.write(summary_message)

    print("\n---- Summary ----")
    print(summary_message)

    print(f"\n(Summary saved to '{outfilepath}')\n")
