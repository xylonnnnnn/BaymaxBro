def advice_sleep(flag):
    if flag == 1:
        return '<i>Старайтесь ложиться спать раньше, в периоде от 22 до 23:30</i>'
    elif flag == 2:
        return '<i>Старайтесь ложиться спать позже, в периоде от 20 до 21:30</i>'
    elif flag == 3:
        return '<i>Вам нужно увеличить продолжительность сна - от 6.5 до 8 часов</i>'
    elif flag == 4:
        return '<i>Вам нужно уменьшить продолжительность сна - от 7 до 8.5 часов</i>'

def get_time_of_sleep(time_to_sleep, hours, minutes):
    if 16 <= time_to_sleep[0] <= 19:
        flags = [2, 0]  # 16:00 - 19:59
    elif (time_to_sleep[0] == 23 and time_to_sleep[1] > 30) or 0 <= time_to_sleep[0] <= 8:
        flags = [1, 0]  # 23:31 - 8:00
    else:
        flags = [0, 0]

    time_of_sleep = hours + (minutes / 60)
    if time_of_sleep > 9.0:
        flags[1] = 4
    elif time_of_sleep < 6.5:
        flags[1] = 3

    if flags[0] != 0:
        s = advice_sleep(flags[0])
        if flags[1] != 0:
            s = s + '\n' + advice_sleep(flags[1])
            return s
        return s
    else:
        if flags[1] != 0:
            s = advice_sleep(flags[1])
            return s
        return ''

