from typing import List
from pathlib import Path

from tkinter import Tk, filedialog, messagebox


def get_files_from_user(initialdir: Path=None) -> List[Path]:

    root = Tk()
    root.withdraw()

    filenames = filedialog.askopenfilenames(
        initialdir=initialdir
    )
    root.destroy()

    fpaths = [Path(fname) for fname in filenames]

    return fpaths


def show_error_and_exit(message:str):
    root = Tk()
    root.withdraw()

    messagebox.showerror(
        title='Error', message=message+"\nTerminating program..."
    )

    root.destroy()
    exit()

