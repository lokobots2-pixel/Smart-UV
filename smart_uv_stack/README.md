# Smart UV Stack

Smart UV Stack ist ein Blender-Add-on für die UV-Ansicht. Es erkennt ähnliche oder nahezu identische UV-Inseln und stapelt sie per Klick übereinander.

## Installation

1. Die ZIP-Datei in Blender über **Edit > Preferences > Add-ons > Install...** laden.
2. Das Add-on aktivieren.
3. Einen Mesh-Objekt im **Edit Mode** öffnen.
4. Im **UV Editor** die Sidebar öffnen und den Tab **UV** wählen.

## Bedienung

- **Detect Similar Islands**: Erkennt ähnliche Inseln und aktualisiert die Vorschau.
- **Stack Selected Islands**: Stapelt ähnliche, ausgewählte UV-Inseln.
- **Stack All Similar Islands**: Stapelt alle ähnlichen Inseln im aktiven Mesh.
- **Select Similar Islands**: Wählt ähnliche Inseln zur aktiven Insel aus.
- **Clear Groups**: Löscht den Cache und die Vorschau.

## Hinweise

- Kein externes Paket nötig.
- Die Erkennung ist auf ähnliche Topologie, polygonale Form, Seitenverhältnisse und relative Winkel ausgelegt.
- Die Vorschau nutzt den UV Editor als Overlay.
- Bei sehr symmetrischen Formen können mehrere gültige Ausrichtungen existieren. In solchen Fällen entscheidet die aktuelle Heuristik.

## Kompatibilität

- Blender 4.5 LTS
- Blender 5.x
- Zukunftssichere Registrierung mit `bpy.utils.register_class`
- Panel in `IMAGE_EDITOR -> UI -> UV`

## Dateien

- `smart_uv_stack/__init__.py`
- `smart_uv_stack/geometry.py`
- `smart_uv_stack/stacking.py`
- `smart_uv_stack/drawing.py`
- `smart_uv_stack/operators.py`
- `smart_uv_stack/ui.py`
- `README.md`
- `CHANGELOG.md`
- `LICENSE`
