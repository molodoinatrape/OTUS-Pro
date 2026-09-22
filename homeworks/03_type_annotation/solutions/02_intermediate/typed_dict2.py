"""
TODO:

Define a class `Student` that represents a dictionary with three keys:
- name, a string
- age, an integer
- school, a string

Note: school can be optional
"""

from typing import TypedDict, NotRequired

class Student(TypedDict):
    name: str
    age: int
    school: NotRequired[str]


a: Student = {"name": "Tom", "age": 15}
a: Student = {"name": "Tom", "age": 15, "school": "Hogwarts"}
a: Student = {"name": 1, "age": 15, "school": "Hogwarts"}  # pyright: ignore[reportAssignmentType]
a: Student = {(1,): "Tom", "age": 2, "school": "Hogwarts"}  # pyright: ignore[reportAssignmentType]
a: Student = {"name": "Tom", "age": "2", "school": "Hogwarts"}  # pyright: ignore[reportAssignmentType]
a: Student = {"z": "Tom", "age": 2}  # pyright: ignore[reportAssignmentType]
assert Student(name="Tom", age=15) == dict(name="Tom", age=15)
assert Student(name="Tom", age=15, school="Hogwarts") == dict(
    name="Tom", age=15, school="Hogwarts"
)
