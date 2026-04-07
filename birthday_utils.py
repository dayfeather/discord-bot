import json
import os

BIRTHDAY_FILE = "birthdays.json"


def load_birthdays():
    if os.path.exists(BIRTHDAY_FILE):
        with open(BIRTHDAY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_birthdays(data):
    with open(BIRTHDAY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def is_valid_birthday(month: int, day: int) -> bool:
    if month < 1 or month > 12:
        return False

    month_days = {
        1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
        7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
    }

    return 1 <= day <= month_days[month]


def register_birthday(user_id: int, display_name: str, month: int, day: int):
    data = load_birthdays()
    data[str(user_id)] = {
        "name": display_name,
        "month": month,
        "day": day
    }
    save_birthdays(data)


def get_birthday(user_id: int):
    data = load_birthdays()
    return data.get(str(user_id))


def delete_birthday(user_id: int) -> bool:
    data = load_birthdays()
    key = str(user_id)

    if key not in data:
        return False

    del data[key]
    save_birthdays(data)
    return True


def get_all_birthdays():
    return load_birthdays()