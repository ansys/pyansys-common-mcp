"""Environment and version checking tools for PyAnsys MCP servers.

These tools provide information about the Python environment and
installed PyAnsys packages.
"""

import logging
import platform
import sys
from importlib.metadata import version, PackageNotFoundError

logger = logging.getLogger(__name__)


def check_package_version(package_name: str) -> str:
    """Check if a Python package is installed and return its version.

    This tool is useful for verifying that required PyAnsys packages
    are installed and determining their versions for compatibility
    checking or troubleshooting.

    Parameters
    ----------
    package_name : str
        Name of the package to check (e.g., 'ansys-mapdl-core').

    Returns
    -------
    str
        Package version if installed, or an error message if not found.

    Examples
    --------
    Check if PyMAPDL is installed:

    >>> check_package_version("ansys-mapdl-core")
    'ansys-mapdl-core version: 0.68.3'

    Check a non-existent package:

    >>> check_package_version("nonexistent-package")
    'Package "nonexistent-package" is not installed'
    """
    try:
        pkg_version = version(package_name)
        logger.info(f"Found {package_name} version {pkg_version}")
        return f"{package_name} version: {pkg_version}"
    except PackageNotFoundError:
        msg = f'Package "{package_name}" is not installed'
        logger.warning(msg)
        return msg
    except Exception as e:
        error_msg = f"Error checking package version for {package_name}: {str(e)}"
        logger.error(error_msg)
        return error_msg


def get_python_environment_info() -> str:
    """Get comprehensive Python environment information.

    This tool returns detailed information about the Python environment,
    which is useful for troubleshooting and ensuring compatibility.

    Returns
    -------
    str
        Formatted string with Python version, platform, and system information.

    Examples
    --------
    Get environment information:

    >>> get_python_environment_info()
    '''Python Environment Information:
    Python Version: 3.11.5
    Platform: Windows-10-10.0.19045-SP0
    System: Windows
    Architecture: AMD64
    Processor: Intel64 Family 6 Model 140 Stepping 1, GenuineIntel
    '''
    """
    try:
        info_lines = [
            "Python Environment Information:",
            f"Python Version: {sys.version.split()[0]}",
            f"Platform: {platform.platform()}",
            f"System: {platform.system()}",
            f"Architecture: {platform.machine()}",
            f"Processor: {platform.processor()}",
        ]

        # Add Python executable path
        info_lines.append(f"Python Executable: {sys.executable}")

        result = "\n".join(info_lines)
        logger.info("Retrieved Python environment information")
        return result

    except Exception as e:
        error_msg = f"Error getting environment information: {str(e)}"
        logger.error(error_msg)
        return error_msg
