"""YAML data loader for Knowledge Base content.

This module handles loading and parsing YAML files containing compliance controls,
service best practices, security patterns, and remediation templates.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml  # type: ignore[import-untyped]

from ib_platform.kb.models import (
    ComplianceControl,
    RemediationTemplate,
    SecurityPattern,
    ServiceBestPractice,
)

logger = logging.getLogger(__name__)


class KBLoader:
    """Knowledge Base YAML data loader.

    Loads structured data from YAML files in the data/compliance directory.

    Args:
        data_dir: Path to the data directory (defaults to data/compliance)

    Example:
        >>> loader = KBLoader()
        >>> controls = loader.load_frameworks()
        >>> practices = loader.load_services()
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        """Initialize the loader with a data directory.

        Args:
            data_dir: Path to data directory, defaults to data/compliance
        """
        if data_dir is None:
            # Default to project root / data / compliance
            # Assumes loader is in src/ib_platform/kb/
            project_root = Path(__file__).parent.parent.parent.parent
            data_dir = project_root / "data" / "compliance"

        self.data_dir = Path(data_dir)
        logger.info(f"KB Loader initialized with data_dir: {self.data_dir}")

    def load_frameworks(self) -> Dict[str, List[ComplianceControl]]:
        """Load compliance framework controls from YAML files.

        Looks for files matching: data/compliance/frameworks/*/controls.yaml

        Returns:
            Dictionary mapping framework names to lists of ComplianceControl objects

        Example:
            >>> controls = loader.load_frameworks()
            >>> cis_controls = controls.get("CIS", [])
        """
        frameworks: Dict[str, List[ComplianceControl]] = {}
        frameworks_dir = self.data_dir / "frameworks"

        if not frameworks_dir.exists():
            logger.warning(f"Frameworks directory not found: {frameworks_dir}")
            return frameworks

        # Look for framework directories
        for framework_dir in frameworks_dir.iterdir():
            if not framework_dir.is_dir():
                continue

            controls_file = framework_dir / "controls.yaml"
            if not controls_file.exists():
                logger.debug(f"No controls.yaml in {framework_dir.name}")
                continue

            try:
                with open(controls_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if not data or "controls" not in data:
                    logger.warning(f"Invalid format in {controls_file}")
                    continue

                framework_name = data.get("framework", framework_dir.name.upper())
                controls = []

                for control_data in data["controls"]:
                    control = ComplianceControl(
                        framework=framework_name,
                        control_id=control_data.get("control_id", ""),
                        name=control_data.get("name", ""),
                        description=control_data.get("description", ""),
                        requirements=control_data.get("requirements", []),
                        aws_services=control_data.get("aws_services", []),
                        implementation_guidance=control_data.get(
                            "implementation_guidance", ""
                        ),
                    )
                    controls.append(control)

                frameworks[framework_name] = controls
                logger.info(
                    f"Loaded {len(controls)} controls for framework {framework_name}"
                )

            except Exception as e:
                logger.error(f"Error loading {controls_file}: {e}")
                continue

        return frameworks

    def load_services(self) -> Dict[str, List[ServiceBestPractice]]:
        """Load AWS service best practices from YAML files.

        Looks for files matching: data/compliance/services/*.yaml

        Returns:
            Dictionary mapping service names to lists of ServiceBestPractice objects

        Example:
            >>> practices = loader.load_services()
            >>> s3_practices = practices.get("S3", [])
        """
        services: Dict[str, List[ServiceBestPractice]] = {}
        services_dir = self.data_dir / "services"

        if not services_dir.exists():
            logger.warning(f"Services directory not found: {services_dir}")
            return services

        # Look for service YAML files
        for service_file in services_dir.glob("*.yaml"):
            try:
                with open(service_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if not data or "practices" not in data:
                    logger.warning(f"Invalid format in {service_file}")
                    continue

                service_name = data.get("service", service_file.stem.upper())
                practices = []

                for practice_data in data["practices"]:
                    practice = ServiceBestPractice(
                        service=service_name,
                        category=practice_data.get("category", ""),
                        title=practice_data.get("title", ""),
                        description=practice_data.get("description", ""),
                        compliance_frameworks=practice_data.get(
                            "compliance_frameworks", []
                        ),
                        implementation=practice_data.get("implementation", ""),
                        terraform_example=practice_data.get("terraform_example", ""),
                        cli_example=practice_data.get("cli_example", ""),
                        console_steps=practice_data.get("console_steps", []),
                    )
                    practices.append(practice)

                services[service_name] = practices
                logger.info(
                    f"Loaded {len(practices)} best practices for service {service_name}"
                )

            except Exception as e:
                logger.error(f"Error loading {service_file}: {e}")
                continue

        return services

    def load_patterns(self) -> List[SecurityPattern]:
        """Load security patterns from YAML files.

        Looks for files matching: data/compliance/patterns/*.yaml

        Returns:
            List of SecurityPattern objects

        Example:
            >>> patterns = loader.load_patterns()
            >>> encryption_patterns = [p for p in patterns if p.category == "encryption"]
        """
        patterns: List[SecurityPattern] = []
        patterns_dir = self.data_dir / "patterns"

        if not patterns_dir.exists():
            logger.warning(f"Patterns directory not found: {patterns_dir}")
            return patterns

        # Look for pattern YAML files
        for pattern_file in patterns_dir.glob("*.yaml"):
            try:
                with open(pattern_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if not data or "patterns" not in data:
                    logger.warning(f"Invalid format in {pattern_file}")
                    continue

                for pattern_data in data["patterns"]:
                    pattern = SecurityPattern(
                        pattern_id=pattern_data.get("pattern_id", ""),
                        name=pattern_data.get("name", ""),
                        category=pattern_data.get("category", ""),
                        description=pattern_data.get("description", ""),
                        applicable_services=pattern_data.get("applicable_services", []),
                        compliance_frameworks=pattern_data.get(
                            "compliance_frameworks", []
                        ),
                        implementation_steps=pattern_data.get(
                            "implementation_steps", []
                        ),
                        code_examples=pattern_data.get("code_examples", {}),
                    )
                    patterns.append(pattern)

                logger.info(
                    f"Loaded {len(data['patterns'])} patterns from {pattern_file.name}"
                )

            except Exception as e:
                logger.error(f"Error loading {pattern_file}: {e}")
                continue

        return patterns

    def load_remediation(self) -> Dict[str, RemediationTemplate]:
        """Load remediation templates from YAML files.

        Looks for: data/compliance/remediation/index.yaml

        Returns:
            Dictionary mapping rule IDs to RemediationTemplate objects

        Example:
            >>> templates = loader.load_remediation()
            >>> template = templates.get("s3-bucket-public-read-prohibited")
        """
        templates: Dict[str, RemediationTemplate] = {}
        remediation_file = self.data_dir / "remediation" / "index.yaml"

        if not remediation_file.exists():
            logger.warning(f"Remediation file not found: {remediation_file}")
            return templates

        try:
            with open(remediation_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data or "templates" not in data:
                logger.warning(f"Invalid format in {remediation_file}")
                return templates

            for template_data in data["templates"]:
                template = RemediationTemplate(
                    template_id=template_data.get("template_id", ""),
                    rule_id=template_data.get("rule_id", ""),
                    title=template_data.get("title", ""),
                    description=template_data.get("description", ""),
                    terraform=template_data.get("terraform", ""),
                    cli=template_data.get("cli", ""),
                    console_steps=template_data.get("console_steps", []),
                )
                templates[template.rule_id] = template

            logger.info(f"Loaded {len(templates)} remediation templates")

        except Exception as e:
            logger.error(f"Error loading {remediation_file}: {e}")

        return templates
