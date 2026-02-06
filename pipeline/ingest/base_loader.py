from abc import ABC, abstractmethod
from pipeline.models import NormalizedLabTest


class BaseLoader(ABC):
    """Abstract base class for lab-specific CSV loaders."""

    @abstractmethod
    def load(self, csv_path: str) -> list[NormalizedLabTest]:
        """Read CSV, normalize all fields, return list of NormalizedLabTest."""
        ...

    @abstractmethod
    def get_lab_slug(self) -> str:
        ...
