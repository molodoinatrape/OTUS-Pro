"""
TODO:

`foo` takes keyword arguments of type integer or string.
"""


def foo(**kwargs: int | str):
    pass

foo(a=1, b=2)
foo(a=[1])  # TyperError