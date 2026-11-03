def report(people, common_sum, amount, average, plus_people, plus_sum,
           minus_people, minus_sum, transaction_minus, transaction_sum,
           transaction_plus):
    """Собирает данные для шаблона в виде списков словарей."""
    participants = [
        {"name": name, "amount": spent}
        for name, spent in zip(people, common_sum)
    ]
    debts = [
        {"name": name, "amount": debt}
        for name, debt in zip(minus_people, minus_sum)
    ]
    overpays = [
        {"name": name, "amount": overpay}
        for name, overpay in zip(plus_people, plus_sum)
    ]
    transactions = [
        {"from": debtor, "to": receiver, "amount": value}
        for debtor, receiver, value in zip(
            transaction_minus, transaction_plus, transaction_sum
        )
    ]
    return participants, amount, average, debts, overpays, transactions
