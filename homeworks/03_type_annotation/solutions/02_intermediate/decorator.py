"""
TODO:

Define a decorator that wraps a function and returns a function with the same signature.
"""

from typing import Any, Callable, TypeVar


F = TypeVar("F", bound=Callable[..., Any])

def decorator(func: F) -> F:
    return func


@decorator
def foo(a: int, *, b: str) -> None:
    ...


@decorator
def bar(c: int, d: str) -> None:
    ...


foo(1, b="2")
bar(c=1, d="2")

foo(1, "2")  # pyright: ignore[reportCallIssue]
foo(a=1, e="2")  # pyright: ignore[reportCallIssue]
decorator(1)  # pyright: ignore[reportArgumentType]
