"""Tests for pattern registry."""

from uuid import uuid4

import pytest

from ib_platform.patterns.models import (
    PatternCategory,
    PatternDefinition,
)
from ib_platform.patterns.registry import PatternRegistry


class TestPatternRegistry:
    """Tests for PatternRegistry class."""

    def test_register_pattern(
        self, pattern_registry: PatternRegistry, sample_cve_pattern: PatternDefinition
    ) -> None:
        """Test registering a pattern."""
        pattern_registry.register(sample_cve_pattern)

        assert pattern_registry.count() == 1
        retrieved = pattern_registry.get(sample_cve_pattern.id)
        assert retrieved is not None
        assert retrieved.name == sample_cve_pattern.name

    def test_register_duplicate_raises_error(
        self, pattern_registry: PatternRegistry, sample_cve_pattern: PatternDefinition
    ) -> None:
        """Test that registering duplicate pattern raises error."""
        pattern_registry.register(sample_cve_pattern)

        with pytest.raises(ValueError, match="already registered"):
            pattern_registry.register(sample_cve_pattern)

    def test_unregister_pattern(
        self, pattern_registry: PatternRegistry, sample_cve_pattern: PatternDefinition
    ) -> None:
        """Test unregistering a pattern."""
        pattern_registry.register(sample_cve_pattern)
        assert pattern_registry.count() == 1

        pattern_registry.unregister(sample_cve_pattern.id)
        assert pattern_registry.count() == 0

    def test_unregister_nonexistent_raises_error(
        self, pattern_registry: PatternRegistry
    ) -> None:
        """Test that unregistering non-existent pattern raises error."""
        with pytest.raises(KeyError, match="not found"):
            pattern_registry.unregister(uuid4())

    def test_get_pattern(
        self, pattern_registry: PatternRegistry, sample_cve_pattern: PatternDefinition
    ) -> None:
        """Test retrieving a pattern by ID."""
        pattern_registry.register(sample_cve_pattern)

        retrieved = pattern_registry.get(sample_cve_pattern.id)
        assert retrieved is not None
        assert retrieved.id == sample_cve_pattern.id

    def test_get_nonexistent_returns_none(
        self, pattern_registry: PatternRegistry
    ) -> None:
        """Test that getting non-existent pattern returns None."""
        result = pattern_registry.get(uuid4())
        assert result is None

    def test_get_by_domain(
        self, populated_registry: PatternRegistry
    ) -> None:
        """Test retrieving patterns by domain."""
        patterns = populated_registry.get_by_domain("security")

        assert len(patterns) == 2
        assert all(p.domain == "security" for p in patterns)

    def test_get_by_domain_with_category_filter(
        self, populated_registry: PatternRegistry
    ) -> None:
        """Test retrieving patterns by domain and category."""
        patterns = populated_registry.get_by_domain(
            "security", category=PatternCategory.ENTITY
        )

        assert all(p.category == PatternCategory.ENTITY for p in patterns)

    def test_get_by_category(
        self, populated_registry: PatternRegistry
    ) -> None:
        """Test retrieving patterns by category."""
        patterns = populated_registry.get_by_category(PatternCategory.ENTITY)

        assert len(patterns) == 2
        assert all(p.category == PatternCategory.ENTITY for p in patterns)

    def test_list_all(
        self, populated_registry: PatternRegistry
    ) -> None:
        """Test listing all patterns."""
        all_patterns = populated_registry.list_all()

        assert len(all_patterns) == 2

    def test_count(
        self, pattern_registry: PatternRegistry, sample_cve_pattern: PatternDefinition
    ) -> None:
        """Test counting registered patterns."""
        assert pattern_registry.count() == 0

        pattern_registry.register(sample_cve_pattern)
        assert pattern_registry.count() == 1

    def test_clear(
        self, populated_registry: PatternRegistry
    ) -> None:
        """Test clearing all patterns."""
        assert populated_registry.count() == 2

        populated_registry.clear()
        assert populated_registry.count() == 0

    def test_thread_safety(
        self, pattern_registry: PatternRegistry, sample_cve_pattern: PatternDefinition
    ) -> None:
        """Test that registry operations are thread-safe."""
        import threading

        def register_and_count() -> None:
            try:
                pattern_registry.register(sample_cve_pattern)
            except ValueError:
                pass  # Already registered in another thread
            pattern_registry.count()

        threads = [threading.Thread(target=register_and_count) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should have exactly 1 pattern (only first thread succeeds)
        assert pattern_registry.count() == 1
