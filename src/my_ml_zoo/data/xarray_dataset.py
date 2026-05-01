"""Xarray dataset loading helpers for variables defined in a DatasetConfig."""

from pathlib import Path
from typing import Dict, Iterable, List, Optional

import xarray as xr

from .dataset_config import DatasetConfig
from .file_discovery import discover_variable_files, select_variable_file


def open_variable_dataset(
    dataset_config: DatasetConfig,
    variable_name: str,
    year: Optional[int] = None,
    file_path: Optional[Path] = None,
    **open_kwargs,
) -> xr.Dataset:
    """Open a single yearly or static file for a dataset variable."""
    if file_path is not None:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Variable file not found: {path}")
    else:
        variable_config = dataset_config.get_variable_config(variable_name)
        if variable_config.is_time_series and year is None:
            raise ValueError("A year must be provided when opening a time-series variable.")
        path = select_variable_file(dataset_config, variable_name, year=year)

    return xr.open_dataset(path, **open_kwargs)


def read_time_variable(
    path: Path,
    time_variable: str = "time",
    decode_times: bool = True,
    **open_kwargs,
) -> xr.DataArray:
    """Open only the time coordinate from a single netCDF file."""
    with xr.open_dataset(path, decode_times=decode_times, **open_kwargs) as ds:
        if time_variable not in ds.variables and time_variable not in ds.coords:
            raise KeyError(f"Time variable '{time_variable}' not found in {path}")
        return ds[time_variable].load()


def infer_file_year(
    path: Path,
    time_variable: str = "time",
    decode_times: bool = True,
    **open_kwargs,
) -> int:
    """Infer the year for a netCDF file from its time coordinate."""
    time_values = read_time_variable(path, time_variable=time_variable, decode_times=decode_times, **open_kwargs)
    if time_values.size == 0:
        raise ValueError(f"No time values found in file: {path}")

    time_index = time_values.to_index()
    return int(time_index[0].year)


def load_variables(
    dataset_config: DatasetConfig,
    variable_names: Optional[Iterable[str]] = None,
    year: Optional[int] = None,
    file_paths: Optional[Dict[str, Path]] = None,
    **open_kwargs,
) -> xr.Dataset:
    """Open and merge one file per variable, using the same year for all variable names."""
    variable_names = variable_names or dataset_config.get_variable_names()
    if file_paths is None and year is None:
        raise ValueError("A year must be provided when loading variables by name.")

    datasets = []
    for name in variable_names:
        if file_paths and name in file_paths:
            datasets.append(xr.open_dataset(file_paths[name], **open_kwargs))
        else:
            datasets.append(open_variable_dataset(dataset_config, name, year=year, **open_kwargs))
    return xr.merge(datasets)
