"""
Logging Decorators for AI Video Factory
Provides decorators for automatic logging of function calls, errors, and timing
"""
import functools
import time
import logging
import traceback
from inspect import signature
from core.logger_config import get_logger, setup_api_logger, setup_agent_logger


def log_api_call(func):
    """
    Decorator to log API calls with timing, request/response preview, and errors.

    Logs to api_calls.log with:
    - Function name and arguments
    - Execution time
    - Response preview (first 200 chars)
    - Errors with full traceback

    Usage:
        @log_api_call
        def ask(prompt: str) -> str:
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get API logger for this function
        logger = setup_api_logger(func.__module__)

        # Get function signature for parameter names
        sig = signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Log function call with parameters
        param_str = ", ".join(f"{k}={_truncate_value(v)}" for k, v in bound_args.arguments.items())
        logger.debug(f"API CALL: {func.__name__}()")
        logger.debug(f"  Args: {param_str}")

        # Execute with timing
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time

            # Log success with timing
            logger.debug(f"  Response: {_truncate_value(result)}")
            logger.debug(f"  Success in {elapsed:.2f}s")

            return result

        except Exception as e:
            elapsed = time.time() - start_time

            # Log error with traceback
            logger.error(f"  Failed in {elapsed:.2f}s: {str(e)}")
            logger.error(f"  Traceback: {traceback.format_exc()}")

            # Re-raise exception
            raise

    return wrapper


def log_agent_call(func):
    """
    Decorator to log agent operations with parameters and results.

    Logs to agents.log with:
    - Agent type and name
    - File path
    - Prompt/response length
    - Execution status

    Usage:
        @log_agent_call
        def load_prompt(agent_type: str, agent_name: str) -> str:
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get agent logger for this function
        logger = setup_agent_logger(func.__module__)

        # Get function signature for parameter names
        sig = signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Log agent operation
        logger.info(f"AGENT: {func.__name__}()")

        # Log key parameters
        for key in ['agent_type', 'agent_name', 'file_path', 'prompt']:
            if key in bound_args.arguments:
                value = bound_args.arguments[key]
                if key == 'prompt':
                    logger.debug(f"  {key}: {len(str(value))} characters")
                elif key == 'file_path':
                    logger.debug(f"  {key}: {value}")
                else:
                    logger.info(f"  {key}: {value}")

        # Execute with timing
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time

            # Log success
            if isinstance(result, str):
                logger.debug(f"  Result: {len(result)} characters")
            logger.debug(f"  Success in {elapsed:.2f}s")

            return result

        except Exception as e:
            elapsed = time.time() - start_time

            # Log error
            logger.error(f"  Failed in {elapsed:.2f}s: {str(e)}")
            logger.debug(f"  Traceback: {traceback.format_exc()}")

            # Re-raise exception
            raise

    return wrapper


def log_errors(func):
    """
    Decorator to catch and log exceptions with full traceback.

    Logs to errors.log with:
    - Function name and location
    - Full exception traceback
    - Parameters that caused the error

    Usage:
        @log_errors
        def risky_operation():
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get regular logger for this function
        logger = get_logger(func.__module__)

        try:
            return func(*args, **kwargs)

        except Exception as e:
            # Get function signature for parameter names
            sig = signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Log error with context
            logger.error(f"Exception in {func.__name__}(): {str(e)}")
            logger.error(f"  Parameters: {bound_args.arguments}")
            logger.error(f"  Traceback:\n{traceback.format_exc()}")

            # Re-raise exception
            raise

    return wrapper


def _truncate_value(value, max_length=200):
    """
    Truncate a value for log display.

    Args:
        value: Value to truncate
        max_length: Maximum length to display

    Returns:
        Truncated string representation
    """
    if value is None:
        return "None"

    value_str = str(value)

    if len(value_str) <= max_length:
        return value_str

    # Truncate and add indicator
    return value_str[:max_length] + "..."


if __name__ == "__main__":
    # Test decorators

    # Test @log_api_call
    @log_api_call
    def test_api_call(prompt, response_format=None):
        """Simulated API call"""
        time.sleep(0.1)
        if "error" in prompt.lower():
            raise ValueError("Simulated API error")
        return f"Response to: {prompt[:50]}"

    print("\n=== Testing @log_api_call decorator ===")
    test_api_call("Hello world")
    try:
        test_api_call("Trigger error")
    except:
        pass

    # Test @log_agent_call
    @log_agent_call
    def test_agent_call(agent_type, agent_name="default"):
        """Simulated agent call"""
        time.sleep(0.1)
        if agent_type == "invalid":
            raise FileNotFoundError("Agent not found")
        return f"Loaded {agent_type}/{agent_name}"

    print("\n=== Testing @log_agent_call decorator ===")
    test_agent_call("story", "default")
    try:
        test_agent_call("invalid", "missing")
    except:
        pass

    # Test @log_errors
    @log_errors
    def test_error_operation(value):
        """Simulated operation that may fail"""
        if value < 0:
            raise ValueError("Value must be positive")
        return value * 2

    print("\n=== Testing @log_errors decorator ===")
    test_error_operation(5)
    try:
        test_error_operation(-1)
    except:
        pass

    print("\nDecorator tests complete. Check logs/")
