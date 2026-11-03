import math

from common_calc.amount import amount_counter
from common_calc.average import average_counter
from common_calc.errors import CalculationError
from common_calc.report import report
from common_calc.sorting import sorting
from common_calc.transaction import transaction

MAX_PARTICIPANTS = 100
MAX_NAME_LENGTH = 60
MAX_AMOUNT = 1_000_000_000


def _form_values(whole_dict, key):
    """Достаёт список значений из MultiDict или обычного словаря."""
    getter = getattr(whole_dict, "getlist", None)
    if callable(getter):
        values = getter(key)
    else:
        values = whole_dict.get(key, [])

    if values is None:
        return []
    if isinstance(values, str):
        return [values]
    return list(values)


def _parse_amount(raw_value, name, position):
    normalized = (
        raw_value.strip()
        .replace("\u00a0", "")
        .replace(" ", "")
        .replace(",", ".")
    )
    if not normalized:
        raise CalculationError(
            f"Укажите сумму для участника «{name}» (позиция {position}).",
            field=f"sum-{position}",
        )

    try:
        value = float(normalized)
    except ValueError:
        raise CalculationError(
            f"Сумма для участника «{name}» должна быть числом.",
            field=f"sum-{position}",
        ) from None

    if not math.isfinite(value):
        raise CalculationError(
            f"Сумма для участника «{name}» должна быть обычным числом.",
            field=f"sum-{position}",
        )
    if value < 0:
        raise CalculationError(
            f"Сумма для участника «{name}» не может быть отрицательной.",
            field=f"sum-{position}",
        )
    if value > MAX_AMOUNT:
        max_amount = f"{MAX_AMOUNT:,.0f}".replace(",", " ")
        raise CalculationError(
            f"Сумма для участника «{name}» слишком большая (максимум {max_amount} ₽).",
            field=f"sum-{position}",
        )

    return round(value, 2)


def receiver(whole_dict):
    people = []
    common_sum = []

    names_list = _form_values(whole_dict, "name")
    sum_list = _form_values(whole_dict, "sum")

    if not names_list:
        raise CalculationError("Добавьте хотя бы одного участника.")
    if len(names_list) != len(sum_list):
        raise CalculationError(
            "Количество имён и сумм не совпадает. Обновите страницу и попробуйте снова."
        )
    if len(names_list) > MAX_PARTICIPANTS:
        raise CalculationError(
            f"Слишком много участников: максимум {MAX_PARTICIPANTS}."
        )

    seen_names = set()

    for index, (raw_name, raw_sum) in enumerate(zip(names_list, sum_list)):
        position = index + 1
        name = raw_name.strip()

        if not name:
            raise CalculationError(
                f"Укажите имя участника №{position}.", field=f"name-{position}"
            )
        if len(name) > MAX_NAME_LENGTH:
            raise CalculationError(
                f"Имя участника №{position} слишком длинное "
                f"(максимум {MAX_NAME_LENGTH} символов).",
                field=f"name-{position}",
            )

        name_key = name.casefold()
        if name_key in seen_names:
            raise CalculationError(
                f"Имя «{name}» указано более одного раза.",
                field=f"name-{position}",
            )
        seen_names.add(name_key)

        people.append(name)
        common_sum.append(_parse_amount(raw_sum, name, position))

    amount = amount_counter(common_sum)
    average = average_counter(people, amount)

    plus_people, plus_sum, minus_people, minus_sum = sorting(
        people, common_sum, amount
    )

    transaction_minus, transaction_sum, transaction_plus = transaction(
        plus_people, plus_sum, minus_people, minus_sum
    )

    names, amount, average, debt, overpay, transactions = report(
        people,
        common_sum,
        amount,
        average,
        plus_people,
        plus_sum,
        minus_people,
        minus_sum,
        transaction_minus,
        transaction_sum,
        transaction_plus,
    )

    return names, amount, average, debt, overpay, transactions
