def sorting(people, common_sum, amount):
    """Делит участников на переплативших и недоплативших.

    Расчёт идёт в копейках, поэтому сумма долгов всегда точно совпадает
    с суммой переплат (без «потерянной» копейки из-за округления).
    """
    total_cents = int(round(amount * 100))
    people_count = len(people)
    base_share, extra_cent = divmod(total_cents, people_count)

    plus_people = []
    plus_sum = []
    minus_people = []
    minus_sum = []

    for index, (name, spent) in enumerate(zip(people, common_sum)):
        share = base_share + (1 if index < extra_cent else 0)
        balance = int(round(spent * 100)) - share

        if balance > 0:
            plus_people.append(name)
            plus_sum.append(balance / 100)
        elif balance < 0:
            minus_people.append(name)
            minus_sum.append(-balance / 100)

    return plus_people, plus_sum, minus_people, minus_sum
