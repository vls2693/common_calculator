def transaction(plus_people, plus_sum, minus_people, minus_sum):
    """Подбирает минимальный набор переводов от должников к переплатившим."""
    # Работаем в копейках и на копиях, чтобы не менять исходные списки
    # и не накапливать ошибку округления float.
    plus_left = [int(round(value * 100)) for value in plus_sum]
    minus_left = [int(round(value * 100)) for value in minus_sum]

    transaction_minus = []
    transaction_sum = []
    transaction_plus = []

    for debtor_index, debt in enumerate(minus_left):
        for receiver_index, overpay in enumerate(plus_left):
            if debt <= 0:
                break
            if overpay <= 0:
                continue

            amount = min(debt, overpay)
            transaction_minus.append(minus_people[debtor_index])
            transaction_plus.append(plus_people[receiver_index])
            transaction_sum.append(amount / 100)

            minus_left[debtor_index] -= amount
            plus_left[receiver_index] -= amount
            debt -= amount

    return transaction_minus, transaction_sum, transaction_plus
