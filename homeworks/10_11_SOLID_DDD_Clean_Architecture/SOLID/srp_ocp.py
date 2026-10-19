"""Пример SRP и OCP на обработке заказа с подключаемыми правилами скидок.

Расчёт, сохранение и уведомление разделены по функциям.
main выбирает правила; общий расчёт ограничивает скидку 50% стоимости.
Сохранение и уведомление имитируются выводом в консоль.
"""
from discounts import (
    calculate_discount,
    keyboard_discount,
    season_discount,
    vip_discount,
)
from notifications import send_notification
from repositories import save_order


# TODO 1.
# Реализуйте расчёт полной стоимости товаров в заказе.
def calculate_total_price(items):
    total_price = 0
    for item in items:
        total_price += item["price"]

    return total_price


# TODO 2.
# Добавьте применение скидки для VIP-клиента.
# Размер скидки выберите самостоятельно.
# Реализовано в discounts.py: правила скидок и общий лимит 50% стоимости.


# TODO 3.
# Реализуйте "сохранение" заказа.
# Настоящее хранилище не требуется — достаточно вывести сообщение в консоль.
# Реализовано в repositories.py: save_order выводит заказ и итоговую сумму.


# TODO 4.
# Реализуйте "отправку уведомления" клиенту.
# Настоящая отправка не требуется — достаточно вывести сообщение в консоль.
# Реализовано в notifications.py: send_notification выводит сообщение клиенту.


# TODO 5.
# Организуйте процесс обработки заказа:
#   1) рассчитать стоимость;
#   2) применить скидку;
#   3) сохранить заказ;
#   4) уведомить клиента.
def process_order(order, season, rules):
    total_price = calculate_total_price(order["items"])
    discount = calculate_discount(order, total_price, season, rules)
    final_price = total_price - discount

    save_order(order, final_price)
    send_notification(order["customer"])

    print(f"Стоимость заказа {final_price:.2f} рублей.")


# TODO 6. Рефакторинг
# Посмотрите на получившееся решение и разделите разные ответственности
# между функциями и/или классами.
#
# Подумайте:
#   - какие абстракции здесь нужны;
#   - как добиться высокой cohesion;
#   - как уменьшить coupling;
#   - какие принципы SOLID применимы к вашему решению.

# Реализовано: обязанности разделены по модулям, правила передаются списком.
# SRP: расчёт, скидки, сохранение и уведомление разделены по функциям.
# OCP: новое правило скидки добавляется отдельной функцией в список rules.
# calculate_discount и process_order при этом не меняются.


def main():
    """Точка входа в программу."""
    # TODO: запустите обработку заказа здесь.
    # Исходные данные — их можно использовать для проверки решения.
    order = {
        "customer": "Alice",
        "customer_type": "vip",
        "items": [
            {"name": "Keyboard", "price": 100},
            {"name": "Mouse", "price": 50},
            {"name": "Monitor", "price": 300},
        ],
    }
    rules = [
        vip_discount,
        season_discount,
        keyboard_discount,
    ]
    season = "autumn"

    process_order(order, season, rules)


if __name__ == "__main__":
    main()
