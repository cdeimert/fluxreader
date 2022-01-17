from typing import List, Dict


class Cell():
    def __init__(
        self, name: str, port: int, extra_pars: List[str] = [], 
        par_defaults: Dict[str, float] = None
    ):
        '''Extra_pars should be a list of cell parameters (aside from 
        'Temp (°C)', which is always a parameter). 
        
        par_defaults should be a dictionary of default values for parameters,
        with keys that are a subset of the cell parameters'''
        self.name = name
        self.port = port
        self.pars = ["Temp (°C)"] + extra_pars

        self.par_defaults = {par: None for par in self.pars}

        if par_defaults:
            for par, val in par_defaults.items():
                if par not in self.pars:
                    raise ValueError(
                        f"Cannot set default for '{par}': not a cell parameter."
                    )
                else:
                    self.par_defaults[par] = val

class DualFilCell(Cell):
    def __init__(
        self, name: str, port: int, tip_ratio_default: float=None
    ) -> None:

        extra_pars = ['Tip Ratio (%)']
        defaults = {'Tip Ratio (%)': tip_ratio_default}

        super().__init__(name, port, extra_pars, defaults)

class SingleFilCell(Cell):
    def __init__(self, name: str, port: int) -> None:

        super().__init__(name, port)
 

class AsCell(Cell):
    def __init__(
        self, name: str, port: int, cracker_temp_default: float=None
    ) -> None:

        extra_pars = ['Valve (%)', 'Crack Temp (°C)', 'Time after opening (min)']
        defaults = {
            'Crack Temp (°C)': cracker_temp_default
        }

        super().__init__(name, port, extra_pars, defaults)

class SbCell(Cell):
    def __init__(
        self, name: str, port: int, cracker_temp_default: float=None,
        cond_temp_default: float=None
    ) -> None:

        extra_pars = ['Valve (%)', 'Crack Temp (°C)', 'Cond Temp (°C)']
        defaults = {
            'Crack Temp (°C)': cracker_temp_default,
            'Cond Temp (°C)': cond_temp_default
        }

        super().__init__(name, port, extra_pars, defaults)

class CellList():
    def __init__(self, cells: List[Cell]) -> None:
        self.cells = cells

    def find_by_port(self, port):
        for cell in self.cells:
            if cell.port == port:
                return cell
        
        raise ValueError(f"No cell with port {port}")

    def find_by_name(self, name):
        for cell in self.cells:
            if cell.name == name:
                return cell
        
        raise ValueError(f"No cell with name '{name}'")


# NOTE: These port numbers may only apply to the 2020-2021 campaign
cells = CellList([
    AsCell(
        name='As', 
        port=1,
        cracker_temp_default=950
    ),
    DualFilCell(
        name='In1',
        port=2,
        tip_ratio_default=200
    ),
    SingleFilCell(
        name='Al2',
        port=6
    ),
    DualFilCell(
        name='Ga2',
        port=7,
        tip_ratio_default=250
    ),
    DualFilCell(
        name='Ga1',
        port=8,
        tip_ratio_default=350
    ),
    DualFilCell(
        name='In2',
        port=9,
        tip_ratio_default=200
    ),
    SingleFilCell(
        name='Al1',
        port=10
    ),
    SbCell(
        name='Sb',
        port=11,
        cond_temp_default=800,
        cracker_temp_default=950
    )
])
