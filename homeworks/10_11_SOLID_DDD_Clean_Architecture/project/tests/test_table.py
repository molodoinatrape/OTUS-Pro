import pytest

from booking.domain.model import PartySize, Table, TableId


@pytest.mark.parametrize("capacity", [0, -1])
def test_table_rejects_nonpositive_capacity(capacity):
    with pytest.raises(ValueError):
        Table(table_id=TableId("T1"), capacity=capacity)


@pytest.mark.parametrize(
    "guests, expected",
    [(3, True), (4, True), (5, False)],
    ids=["spare-seats", "exact-fit", "too-many-guests"],
)
def test_table_checks_capacity(guests, expected):
    table = Table(table_id=TableId("T1"), capacity=4)

    # Ровно четыре гостя допустимы: граница сравнения включительная.
    assert table.can_fit(PartySize(guests)) is expected


@pytest.mark.parametrize(
    "attribute, replacement",
    [("id", TableId("T2")), ("capacity", 6)],
)
def test_table_public_properties_reject_assignment(attribute, replacement):
    table = Table(table_id=TableId("T1"), capacity=4)

    # setattr позволяет проверить одинаковый запрет присваивания для двух свойств.
    with pytest.raises(AttributeError):
        setattr(table, attribute, replacement)

    assert table.id == TableId("T1")
    assert table.capacity == 4
