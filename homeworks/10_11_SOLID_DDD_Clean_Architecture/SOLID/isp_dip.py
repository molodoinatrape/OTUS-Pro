"""Пример ISP и DIP на сохранении заказа и уведомлении клиента.

ISP: OrderRepository задаёт только save, Notifier - только send.
ConsoleOrderRepository сохраняет заказ, EmailNotifier и SmsNotifier уведомляют.
DIP: saved_order и notify_customer работают через эти абстракции.
main выбирает реализации и передаёт их функциям извне.
Сохранение и отправка сообщений имитируются выводом в консоль.
"""
from notifications import EmailNotifier, Notifier, SmsNotifier
from repositories import ConsoleOrderRepository, OrderRepository


def saved_order(order, repository: OrderRepository):
    repository.save(order)


def notify_customer(customer, notifier: Notifier):
    notifier.send(customer)


def main():
    order = {"customer": "Alice", "total_price": 450}
    repository = ConsoleOrderRepository()
    notifier = SmsNotifier()

    saved_order(order, repository)
    notify_customer(order["customer"], notifier)


if __name__ == '__main__':
    main()
