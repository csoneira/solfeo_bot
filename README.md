Solfeo Bot — local and Telegram modes

Overview

This repository contains a small solfège practice tool implemented in a single script `solfeo_bot.py`.
The same script can run either as a local interactive program (default) or as a Telegram bot (use `--telegram`).
# Solfeo Bot — local and Telegram modes

## Overview

This repository contains a small solfège practice tool implemented in a single script `solfeo_bot.py`.
The same script can run either as a local interactive program (default) or as a Telegram bot (use `--telegram`).

## Features

- Show musical notes on a staff (treble/bass) using matplotlib.
- Two play modes:
  - Free mode (`/free`): practice without saving or timing.
  - Timed mode (`/time`): measure response time and correctness; save sessions as CSV.
- Session persistence: timed sessions are saved under `sessions/<username>/session_YYYYMMDD_HHMMSS.csv`.
- Commands to list history and generate plots:
  - `/historial [n]` — list last n sessions.
  - `/tiempos [n]` — plot average times per note (treble & bass panels).
  - `/aciertos [n]` — plot success rates per note (treble & bass panels).
- Local mode supports the same commands typed at the prompt (you may omit the leading `/`).
- Console focus is restored after showing plot windows on Windows and (when available) on Linux via xdotool/wmctrl.

## Requirements

Python packages (install with pip):

- python-telegram-bot>=20.0
- matplotlib

Optional (Linux) system packages:

- xdotool (recommended for returning focus to terminal on X11)
- wmctrl (fallback option)

See `requirements.txt` for the pip-list.

## Installation

1. Create a virtual environment (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install Python dependencies:

```powershell
pip install -r requirements.txt
```

3. (Linux) optionally install focus helpers:

```bash
sudo apt update
sudo apt install -y xdotool wmctrl
```

## Configuration

- By default the script will look for a file named `telegram_token.txt` in the current working directory when run with `--telegram`. If the file does not exist a template file will be created containing a commented instruction line; paste your bot token as a single non-comment line into that file and re-run with `--telegram`.

- If you still have an embedded `TELEGRAM_TOKEN` constant in `solfeo_bot.py`, the script will use it as a fallback but it's recommended to move the token to `telegram_token.txt` for safety.

## Usage — Local (default)

Run locally (default):

```powershell
python .\solfeo_bot.py
```

Commands (type in the prompt; in local mode you may omit the leading `/`):

- `free` or `/free` — switch to free mode (no timing, no saving).
- `time` or `/time` — start a timed session; answers will be timed and recorded.
- `stop` or `/stop` — stop the timed session and save results to `sessions/local_<os_user>/` as CSV.
- `historial [n]` or `/historial [n]` — show last `n` sessions for the local user.
- `tiempos [n]` or `/tiempos [n]` — display time plots (last `n` sessions).
- `aciertos [n]` or `/aciertos [n]` — display success-rate plots (last `n` sessions).
- (No `play` command required) — use `free` or `time` to begin showing notes immediately after selecting a mode.
- `help` or `/help` — show instructions.
- `q`, `quit`, `exit` — exit the program.

### How local interaction works

- The program starts in an idle prompt. Type `free` (or `time`) to choose a mode — notes are shown immediately.
- When a note is active, the program shows a note image in a matplotlib window (non-blocking) and prompts for the note name in the console.
- Answer using solfège (`do`, `re`, `mi`, etc.) or letter names (`C`, `D`, `E`, ...).
- If you enter an unrecognized answer twice in a row, the session is stopped and help/instructions are shown.
- In timed mode, answers taking more than 60 seconds will automatically stop the timed session and previous records (if any) are saved; the slow attempt itself will NOT be recorded.

## Usage — Telegram

Run the Telegram bot (requires `--telegram`):

```powershell
python .\solfeo_bot.py --telegram
```

Interact with the bot via Telegram chat. The same commands are available (`/start`, `/free`, `/time`, `/stop`, `/historial`, `/tiempos`, `/aciertos`, `/help`).

## Session files and format

Timed sessions are saved as CSV files under `sessions/<username>/session_YYYYMMDD_HHMMSS.csv`.
Columns:
- timestamp — ISO timestamp for the recorded attempt
- clef — `treble` or `bass`
- letter — note letter (C, D, E, ...)
- solfege — Do/Re/Mi...
- correct — 0 or 1
- time_seconds — response time in seconds

## Plots

- `/tiempos` creates a two-panel figure (treble over bass) with average times and error bars (stddev). Both panels share the same y-axis range for easy comparison.
- `/aciertos` creates a two-panel figure with success rates (%) and error bars.

## Notes and troubleshooting

- On Windows, the script tries to bring the PowerShell console back into focus after showing figure windows. If you still need to click into the terminal, your OS focus settings may prevent automatic focus.
- On Linux, installing `xdotool` or `wmctrl` improves focus behavior but these tools work on X11 (not Wayland). On Wayland you may need compositor-specific tools.
- If plots block or multiple windows appear, try closing extra windows. If you prefer a single persistent GUI, I can switch to an in-window GUI (Tkinter) or reuse a single matplotlib figure and update it in-place.

## License

This project is licensed under the MIT License — see the included `LICENSE` file for details.

---

Small utility for private practice. Feel free to adapt or open issues if you want features or changes.


