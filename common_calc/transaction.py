def transaction(plus_people, plus_sum, minus_people, minus_sum):
    plus_people = plus_people
    plus_sum = plus_sum
    minus_people = minus_people
    minus_sum = minus_sum
    transaction_minus = []
    transaction_sum = []
    transaction_plus = []
    for i in range(0, len(minus_sum)):
        for k in range(0, len(plus_sum)):
            if plus_sum[k] <= 0:
                continue
            elif minus_sum[i] <= 0:
                continue
            else:
                if minus_sum[i] < plus_sum[k]:
                    transaction_minus.append(minus_people[i])
                    transaction_sum.append(minus_sum[i])
                    transaction_plus.append(plus_people[k])
                    plus_sum[k] = float('{:.2f}'.format(plus_sum[k] - minus_sum[i]))
                    minus_sum[i] = 0
                elif minus_sum[i] >= plus_sum[k]:
                    transaction_minus.append(minus_people[i])
                    transaction_sum.append(plus_sum[k])
                    transaction_plus.append(plus_people[k])
                    minus_sum[i] = minus_sum[i] - plus_sum[k]
                    plus_sum[k] = 0

    return transaction_minus, transaction_sum, transaction_plus
