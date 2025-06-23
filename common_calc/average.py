# среднее арифметическое потраченного
def average_counter(list_of_persons, amount):
    if len(list_of_persons) == 0:
        print("Division by zero is impossible")
    else:
        average = round(amount / len(list_of_persons), 2)
        return average
