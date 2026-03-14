from __future__ import annotations

import json
from importlib import resources

_RESOURCE_PACKAGE = "prisoners_gambit.web"
_DEFAULT_LANGUAGE = "en"


def _read_text_resource(path: str) -> str:
    return resources.files(_RESOURCE_PACKAGE).joinpath(path).read_text(encoding="utf-8")


def _deep_merge(base: dict[str, object], overrides: dict[str, object]) -> dict[str, object]:
    merged: dict[str, object] = dict(base)
    for key, value in overrides.items():
        base_value = merged.get(key)
        if isinstance(base_value, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(base_value, value)
        else:
            merged[key] = value
    return merged


def load_ui_strings(language: str = _DEFAULT_LANGUAGE) -> dict[str, object]:
    fallback = json.loads(_read_text_resource(f"i18n/{_DEFAULT_LANGUAGE}.json"))
    normalized = (language or _DEFAULT_LANGUAGE).strip().lower()
    if normalized == _DEFAULT_LANGUAGE:
        return fallback
    candidate = f"i18n/{normalized}.json"
    try:
        requested = json.loads(_read_text_resource(candidate))
    except FileNotFoundError:
        return fallback
    return _deep_merge(fallback, requested)


def render_web_app(language: str = _DEFAULT_LANGUAGE) -> str:
    template = _read_text_resource("templates/app.html")
    css = _read_text_resource("static/app.css")
    js = _read_text_resource("static/app.js")
    strings = load_ui_strings(language)
    app_strings = strings.get("app") if isinstance(strings.get("app"), dict) else {}
    page_title = app_strings.get("page_title", "Prisoner's Gambit")
    return (
        template.replace("{{PAGE_TITLE}}", str(page_title))
        .replace("{{INLINE_CSS}}", css.rstrip())
        .replace("{{INLINE_JS}}", js.rstrip())
        .replace("{{UI_STRINGS_JSON}}", json.dumps(strings, ensure_ascii=False))
    )
