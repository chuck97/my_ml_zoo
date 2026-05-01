"""Helpers to discover dataset files using a dataset configuration."""

from pathlib import Path
from typing import Dict, List, Optional

import xarray as xr

from .dataset_config import DatasetConfig, VariableConfig


def discover_variable_files(dataset_config: DatasetConfig, variable_name: str) -> List[Path]:
    """Return a sorted list of file paths for a specific variable."""
    variable = dataset_config.get_variable_config(variable_name)

    directory = dataset_config.base_directory
    if variable.directory:
        directory = directory / variable.directory

    if not directory.exists():
        raise FileNotFoundError(
            f"Variable directory not found for '{variable_name}': {directory}"
        )

    file_pattern = variable.file_pattern or dataset_config.storage_layout.default_file_pattern
    file_paths = sorted(directory.glob(file_pattern))
    return file_paths


def _infer_file_year(path: Path, time_variable: str = "time") -> int:
    """Open only the time coordinate of a netCDF file and return the first year."""
    with xr.open_dataset(path, decode_times=True) as ds:
        if time_variable not in ds.variables and time_variable not in ds.coords:
            raise KeyError(f"Time variable '{time_variable}' not found in {path}")

        time_values = ds[time_variable]
        if time_values.size == 0:
            raise ValueError(f"No time values found in file: {path}")

        time_index = time_values.to_index()
        return int(time_index[0].year)


def select_variable_file(
    dataset_config: DatasetConfig,
    variable_name: str,
    year: Optional[int] = None,
    file_name: Optional[str] = None,
) -> Path:
    """Select one file for a variable, by explicit name or year.

    For static variables, the year argument is ignored because the file
    represents a single static snapshot rather than a time series.
    """
    variable_config = dataset_config.get_variable_config(variable_name)
    file_paths = discover_variable_files(dataset_config, variable_name)
    if not file_paths:
        raise FileNotFoundError(f"No files found for variable '{variable_name}'")

    if file_name is not None:
        matching = [path for path in file_paths if path.name == file_name]
        if not matching:
            raise FileNotFoundError(
                f"File '{file_name}' not found for variable '{variable_name}'"
            )
        return matching[0]

    if variable_config.is_time_series and year is not None:
        year_str = str(year)
        candidates = [path for path in file_paths if year_str in path.name]
        if not candidates:
            candidates = file_paths

        for candidate in candidates:
            try:
                if _infer_file_year(candidate) == year:
                    return candidate
            except (KeyError, ValueError):
                continue

        raise FileNotFoundError(
            f"No files found for variable '{variable_name}' matching year {year}"
        )

    return file_paths[0]


def discover_all_variables(dataset_config: DatasetConfig) -> Dict[str, List[Path]]:
    """Discover all dataset variables and return their matching files."""
    return {
        variable_name: discover_variable_files(dataset_config, variable_name)
        for variable_name in dataset_config.get_variable_names()
    }
