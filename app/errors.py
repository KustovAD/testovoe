from http import HTTPStatus

from starlette.exceptions import HTTPException

HTTP_MESSAGES = {
    HTTPStatus.BAD_REQUEST: "Некорректный запрос",
    HTTPStatus.NOT_FOUND: "Страница не найдена",
    HTTPStatus.METHOD_NOT_ALLOWED: "Метод не поддерживается",
    HTTPStatus.INTERNAL_SERVER_ERROR: "Внутренняя ошибка сервера",
}


def http_error_message(exc: HTTPException) -> str:
    # starlette fills detail with the English status phrase when none is given
    if exc.detail and exc.detail != HTTPStatus(exc.status_code).phrase:
        return exc.detail
    return HTTP_MESSAGES.get(exc.status_code, "Ошибка запроса")


def _one(err: dict) -> str:
    name = err["loc"][-1] if err.get("loc") else "запрос"
    ctx = err.get("ctx") or {}
    match err.get("type"):
        case "missing":
            return f"Не передан обязательный параметр «{name}»"
        case "string_too_short":
            return f"Параметр «{name}» не может быть пустым"
        case "string_too_long":
            return f"Параметр «{name}» слишком длинный (максимум {ctx.get('max_length')} символов)"
        case "int_parsing" | "int_type":
            return f"Параметр «{name}» должен быть целым числом"
        case "greater_than_equal":
            return f"Параметр «{name}» должен быть не меньше {ctx.get('ge')}"
        case _:
            return f"Некорректное значение параметра «{name}»"


def validation_error_message(errors) -> str:
    return "; ".join(dict.fromkeys(_one(e) for e in errors)) or "Некорректный запрос"
