import logging
from datetime import datetime
from typing import Optional, Any, Dict, Tuple

from flask import Response, jsonify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s"
)

# Get module-specific logger
logger = logging.getLogger(__name__)


def parse_date_params(start_str: Optional[str] = None, end_str: Optional[str] = None) -> Tuple[
    Optional[datetime], Optional[datetime], Optional[Dict[str, str]]]:
    """
    Parse start_date and end_date from request parameters.

    Args:
        start_str: The start date string in ISO format (YYYY-MM-DD)
        end_str: The end date string in ISO format (YYYY-MM-DD)

    Returns:
        Tuple containing:
        - start_date: Parsed start date or None
        - end_date: Parsed end date or None
        - error: Error dict if parsing fails, None otherwise
    """
    try:
        start_date = datetime.fromisoformat(start_str) if start_str else None
        end_date = datetime.fromisoformat(end_str) if end_str else None
        return start_date, end_date, None
    except ValueError:
        return None, None, {'error': 'Invalid date format. Use YYYY-MM-DD.'}


def parse_boolean_param(param_value: Optional[str], default: Optional[bool] = False) -> Optional[bool]:
    """
    Parse a boolean parameter from a string value.

    Args:
        param_value: The string value to parse
        default: Default value if param_value is None or invalid

    Returns:
        Parsed boolean value or None if param_value is None
    """
    return param_value.lower() == 'true' if param_value is not None else default


def parse_tier_param(tier_param: Optional[str]) -> Optional[int]:
    """
    Parse a tier parameter from a string value.

    Args:
        tier_param: The string value to parse

    Returns:
        Parsed tier as int or None
    """
    return int(tier_param) if tier_param is not None else None


def api_response(data: Any, status_code: int = 200) -> tuple[Response, int]:
    """
    Create a standardized API response.

    Args:
        data: The data to include in the response
        status_code: HTTP status code

    Returns:
        Tuple of (Flask Response object, status code)
    """
    return jsonify(data), status_code


def handle_request_error(e: Exception, error_msg: str = 'Internal server error', status_code: int = 500) -> tuple[
    Response, int]:
    """
    Handle request errors in a standardized way.

    Args:
        e: The exception that occurred
        error_msg: Custom error message
        status_code: Error code

    Returns:
        Tuple of (Flask Response object with error details, status code)
    """
    logger.error(f"{error_msg}: {str(e)}", exc_info=True)
    return api_response({'error': error_msg}, status_code)
