# Contributing to TuonTa

Thanks for helping. TuonTa is a small, focused app, so changes that keep it simple are the most welcome.

## Ground rules

- **No AI.** No AI APIs, chatbots, assistants or generative features. Logic stays deterministic.
- **Stay offline.** No network calls, accounts or telemetry.
- **Every button must work**, and bad input must produce a clear message, never a traceback.

## Setup

```bash
git clone <your fork>
cd TuonTa
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
python -m unittest discover tests
```

## Architecture

- `tuonta/core/` holds logic and storage. It must not import `tkinter` or `customtkinter`, so it stays testable.
- `tuonta/ui/` holds the interface. Each screen is a `Page` subclass in `ui/pages/` with `on_show()` and, when needed, `on_hide()`.
- Reuse widgets from `ui/components.py` and colours from `ui/theme.py` instead of styling inline.
- Icons are drawn in `ui/drawing.py`. Add a function there and register it in `ICONS`.

## Design guidelines

Charcoal, off-white and one blue accent. Fixed sidebar, flat surfaces, thin dividers instead of cards,
4px corner radius, no gradients or glow. Motion only where it answers an action (flip, toast, chart rise).
Buttons say what they do ("Save note", not "Submit"). Errors say what went wrong and how to fix it.

## Pull requests

1. Branch from `main` and keep each PR to one change.
2. Add or update tests for anything in `core/`.
3. Run the tests and click through the screens you touched.
4. Describe the change and add a screenshot for UI work.

## Ideas

Anki export, drag-and-drop import, light theme, more card-detection patterns, spaced-repetition due dates.
