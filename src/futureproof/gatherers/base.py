"""Base class for data gatherers."""

from abc import ABC
from typing import Any


class BaseGatherer(ABC):
    """Base class for all data gatherers."""

    def gather(self, *args: Any, **kwargs: Any) -> str:
        """Gather data and return content as markdown string."""
        raise NotImplementedError
