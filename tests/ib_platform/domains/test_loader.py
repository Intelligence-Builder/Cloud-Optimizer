"""Tests for domain loader."""

from pathlib import Path
from platform.domains.loader import DomainLoader

import pytest


class TestDomainLoader:
    """Tests for DomainLoader."""

    def test_loader_initialization(self) -> None:
        """Test loader initialization."""
        loader = DomainLoader()
        assert loader._loaded_modules == []

    def test_load_from_module(self) -> None:
        """Test loading domain from module path."""
        loader = DomainLoader()

        # Load security domain
        domain = loader.load_from_module("platform.domains.security.domain")

        assert domain.name == "security"
        assert domain.version == "1.0.0"
        assert len(domain.entity_types) == 9
        assert len(domain.relationship_types) == 7

    def test_load_from_invalid_module(self) -> None:
        """Test loading from invalid module path."""
        loader = DomainLoader()

        with pytest.raises(ImportError):
            loader.load_from_module("invalid.module.path")

    def test_load_from_module_without_domain(self) -> None:
        """Test loading from module without domain class."""
        loader = DomainLoader()

        with pytest.raises(ValueError, match="No BaseDomain subclass found"):
            loader.load_from_module("platform.domains.base")

    def test_load_from_directory(self) -> None:
        """Test loading domains from directory."""
        loader = DomainLoader()

        # Load from security directory
        security_dir = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "platform"
            / "domains"
            / "security"
        )

        if security_dir.exists():
            domains = loader.load_from_directory(security_dir)
            assert len(domains) >= 1
            assert any(d.name == "security" for d in domains)

    def test_load_from_nonexistent_directory(self) -> None:
        """Test loading from nonexistent directory."""
        loader = DomainLoader()

        with pytest.raises(ValueError, match="does not exist"):
            loader.load_from_directory(Path("/nonexistent/path"))

    def test_load_from_file_not_directory(self) -> None:
        """Test loading from file instead of directory."""
        loader = DomainLoader()

        with pytest.raises(ValueError, match="not a directory"):
            loader.load_from_directory(Path(__file__))
