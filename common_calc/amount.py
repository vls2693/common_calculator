def amount_counter(list_of_sum):
    amount = 0
    for i in range(0, len(list_of_sum)):
        amount = round(amount + list_of_sum[i], 2)
    return amount
