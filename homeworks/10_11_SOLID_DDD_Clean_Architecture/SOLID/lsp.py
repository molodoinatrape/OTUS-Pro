"""LSP: подклассы должны сохранять контракт базового класса.

VipDiscount, NoDiscount и FixedDiscount возвращают скидку от нуля
до исходной неотрицательной конечной суммы. WrongDiscount оставлен
как антипример: при сумме меньше 100 итоговая цена отрицательна.
main сравнивает реализации через общую функцию calculate_final_price.
"""


class Discount:
    def calculate(self, total_price: float) -> float:
        """Вернуть размер скидки.

        :param total_price: Неотрицательное конечное число
        :return: Число от 0 до total_price
        """
        raise NotImplementedError


class VipDiscount(Discount):
    def calculate(self, total_price: float) -> float:
        return total_price * 0.2


class NoDiscount(Discount):
    def calculate(self, total_price: float) -> float:
        return 0


class WrongDiscount(Discount):
    """Вернуть 100, нарушая контракт при стоимости заказа меньше 100."""
    def calculate(self, total_price: float) -> float:
        return 100


class FixedDiscount(Discount):
    """Вернуть скидку 100, ограниченную стоимостью заказа."""
    def calculate(self, total_price: float) -> float:
        return min(total_price, 100)


def calculate_final_price(total_price, discount: Discount) -> float:
    return total_price - discount.calculate(total_price)


def main():
    discounts = [VipDiscount(), NoDiscount(), WrongDiscount(), FixedDiscount()]

    for discount in discounts:
        for total_price in [0, 50, 450]:
            final_price = calculate_final_price(total_price, discount)
            print(type(discount).__name__, total_price, final_price)


if __name__ == "__main__":
    main()
