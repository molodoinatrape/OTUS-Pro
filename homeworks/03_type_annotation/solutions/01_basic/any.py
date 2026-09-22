"""
TODO:

Modify `foo` so it takes an argument of arbitrary type.
"""

from typing import Any


def foo(x: Any):
    pass

foo(1)
foo("10")
foo(1, 2)  # pyright: ignore[reportCallIssue]
