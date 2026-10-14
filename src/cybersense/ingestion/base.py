"""BaseLoader — abstract contract every data-source loader must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from cybersense.models import Document


class BaseLoader(ABC):
    """Every source loader inherits this and implements `load()`."""

    source_name: str = ""

    @abstractmethod
    def load(self, **kwargs) -> Iterator[Document]:
        """Yield normalized Document objects from the source.

        Keyword args vary per loader (e.g. `since`, `limit`).
        Implementations must:
        - Be idempotent (safe to call multiple times).
        - Respect rate limits and robots.txt.
        - Catch and log errors per record; never raise from inside the loop
          unless the whole source is unreachable.
        """
        ...
