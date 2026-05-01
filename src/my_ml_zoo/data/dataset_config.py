"""Dataset configuration loading utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class StorageLayout:
    """Storage layout options for dataset files."""

    variables_in_subdirectories: bool
    default_file_pattern: str


@dataclass(frozen=True)
class VariableConfig:
    """Configuration for a single dataset variable."""

    name: str
    description: str
    directory: Optional[str]
    file_pattern: Optional[str]
    native_temporal_resolution: str

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "VariableConfig":
        """Create a VariableConfig from a dictionary loaded from JSON."""
        return cls(
            name=name,
            description=data.get("description", ""),
            directory=data.get("directory"),
            file_pattern=data.get("file_pattern"),
            native_temporal_resolution=data.get("native_temporal_resolution", ""),
        )

    @property
    def is_time_series(self) -> bool:
        """Return True when the variable contains a time coordinate series."""
        return self.native_temporal_resolution != "single_time_step"


@dataclass(frozen=True)
class DatasetConfig:
    """Strongly-typed dataset configuration for model data loading."""

    dataset_name: str
    description: str
    base_directory: Path
    file_format: str
    storage_layout: StorageLayout
    variables: Dict[str, VariableConfig]

    @classmethod
    def load_from_json(cls, path: Path) -> "DatasetConfig":
        """Load dataset configuration from a JSON file path."""
        path = Path(path)
        with path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)

        storage_layout = StorageLayout(
            variables_in_subdirectories=config.get("storage_layout", {}).get("variables_in_subdirectories", False),
            default_file_pattern=config.get("storage_layout", {}).get("default_file_pattern", "*"),
        )

        base_directory = Path(config["base_directory"])

        variables = {
            name: VariableConfig.from_dict(name, value)
            for name, value in config.get("variables", {}).items()
        }

        return cls(
            dataset_name=config.get("dataset_name", ""),
            description=config.get("description", ""),
            base_directory=base_directory,
            file_format=config.get("file_format", ""),
            storage_layout=storage_layout,
            variables=variables,
        )

    def get_variable_names(self) -> List[str]:
        """Return the ordered list of variable names defined in the config."""
        return list(self.variables.keys())

    def get_variable_config(self, variable_name: str) -> VariableConfig:
        """Return the configuration for a named variable or raise if missing."""
        try:
            return self.variables[variable_name]
        except KeyError as exc:
            raise KeyError(f"Variable '{variable_name}' is not defined in dataset config") from exc
