# Solfeo Bot — Local & Telegram

## Overview

Solfeo Bot is a single-file solfège practice tool that can run in local mode (default) or as a Telegram bot (`--telegram`). It shows randomly selected staff notes, lets players answer using solfège or letter names, and keeps per-user settings so each student can choose language and notation preferences.

## Feature snapshot

- One script (`solfeo_bot.py`) for both environments.
- `/help` and `/start` present three clear entry points: **play**, **historial**, **settings**.
- Per-user settings saved under `SESSIONS/SETTINGS/` (`<username>.lang`, `<username>.system`). First-time users are prompted for language (ES/EN) and notation system (letter/solfege); `/settings` can change them later.
- Timed sessions stored as CSV files under `SESSIONS/SAVED_GAMES/<username>/session_YYYYMMDD_HHMMSS.csv`.
- Analytics helpers: `/old_games [n]`, `/tiempos [n]`, `/aciertos [n]`.
- Local mode mirrors Telegram commands (slash optional) and displays matplotlib figures inline while keeping the console in focus.
- Automatic migration from legacy lowercase `sessions/` directories into the uppercase `SESSIONS/` layout.

## Requirements

- Python 3.10+
- `python-telegram-bot>=20.0`
- `matplotlib`
- Optional (Linux): `xdotool`, `wmctrl` for focus restoration

Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

*(On macOS/Linux replace the activation command accordingly.)*

## Configuration

1. **Telegram token** — store your bot token in `telegram_token.txt`. The file is ignored by git. If it is missing, the script creates a template the first time you start with `--telegram`.
2. **Per-user settings** — every user (Telegram username or `local_<os_user>`) gets:
   - `SESSIONS/SETTINGS/<user>.lang` → `es` or `en`.
   - `SESSIONS/SETTINGS/<user>.system` → `letter` or `solfege`.
   These files are created automatically after the user answers the onboarding questions or uses `/set_language` / `/set_system`.

## Usage

### Local mode (default)

```powershell
python .\solfeo_bot.py
```

- Start by typing `play`, `historial`, or `settings`.
- `play` explains `free` and `time` modes.
- `historial` highlights `old_games`, `tiempos`, `aciertos`.
- `settings` lists `set_language` and `set_system` prompts.
- `free` and `time` immediately show notes; `stop` saves timed results.
- `q`, `quit`, or `exit` leaves the program.

### Telegram bot

```powershell
python .\solfeo_bot.py --telegram
```

All commands accept the slash prefix; `/help` or `/start` re-display the three-option landing menu.

| Command | Description |
| --- | --- |
| `/play` | Recaps `free` vs `time` modes. |
| `/historial` | Points to `/old_games`, `/tiempos`, `/aciertos`. |
| `/settings` | Introduces `/set_language` and `/set_system`. |
| `/free`, `/time` | Begin practice immediately (free mode does not save; timed mode records attempts). |
| `/stop` | Ends the current timed session and writes CSV data. |
| `/old_games [n]` | Lists the latest `n` saved CSV files (default 5). |
| `/tiempos [n]` | Generates time-per-note plots across the last `n` sessions. |
| `/aciertos [n]` | Generates accuracy plots for the last `n` sessions. |

### Session data

Timed sessions are written as CSV files containing:

`timestamp`, `clef`, `letter`, `solfege`, `correct`, `time_seconds`.

Plots are rendered as temporary PNG files displayed through matplotlib.

## Project layout

```
solfeo_bot.py          # main application
README.md
requirements.txt
SESSIONS/
  SETTINGS/            # per-user language/system files
  SAVED_GAMES/<user>/  # timed session CSVs
telegram_token.txt     # git-ignored bot token
to_do.md               # development backlog
```

`SESSIONS/`, `JUNK/`, and other generated artifacts are ignored automatically via `.gitignore`.

## Development notes

- Quick syntax check: `python -m py_compile solfeo_bot.py`.
- The roadmap lives in `to_do.md` (localization, consolidated JSON configs, inline keyboards, automated tests, diagnostics improvements, etc.).
- Contributions are welcome — open an issue or PR if you want to extend the bot.

## License

MIT — see `LICENSE`.


