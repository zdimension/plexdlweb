from config import config
import json


def get_data(lang: str) -> dict[str, str]:
    with open(f"locales/{lang}.json", "r", encoding="utf-8") as f:
        return json.load(f)


default_lang = get_data("en")
user_lang = get_data(config.lang)


def _(key: str, **kwargs) -> str:
    return user_lang.get(key, default_lang[key]).format(**kwargs)
