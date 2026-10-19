"""Консольная имитация сохранения заказа без настоящего хранилища.

Предоставляет функцию save_order и интерфейс OrderRepository
с реализацией ConsoleOrderRepository.
"""


class OrderRepository:
    def save(self, order):
        raise NotImplementedError


class ConsoleOrderRepository(OrderRepository):
    def save(self, order):
        print(f"Заказ клиента {order['customer']} сохранён.")


def save_order(order, final_price):
    print(
        f"Заказ клиента {order['customer']} сохранён. "
        f"Итоговая сумма: {final_price:.2f} рублей"
    )


if __name__ == '__main__':
    pass
