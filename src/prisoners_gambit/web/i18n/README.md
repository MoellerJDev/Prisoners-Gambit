# Web UI language bundles

The web prototype reads user-facing copy from JSON bundles in this folder.

## Default behavior

- `en.json` is the default bundle.
- The server renders `/` using `render_web_app(language=...)` and injects the selected bundle into `window` bootstrap JS as `UI_STRINGS`.
- `?lang=<code>` can be used to select a bundle (for example `/?lang=en-x-test`).
- Unknown language codes fall back to `en.json`.

## Adding a new language

1. Add a new JSON file named with the language code (for example `es.json`).
2. Keep the same semantic key structure as `en.json`.
3. Start the server and open `/?lang=<code>` to verify all labels/helpers render.

This structure keeps localization content-driven: adding a language should only require a new JSON bundle, not JavaScript/server rewrites.
