"""Расчёт оценки с кешированием и чтение интересов клиентов."""

import json


def get_score(
    store,
    phone,
    email,
    birthday=None,
    gender=None,
    first_name=None,
    last_name=None,
) -> float:
    """Читает оценку из кеша или вычисляет и сохраняет её на час."""
    birthday_key = birthday.strftime("%Y%m%d") if birthday else None

    key_parts = [phone, email, birthday_key, gender, first_name, last_name]
    key = "uid:" + json.dumps(key_parts)

    score = store.cache_get(key)

    if score is not None:
        return float(score)

    score = 0.0

    if phone:
        score += 1.5

    if email:
        score += 1.5

    if birthday and gender is not None:
        score += 1.5

    if first_name and last_name:
        score += 0.5

    store.cache_set(key, score, 3600)

    return score


def get_interests(store, cid: int) -> list[str]:
    """Читает JSON интересов по ключу i:<cid>. При отсутствии возвращает []."""
    interests = store.get(f"i:{cid}")

    if not interests:
        return []

    return json.loads(interests)
