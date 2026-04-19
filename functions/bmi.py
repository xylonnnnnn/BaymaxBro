def BMI(height, weight):
    height_m = height / 100
    bmi = weight / (height_m ** 2)  # формула ИМТ
    if bmi <= 16:
        grade = '<i>Выраженный дефицит массы тела</i>'
        norm_bmi = 18.5
        norm_weight = norm_bmi * (height_m ** 2)
        norm_weight = norm_weight - weight
    elif 16 < bmi < 18.5:
        grade = '<i>Недостаточная (дефицит) масса тела</i>'
        norm_bmi = 18.5
        norm_weight = norm_bmi * (height_m ** 2)
        norm_weight = norm_weight - weight
    elif 18.5 <= bmi <= 25:
        grade = 'Норма'
        norm_weight = 0
    elif 25 < bmi <= 30:
        grade = '<i>Избыточная масса тела (предожирение)</i>'
        norm_bmi = 25
        norm_weight = norm_bmi * (height_m ** 2)
        norm_weight = norm_weight - weight
    elif 30 < bmi <= 35:
        grade = '<i>Ожирение первой степени</i>'
        norm_bmi = 25
        norm_weight = norm_bmi * (height_m ** 2)
        norm_weight = norm_weight - weight
    elif 35 < bmi <= 40:
        grade = '<i>Ожирение второй степени</i>'
        norm_bmi = 25
        norm_weight = norm_bmi * (height_m ** 2)
        norm_weight = norm_weight - weight
    else:
        grade = '<i>Ожирение третьей степени</i>'
        norm_bmi = 25
        norm_weight = norm_bmi * (height_m ** 2)
        norm_weight = norm_weight - weight

    if norm_weight == 0:
        state_of_weight = 'Вы молодец!\n<i>Ваш ИМТ находится в норме</i>'
    elif norm_weight > 0:
        state_of_weight = f'Вам нужно набрать <b>{norm_weight:.2f} кг</b> до нормы'
    else:
        state_of_weight = f'Вам нужно сбросить <b>{(-1) * norm_weight:.2f} кг</b> до нормы'

    return bmi, grade, state_of_weight
