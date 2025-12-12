"""
Metadata utility functions for auditing information.

Provides functions to collect and generate metadata for pipeline component outputs.
"""

import os
import platform
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def get_git_hash() -> str | None:
    """
    Get the current git commit hash (short form).

    Returns:
        str | None: The short git hash, or None if not in a git repository.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_package_version() -> str:
    """
    Get the package version from pyproject.toml.

    Returns:
        str: The package version, or "unknown" if not found.
    """
    try:
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "r") as f:
                for line in f:
                    if line.strip().startswith("version"):
                        # Parse: version = "0.1.0"
                        version = line.split("=")[1].strip().strip('"').strip("'")
                        return version
    except Exception:
        pass
    return "unknown"


def get_environment_info() -> dict[str, str]:
    """
    Get environment information.

    Returns:
        dict: Dictionary containing python_version, platform, and hostname.
    """
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
    }


def get_input_file_info(file_path: str) -> dict[str, Any]:
    """
    Get information about the input file.

    Args:
        file_path: Path to the input file.

    Returns:
        dict: Dictionary containing input_file (basename) and input_file_size_bytes.
    """
    path = Path(file_path)
    return {
        "input_file": path.name,
        "input_file_size_bytes": os.path.getsize(file_path) if path.exists() else None,
    }


def create_metadata(
    component: str,
    input_file: str,
    items_processed: int,
    processing_time_seconds: float,
    parameters: dict[str, Any],
    model_name: str | None = None,
    backend: str | None = None,
    device: str | None = None,
    api_calls: int | None = None,
) -> dict[str, Any]:
    """
    Create a metadata dictionary for a pipeline component output.

    Args:
        component: Name of the pipeline component.
        input_file: Path to the input video file.
        items_processed: Number of items processed.
        processing_time_seconds: Time taken for processing in seconds.
        parameters: Dictionary of component-specific parameters.
        model_name: Name of the model used (optional).
        backend: Backend used - "local" or "api" (optional).
        device: Compute device used - "cuda", "mps", "cpu" (optional).
        api_calls: Number of API calls made (optional, for API backend).

    Returns:
        dict: Metadata dictionary with all auditing information.
    """
    file_info = get_input_file_info(input_file)
    env_info = get_environment_info()

    return {
        "component": component,
        "processed_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "processing_time_seconds": round(processing_time_seconds, 2),
        "backend": backend,
        "model_name": model_name,
        "device": device,
        "input_file": file_info["input_file"],
        "input_file_size_bytes": file_info["input_file_size_bytes"],
        "items_processed": items_processed,
        "api_calls": api_calls,
        "parameters": parameters,
        "package_version": get_package_version(),
        "git_hash": get_git_hash(),
        "python_version": env_info["python_version"],
        "platform": env_info["platform"],
        "hostname": env_info["hostname"],
    }
