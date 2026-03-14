from __future__ import annotations

import json
from importlib import resources

_RESOURCE_PACKAGE = "prisoners_gambit.web"
_DEFAULT_LANGUAGE = "en"


def _read_text_resource(path: str) -> str:
    return resources.files(_RESOURCE_PACKAGE).joinpath(path).read_text(encoding="utf-8")


def load_ui_strings(language: str = _DEFAULT_LANGUAGE) -> dict[str, object]:
    normalized = (language or _DEFAULT_LANGUAGE).strip().lower()
    candidate = f"i18n/{normalized}.json"
    fallback = f"i18n/{_DEFAULT_LANGUAGE}.json"
    try:
        return json.loads(_read_text_resource(candidate))
    except FileNotFoundError:
        return json.loads(_read_text_resource(fallback))


def render_web_app(language: str = _DEFAULT_LANGUAGE) -> str:
    template = _read_text_resource("templates/app.html")
    css = _read_text_resource("static/app.css")
    js = _read_text_resource("static/app.js")
    strings = load_ui_strings(language)
    return (
        template.replace("{{INLINE_CSS}}", css.rstrip())
        .replace("{{INLINE_JS}}", js.rstrip())
        .replace("{{UI_STRINGS_JSON}}", json.dumps(strings, ensure_ascii=False))
    )
