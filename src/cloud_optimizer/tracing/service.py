"""AWS X-Ray Tracing Service for Cloud Optimizer.

Issue #167: Distributed tracing with X-Ray.
Provides X-Ray SDK integration with graceful degradation when SDK unavailable.
"""

import threading
from contextlib import contextmanager
from typing import Any, Generator, Optional

from cloud_optimizer.config import get_settings
from cloud_optimizer.logging.config import get_logger
from cloud_optimizer.tracing.config import TracingConfig

logger = get_logger(__name__)

# Try to import X-Ray SDK
try:
    from aws_xray_sdk.core import xray_recorder
    from aws_xray_sdk.core import patch_all, patch
    from aws_xray_sdk.core.models.segment import Segment
    from aws_xray_sdk.core.models.subsegment import Subsegment

    XRAY_SDK_AVAILABLE = True
except ImportError:
    XRAY_SDK_AVAILABLE = False
    xray_recorder = None
    Segment = None
    Subsegment = None


class TracingService:
    """AWS X-Ray tracing service with graceful degradation.

    Features:
    - X-Ray segment and subsegment management
    - Automatic patching of boto3, httpx, etc.
    - Graceful degradation when SDK not installed
    - Thread-safe operation
    - Integration with existing correlation ID infrastructure
    """

    def __init__(self, config: Optional[TracingConfig] = None) -> None:
        """Initialize tracing service.

        Args:
            config: Optional TracingConfig. Uses defaults if not provided.
        """
        self.config = config or TracingConfig()
        self._initialized = False
        self._lock = threading.Lock()

        if self.config.enabled and XRAY_SDK_AVAILABLE:
            self._initialize()
        elif self.config.enabled and not XRAY_SDK_AVAILABLE:
            logger.warning(
                "xray_sdk_not_available",
                message="aws-xray-sdk not installed. Tracing disabled.",
            )

    def _initialize(self) -> None:
        """Initialize X-Ray recorder and patch libraries."""
        if not XRAY_SDK_AVAILABLE:
            return

        try:
            # Configure X-Ray recorder
            xray_recorder.configure(
                service=self.config.service_name,
                daemon_address=self.config.daemon_address,
                context_missing=self.config.context_missing,
                streaming_threshold=10,  # Flush every 10 subsegments
            )

            # Patch supported libraries
            # Only patch libraries that are installed
            libraries_to_patch = []

            try:
                import boto3
                libraries_to_patch.append("boto3")
            except ImportError:
                pass

            try:
                import botocore
                libraries_to_patch.append("botocore")
            except ImportError:
                pass

            try:
                import httpx
                libraries_to_patch.append("httpx")
            except ImportError:
                pass

            try:
                import requests
                libraries_to_patch.append("requests")
            except ImportError:
                pass

            try:
                import aiobotocore
                libraries_to_patch.append("aiobotocore")
            except ImportError:
                pass

            if libraries_to_patch:
                patch(libraries_to_patch)
                logger.info(
                    "xray_libraries_patched",
                    libraries=libraries_to_patch,
                )

            self._initialized = True
            logger.info(
                "xray_tracing_initialized",
                service=self.config.service_name,
                daemon_address=self.config.daemon_address,
            )

        except Exception as e:
            logger.error("xray_initialization_failed", error=str(e))
            self._initialized = False

    @property
    def enabled(self) -> bool:
        """Check if tracing is enabled and initialized."""
        return self.config.enabled and self._initialized and XRAY_SDK_AVAILABLE

    def begin_segment(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        sampling: Optional[bool] = None,
    ) -> Optional[Any]:
        """Begin a new X-Ray segment.

        Args:
            name: Segment name
            trace_id: Optional trace ID to continue existing trace
            parent_id: Optional parent segment ID
            sampling: Optional sampling decision

        Returns:
            Segment object or None if tracing disabled
        """
        if not self.enabled:
            return None

        try:
            segment = xray_recorder.begin_segment(
                name=name,
                traceid=trace_id,
                parent_id=parent_id,
                sampling=sampling,
            )

            # Add default annotations
            for key, value in self.config.default_annotations.items():
                segment.put_annotation(key, value)

            # Add default metadata
            for namespace, data in self.config.default_metadata.items():
                for key, value in data.items():
                    segment.put_metadata(key, value, namespace)

            return segment

        except Exception as e:
            logger.debug("xray_begin_segment_failed", error=str(e))
            return None

    def end_segment(self) -> None:
        """End the current X-Ray segment."""
        if not self.enabled:
            return

        try:
            xray_recorder.end_segment()
        except Exception as e:
            logger.debug("xray_end_segment_failed", error=str(e))

    @contextmanager
    def segment(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> Generator[Optional[Any], None, None]:
        """Context manager for X-Ray segments.

        Args:
            name: Segment name
            trace_id: Optional trace ID
            parent_id: Optional parent ID

        Yields:
            Segment object or None
        """
        segment = self.begin_segment(name, trace_id, parent_id)
        try:
            yield segment
        except Exception as e:
            if segment:
                self.add_exception(e)
            raise
        finally:
            self.end_segment()

    def begin_subsegment(
        self,
        name: str,
        namespace: str = "local",
    ) -> Optional[Any]:
        """Begin a new X-Ray subsegment.

        Args:
            name: Subsegment name
            namespace: Namespace (local, remote, aws)

        Returns:
            Subsegment object or None if tracing disabled
        """
        if not self.enabled:
            return None

        try:
            return xray_recorder.begin_subsegment(name, namespace=namespace)
        except Exception as e:
            logger.debug("xray_begin_subsegment_failed", error=str(e))
            return None

    def end_subsegment(self) -> None:
        """End the current X-Ray subsegment."""
        if not self.enabled:
            return

        try:
            xray_recorder.end_subsegment()
        except Exception as e:
            logger.debug("xray_end_subsegment_failed", error=str(e))

    @contextmanager
    def subsegment(
        self,
        name: str,
        namespace: str = "local",
    ) -> Generator[Optional[Any], None, None]:
        """Context manager for X-Ray subsegments.

        Args:
            name: Subsegment name
            namespace: Namespace (local, remote, aws)

        Yields:
            Subsegment object or None
        """
        subseg = self.begin_subsegment(name, namespace)
        try:
            yield subseg
        except Exception as e:
            if subseg:
                self.add_exception(e, subseg)
            raise
        finally:
            self.end_subsegment()

    def add_annotation(
        self,
        key: str,
        value: Any,
        segment: Optional[Any] = None,
    ) -> None:
        """Add annotation to current or specified segment.

        Annotations are indexed and searchable in X-Ray console.

        Args:
            key: Annotation key
            value: Annotation value (string, number, or boolean)
            segment: Optional segment to annotate
        """
        if not self.enabled:
            return

        try:
            if segment:
                segment.put_annotation(key, value)
            else:
                current = xray_recorder.current_segment()
                if current:
                    current.put_annotation(key, value)
        except Exception as e:
            logger.debug("xray_add_annotation_failed", error=str(e))

    def add_metadata(
        self,
        key: str,
        value: Any,
        namespace: str = "default",
        segment: Optional[Any] = None,
    ) -> None:
        """Add metadata to current or specified segment.

        Metadata is not indexed but can store arbitrary data.

        Args:
            key: Metadata key
            value: Metadata value (any JSON-serializable object)
            namespace: Metadata namespace
            segment: Optional segment to add metadata to
        """
        if not self.enabled:
            return

        try:
            if segment:
                segment.put_metadata(key, value, namespace)
            else:
                current = xray_recorder.current_segment()
                if current:
                    current.put_metadata(key, value, namespace)
        except Exception as e:
            logger.debug("xray_add_metadata_failed", error=str(e))

    def add_exception(
        self,
        exception: Exception,
        segment: Optional[Any] = None,
    ) -> None:
        """Add exception to current or specified segment.

        Args:
            exception: Exception to record
            segment: Optional segment to add exception to
        """
        if not self.enabled:
            return

        try:
            if segment:
                segment.add_exception(exception, stack=True)
            else:
                current = xray_recorder.current_subsegment()
                if current:
                    current.add_exception(exception, stack=True)
                else:
                    current = xray_recorder.current_segment()
                    if current:
                        current.add_exception(exception, stack=True)
        except Exception as e:
            logger.debug("xray_add_exception_failed", error=str(e))

    def get_trace_header(self) -> Optional[str]:
        """Get the current X-Ray trace header for propagation.

        Returns:
            X-Ray trace header string or None
        """
        if not self.enabled:
            return None

        try:
            segment = xray_recorder.current_segment()
            if segment:
                return f"Root={segment.trace_id};Parent={segment.id};Sampled={1 if segment.sampled else 0}"
            return None
        except Exception:
            return None

    def is_sampled(self) -> bool:
        """Check if current trace is sampled.

        Returns:
            True if current trace is sampled
        """
        if not self.enabled:
            return False

        try:
            segment = xray_recorder.current_segment()
            return segment.sampled if segment else False
        except Exception:
            return False


# Singleton instance management
_tracing_service: Optional[TracingService] = None
_service_lock = threading.Lock()


def get_tracing_service() -> TracingService:
    """Get or create the global tracing service instance.

    Returns:
        Configured TracingService instance
    """
    global _tracing_service

    if _tracing_service is None:
        with _service_lock:
            if _tracing_service is None:
                settings = get_settings()
                config = TracingConfig(
                    enabled=True,
                    service_name="cloud-optimizer",
                )
                _tracing_service = TracingService(config)

    return _tracing_service


def reset_tracing_service() -> None:
    """Reset the global tracing service (for testing)."""
    global _tracing_service
    with _service_lock:
        _tracing_service = None
