import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


def exception_wrapper(func: Callable[[], Any]) -> Any | str:
    """Wrap to catch exceptions and return error messages."""
    try:
        return func()
    except ImportError as e:
        error_msg = f"Error when running {str(func)}: {e}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error when running {str(func)}: {e}"
        logger.error(error_msg)
        return error_msg

