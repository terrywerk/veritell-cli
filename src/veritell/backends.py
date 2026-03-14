"""Backend contracts for the Veritell CLI scaffold."""

from __future__ import annotations

from typing import Protocol

from .testcase import TestCase


class Backend(Protocol):
    """Minimal execution backend interface."""

    def run(self, testcase: TestCase) -> str:
        """Execute a test case and return the backend output."""

