def BMR(sex, age, height, weight):
    if sex == 'м':
        return (10 * weight + 6.25 * height - 5 * age + 5)
    else:
        return (10 * weight + 6.25 * height - 5 * age - 161)

def TDEE(bmr, level):
    if level == 1:
        return bmr * 1.2
    elif level == 2:
        return bmr * 1.375
    elif level == 3:
        return bmr * 1.55
    elif level == 4:
        return bmr * 1.725
    else:
        return bmr * 1.9


def ITOG(tdee, goal):
    if goal == 1:
        tdee = tdee
        b = 0.25 * tdee
        zh = 0.3 * tdee
        u = 0.45 * tdee
    elif goal == 2:
        tdee = tdee * 0.85
        b = 0.3 * tdee
        zh = 0.275 * tdee
        u = 0.425 * tdee
    elif goal == 3:
        tdee = tdee * 1.125
        b = 0.3 * tdee
        zh = 0.2 * tdee
        u = 0.5 * tdee
    else:
        tdee = tdee * 0.8
        b = 0.4 * tdee
        zh = 0.225 * tdee
        u = 0.375 * tdee

    return int(tdee), int(b/4), int(zh/9), int(u/4)

def get_kbzhu(sex, age, height, weight, level, goal):
    bmr = BMR(sex, age, height, weight)
    tdee = TDEE(bmr, level)
    itog = ITOG(tdee, goal)
    return itog

#print(get_kbzhu('М', 19, 185, 68, 4, 3))