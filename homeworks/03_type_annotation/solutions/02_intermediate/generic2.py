"""
TODO:

The function `add` accepts two arguments and returns a value, they all have the same type.
The type can only be str or int.
"""

from typing import TypeVar

T = TypeVar("T", str, int)

def add(a: T, b: T) -> T:
    raise NotImplementedError


from typing import assert_type

assert_type(add(1, 2), int)
assert_type(add("1", "2"), str)

add(["1"], ["2"])  # pyright: ignore[reportArgumentType]
add("1", 2)  # pyright: ignore[reportArgumentType]
