from common_calc.errors import CalculationError


# среднее арифметическое потраченного
def average_counter(list_of_persons, amount):
    if not list_of_persons:
        raise CalculationError("Добавьте хотя бы одного участника.")
    return round(amount / len(list_of_persons), 2)
