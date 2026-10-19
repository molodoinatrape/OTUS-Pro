"""Правила скидок и их суммирование с общим лимитом 50% стоимости заказа.

Каждое правило принимает заказ, исходную сумму и сезон, возвращая размер скидки.
"""


def vip_discount(order, total_price, season):
    if order["customer_type"] == "vip":
        return total_price * 0.2
    return 0


def season_discount(order, total_price, season):
    if season == "autumn":
        return total_price * 0.1
    return 0


def keyboard_discount(order, total_price, season):
    discount = 0
    for item in order["items"]:
        if item["name"] == "Keyboard":
            discount += 100
    return discount


def calculate_discount(order, total_price, season, rules):
    discount = sum(
        rule(order, total_price, season)
        for rule in rules
    )
    return min(discount, total_price * 0.5) # Скидка не может быть >50% от заказа


if __name__ == '__main__':
    pass
