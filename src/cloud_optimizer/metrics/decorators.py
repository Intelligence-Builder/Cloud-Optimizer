"""Metrics decorators for easy instrumentation.

Issue #166: Application metrics with CloudWatch Metrics.
Provides decorators to automatically track latency, errors, and invocations.
"""

import functools
import time
from typing import Any, Callable, Optional, TypeVar, cast

from cloud_optimizer.metrics.service import get_metrics_service
from cloud_optimizer.metrics.types import MetricDimension, MetricUnit

F = TypeVar("F", bound=Callable[..., Any])


def track_latency(
    metric_name: str = "FunctionLatency",
    operation: Optional[str] = None,
    dimensions: Optional[list[MetricDimension]] = None,
) -> Callable[[F], F]:
    """Decorator to track function execution latency.

    Args:
        metric_name: Name of the latency metric
        operation: Optional operation name for dimension
        dimensions: Additional dimensions to include

    Returns:
        Decorated function that records latency metrics

    Example:
        @track_latency("ScanLatency", operation="iam_scan")
        def scan_iam_policies():
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                _record_latency(
                    metric_name,
                    duration_ms,
                    operation or func.__name__,
                    dimensions,
                )

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                _record_latency(
                    metric_name,
                    duration_ms,
                    operation or func.__name__,
                    dimensions,
                )

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)

    return decorator


def _record_latency(
    metric_name: str,
    duration_ms: float,
    operation: str,
    extra_dimensions: Optional[list[MetricDimension]],
) -> None:
    """Record latency metric."""
    service = get_metrics_service()
    dims = [MetricDimension("Operation", operation)]
    if extra_dimensions:
        dims.extend(extra_dimensions)
    service.put_metric(metric_name, duration_ms, MetricUnit.MILLISECONDS, dims)


def track_errors(
    metric_name: str = "FunctionErrors",
    operation: Optional[str] = None,
    dimensions: Optional[list[MetricDimension]] = None,
    reraise: bool = True,
) -> Callable[[F], F]:
    """Decorator to track function errors.

    Args:
        metric_name: Name of the error metric
        operation: Optional operation name for dimension
        dimensions: Additional dimensions to include
        reraise: Whether to re-raise caught exceptions

    Returns:
        Decorated function that records error metrics

    Example:
        @track_errors("ScanErrors", operation="s3_scan")
        def scan_s3_buckets():
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                _record_error(
                    metric_name,
                    operation or func.__name__,
                    type(e).__name__,
                    dimensions,
                )
                if reraise:
                    raise

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                _record_error(
                    metric_name,
                    operation or func.__name__,
                    type(e).__name__,
                    dimensions,
                )
                if reraise:
                    raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)

    return decorator


def _record_error(
    metric_name: str,
    operation: str,
    error_type: str,
    extra_dimensions: Optional[list[MetricDimension]],
) -> None:
    """Record error metric."""
    service = get_metrics_service()
    dims = [
        MetricDimension("Operation", operation),
        MetricDimension("ErrorType", error_type),
    ]
    if extra_dimensions:
        dims.extend(extra_dimensions)
    service.put_metric(metric_name, 1, MetricUnit.COUNT, dims)


def count_invocations(
    metric_name: str = "FunctionInvocations",
    operation: Optional[str] = None,
    dimensions: Optional[list[MetricDimension]] = None,
) -> Callable[[F], F]:
    """Decorator to count function invocations.

    Args:
        metric_name: Name of the invocation metric
        operation: Optional operation name for dimension
        dimensions: Additional dimensions to include

    Returns:
        Decorated function that counts invocations

    Example:
        @count_invocations("ScanInvocations", operation="lambda_scan")
        def scan_lambda_functions():
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            _record_invocation(
                metric_name,
                operation or func.__name__,
                dimensions,
            )
            return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            _record_invocation(
                metric_name,
                operation or func.__name__,
                dimensions,
            )
            return await func(*args, **kwargs)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)

    return decorator


def _record_invocation(
    metric_name: str,
    operation: str,
    extra_dimensions: Optional[list[MetricDimension]],
) -> None:
    """Record invocation metric."""
    service = get_metrics_service()
    dims = [MetricDimension("Operation", operation)]
    if extra_dimensions:
        dims.extend(extra_dimensions)
    service.put_metric(metric_name, 1, MetricUnit.COUNT, dims)


def track_all(
    operation: Optional[str] = None,
    latency_metric: str = "FunctionLatency",
    error_metric: str = "FunctionErrors",
    invocation_metric: str = "FunctionInvocations",
    dimensions: Optional[list[MetricDimension]] = None,
) -> Callable[[F], F]:
    """Decorator that tracks latency, errors, and invocations.

    Combines track_latency, track_errors, and count_invocations.

    Args:
        operation: Operation name for dimensions
        latency_metric: Name of latency metric
        error_metric: Name of error metric
        invocation_metric: Name of invocation metric
        dimensions: Additional dimensions to include

    Returns:
        Decorated function with full instrumentation

    Example:
        @track_all(operation="full_security_scan")
        def run_full_scan():
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            op_name = operation or func.__name__
            _record_invocation(invocation_metric, op_name, dimensions)

            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                _record_error(error_metric, op_name, type(e).__name__, dimensions)
                raise
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                _record_latency(latency_metric, duration_ms, op_name, dimensions)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            op_name = operation or func.__name__
            _record_invocation(invocation_metric, op_name, dimensions)

            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                _record_error(error_metric, op_name, type(e).__name__, dimensions)
                raise
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                _record_latency(latency_metric, duration_ms, op_name, dimensions)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)

    return decorator
