"""
TODO:

Create a new type called Vector, which is a list of float.
"""

type Vector = list[float]

def foo(v: Vector):
    pass


foo([1.1, 2])
foo(1)  # expect-type-error
foo(["1"])  # expect-type-error
