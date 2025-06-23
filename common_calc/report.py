def report(people, common_sum, amount, average, plus_people_rep, plus_sum_rep,
           minus_people_rep, minus_sum_rep, transaction_minus,
           transaction_sum, transaction_plus):

    names = []
    debt = []
    overpay = []
    transactions = []
    for i in range(0, len(common_sum)):
        names.append('{};{}'.format(people[i], common_sum[i]))
    for i in range(0, len(minus_people_rep)):
        debt.append('{};{}'.format(minus_people_rep[i], minus_sum_rep[i]))
    for i in range(0, len(plus_people_rep)):
        overpay.append('{};{}'.format(plus_people_rep[i], plus_sum_rep[i]))
    for i in range(0, len(transaction_minus)):
        transactions.append('{};{};{}'.format(transaction_minus[i], transaction_plus[i], transaction_sum[i]))
    return names, amount, average, debt, overpay, transactions
