"""X-Ray tracing decorators for function instrumentation.

Issue #167: Distributed tracing with X-Ray.
"""

import functools
import time
from typing import Any, Callable, Optional, TypeVar

from cloud_optimizer.tracing.service import get_tracing_service

F = TypeVar("F", bound=Callable[..., Any])


def trace_function(
    name: Optional[str] = None,
    namespace: str = "local",
    capture_args: bool = False,
    capture_result: bool = False,
) -> Callable[[F], F]:
    """Decorator to trace synchronous function execution with X-Ray.

    Creates a subsegment for the decorated function.

    Args:
        name: Optional subsegment name (defaults to function name)
        namespace: Subsegment namespace (local, remote, aws)
        capture_args: Whether to capture function arguments as metadata
        capture_result: Whether to capture return value as metadata

    Returns:
        Decorated function

    Example:
        @trace_function("process_data")
        def process_data(data):
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracing = get_tracing_service()
            subseg_name = name or func.__name__

            with tracing.subsegment(subseg_name, namespace) as subseg:
                start_time = time.perf_counter()

                try:
                    # Capture arguments if enabled
                    if capture_args and subseg:
                        tracing.add_metadata(
                            "args",
                            {"args": str(args)[:500], "kwargs": str(kwargs)[:500]},
                            namespace="function",
                        )

                    result = func(*args, **kwargs)

                    # Capture result if enabled
                    if capture_result and subseg:
                        tracing.add_metadata(
                            "result",
                            str(result)[:500],
                            namespace="function",
                        )

                    return result

                except Exception as e:
                    if subseg:
                        tracing.add_exception(e, subseg)
                    raise

                finally:
                    if subseg:
                        duration_ms = (time.perf_counter() - start_time) * 1000
                        tracing.add_metadata(
                            "duration_ms",
                            round(duration_ms, 2),
                            namespace="performance",
                        )

        return wrapper  # type: ignore

    return decorator


def trace_async_function(
    name: Optional[str] = None,
    namespace: str = "local",
    capture_args: bool = False,
    capture_result: bool = False,
) -> Callable[[F], F]:
    """Decorator to trace async function execution with X-Ray.

    Creates a subsegment for the decorated async function.

    Args:
        name: Optional subsegment name (defaults to function name)
        namespace: Subsegment namespace (local, remote, aws)
        capture_args: Whether to capture function arguments as metadata
        capture_result: Whether to capture return value as metadata

    Returns:
        Decorated async function

    Example:
        @trace_async_function("fetch_data")
        async def fetch_data(url):
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracing = get_tracing_service()
            subseg_name = name or func.__name__

            with tracing.subsegment(subseg_name, namespace) as subseg:
                start_time = time.perf_counter()

                try:
                    # Capture arguments if enabled
                    if capture_args and subseg:
                        tracing.add_metadata(
                            "args",
                            {"args": str(args)[:500], "kwargs": str(kwargs)[:500]},
                            namespace="function",
                        )

                    result = await func(*args, **kwargs)

                    # Capture result if enabled
                    if capture_result and subseg:
                        tracing.add_metadata(
                            "result",
                            str(result)[:500],
                            namespace="function",
                        )

                    return result

                except Exception as e:
                    if subseg:
                        tracing.add_exception(e, subseg)
                    raise

                finally:
                    if subseg:
                        duration_ms = (time.perf_counter() - start_time) * 1000
                        tracing.add_metadata(
                            "duration_ms",
                            round(duration_ms, 2),
                            namespace="performance",
                        )

        return wrapper  # type: ignore

    return decorator


def trace_database(
    operation: Optional[str] = None,
    database_type: str = "postgresql",
    capture_query: bool = False,
) -> Callable[[F], F]:
    """Decorator to trace database operations with X-Ray.

    Creates a subsegment with database-specific metadata.

    Args:
        operation: Database operation name (query, insert, update, delete)
        database_type: Type of database
        capture_query: Whether to capture query text (may contain PII)

    Returns:
        Decorated function

    Example:
        @trace_database(operation="query", database_type="postgresql")
        async def get_users():
            ...
    """

    def decorator(func: F) -> F:
        import asyncio

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracing = get_tracing_service()
            op_name = operation or func.__name__
            subseg_name = f"database.{op_name}"

            with tracing.subsegment(subseg_name, namespace="remote") as subseg:
                start_time = time.perf_counter()

                try:
                    if subseg:
                        tracing.add_annotation("db.type", database_type)
                        tracing.add_annotation("db.operation", op_name)

                    result = func(*args, **kwargs)
                    return result

                except Exception as e:
                    if subseg:
                        tracing.add_exception(e, subseg)
                        tracing.add_annotation("db.error", True)
                    raise

                finally:
                    if subseg:
                        duration_ms = (time.perf_counter() - start_time) * 1000
                        tracing.add_metadata(
                            "sql",
                            {
                                "database_type": database_type,
                                "operation": op_name,
                                "duration_ms": round(duration_ms, 2),
                            },
                            namespace="sql",
                        )

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracing = get_tracing_service()
            op_name = operation or func.__name__
            subseg_name = f"database.{op_name}"

            with tracing.subsegment(subseg_name, namespace="remote") as subseg:
                start_time = time.perf_counter()

                try:
                    if subseg:
                        tracing.add_annotation("db.type", database_type)
                        tracing.add_annotation("db.operation", op_name)

                    result = await func(*args, **kwargs)
                    return result

                except Exception as e:
                    if subseg:
                        tracing.add_exception(e, subseg)
                        tracing.add_annotation("db.error", True)
                    raise

                finally:
                    if subseg:
                        duration_ms = (time.perf_counter() - start_time) * 1000
                        tracing.add_metadata(
                            "sql",
                            {
                                "database_type": database_type,
                                "operation": op_name,
                                "duration_ms": round(duration_ms, 2),
                            },
                            namespace="sql",
                        )

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def trace_http_call(
    service: Optional[str] = None,
    operation: Optional[str] = None,
) -> Callable[[F], F]:
    """Decorator to trace external HTTP calls with X-Ray.

    Creates a subsegment for HTTP requests to external services.

    Args:
        service: Name of the external service being called
        operation: Name of the operation being performed

    Returns:
        Decorated function

    Example:
        @trace_http_call(service="intelligence-builder", operation="query")
        async def call_ib_api():
            ...
    """

    def decorator(func: F) -> F:
        import asyncio

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracing = get_tracing_service()
            svc_name = service or "external"
            op_name = operation or func.__name__
            subseg_name = f"{svc_name}.{op_name}"

            with tracing.subsegment(subseg_name, namespace="remote") as subseg:
                start_time = time.perf_counter()

                try:
                    if subseg:
                        tracing.add_annotation("http.service", svc_name)
                        tracing.add_annotation("http.operation", op_name)

                    result = func(*args, **kwargs)
                    return result

                except Exception as e:
                    if subseg:
                        tracing.add_exception(e, subseg)
                        tracing.add_annotation("http.error", True)
                    raise

                finally:
                    if subseg:
                        duration_ms = (time.perf_counter() - start_time) * 1000
                        tracing.add_metadata(
                            "http",
                            {
                                "service": svc_name,
                                "operation": op_name,
                                "duration_ms": round(duration_ms, 2),
                            },
                            namespace="http",
                        )

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracing = get_tracing_service()
            svc_name = service or "external"
            op_name = operation or func.__name__
            subseg_name = f"{svc_name}.{op_name}"

            with tracing.subsegment(subseg_name, namespace="remote") as subseg:
                start_time = time.perf_counter()

                try:
                    if subseg:
                        tracing.add_annotation("http.service", svc_name)
                        tracing.add_annotation("http.operation", op_name)

                    result = await func(*args, **kwargs)
                    return result

                except Exception as e:
                    if subseg:
                        tracing.add_exception(e, subseg)
                        tracing.add_annotation("http.error", True)
                    raise

                finally:
                    if subseg:
                        duration_ms = (time.perf_counter() - start_time) * 1000
                        tracing.add_metadata(
                            "http",
                            {
                                "service": svc_name,
                                "operation": op_name,
                                "duration_ms": round(duration_ms, 2),
                            },
                            namespace="http",
                        )

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def trace_scanner(
    scanner_type: str,
) -> Callable[[F], F]:
    """Decorator to trace scanner operations with X-Ray.

    Creates a subsegment with scanner-specific metadata.

    Args:
        scanner_type: Type of scanner (iam, s3, lambda, ec2, etc.)

    Returns:
        Decorated function

    Example:
        @trace_scanner("iam")
        async def scan_iam_policies():
            ...
    """

    def decorator(func: F) -> F:
        import asyncio

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracing = get_tracing_service()
            subseg_name = f"scanner.{scanner_type}"

            with tracing.subsegment(subseg_name, namespace="local") as subseg:
                start_time = time.perf_counter()

                try:
                    if subseg:
                        tracing.add_annotation("scanner.type", scanner_type)

                    result = func(*args, **kwargs)

                    # Record result metrics if available
                    if subseg and isinstance(result, dict):
                        if "findings_count" in result:
                            tracing.add_annotation(
                                "scanner.findings", result["findings_count"]
                            )
                        if "resources_scanned" in result:
                            tracing.add_annotation(
                                "scanner.resources", result["resources_scanned"]
                            )

                    return result

                except Exception as e:
                    if subseg:
                        tracing.add_exception(e, subseg)
                        tracing.add_annotation("scanner.error", True)
                    raise

                finally:
                    if subseg:
                        duration_ms = (time.perf_counter() - start_time) * 1000
                        tracing.add_metadata(
                            "scanner",
                            {
                                "type": scanner_type,
                                "duration_ms": round(duration_ms, 2),
                            },
                            namespace="scanner",
                        )

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracing = get_tracing_service()
            subseg_name = f"scanner.{scanner_type}"

            with tracing.subsegment(subseg_name, namespace="local") as subseg:
                start_time = time.perf_counter()

                try:
                    if subseg:
                        tracing.add_annotation("scanner.type", scanner_type)

                    result = await func(*args, **kwargs)

                    # Record result metrics if available
                    if subseg and isinstance(result, dict):
                        if "findings_count" in result:
                            tracing.add_annotation(
                                "scanner.findings", result["findings_count"]
                            )
                        if "resources_scanned" in result:
                            tracing.add_annotation(
                                "scanner.resources", result["resources_scanned"]
                            )

                    return result

                except Exception as e:
                    if subseg:
                        tracing.add_exception(e, subseg)
                        tracing.add_annotation("scanner.error", True)
                    raise

                finally:
                    if subseg:
                        duration_ms = (time.perf_counter() - start_time) * 1000
                        tracing.add_metadata(
                            "scanner",
                            {
                                "type": scanner_type,
                                "duration_ms": round(duration_ms, 2),
                            },
                            namespace="scanner",
                        )

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator
