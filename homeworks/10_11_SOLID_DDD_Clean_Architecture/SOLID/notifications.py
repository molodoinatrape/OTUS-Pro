"""Консольная имитация уведомлений: функция и реализации интерфейса Notifier.

EmailNotifier и SmsNotifier предоставляют общий метод send(customer).
Настоящие письма и SMS не отправляются.
"""


def send_notification(customer):
    print(f"{customer}, ваш заказ готов к получению!")


class Notifier:
    def send(self, customer):
        raise NotImplementedError


class EmailNotifier(Notifier):
    def send(self, customer):
        print(f"EMAIL для {customer}: ваш заказ отправлен.")


class SmsNotifier(Notifier):
    def send(self, customer):
        print(f"SMS для {customer}: ваш заказ отправлен.")


if __name__ == '__main__':
    pass
