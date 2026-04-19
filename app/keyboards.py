from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text = '📊Расчет ИМТ📊', callback_data='imt'), InlineKeyboardButton(text = '💧Трекер воды💧', callback_data='water')],
    [InlineKeyboardButton(text = '💤Анализ сна💤', callback_data='sleep'), InlineKeyboardButton(text = '🍽План КБЖУ🍽', callback_data='eat')],
    [InlineKeyboardButton(text = '📋Общая статистика📋', callback_data='daily_stats')],
    [InlineKeyboardButton(text = '👾О разработчике👾', callback_data='about')],
    [InlineKeyboardButton(text = '🆘Помощь🆘', callback_data='help')]
])

back_to_menu = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text = '🔙Вернуться в меню🔙', callback_data='back')]])


def saved_data_keyboard(use_callback, change_callback):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Использовать сохраненные данные', callback_data=use_callback)],
        [InlineKeyboardButton(text='Изменить данные', callback_data=change_callback)],
    ])


sex_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Мужчина', callback_data='eat_sex_m')],
    [InlineKeyboardButton(text='Женщина', callback_data='eat_sex_f')],
])


water_sport_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='Да', callback_data='water_sport_yes'),
        InlineKeyboardButton(text='Нет', callback_data='water_sport_no'),
    ],
])


water_amount_mode_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Добавить к текущему', callback_data='water_mode_add')],
    [InlineKeyboardButton(text='Изменить количество за день', callback_data='water_mode_replace')],
])


def number_keyboard(prefix, count, columns=5):
    buttons = [
        InlineKeyboardButton(text=str(number), callback_data=f'{prefix}_{number}')
        for number in range(1, count + 1)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[
        buttons[index:index + columns]
        for index in range(0, len(buttons), columns)
    ])


sleep_state_keyboard = number_keyboard('sleep_state', 5)
sleep_grade_keyboard = number_keyboard('sleep_grade', 10, columns=5)
activity_keyboard = number_keyboard('eat_level', 5)


goal_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Поддержание веса', callback_data='eat_goal_1')],
    [InlineKeyboardButton(text='Похудение', callback_data='eat_goal_2')],
    [InlineKeyboardButton(text='Набор массы', callback_data='eat_goal_3')],
    [InlineKeyboardButton(text='Сушка', callback_data='eat_goal_4')],
])


def stats_button(callback_data):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📈 Статистика', callback_data=callback_data)],
    ])
