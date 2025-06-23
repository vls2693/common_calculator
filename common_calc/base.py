from common_calc.amount import amount_counter
from common_calc.average import average_counter
from common_calc.sorting import sorting
from common_calc.report import report
from common_calc.transaction import transaction


def receiver(whole_dict):
    people = []
    common_sum = []

    for i in range(0, int(len(whole_dict.getlist('name')))):
        people.append(whole_dict.getlist('name')[i])
        common_sum.append(int(whole_dict.getlist('sum')[i]))

    amount = amount_counter(common_sum)
    average = average_counter(common_sum, amount)

    plus_people, plus_sum, minus_people, minus_sum, plus_people_rep, \
        plus_sum_rep, minus_people_rep, minus_sum_rep = \
        sorting(people, common_sum, average)

    transaction_minus, transaction_sum, transaction_plus = transaction(
        plus_people, plus_sum, minus_people, minus_sum)

    names, amount, average, debt, overpay, transactions = report(people, common_sum, amount, average, plus_people_rep,
                                                                 plus_sum_rep, minus_people_rep, minus_sum_rep,
                                                                 transaction_minus, transaction_sum, transaction_plus)

    return names, amount, average, debt, overpay, transactions
