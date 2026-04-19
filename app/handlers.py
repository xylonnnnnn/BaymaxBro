from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile, Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import app.keyboards as kb
from database import (
    add_bmi_entry,
    add_kbzhu_entry,
    add_sleep_entry,
    add_water_entry,
    ensure_user,
    get_bmi_history,
    get_profile,
    get_sleep_history,
    get_today_summary,
    get_water_history,
    update_profile,
)
from stats_graphs import build_line_chart_png, build_progress_text
from functions.bmi import BMI

router = Router()
last_menu_messages = {}


async def send_main_menu(message: Message):
    sent_message = await message.answer('Выберите интересующую вас функцию!', reply_markup=kb.menu)
    last_menu_messages[message.chat.id] = sent_message.message_id


async def delete_last_menu(callback: CallbackQuery):
    message_id = last_menu_messages.pop(callback.message.chat.id, None)
    if not message_id:
        return

    try:
        await callback.bot.delete_message(callback.message.chat.id, message_id)
    except Exception:
        pass


async def delete_message_safe(message: Message):
    try:
        await message.delete()
    except Exception:
        pass


async def remember_prompt(state: FSMContext, message: Message):
    data = await state.get_data()
    prompt_ids = data.get("prompt_ids", [])
    prompt_ids.append(message.message_id)
    await state.update_data(prompt_ids=prompt_ids)


async def ask_question(message: Message, state: FSMContext, text, **kwargs):
    prompt = await message.answer(text, **kwargs)
    await remember_prompt(state, prompt)
    return prompt


async def ask_callback_question(callback: CallbackQuery, state: FSMContext, text, **kwargs):
    await callback.message.edit_text(text, **kwargs)
    await remember_prompt(state, callback.message)


async def cleanup_message_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    for message_id in data.get("prompt_ids", []):
        try:
            await message.bot.delete_message(message.chat.id, message_id)
        except Exception:
            pass
    await state.update_data(prompt_ids=[])
    await delete_message_safe(message)


async def cleanup_callback_answer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prompt_ids = data.get("prompt_ids", [])
    if callback.message.message_id not in prompt_ids:
        prompt_ids.append(callback.message.message_id)
    for message_id in prompt_ids:
        try:
            await callback.bot.delete_message(callback.message.chat.id, message_id)
        except Exception:
            pass
    await state.update_data(prompt_ids=[])

@router.message(CommandStart())
async def start(message: Message):
    ensure_user(message.from_user.id)
    await message.answer('Привет!\n'
                         'Я твой личный помощник по здоровью - <b>Baymax</b>\n'
                         'С помощью данных функций ниже, ты можешь проанализировать свое здоровье!\n ', parse_mode="HTML", reply_markup = kb.menu)


@router.callback_query(F.data == 'about')
async def about(callback: CallbackQuery):
    await callback.answer('Вы выбрали "О разработчике"')
    await callback.message.edit_text('<b>Имя:</b> Руслан\n'
                         '<b>Возраст:</b> 19 лет\n'
                         '<b>Город:</b> Новосибирск\n'
                         'Студент 2 курса ИИР в НГУ\n ', reply_markup = kb.back_to_menu, parse_mode="HTML")


@router.callback_query(F.data == 'help')
async def help(callback: CallbackQuery):
    await callback.answer('Вы выбрали "Помощь"')
    await callback.message.edit_text('Напиши нам в ТГ!\n'
                                     '@smglvrus\n ', reply_markup = kb.back_to_menu)

@router.callback_query(F.data == 'back')
async def menu(callback: CallbackQuery):
    await callback.answer('Вы выбрали "Меню"')
    await callback.message.edit_text('Выберите интересующую вас функцию!\n ', reply_markup = kb.menu)


def format_missing(value, formatter=str):
    if value:
        return formatter(value)
    return "отсутствует"


def sex_title(sex):
    return "Мужчина" if sex == "м" else "Женщина"


def build_daily_stats_text(profile, summary):
    missing_profile = []
    if not profile.get("sex"):
        missing_profile.append("пол")
    if not profile.get("age"):
        missing_profile.append("возраст")
    if not profile.get("height"):
        missing_profile.append("рост")
    if not profile.get("weight"):
        missing_profile.append("вес")

    lines = [
        f'<b>Общая статистика за день</b>',
        f'<b>Дата:</b> {summary["date"]}',
        '',
        '<b>Профиль:</b>',
        f'<b>Пол:</b> {format_missing(profile.get("sex"), sex_title)}',
        f'<b>Возраст:</b> {format_missing(profile.get("age"))}',
        f'<b>Рост:</b> {format_missing(profile.get("height"), lambda value: f"{value:.1f} см")}',
        f'<b>Вес:</b> {format_missing(profile.get("weight"), lambda value: f"{value:.1f} кг")}',
        '',
    ]

    bmi_entry = summary["bmi"]
    if bmi_entry:
        lines.extend([
            '<b>ИМТ:</b>',
            f'<b>Текущий ИМТ:</b> {bmi_entry["bmi"]:.2f}',
        ])
    elif profile.get("height") and profile.get("weight"):
        bmi = BMI(profile["height"], profile["weight"])
        lines.extend([
            '<b>ИМТ:</b>',
            f'<b>Текущий ИМТ:</b> {bmi[0]:.2f}',
        ])
    else:
        lines.extend(['<b>ИМТ:</b>', 'отсутствует'])

    water_entry = summary["water"]
    lines.append('')
    lines.append('<b>Вода:</b>')
    if water_entry:
        lines.append(f'<b>Выпито за день:</b> {int(water_entry["water_ml"])} мл')
    else:
        lines.append('отсутствует')

    sleep_entry = summary["sleep"]
    lines.append('')
    lines.append('<b>Сон:</b>')
    if sleep_entry:
        lines.extend([
            f'<b>Оценка сна:</b> {sleep_entry["score"]:.1f} из 100',
            f'<b>Продолжительность:</b> {sleep_entry["duration_hours"]}ч. {sleep_entry["duration_minutes"]}мин.',
            f'<b>Время:</b> {sleep_entry["sleep_time"]} - {sleep_entry["wake_time"]}',
        ])
    else:
        lines.append('отсутствует')

    kbzhu_entry = summary["today_kbzhu"] or summary["latest_kbzhu"]
    lines.append('')
    lines.append('<b>План КБЖУ:</b>')
    if kbzhu_entry:
        lines.extend([
            f'<b>Ккал:</b> ~{kbzhu_entry["calories"]}',
            f'<b>Белки:</b> ~{kbzhu_entry["proteins"]} г',
            f'<b>Жиры:</b> ~{kbzhu_entry["fats"]} г',
            f'<b>Углеводы:</b> ~{kbzhu_entry["carbs"]} г',
        ])
    else:
        lines.append('отсутствует')

    todo = []
    if missing_profile:
        todo.append('Заполнить данные профиля: ' + ', '.join(missing_profile))
    if not summary["latest_bmi"] and not (profile.get("height") and profile.get("weight")):
        todo.append('Пройти расчет ИМТ')
    if not water_entry:
        todo.append('Пройти трекер воды сегодня')
    if not sleep_entry:
        todo.append('Пройти анализ сна сегодня')
    if not summary["latest_kbzhu"]:
        todo.append('Сформировать план КБЖУ')

    if todo:
        lines.append('')
        lines.append('<b>Что стоит сделать:</b>')
        lines.extend(f'- {item}' for item in todo)

    return '\n'.join(lines)


@router.callback_query(F.data == 'daily_stats')
async def daily_stats(callback: CallbackQuery):
    await callback.answer('Общая статистика')
    profile = get_profile(callback.from_user.id)
    summary = get_today_summary(callback.from_user.id)
    await callback.message.edit_text(
        build_daily_stats_text(profile, summary),
        parse_mode="HTML",
        reply_markup=kb.back_to_menu,
    )


@router.callback_query(F.data == 'stats_bmi')
async def stats_bmi(callback: CallbackQuery):
    records = get_bmi_history(callback.from_user.id)
    await callback.answer()
    await delete_last_menu(callback)
    await callback.message.edit_text(
        build_progress_text('Статистика ИМТ', records, 'bmi', ''),
        parse_mode="HTML",
        reply_markup=kb.back_to_menu,
    )
    if records:
        chart = build_line_chart_png('Как меняется ИМТ', records, 'created_at', 'bmi', 'ИМТ')
        await callback.message.answer_photo(
            photo=BufferedInputFile(chart, filename='bmi_progress.png'),
            caption='График изменения ИМТ',
        )
    await send_main_menu(callback.message)


@router.callback_query(F.data == 'stats_water')
async def stats_water(callback: CallbackQuery):
    records = get_water_history(callback.from_user.id)
    await callback.answer()
    await delete_last_menu(callback)
    await callback.message.edit_text(
        build_progress_text('Статистика воды', records, 'water_ml', 'мл'),
        parse_mode="HTML",
        reply_markup=kb.back_to_menu,
    )
    if records:
        chart = build_line_chart_png('Как меняется количество выпитой воды', records, 'entry_date', 'water_ml', 'мл')
        await callback.message.answer_photo(
            photo=BufferedInputFile(chart, filename='water_progress.png'),
            caption='График воды по дням',
        )
    await send_main_menu(callback.message)


@router.callback_query(F.data == 'stats_sleep')
async def stats_sleep(callback: CallbackQuery):
    records = get_sleep_history(callback.from_user.id)
    await callback.answer()
    await delete_last_menu(callback)
    await callback.message.edit_text(
        build_progress_text('Статистика сна', records, 'score', 'баллов'),
        parse_mode="HTML",
        reply_markup=kb.back_to_menu,
    )
    if records:
        chart = build_line_chart_png('Как меняется оценка сна', records, 'created_at', 'score', 'баллы')
        await callback.message.answer_photo(
            photo=BufferedInputFile(chart, filename='sleep_progress.png'),
            caption='График оценки сна',
        )
    await send_main_menu(callback.message)


#IMT
class BMIState(StatesGroup):
    age = State()
    height = State()
    weight = State()


@router.callback_query(F.data == 'imt')
async def get_imt(callback: CallbackQuery, state: FSMContext):
    await callback.answer('Вы выбрали "Расчет ИМТ"')
    profile = get_profile(callback.from_user.id)
    if profile.get("age") and profile.get("height"):
        await ask_callback_question(
            callback,
            state,
            f'У меня сохранены ваши данные:\n'
            f'<b>Возраст:</b> {profile["age"]}\n'
            f'<b>Рост:</b> {profile["height"]:.1f} см\n\n'
            f'Использовать их для расчета ИМТ?',
            parse_mode="HTML",
            reply_markup=kb.saved_data_keyboard("bmi_use_saved", "bmi_change_saved"),
        )
    else:
        await state.set_state(BMIState.age)
        await ask_callback_question(callback, state, 'Сколько вам лет?')


@router.callback_query(F.data == 'bmi_use_saved')
async def use_saved_bmi(callback: CallbackQuery, state: FSMContext):
    profile = get_profile(callback.from_user.id)
    if profile.get("age") and profile.get("height"):
        await cleanup_callback_answer(callback, state)
        await state.update_data(age=profile["age"], height=profile["height"])
        await state.set_state(BMIState.weight)
        await callback.answer()
        await ask_question(callback.message, state, 'Напишите свой вес (кг)')
    else:
        await cleanup_callback_answer(callback, state)
        await state.set_state(BMIState.age)
        await callback.answer()
        await ask_question(callback.message, state, 'Сохраненных данных пока нет. Сколько вам лет?')


@router.callback_query(F.data == 'bmi_change_saved')
async def change_saved_bmi(callback: CallbackQuery, state: FSMContext):
    await cleanup_callback_answer(callback, state)
    await state.set_state(BMIState.age)
    await callback.answer()
    await ask_question(callback.message, state, 'Сколько вам лет?')


@router.message(BMIState.age, F.text)
async def get_bmi_age(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    if message.text.isdigit() and 8 <= int(message.text) <= 150:
        await state.update_data(age=int(message.text))
        await state.set_state(BMIState.height)
        await ask_question(message, state, 'Напишите свой рост (см)')
    else:
        await state.set_state(BMIState.age)
        await ask_question(message, state, 'Неправильное значение, введите еще раз, в диапазоне <b>от 8 до 150</b>', parse_mode="HTML")


@router.message(BMIState.height, F.text)
async def get_height(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    try:
        height = float(message.text.replace(',', '.'))  # на случай "180,5"
        if 50 <= height <= 250:
            await state.update_data(height = height)
            await state.set_state(BMIState.weight)
            await ask_question(message, state, f'Напишите свой вес (кг)')
        else:
            await state.set_state(BMIState.height)
            await ask_question(message, state, f'Неправильное значение, введите еще раз, в диапазоне <b>от 50 до 250</b>', parse_mode="HTML")
    except ValueError:
        await state.set_state(BMIState.height)
        await ask_question(message, state, 'Неправильное значение, введите еще раз\n'
                             '<b>Пример:</b> 170', parse_mode="HTML")


@router.message(BMIState.weight, F.text)
async def get_weight(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    try:
        weight = float(message.text.replace(',', '.'))  # на случай "80,5"
        if 10 <= weight <= 500:
            await state.update_data(weight = weight)
            data = await state.get_data()
            bmi = BMI(data['height'], data['weight'])
            update_profile(message.from_user.id, age=data.get('age'), height=data['height'], weight=data['weight'])
            add_bmi_entry(
                message.from_user.id,
                data.get('age'),
                data['height'],
                data['weight'],
                bmi[0],
                bmi[1],
            )
            await message.answer(f'<b>Ваш ИМТ:</b> {bmi[0]:.3f}\n'
                                 f'<b>Оценка ИМТ</b>: {bmi[1]}\n'
                                 f'{bmi[2]}\n\n'
                                 f'<i>Возраст, рост, вес и результат сохранены в историю.</i>',
                                 parse_mode="HTML",
                                 reply_markup=kb.stats_button('stats_bmi'))
            await send_main_menu(message)
            await state.clear()
        else:
            await state.set_state(BMIState.weight)
            await ask_question(message, state, f'Неправильное значение, введите еще раз, в диапазоне <b>от 10 до 500</b>', parse_mode="HTML")
    except ValueError:
        await state.set_state(BMIState.weight)
        await ask_question(message, state, 'Неправильное значение, введите еще раз\n'
                             '<b>Пример:</b> 70', parse_mode="HTML")



# Трекер воды

class Water(StatesGroup):
    weight = State()
    sport = State()
    mode = State()
    k = State()


@router.callback_query(F.data == 'water')
async def get_weight(callback: CallbackQuery, state: FSMContext):
    await callback.answer('Вы выбрали "Трекер воды"')
    profile = get_profile(callback.from_user.id)
    if profile.get("weight"):
        await ask_callback_question(
            callback,
            state,
            f'У меня сохранен ваш вес: <b>{profile["weight"]:.1f} кг</b>.\n'
            f'Использовать его для расчета нормы воды?',
            parse_mode="HTML",
            reply_markup=kb.saved_data_keyboard("water_use_saved", "water_change_saved"),
        )
    else:
        await state.set_state(Water.weight)
        await ask_callback_question(callback, state, 'Напишите свой вес (кг)')


@router.callback_query(F.data == 'water_use_saved')
async def use_saved_water(callback: CallbackQuery, state: FSMContext):
    profile = get_profile(callback.from_user.id)
    if profile.get("weight"):
        await cleanup_callback_answer(callback, state)
        await state.update_data(weight=profile["weight"])
        await state.set_state(Water.sport)
        await callback.answer()
        await ask_question(callback.message, state, 'Была ли тренировка сегодня?', reply_markup=kb.water_sport_keyboard)
    else:
        await cleanup_callback_answer(callback, state)
        await state.set_state(Water.weight)
        await callback.answer()
        await ask_question(callback.message, state, 'Сохраненного веса пока нет. Напишите свой вес (кг)')


@router.callback_query(F.data == 'water_change_saved')
async def change_saved_water(callback: CallbackQuery, state: FSMContext):
    await cleanup_callback_answer(callback, state)
    await state.set_state(Water.weight)
    await callback.answer()
    await ask_question(callback.message, state, 'Напишите новый вес (кг)')

@router.message(Water.weight, F.text)
async def get_sport(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    try:
        weight = float(message.text.replace(',', '.'))  # на случай "80,5"
        if 10 <= weight <= 500:
            await state.update_data(weight = weight)
            update_profile(message.from_user.id, weight=weight)
            await state.set_state(Water.sport)
            await ask_question(message, state, 'Была ли тренировка сегодня?', reply_markup=kb.water_sport_keyboard)
        else:
            await state.set_state(Water.weight)
            await ask_question(message, state, 'Неправильное значение, введите еще раз, в диапазоне <b>от 10 до 500</b>', parse_mode="HTML")
    except ValueError:
        await state.set_state(Water.weight)
        await ask_question(message, state, 'Неправильное значение, введите еще раз\n'
                             '<b>Пример:</b> 70', parse_mode="HTML")


@router.callback_query(Water.sport, F.data.in_({'water_sport_yes', 'water_sport_no'}))
async def choose_water_sport(callback: CallbackQuery, state: FSMContext):
    await cleanup_callback_answer(callback, state)
    sport = 'да' if callback.data == 'water_sport_yes' else 'нет'
    await state.update_data(sport=sport)
    await state.set_state(Water.mode)
    await callback.answer()
    await ask_question(callback.message, state, 'Как записать воду?', reply_markup=kb.water_amount_mode_keyboard)


@router.message(Water.sport, F.text)
async def get_water(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    sport = message.text.lower()
    if sport == 'да' or sport == 'нет':
        await state.update_data(sport = sport)
        await state.set_state(Water.mode)
        await ask_question(message, state, 'Как записать воду?', reply_markup=kb.water_amount_mode_keyboard)
    else:
        await state.set_state(Water.sport)
        await ask_question(message, state, 'Неправильное значение, выберите кнопку или напишите Да/Нет', reply_markup=kb.water_sport_keyboard)


@router.callback_query(Water.mode, F.data.in_({'water_mode_add', 'water_mode_replace'}))
async def choose_water_mode(callback: CallbackQuery, state: FSMContext):
    await cleanup_callback_answer(callback, state)
    mode = 'add' if callback.data == 'water_mode_add' else 'replace'
    await state.update_data(water_mode=mode)
    await state.set_state(Water.k)
    await callback.answer()
    await ask_question(callback.message, state, 'Напишите количество воды выпитой за день (мл)')


@router.message(Water.k, F.text)
async def get_tracker(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    try:
        tracker = float(message.text.replace(',', '.'))
        if 0 <= tracker <= 10000:
            data = await state.get_data()

            if data['sport'] == 'да':
                norma = 40
            else:
                norma = 30

            norma = norma * data['weight']

            part_of_norma = (tracker / norma) * 100
            total_water, updated_today = add_water_entry(
                message.from_user.id,
                data['weight'],
                data['sport'],
                tracker,
                norma,
                part_of_norma,
                data.get('water_mode', 'add'),
            )
            total_percent = (total_water / norma) * 100
            save_text = (
                f'Запись за сегодня обновлена. Всего за день: <b>{int(total_water)} мл</b>.'
                if updated_today and data.get('water_mode', 'add') == 'add' else
                f'Количество за сегодня изменено: <b>{int(total_water)} мл</b>.'
                if updated_today else
                'Запись сохранена в историю воды.'
            )
            if total_percent <= 100:
                await message.answer(f'<b>Суточная норма:</b> {int(norma)} мл\n'
                                     f'<b>Процент выполнения нормы:</b> {total_percent:.3f}%\n\n'
                                     f'<i>{save_text}</i>',
                                     parse_mode="HTML",
                                     reply_markup=kb.stats_button('stats_water'))
                await send_main_menu(message)
                await state.clear()
            else:
                await message.answer(f'<b>Суточная норма:</b> {int(norma)} мл\n'
                                     f'<b>Процент выполнения нормы:</b> 100% (+{total_water-norma} мл)\n\n'
                                     f'<i>{save_text}</i>',
                                     parse_mode="HTML",
                                     reply_markup=kb.stats_button('stats_water'))
                await send_main_menu(message)
                await state.clear()
        else:
            await state.set_state(Water.k)
            await ask_question(message, state, 'Неправильное значение, введите еще раз, в диапазоне <b>от 0 до 10000</b>', parse_mode="HTML")
    except ValueError:
        await state.set_state(Water.k)
        await ask_question(message, state, 'Неправильное значение, введите еще раз')


@router.message(Water.mode, F.text)
async def get_water_mode_text(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    text = message.text.lower()
    if text in {'добавить', 'добавить к текущему', '+'}:
        await state.update_data(water_mode='add')
        await state.set_state(Water.k)
        await ask_question(message, state, 'Напишите количество воды выпитой за день (мл)')
    elif text in {'изменить', 'заменить', 'изменить количество за день'}:
        await state.update_data(water_mode='replace')
        await state.set_state(Water.k)
        await ask_question(message, state, 'Напишите количество воды выпитой за день (мл)')
    else:
        await state.set_state(Water.mode)
        await ask_question(message, state, 'Выберите действие кнопкой ниже', reply_markup=kb.water_amount_mode_keyboard)


# Анализ сна

class Sleep(StatesGroup):
    time_to_sleep = State()
    time_for_sleep = State()
    state_sleep = State()
    avg_sleep = State()
    grade_sleep = State()


def parse_sleep_time(value):
    value = value.strip()
    if ":" in value:
        parts = value.split(":")
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            return None
        hour = int(parts[0])
        minute = int(parts[1])
    elif value.isdigit():
        hour = int(value)
        minute = 0
    else:
        return None

    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return [hour, minute]
    return None


@router.callback_query(F.data == 'sleep')
async def get_time_to_sleep(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Sleep.time_to_sleep)
    await callback.answer('Вы выбрали "Анализ сна"')
    await ask_callback_question(callback, state, 'Напишите время, во сколько вы легли спать\n'
                                     '<b>Примеры:</b> 22:30, 23\n', parse_mode="HTML")

@router.message(Sleep.time_to_sleep, F.text)
async def get_time_for_sleep(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    time_to_sleep = parse_sleep_time(message.text)
    if time_to_sleep:
        await state.update_data(time_to_sleep=time_to_sleep)
        await state.set_state(Sleep.time_for_sleep)
        await ask_question(message, state, f'Напишите время, во сколько вы проснулись\n<b>Примеры:</b> 6:30, 7', parse_mode="HTML")
    else:
        await state.set_state(Sleep.time_to_sleep)
        await ask_question(message, state, 'Неправильное значение, введите еще раз')


@router.message(Sleep.time_for_sleep, F.text)
async def get_state_sleep(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    time_for_sleep = parse_sleep_time(message.text)
    if time_for_sleep:
        await state.update_data(time_for_sleep=time_for_sleep)
        await state.set_state(Sleep.state_sleep)
        await ask_question(message, state, 'Проснулись ли вы отдохнувшим?', reply_markup=kb.sleep_state_keyboard)
    else:
        await state.set_state(Sleep.time_for_sleep)
        await ask_question(message, state, 'Неправильное значение, введите еще раз')


@router.callback_query(Sleep.state_sleep, F.data.startswith('sleep_state_'))
async def choose_sleep_state(callback: CallbackQuery, state: FSMContext):
    await cleanup_callback_answer(callback, state)
    state_sleep = int(callback.data.split('_')[-1])
    await state.update_data(state_sleep=state_sleep)
    profile = get_profile(callback.from_user.id)
    await callback.answer()
    if profile.get("avg_sleep"):
        await ask_question(
            callback.message,
            state,
            f'У меня сохранено среднее время сна: <b>{profile["avg_sleep"]:.1f} ч.</b>\n'
            f'Использовать его?',
            parse_mode="HTML",
            reply_markup=kb.saved_data_keyboard("sleep_use_saved_avg", "sleep_change_saved_avg"),
        )
    else:
        await state.set_state(Sleep.avg_sleep)
        await ask_question(callback.message, state, 'Сколько часов в среднем вы спите?\n<b>Примеры:</b> 5, 6.7, 8-9', parse_mode="HTML")


@router.message(Sleep.state_sleep, F.text)
async def get_avg_sleep(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    a = message.text
    if a.isdigit() and 1 <= int(a) <= 5:
        await state.update_data(state_sleep = int(a))
        profile = get_profile(message.from_user.id)
        if profile.get("avg_sleep"):
            await ask_question(
                message,
                state,
                f'У меня сохранено среднее время сна: <b>{profile["avg_sleep"]:.1f} ч.</b>\n'
                f'Использовать его?',
                parse_mode="HTML",
                reply_markup=kb.saved_data_keyboard("sleep_use_saved_avg", "sleep_change_saved_avg"),
            )
        else:
            await state.set_state(Sleep.avg_sleep)
            await ask_question(message, state, 'Сколько часов в среднем вы спите?\n<b>Примеры:</b> 5, 6.7, 8-9', parse_mode="HTML")
    else:
        await state.set_state(Sleep.state_sleep)
        await ask_question(message, state, 'Неправильное значение, введите еще раз', reply_markup=kb.sleep_state_keyboard)


@router.callback_query(F.data == 'sleep_use_saved_avg')
async def use_saved_sleep_avg(callback: CallbackQuery, state: FSMContext):
    profile = get_profile(callback.from_user.id)
    await cleanup_callback_answer(callback, state)
    if profile.get("avg_sleep"):
        await state.update_data(avg_sleep=profile["avg_sleep"])
        await state.set_state(Sleep.grade_sleep)
        await callback.answer()
        await ask_question(
            callback.message,
            state,
            'Оцените ваш сон <b>(от 1 до 10)</b>\n'
            'Где <b>1</b> - очень плохо, <b>10</b> - идеально\n',
            parse_mode="HTML",
            reply_markup=kb.sleep_grade_keyboard,
        )
    else:
        await state.set_state(Sleep.avg_sleep)
        await callback.answer()
        await ask_question(callback.message, state, 'Сохраненного среднего сна пока нет. Сколько часов в среднем вы спите?')


@router.callback_query(F.data == 'sleep_change_saved_avg')
async def change_saved_sleep_avg(callback: CallbackQuery, state: FSMContext):
    await cleanup_callback_answer(callback, state)
    await state.set_state(Sleep.avg_sleep)
    await callback.answer()
    await ask_question(callback.message, state, 'Сколько часов в среднем вы спите?\n<b>Примеры:</b> 5, 6.7, 8-9', parse_mode="HTML")

@router.message(Sleep.avg_sleep, F.text)
async def get_grade_sleep(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    a = message.text.replace(',', '.').strip()
    avg_sleep = None

    if '-' in a:
        parts = a.split('-')
        if len(parts) == 2:
            try:
                left = float(parts[0])
                right = float(parts[1])
                avg_sleep = (left + right) / 2
            except ValueError:
                avg_sleep = None
    else:
        try:
            avg_sleep = float(a)
        except ValueError:
            avg_sleep = None

    if avg_sleep is not None and 0.0 <= avg_sleep < 24.0:
        await state.update_data(avg_sleep=avg_sleep)
        update_profile(message.from_user.id, avg_sleep=avg_sleep)
        await state.set_state(Sleep.grade_sleep)
        await ask_question(message, state, 'Оцените ваш сон <b>(от 1 до 10)</b>\nГде <b>1</b> - очень плохо, <b>10</b> - идеально\n', parse_mode="HTML", reply_markup=kb.sleep_grade_keyboard)
    else:
        await state.set_state(Sleep.avg_sleep)
        await ask_question(message, state, 'Неправильное значение, введите еще раз')


@router.callback_query(Sleep.grade_sleep, F.data.startswith('sleep_grade_'))
async def choose_sleep_grade(callback: CallbackQuery, state: FSMContext):
    await cleanup_callback_answer(callback, state)
    grade_sleep = int(callback.data.split('_')[-1])
    await state.update_data(grade_sleep=grade_sleep)
    await finish_sleep(callback.message, state, callback.from_user.id)


from functions.sleep import grade
from advices.sleep import get_time_of_sleep


async def finish_sleep(message: Message, state: FSMContext, user_id):
    data = await state.get_data()
    ggg = grade(data['time_to_sleep'], data['time_for_sleep'], data['state_sleep'], data['avg_sleep'],
                data['grade_sleep'])
    s = get_time_of_sleep(data['time_to_sleep'], ggg[1], ggg[2])
    sleep_time = f'{data["time_to_sleep"][0]:02d}:{data["time_to_sleep"][1]:02d}'
    wake_time = f'{data["time_for_sleep"][0]:02d}:{data["time_for_sleep"][1]:02d}'
    add_sleep_entry(
        user_id,
        sleep_time,
        wake_time,
        data['state_sleep'],
        data['avg_sleep'],
        data['grade_sleep'],
        ggg[0],
        ggg[1],
        ggg[2],
    )
    await message.answer(f'<b>Продолжительность вашего сна была:</b> {ggg[1]}ч. {ggg[2]}мин.\n'
                         f'<b>Оценка вашего сна:</b> {ggg[0]: .1f} из 100\n\n'
                         f'{s}\n\n'
                         f'<i>Запись сохранена в историю сна.</i>',
                         parse_mode="HTML",
                         reply_markup=kb.stats_button('stats_sleep'))
    await send_main_menu(message)
    await state.clear()


@router.message(Sleep.grade_sleep, F.text)
async def get_sleep(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    a = message.text
    if (len(a) == 1 and a.isdigit() and a != '0') or (len(a) == 2 and a[0] == '1' and a[1] == '0'):
        await state.update_data(grade_sleep = int(a))
        await finish_sleep(message, state, message.from_user.id)
    else:
        await state.set_state(Sleep.grade_sleep)
        await ask_question(message, state, 'Неправильное значение, выберите оценку от 1 до 10', reply_markup=kb.sleep_grade_keyboard)


# План КБЖУ
class Eat(StatesGroup):
    sex = State()
    age = State()
    height = State()
    weight = State()
    level = State()
    goal = State()


def saved_eat_fields(profile):
    return {
        key: profile[key]
        for key in ("sex", "age", "height", "weight", "activity_level")
        if profile.get(key)
    }


async def ask_next_eat_step(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("sex"):
        await state.set_state(Eat.sex)
        await ask_question(message, state, 'Выберите свой пол:', reply_markup=kb.sex_keyboard)
    elif not data.get("age"):
        await state.set_state(Eat.age)
        await ask_question(message, state, 'Сколько вам лет?')
    elif not data.get("height"):
        await state.set_state(Eat.height)
        await ask_question(message, state, 'Напишите свой рост (см)')
    elif not data.get("weight"):
        await state.set_state(Eat.weight)
        await ask_question(message, state, 'Напишите свой вес (кг)')
    elif not data.get("level"):
        await state.set_state(Eat.level)
        await ask_question(
            message,
            state,
            'Оцените свой уровень активности <b>(от 1 до 5)</b>\n'
            'Где <b>1</b> - сидячий, <b>5</b> - очень активный (тренировки каждый день)',
            parse_mode="HTML",
            reply_markup=kb.activity_keyboard,
        )
    else:
        await state.set_state(Eat.goal)
        await ask_question(
            message,
            state,
            '<b>Выберите цель:</b>',
            parse_mode="HTML",
            reply_markup=kb.goal_keyboard,
        )


async def finish_kbzhu(message: Message, state: FSMContext, user_id):
    data = await state.get_data()
    gg = get_kbzhu(data['sex'], data['age'], data['height'], data['weight'], data['level'], data['goal'])
    s = advice_kbzhu(data['goal'])
    update_profile(
        user_id,
        sex=data['sex'],
        age=data['age'],
        height=data['height'],
        weight=data['weight'],
        activity_level=data['level'],
    )
    add_kbzhu_entry(
        user_id,
        data['sex'],
        data['age'],
        data['height'],
        data['weight'],
        data['level'],
        data['goal'],
        gg[0],
        gg[1],
        gg[2],
        gg[3],
    )
    await message.answer(f'<b>Ваш индивидуальный план КБЖУ:</b>\n'
                         f'<b>Кол-во ккал в сутки:</b> ~{gg[0]}\n'
                         f'<b>Белки:</b> ~{gg[1]} г\n'
                         f'<b>Жиры:</b> ~{gg[2]} г\n'
                         f'<b>Углеводы:</b> ~{gg[3]} г\n\n'
                         f'<b>Совет:</b>\n<i>{s}</i>\n\n'
                         f'<i>План сохранен в историю КБЖУ.</i>', parse_mode="HTML")
    await send_main_menu(message)
    await state.clear()


@router.callback_query(F.data == 'eat')
async def get_sex(callback: CallbackQuery, state: FSMContext):
    await callback.answer('Вы выбрали "План КБЖУ"')
    profile = get_profile(callback.from_user.id)
    fields = saved_eat_fields(profile)
    if fields:
        await state.update_data(
            sex=profile.get("sex"),
            age=profile.get("age"),
            height=profile.get("height"),
            weight=profile.get("weight"),
            level=profile.get("activity_level"),
        )
        profile_lines = []
        if profile.get("sex"):
            profile_lines.append(f'<b>Пол:</b> {sex_title(profile["sex"])}')
        if profile.get("age"):
            profile_lines.append(f'<b>Возраст:</b> {profile["age"]}')
        if profile.get("height"):
            profile_lines.append(f'<b>Рост:</b> {profile["height"]:.1f} см')
        if profile.get("weight"):
            profile_lines.append(f'<b>Вес:</b> {profile["weight"]:.1f} кг')
        if profile.get("activity_level"):
            profile_lines.append(f'<b>Активность:</b> {profile["activity_level"]} из 5')
        await ask_callback_question(
            callback,
            state,
            'У меня сохранены эти данные для КБЖУ:\n'
            + '\n'.join(profile_lines)
            + '\n\nИспользовать их и заполнить только недостающие данные?',
            parse_mode="HTML",
            reply_markup=kb.saved_data_keyboard("eat_use_saved", "eat_change_saved"),
        )
    else:
        await state.set_state(Eat.sex)
        await ask_callback_question(callback, state, 'Выберите свой пол:', reply_markup=kb.sex_keyboard)


@router.callback_query(F.data == 'eat_use_saved')
async def use_saved_eat(callback: CallbackQuery, state: FSMContext):
    profile = get_profile(callback.from_user.id)
    await callback.answer()
    await cleanup_callback_answer(callback, state)
    await state.update_data(
        sex=profile.get("sex"),
        age=profile.get("age"),
        height=profile.get("height"),
        weight=profile.get("weight"),
        level=profile.get("activity_level"),
    )
    await ask_next_eat_step(callback.message, state)


@router.callback_query(F.data == 'eat_change_saved')
async def change_saved_eat(callback: CallbackQuery, state: FSMContext):
    await cleanup_callback_answer(callback, state)
    await state.clear()
    await state.set_state(Eat.sex)
    await callback.answer()
    await ask_question(callback.message, state, 'Выберите свой пол:', reply_markup=kb.sex_keyboard)


@router.callback_query(F.data.in_({'eat_sex_m', 'eat_sex_f'}))
async def choose_eat_sex(callback: CallbackQuery, state: FSMContext):
    await cleanup_callback_answer(callback, state)
    sex = 'м' if callback.data == 'eat_sex_m' else 'ж'
    await state.update_data(sex=sex)
    await callback.answer()
    await ask_next_eat_step(callback.message, state)


@router.message(Eat.sex, F.text)
async def get_age(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    a = message.text.lower()
    if len(a) == 1 and (a == 'м' or a == 'ж'):
        await state.update_data(sex = a)
        await ask_next_eat_step(message, state)
    else:
        await state.set_state(Eat.sex)
        await ask_question(message, state, 'Выберите пол с помощью кнопок ниже.', reply_markup=kb.sex_keyboard)

@router.message(Eat.age, F.text)
async def get_height(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    a = message.text
    if a.isdigit() and 8 <= int(a) <= 150:
        await state.update_data(age=int(a))
        await ask_next_eat_step(message, state)
    else:
        await state.set_state(Eat.age)
        await ask_question(message, state, 'Неправильное значение, введите еще раз, в диапазоне <b>от 8 до 150</b>', parse_mode="HTML")


@router.message(Eat.height, F.text)
async def get_weight(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    try:
        height = float(message.text.replace(',', '.'))  # на случай "180,5"
        if 50 <= height <= 250:
            await state.update_data(height = height)
            await ask_next_eat_step(message, state)
        else:
            await state.set_state(Eat.height)
            await ask_question(message, state, f'Неправильное значение, введите еще раз, в диапазоне <b>от 50 до 250</b>', parse_mode="HTML")
    except ValueError:
        await state.set_state(Eat.height)
        await ask_question(message, state, 'Неправильное значение, введите еще раз\n'
                             '<b>Пример:</b> 170', parse_mode="HTML")
        
        
@router.message(Eat.weight, F.text)
async def get_level(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    try:
        weight = float(message.text.replace(',', '.'))  # на случай "180,5"
        if 10 <= weight <= 500:
            await state.update_data(weight = weight)
            await ask_next_eat_step(message, state)
        else:
            await state.set_state(Eat.weight)
            await ask_question(message, state, f'Неправильное значение, введите еще раз, в диапазоне <b>от 10 до 500</b>', parse_mode="HTML")
    except ValueError:
        await state.set_state(Eat.weight)
        await ask_question(message, state, 'Неправильное значение, введите еще раз\n'
                             '<b>Пример:</b> 70', parse_mode="HTML")


@router.callback_query(Eat.level, F.data.startswith('eat_level_'))
async def choose_eat_level(callback: CallbackQuery, state: FSMContext):
    await cleanup_callback_answer(callback, state)
    await state.update_data(level=int(callback.data.split('_')[-1]))
    await callback.answer()
    await ask_next_eat_step(callback.message, state)
        
        
@router.message(Eat.level, F.text)
async def get_goal(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    a = message.text
    if len(a) == 1 and a.isdigit() and 1 <= int(a) <= 5:
        await state.update_data(level=int(a))
        await ask_next_eat_step(message, state)
    else:
        await state.set_state(Eat.level)
        await ask_question(message, state, 'Неправильное значение, выберите уровень активности', reply_markup=kb.activity_keyboard)

from functions.eat import get_kbzhu
from advices.eat import advice_kbzhu


@router.callback_query(Eat.goal, F.data.startswith('eat_goal_'))
async def choose_eat_goal(callback: CallbackQuery, state: FSMContext):
    await cleanup_callback_answer(callback, state)
    await state.update_data(goal=int(callback.data.split('_')[-1]))
    await callback.answer()
    await finish_kbzhu(callback.message, state, callback.from_user.id)


@router.message(Eat.goal, F.text)
async def get_plan(message: Message, state: FSMContext):
    await cleanup_message_answer(message, state)
    a = message.text
    if len(a) == 1 and a.isdigit() and 1 <= int(a) <= 4:
        await state.update_data(goal=int(a))
        await finish_kbzhu(message, state, message.from_user.id)
    else:
        await state.set_state(Eat.goal)
        await ask_question(message, state, 'Неправильное значение, выберите цель', reply_markup=kb.goal_keyboard)
