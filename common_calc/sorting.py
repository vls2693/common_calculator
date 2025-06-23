def sorting(people, common_sum, average):
    plus_people = []
    minus_people = []
    plus_sum = []
    minus_sum = []
    plus_people_rep = []
    minus_people_rep = []
    plus_sum_rep = []
    minus_sum_rep = []
    for i in range(0, len(common_sum)):
        if common_sum[i] > average:
            m = float('{:.2f}'.format(common_sum[i] - average))
            plus_sum.append(m)
            plus_people.append(people[i])
            plus_sum_rep.append(m)
            plus_people_rep.append(people[i])
        elif common_sum[i] < average:
            n = float('{:.2f}'.format(average - common_sum[i]))
            minus_sum.append(n)
            minus_people.append(people[i])
            minus_sum_rep.append(n)
            minus_people_rep.append(people[i])
        else:
            continue
    return plus_people, plus_sum, minus_people, minus_sum, plus_people_rep, \
        plus_sum_rep, minus_people_rep, minus_sum_rep
# добавить сортировку списков, добавить классы, примеры по ссылке
# https://tproger.ru/translations/python-sorting
