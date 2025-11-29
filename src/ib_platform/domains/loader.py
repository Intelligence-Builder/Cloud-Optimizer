"""Domain loader for dynamic domain discovery and loading.

This module provides functionality to load domains from Python modules
and directories, enabling dynamic domain registration.
"""

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import List, Optional

from .base import BaseDomain

logger = logging.getLogger(__name__)


class DomainLoader:
    """Loader for dynamically loading domain modules.

    This class provides functionality to load domain definitions from
    Python modules and directories, supporting both installed packages
    and development environments.
    """

    def __init__(self) -> None:
        """Initialize the domain loader."""
        self._loaded_modules: List[str] = []
        logger.info("Domain loader initialized")

    def load_from_module(self, module_path: str) -> BaseDomain:
        """Load a domain from a Python module path.

        The module must contain a domain class that inherits from BaseDomain.
        The domain class is expected to be the first BaseDomain subclass
        found in the module.

        Args:
            module_path: Python module path (e.g., 'platform.domains.security.domain')

        Returns:
            Instantiated domain object

        Raises:
            ImportError: If module cannot be imported
            ValueError: If no domain class found in module
        """
        try:
            # Import the module
            module = importlib.import_module(module_path)
            logger.info(
                f"Imported module '{module_path}'",
                extra={"module_path": module_path},
            )

            # Find domain class
            domain_class = self._find_domain_class(module)
            if not domain_class:
                raise ValueError(
                    f"No BaseDomain subclass found in module '{module_path}'"
                )

            # Instantiate and return
            domain = domain_class()
            self._loaded_modules.append(module_path)

            logger.info(
                f"Loaded domain '{domain.name}' from module '{module_path}'",
                extra={
                    "domain": domain.name,
                    "module_path": module_path,
                    "version": domain.version,
                },
            )

            return domain

        except ImportError as e:
            logger.error(
                f"Failed to import module '{module_path}': {e}",
                exc_info=True,
            )
            raise

    def load_from_directory(self, directory: Path) -> List[BaseDomain]:
        """Load all domains from a directory.

        Searches for Python modules in the directory and attempts to load
        domains from each module. Only successfully loaded domains are returned.

        Args:
            directory: Path to directory containing domain modules

        Returns:
            List of loaded domain instances

        Raises:
            ValueError: If directory does not exist
        """
        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory}")

        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        domains = []
        module_files = list(directory.glob("**/*domain.py"))

        logger.info(
            f"Scanning directory '{directory}' for domain modules",
            extra={"directory": str(directory), "files_found": len(module_files)},
        )

        for module_file in module_files:
            try:
                domain = self._load_from_file(module_file)
                if domain:
                    domains.append(domain)
            except Exception as e:
                logger.warning(
                    f"Failed to load domain from '{module_file}': {e}",
                    extra={"file": str(module_file)},
                )

        logger.info(
            f"Loaded {len(domains)} domains from directory '{directory}'",
            extra={"directory": str(directory), "domains_loaded": len(domains)},
        )

        return domains

    def reload_domain(self, domain_name: str) -> BaseDomain:
        """Reload a previously loaded domain.

        This is useful for development environments where domain definitions
        may change during runtime.

        Args:
            domain_name: Name of domain to reload

        Returns:
            Reloaded domain instance

        Raises:
            ValueError: If domain was not previously loaded
        """
        # Find the module path for this domain
        module_path = None
        for loaded_module in self._loaded_modules:
            try:
                module = importlib.import_module(loaded_module)
                domain_class = self._find_domain_class(module)
                if domain_class and domain_class().name == domain_name:
                    module_path = loaded_module
                    break
            except Exception:
                continue

        if not module_path:
            raise ValueError(
                f"Domain '{domain_name}' was not previously loaded "
                f"or cannot be found"
            )

        # Reload the module
        importlib.reload(importlib.import_module(module_path))

        # Load and return the domain
        return self.load_from_module(module_path)

    # --- Helper Methods ---

    def _find_domain_class(self, module: object) -> Optional[type]:
        """Find BaseDomain subclass in a module.

        Args:
            module: Python module object

        Returns:
            Domain class if found, None otherwise
        """
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseDomain)
                and attr is not BaseDomain
            ):
                return attr
        return None

    def _load_from_file(self, file_path: Path) -> Optional[BaseDomain]:
        """Load domain from a Python file.

        Args:
            file_path: Path to Python file

        Returns:
            Domain instance if successfully loaded, None otherwise
        """
        try:
            # Create module spec
            module_name = file_path.stem
            spec = importlib.util.spec_from_file_location(module_name, file_path)

            if not spec or not spec.loader:
                logger.warning(
                    f"Could not create module spec for '{file_path}'",
                    extra={"file": str(file_path)},
                )
                return None

            # Load module
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find and instantiate domain
            domain_class = self._find_domain_class(module)
            if not domain_class:
                return None

            domain = domain_class()
            self._loaded_modules.append(str(file_path))

            logger.info(
                f"Loaded domain '{domain.name}' from file '{file_path}'",
                extra={
                    "domain": domain.name,
                    "file": str(file_path),
                    "version": domain.version,
                },
            )

            return domain

        except Exception as e:
            logger.error(
                f"Error loading domain from '{file_path}': {e}",
                exc_info=True,
            )
            return None
