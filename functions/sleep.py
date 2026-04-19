def get_time_of_sleep(time_to_sleep, time_for_sleep):
    if time_for_sleep[0] - time_to_sleep[0] >= 0:
        hour_sleep = time_for_sleep[0] - time_to_sleep[0]
    else:
        hour_sleep = time_for_sleep[0] + (24 - time_to_sleep[0])

    if time_for_sleep[1] - time_to_sleep[1] >= 0:
        minutes_sleep = time_for_sleep[1] - time_to_sleep[1]
    else:
        minutes_sleep = time_for_sleep[1] + (60 - time_to_sleep[1])
        hour_sleep -= 1

    time_of_sleep = hour_sleep + (minutes_sleep/60)
    return hour_sleep, minutes_sleep, time_of_sleep


def to_sleep(time_to_sleep):
    if time_to_sleep[0] == 21 or (time_to_sleep[0] == 22 and time_to_sleep[1] <= 30):
        return 20 #21:00 - 22:30
    elif time_to_sleep[0] == 20 or time_to_sleep[0] == 22 or (time_to_sleep[0] == 23 and time_to_sleep[1] <= 30):
        return 16 #20:00 - 20:59 or 22:31 - 23:30
    elif time_to_sleep[0] == 19 or time_to_sleep[0] == 23 or (time_to_sleep[0] == 0 and time_to_sleep[1] <= 30):
        return 12 #19:00 - 19:59 or 23:31 - 0:30
    elif time_to_sleep[0] == 18 or time_to_sleep[0] == 0 or (time_to_sleep[0] == 1 and time_to_sleep[1] <= 30):
        return 8 #18:00 - 18:59 or 0:31 - 1:30
    else:
        return 4


def for_sleep(time_for_sleep):
    if (time_for_sleep[0] == 6 and time_for_sleep[1] >= 30) or time_for_sleep[0] == 7:
        return 17.5 #6:30 - 7:59
    elif time_for_sleep[0] == 6 or (time_for_sleep[0] == 8 and time_for_sleep[1] <= 30):
        return 14 #6:00 - 6:29 or 8:00 - 8:30
    elif (time_for_sleep[0] == 5 and time_for_sleep[1] >= 30) or time_for_sleep[0] == 8:
        return 10.5 #5:30 - 5:59 or 8:31 - 8:59
    elif time_for_sleep[0] == 5 or time_for_sleep[0] == 9:
        return 7 #5:00 - 5:29 or 9:00 - 9:59
    else:
        return 3.5

def ball_of_time(time_of_sleep):
    if 7.0 <= time_of_sleep <= 8.0:
        return 25
    elif 6.5 <= time_of_sleep < 7.0 or 8.0 < time_of_sleep <= 8.5:
        return 20
    elif 6.0 <= time_of_sleep < 6.5 or 8.5 < time_of_sleep <= 9.0:
        return 15
    elif 5.0 <= time_of_sleep < 6 or 9.0 < time_of_sleep <= 9.5:
        return 10
    elif 3.0 <= time_of_sleep < 5 or 9.5 < time_of_sleep <= 13.0:
        return 5
    else:
        return -15


def samoocenka_wake(state_sleep):
    if state_sleep == 5:
        return 10
    elif state_sleep == 4:
        return 8
    elif state_sleep == 3:
        return 6
    elif state_sleep == 2:
        return 4
    elif state_sleep == 1:
        return 2

def grade_of_avg(avg_sleep):
    if 7.0 <= avg_sleep <= 8.0:
        return 17.5
    elif 6.5 <= avg_sleep < 7.0 or 8.0 < avg_sleep <= 8.5:
        return 14
    elif 6.0 <= avg_sleep < 6.5 or 8.5 < avg_sleep <= 9.0:
        return 10.5
    elif 5.5 <= avg_sleep < 6.0 or 9.0 < avg_sleep <= 9.5:
        return 7
    else:
        return 3.5

def grade_of_grade(grade_sleep):
    if grade_sleep == 9 or grade_sleep == 10:
        return 10
    elif grade_sleep == 7 or grade_sleep == 8:
        return 8
    elif grade_sleep == 5 or grade_sleep == 6:
        return 6
    elif grade_sleep == 3 or grade_sleep == 4:
        return 4
    else:
        return 2


def grade(time_to_sleep, time_for_sleep, state_sleep, avg_sleep, grade_sleep):
    time_of_sleep = get_time_of_sleep(time_to_sleep, time_for_sleep)
    SLEEP_SCORE = to_sleep(time_to_sleep) + for_sleep(time_for_sleep) + ball_of_time(time_of_sleep[2]) + samoocenka_wake(state_sleep) + grade_of_avg(avg_sleep) + grade_of_grade(grade_sleep)
    return SLEEP_SCORE, time_of_sleep[0], time_of_sleep[1]

#print(grade([22, 30], [6, 30], 5, 7.6, 10))