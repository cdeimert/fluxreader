from XGEN_flux_file_parsing import (
    parse_flux_filename, get_corrected_readings_from_XGEN_file, save_readings
)
from input_dialogs import get_files_from_user

filenames = get_files_from_user(
    initialdir=r"V:\Growths\XGEN data\Flux data"
)

all_readings = []
for filename in filenames:
    cell, timestamp = parse_flux_filename(filename)

    readings = get_corrected_readings_from_XGEN_file(filename)

    for reading in readings:
        print(reading.print_to_str())

    all_readings += readings

save_readings(all_readings)