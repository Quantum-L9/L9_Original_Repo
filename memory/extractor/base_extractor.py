"""
Base Extractor Class

All extractors inherit from this base class to ensure consistent interface.
"""

from abc import ABC, abstractmethod
import logging
from pathlib import Path
from typing import Dict, Any


class BaseExtractor(ABC):
    """Base class for all extractors."""

    def __init__(self, config: Dict, logger: logging.Logger):
        """
        Initialize base extractor.

        Args:
            config: Suite configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.name = self.__class__.__name__

    @abstractmethod
    def extract(self, input_path: Path, output_root: Path) -> Dict[str, Any]:
        """
        Extract data from input file.

        Args:
            input_path: Path to input file
            output_root: Root output directory (Extracted Files/)

        Returns:
            Dict with extraction results:
            {
                'success': bool,
                'files_extracted': int,
                'output_path': str,
                'errors': List[str]
            }
        """
        pass

    def get_config(self, key: str) -> Any:
        """Get extractor-specific configuration."""
        extractor_key = self.name.lower().replace("extractor", "_extractor")
        return self.config["extractors"].get(extractor_key, {}).get(key)

    def is_enabled(self) -> bool:
        """Check if this extractor is enabled."""
        extractor_key = self.name.lower().replace("extractor", "_extractor")
        return self.config["extractors"].get(extractor_key, {}).get("enabled", False)

    def create_output_dir(self, output_root: Path, subdir: str = "") -> Path:
        """
        Create output directory for this extractor.

        Args:
            output_root: Root output directory
            subdir: Optional subdirectory name

        Returns:
            Path to output directory
        """
        if subdir:
            output_dir = output_root / subdir
        else:
            output_dir = output_root

        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
