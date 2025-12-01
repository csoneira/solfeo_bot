import argparse
import logging
import random
import re
import sys
from io import BytesIO

import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import os
import time
import csv
import math
import statistics
from datetime import datetime
from pathlib import Path
import getpass
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

# Name of the token file. When running with --telegram, the script will try to
# read the bot token from this file. If the file does not exist it will be
# created containing a single commented instruction line so you can paste the
# token there. The loader will read the first non-empty, non-comment line as
# the token.
TOKEN_FILE = Path.cwd() / "telegram_token.txt"


def _load_or_create_telegram_token() -> str | None:
    """Read token from TOKEN_FILE. If the file does not exist, create it with
    a single commented instruction line and return None. If the file exists,
    return the first non-comment, non-empty line (literal token) or None if
    none found.
    """
    try:
        if not TOKEN_FILE.exists():
            # Create a template file with one commented line explaining usage
            TOKEN_FILE.write_text(
                "# Paste your Telegram bot token on a non-commented line below this comment and save the file.\n",
                encoding="utf-8",
            )
            return None

        # Read and find first non-comment line
        text = TOKEN_FILE.read_text(encoding="utf-8")
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            # Found a candidate token line — return it literally
            return line
        return None
    except Exception:
        return None

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# =========================================================
# MAPAS DE NOTAS
# =========================================================

# Notas en clave de sol (treble) usando C4 como do central
# Secuencia diatónica (pasos línea/espacio)
TREBLE_PITCHES = [
    "C4", "D4", "E4", "F4", "G4", "A4", "B4",
    "C5", "D5", "E5", "F5", "G5", "A5", "B5", "C6"
]

# Notas en clave de fa (bass)
BASS_PITCHES = [
    "E2", "F2", "G2", "A2", "B2", "C3", "D3", "E3",
    "F3", "G3", "A3", "B3", "C4", "D4", "E4", "F4"
]

LETTER_TO_SOLFEGE = {
    "C": "Do",
    "D": "Re",
    "E": "Mi",
    "F": "Fa",
    "G": "Sol",
    "A": "La",
    "B": "Si",
}

SOLFEGE_TO_LETTER = {
    "do": "C",
    "re": "D",
    "mi": "E",
    "fa": "F",
    "sol": "G",
    "la": "A",
    "si": "B",
}


def get_note_info(clef: str, staff_index: int) -> dict:
    """
    Devuelve información de la nota elegida por posición en el pentagrama.

    staff_index es un índice entero en pasos diatónicos:
        0 = línea inferior del pentagrama,
        1 = primer espacio,
        2 = segunda línea, etc.

    Se permiten valores negativos y mayores que 8 (líneas adicionales).
    """
    if clef == "treble":
        pitches = TREBLE_PITCHES
    elif clef == "bass":
        pitches = BASS_PITCHES
    else:
        raise ValueError("Clave desconocida")

    # Definimos que staff_index = 0 (línea inferior) corresponde a pitches[2]
    pitch_index = staff_index + 2
    if pitch_index < 0 or pitch_index >= len(pitches):
        raise ValueError("Índice de nota fuera de rango para esta clave")

    pitch_name = pitches[pitch_index]  # por ejemplo "C4"
    letter = pitch_name[0]             # "C"
    solfege = LETTER_TO_SOLFEGE[letter]

    return {
        "pitch": pitch_name,
        "letter": letter,
        "solfege": solfege,
        "staff_index": staff_index,
    }


# =========================================================
# GENERACIÓN DE IMAGEN
# =========================================================

def generate_note_image(clef: str, staff_index: int) -> BytesIO:
    """
    Genera una imagen PNG en memoria con:
      - pentagrama de 5 líneas (negro)
      - etiqueta de clave ("SOL" o "FA") centrada en la línea de referencia
        (G4 para clave de sol, F3 para clave de fa)
      - una nota como elipse negra en la posición indicada

    Convención:
      staff_index = 0  -> línea inferior del pentagrama
      staff_index = 1  -> primer espacio
      ...
      staff_index = 8  -> línea superior del pentagrama

    Cada paso (±1) equivale a 0.5 unidades en y.
    """
    # Figura suficientemente grande para que se vea bien en Telegram
    fig, ax = plt.subplots(figsize=(6, 3))

    # -------------------------
    # Pentagrama principal (negro)
    # -------------------------
    # Líneas en y = 0, 1, 2, 3, 4
    for y in [0, 1, 2, 3, 4]:
        ax.hlines(y, 1.3, 10.0, linewidth=1.8, color="black")

    # -------------------------
    # Etiqueta de clave, centrada en la línea de referencia
    # -------------------------
    # En nuestra convención:
    #   clave de sol: línea de G4 = staff_index 2 -> y = 2 * 0.5 = 1.0
    #   clave de fa:  línea de F3 = staff_index 6 -> y = 6 * 0.5 = 3.0
    if clef == "treble":
        clef_label = "Sol"
        clef_staff_index = 2  # línea de SOL (G4)
    else:
        clef_label = "Fa"
        clef_staff_index = 6  # línea de FA (F3)

    clef_y = clef_staff_index * 0.5

    ax.text(
        0.6,               # x
        clef_y,            # y, sobre la línea de referencia
        clef_label,
        fontsize=18,
        ha="center",
        va="center",
        color="black",
    )

    # -------------------------
    # Nota
    # -------------------------
    # cada step = 0.5 en y
    note_x = 8.0
    note_y = staff_index * 0.5
    
    # Cabeza de nota: elipse negra ligeramente inclinada
    factor = 1.35
    note_head = Ellipse(
        (note_x, note_y),
        width=0.9*factor,
        height=0.6*factor,
        angle=20,
        facecolor="black",
        edgecolor="black",
    )
    ax.add_patch(note_head)

    # -------------------------
    # Líneas adicionales (ledger lines), en negro
    # -------------------------
    # Solo para índices fuera de 0..8, y solo en índices pares (líneas)
    # Por encima del pentagrama
    if staff_index > 8:
        # primera línea adicional por encima: índice 10
        for line_index in range(10, staff_index + 1, 2):
            y_line = line_index * 0.5
            ax.hlines(
                y_line,
                note_x - 0.9,
                note_x + 0.9,
                linewidth=1.5,
                color="black",
            )

    # Por debajo del pentagrama
    if staff_index < 0:
        # primera línea adicional por debajo: índice -2
        for line_index in range(-2, staff_index - 1, -2):
            y_line = line_index * 0.5
            ax.hlines(
                y_line,
                note_x - 0.9,
                note_x + 0.9,
                linewidth=1.5,
                color="black",
            )

    # -------------------------
    # Ajustes de eje
    # -------------------------
    # Rango suficiente para dos líneas auxiliares arriba y abajo
    ax.set_xlim(-0.2, 10.5)
    ax.set_ylim(-2.0, 6.0)

    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=580, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    buf.seek(0)
    return buf


# =========================================================
# LÓGICA DE RESPUESTAS
# =========================================================

def normalize_answer(text: str):
    """
    Convierte la respuesta del usuario a una letra de nota canónica: C, D, E, F, G, A, B.

    Acepta:
      - "do, re, mi, fa, sol, la, si"
      - "C, D, E, F, G, A, B"
      - con o sin número de octava (C4, do4, etc.).
    """
    t = text.strip().lower()
    # Quitar acentos básicos
    t = (
        t.replace("ó", "o")
         .replace("á", "a")
         .replace("é", "e")
         .replace("í", "i")
         .replace("ú", "u")
    )

    # Quitar dígitos (octava)
    t = re.sub(r"\d", "", t)

    # Solfeo completo
    if t in SOLFEGE_TO_LETTER:
        return SOLFEGE_TO_LETTER[t]

    # Letras inglesas
    if len(t) == 0:
        return None

    first = t[0]
    if first.upper() in ["A", "B", "C", "D", "E", "F", "G"]:
        return first.upper()

    return None


async def send_new_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Genera una nueva nota aleatoria (clave y posición) y la envía al usuario.
    Guarda la solución en context.user_data.
    """
    # Elegir clave aleatoriamente (sol o fa)
    clef = random.choice(["treble", "bass"])

    # Rango de posiciones:
    # -2 -> primera línea adicional por debajo
    # 12 -> segunda línea adicional por encima
    staff_index = random.randint(-2, 12)

    # Garantizar que la nota está en el rango de la tabla para esa clave
    while True:
        try:
            note_info = get_note_info(clef, staff_index)
            break
        except ValueError:
            staff_index = random.randint(-2, 12)

    # Guardar la nota esperada para este usuario
    context.user_data["current_note"] = {
        "clef": clef,
        "staff_index": staff_index,
        "pitch": note_info["pitch"],
        "letter": note_info["letter"],
        "solfege": note_info["solfege"],
    }
    # Reset consecutive-invalid counter when a new note is issued
    context.user_data["invalid_count"] = 0

    buf = generate_note_image(clef, staff_index)

    # If running in timed mode, record the timestamp when the note was shown
    # so we can measure response time.
    try:
        if context and isinstance(context.user_data, dict) and context.user_data.get("mode") == "time":
            context.user_data["last_shown_ts"] = time.time()
    except Exception:
        pass

    clef_name = "clave de sol" if clef == "treble" else "clave de fa"
    caption = (
        f"¿Qué nota es esta en {clef_name}?\n"
        "Puedes responder con do, re, mi... o con letras (C, D, E...)."
    )

    await update.effective_chat.send_photo(photo=buf, caption=caption)


def _safe_username_from_update(update: Update) -> str:
    """Return a filesystem-safe username from a Telegram update (fallback to names)."""
    user = update.effective_user
    if user is None:
        return "local"
    name = user.username or f"{user.first_name or 'user'}_{user.id}"
    # sanitize: keep alphanum, dash and underscore
    safe = "".join(c for c in name if c.isalnum() or c in ("-","_"))
    return safe or "user"


def _ensure_user_dir(username: str) -> Path:
    # Save sessions under SESSIONS/SAVED_GAMES/<username>/
    base = Path.cwd() / "SESSIONS" / "SAVED_GAMES" / username
    base.mkdir(parents=True, exist_ok=True)
    return base


def _save_session_records(username: str, records: list[dict]) -> Path:
    """Save session records (list of dicts) to CSV under sessions/<username>/session_YYYYmmdd_HHMMSS.csv
    Returns path to file.
    """
    if not records:
        raise ValueError("No records to save")
    user_dir = _ensure_user_dir(username)
    fname = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    p = user_dir / fname
    fieldnames = ["timestamp", "clef", "letter", "solfege", "correct", "time_seconds"]
    with p.open("w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow({
                "timestamp": r.get("timestamp"),
                "clef": r.get("clef"),
                "letter": r.get("letter"),
                "solfege": r.get("solfege"),
                "correct": int(bool(r.get("correct"))),
                "time_seconds": float(r.get("time_seconds") or 0),
            })
    return p


def _list_user_sessions(username: str) -> list[Path]:
    user_dir = Path.cwd() / "SESSIONS" / "SAVED_GAMES" / username
    if not user_dir.exists():
        return []
    files = sorted([p for p in user_dir.iterdir() if p.suffix == ".csv"], key=lambda x: x.stat().st_mtime, reverse=True)
    return files


def _settings_dir() -> Path:
    d = Path.cwd() / "SESSIONS" / "SETTINGS"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _user_lang_file(username: str) -> Path:
    return _settings_dir() / f"{username}.lang"


def _user_system_file(username: str) -> Path:
    return _settings_dir() / f"{username}.system"


def _read_user_system(username: str) -> str | None:
    p = _user_system_file(username)
    if p.exists():
        txt = p.read_text(encoding='utf-8').strip()
        if txt:
            return txt
    return None


def _write_user_system(username: str, system: str) -> Path:
    p = _user_system_file(username)
    p.write_text(system.strip(), encoding='utf-8')
    return p


def _read_user_language(username: str) -> str | None:
    p = _user_lang_file(username)
    if p.exists():
        txt = p.read_text(encoding='utf-8').strip()
        if txt:
            return txt
    return None


def _write_user_language(username: str, lang: str) -> Path:
    p = _user_lang_file(username)
    p.write_text(lang.strip(), encoding='utf-8')
    return p


def _read_session_csv(path: Path) -> list[dict]:
    recs = []
    with path.open("r", encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            recs.append({
                "timestamp": row.get("timestamp"),
                "clef": row.get("clef"),
                "letter": row.get("letter"),
                "solfege": row.get("solfege"),
                "correct": bool(int(row.get("correct", "0"))),
                "time_seconds": float(row.get("time_seconds", "0")),
            })
    return recs


def _aggregate_records(records: list[dict]):
    """Aggregate records per clef and letter. Returns dict[clef][letter] -> dict(stats).

    stats include: attempts, corrects, times_correct (list), avg_time_correct, std_time_correct, success_rate
    """
    agg = {}
    for r in records:
        clef = r.get("clef", "unknown")
        letter = r.get("letter", "?")
        agg.setdefault(clef, {})
        bucket = agg[clef].setdefault(letter, {"attempts": 0, "corrects": 0, "times_correct": []})
        bucket["attempts"] += 1
        if r.get("correct"):
            bucket["corrects"] += 1
            bucket["times_correct"].append(r.get("time_seconds", 0.0))

    # compute derived stats
    for clef, letters in agg.items():
        for letter, data in letters.items():
            attempts = data["attempts"]
            corrects = data["corrects"]
            times = data["times_correct"]
            avg = statistics.mean(times) if times else 0.0
            std = statistics.pstdev(times) if len(times) > 1 else 0.0
            success_rate = (corrects / attempts * 100.0) if attempts > 0 else 0.0
            # approximate deviation for success rate (percent) using binomial std
            se = math.sqrt(success_rate/100.0 * (1 - success_rate/100.0) / attempts) * 100.0 if attempts > 0 else 0.0
            data.update({"avg_time_correct": avg, "std_time_correct": std, "success_rate": success_rate, "success_se": se})

    return agg


def restore_console_focus():
    """Attempt to bring the terminal/console window to the foreground.

    On Windows uses SetForegroundWindow. On Linux tries xdotool/wmctrl after
    setting a unique terminal title. Fail silently on errors.
    """
    try:
        if sys.platform.startswith("win"):
            import ctypes

            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                SW_SHOW = 5
                user32.ShowWindow(hwnd, SW_SHOW)
                user32.SetForegroundWindow(hwnd)

        elif sys.platform.startswith("linux"):
            import os
            import subprocess

            title = f"SolfeoTerminal-{os.getpid()}"
            sys.stdout.write(f"\033]0;{title}\007")
            sys.stdout.flush()

            try:
                subprocess.run([
                    "xdotool",
                    "search",
                    "--name",
                    title,
                    "windowactivate",
                    "--sync",
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                try:
                    subprocess.run(["wmctrl", "-a", title], check=True,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
    except Exception:
        pass


def _menu_text_main() -> str:
    return (
        "Bienvenido a Solfeo — elige una opción para empezar:\n\n"
        "• /play — comenzar a practicar (luego elige entre modos: free o time).\n"
        "• /historial — ver opciones de historial y estadísticas (tiempos, aciertos, listado de partidas).\n"
        "• /settings — configurar preferencia de idioma y sistema de notación.\n\n"
        "En local puedes escribir 'play', 'historial' o 'settings' sin '/'.\n"
    )


def _menu_text_play() -> str:
    return (
        "Modos de juego:\n\n"
        "• Usa /free para modo libre — no guarda datos ni mide tiempos.\n"
        "• Usa /time para iniciar sesión temporizada — se guardarán tiempos y aciertos.\n\n"
        "En local puedes escribir 'free' o 'time' sin '/'.\n"
    )


def _menu_text_historial() -> str:
    return (
        "Historial y estadísticas:\n\n"
        "• /tiempos [n] — genera gráficos de tiempos por nota para las últimas n sesiones.\n"
        "• /aciertos [n] — genera gráficos de tasa de aciertos por nota para las últimas n sesiones.\n"
        "• /old_games [n] — lista rápida de las últimas n partidas guardadas.\n\n"
        "En local puedes escribir 'tiempos', 'aciertos' u 'old_games' sin '/'.\n"
    )


def _menu_text_settings() -> str:
    return (
        "Ajustes de usuario:\n\n"
        "• /set_language — cambiar el idioma de los mensajes (es/en).\n"
        "• /set_system — elegir el sistema de notación ('letter' o 'solfege').\n\n"
        "En local puedes teclear 'set_language' o 'set_system'.\n"
    )


# =========================================================
# HANDLERS DE TELEGRAM
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Make /start behave the same as /help: show instructions and modes.
    await help_command(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(_menu_text_main())


async def play_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(_menu_text_play())


async def set_language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Begin an interactive language-setting flow for the user."""
    username = _safe_username_from_update(update)
    context.user_data["awaiting_language"] = True
    await update.message.reply_text(
        "Por favor responde con el código de idioma que prefieres (ej.: 'es' o 'en')."
    )


async def set_system_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Begin an interactive notation-system-setting flow for the user."""
    username = _safe_username_from_update(update)
    context.user_data["awaiting_system"] = True
    await update.message.reply_text(
        "Indica el sistema de notación que prefieres: 'letter' (C D E ...) o 'solfege' (do re mi ...)."
    )


async def old_games_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick list of recent saved games (convenience replacement for quick-history)."""
    args = context.args if hasattr(context, 'args') else []
    n = 5
    if args:
        try:
            n = max(1, int(args[0]))
        except Exception:
            n = 5

    username = _safe_username_from_update(update)
    files = _list_user_sessions(username)[:n]
    if not files:
        await update.message.reply_text("No hay sesiones guardadas para este usuario.")
        return

    lines = [f"Últimas {len(files)} sesiones:"]
    for p in files:
        lines.append(p.name)
    await update.message.reply_text("\n".join(lines))


async def free_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enter free mode: no timing, no saving."""
    context.user_data["mode"] = "free"
    context.user_data.pop("session_records", None)
    context.user_data["invalid_count"] = 0
    await update.message.reply_text("Modo libre activado. Te mostraré notas sin medir tiempos ni guardar resultados.")
    await send_new_note(update, context)


async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enter timed mode: start a new timed session."""
    context.user_data["mode"] = "time"
    context.user_data["session_records"] = []
    context.user_data["invalid_count"] = 0
    await update.message.reply_text("Modo temporizado activado. Tus tiempos y aciertos se guardarán en la carpeta de sesiones al finalizar (/stop).")
    await send_new_note(update, context)


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop a timed session and save CSV if any records exist."""
    if context.user_data.get("mode") != "time":
        await update.message.reply_text("No hay una sesión temporizada en curso.")
        return

    records = context.user_data.get("session_records", [])
    username = _safe_username_from_update(update)
    if not records:
        await update.message.reply_text("No hay datos de sesión para guardar.")
    else:
        try:
            p = _save_session_records(username, records)
            await update.message.reply_text(f"Sesión guardada en: {p}")
        except Exception as e:
            await update.message.reply_text(f"Error guardando la sesión: {e}")

    # Clear session
    context.user_data.pop("session_records", None)
    context.user_data.pop("mode", None)
    context.user_data.pop("current_note", None)
    context.user_data["invalid_count"] = 0


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(_menu_text_settings())


async def historial_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(_menu_text_historial())


def _make_time_plot(records: list[dict]) -> BytesIO:
    # aggregate across records
    agg = _aggregate_records(records)
    notes_order = ["C","D","E","F","G","A","B"]

    # Build data for both clefs first so we can compute a common y-axis
    data_by_clef = {}
    global_max = 0.0
    for clef in ["treble", "bass"]:
        means = []
        errs = []
        labels = []
        for note in notes_order:
            data = agg.get(clef, {}).get(note)
            if data:
                m = float(data.get('avg_time_correct', 0.0))
                e = float(data.get('std_time_correct', 0.0))
            else:
                m = 0.0
                e = 0.0
            means.append(m)
            errs.append(e)
            labels.append(note)
            global_max = max(global_max, m + e)
        data_by_clef[clef] = (means, errs, labels)

    # Ensure a non-zero y range
    if global_max <= 0:
        global_max = 1.0

    fig, axes = plt.subplots(2, 1, figsize=(8, 6), constrained_layout=True)
    for i, clef in enumerate(["treble", "bass"]):
        ax = axes[i]
        means, errs, labels = data_by_clef[clef]
        x = range(len(labels))
        ax.bar(x, means, yerr=errs, capsize=5)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylabel('Tiempo medio (s)')
        ax.set_title('Tiempos por nota — ' + ("Clave de SOL" if clef=="treble" else "Clave de FA"))
        ax.set_ylim(0, global_max * 1.10)

    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def _make_success_plot(records: list[dict]) -> BytesIO:
    agg = _aggregate_records(records)
    notes_order = ["C","D","E","F","G","A","B"]

    fig, axes = plt.subplots(2, 1, figsize=(8, 6), constrained_layout=True)
    for i, clef in enumerate(["treble", "bass"]):
        ax = axes[i]
        means = []
        errs = []
        labels = []
        for note in notes_order:
            data = agg.get(clef, {}).get(note)
            if data:
                means.append(data.get('success_rate', 0.0))
                errs.append(data.get('success_se', 0.0))
                labels.append(note)
            else:
                means.append(0.0)
                errs.append(0.0)
                labels.append(note)

        x = range(len(labels))
        ax.bar(x, means, yerr=errs, capsize=5)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylim(0, 100)
        ax.set_ylabel('Aciertos (%)')
        ax.set_title('Tasa de aciertos por nota — ' + ("Clave de SOL" if clef=="treble" else "Clave de FA"))

    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


async def tiempos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # optional arg: number of last sessions to include
    args = context.args if hasattr(context, 'args') else []
    n = 1
    if args:
        try:
            n = max(1, int(args[0]))
        except Exception:
            n = 1

    username = _safe_username_from_update(update)
    files = _list_user_sessions(username)[:n]
    if not files:
        await update.message.reply_text("No hay sesiones para generar graficas.")
        return

    combined = []
    for p in files:
        combined.extend(_read_session_csv(p))

    buf = _make_time_plot(combined)
    await update.effective_chat.send_photo(photo=buf)


async def aciertos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args if hasattr(context, 'args') else []
    n = 1
    if args:
        try:
            n = max(1, int(args[0]))
        except Exception:
            n = 1

    username = _safe_username_from_update(update)
    files = _list_user_sessions(username)[:n]
    if not files:
        await update.message.reply_text("No hay sesiones para generar graficas.")
        return

    combined = []
    for p in files:
        combined.extend(_read_session_csv(p))

    if not combined:
        await update.message.reply_text("No hay datos de aciertos para mostrar.")
        return

    buf = _make_success_plot(combined)
    await update.effective_chat.send_photo(photo=buf)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    current = context.user_data.get("current_note")

    # Ensure user language is configured: if missing, ask for it and set awaiting flag
    username = _safe_username_from_update(update)
    user_lang = _read_user_language(username)
    if not user_lang and not context.user_data.get("awaiting_language"):
        context.user_data["awaiting_language"] = True
        await update.message.reply_text(
            "No tienes configurado el idioma. Por favor responde con el código de idioma que prefieres (ej. 'es' o 'en')."
        )
        return

    # If we're awaiting a language reply, accept it here and save
    if context.user_data.get("awaiting_language") and not current:
        lang_try = (user_text or "").strip().lower()
        if not lang_try:
            await update.message.reply_text("No se recibió un idioma válido. Intenta de nuevo: 'es' o 'en'.")
            return
        # normalize common names
        if lang_try.startswith("es") or lang_try.startswith("span"):
            lang = "es"
        elif lang_try.startswith("en") or lang_try.startswith("eng"):
            lang = "en"
        else:
            # accept raw two-letter codes
            lang = lang_try[:2]

        try:
            _write_user_language(username, lang)
            context.user_data["awaiting_language"] = False
            await update.message.reply_text(f"Idioma almacenado: {lang}. Puedes usar /help para ver opciones.")
        except Exception as e:
            await update.message.reply_text(f"Error guardando la configuración: {e}")
        return

    if context.user_data.get("awaiting_system") and not current:
        sys_try = (user_text or "").strip().lower()
        if not sys_try:
            await update.message.reply_text("No se recibió un sistema válido. Escribe 'letter' o 'solfege'.")
            return

        if sys_try.startswith("let") or sys_try in ("letter", "letters", "abc"):
            system = "letter"
        elif sys_try.startswith("sol") or sys_try in ("solfege", "solfeo", "do", "doremi"):
            system = "solfege"
        else:
            await update.message.reply_text("Opción no reconocida. Escribe 'letter' o 'solfege'.")
            return

        try:
            _write_user_system(username, system)
            context.user_data["awaiting_system"] = False
            await update.message.reply_text(f"Sistema almacenado: {system}. Usa /play para continuar practicando.")
        except Exception as e:
            await update.message.reply_text(f"Error guardando la configuración: {e}")
        return

    # If there's no active note, still count unrecognized answers so that
    # two nonsense messages (even before /start) will trigger the help text.
    if not current:
        # Intercept first-layer commands like play / historial / help / start
        cmd = (user_text or "").strip().lstrip('/').lower()
        if cmd in ("play",):
            # second-layer: show play modes
            await update.message.reply_text(_menu_text_play())
            return
        if cmd in ("historial",):
            await update.message.reply_text(_menu_text_historial())
            return
        if cmd in ("help", "start"):
            await help_command(update, context)
            return
        if cmd in ("settings",):
            # Show settings quick menu (language & notation system)
            await update.message.reply_text(_menu_text_settings())
            return

        user_letter_try = normalize_answer(user_text)
        if user_letter_try is None:
            invalid_count = context.user_data.get("invalid_count", 0) + 1
            context.user_data["invalid_count"] = invalid_count
            if invalid_count >= 2:
                context.user_data["invalid_count"] = 0
                await update.message.reply_text(
                    "Demasiadas respuestas no reconocidas. Reiniciando la sesión."
                )
                await help_command(update, context)
                return
            await update.message.reply_text(
                "Escribe '/start' para ver la ayuda."
            )
            return
        else:
            # It's a valid note text but there's no active note
            await update.message.reply_text(
                "Escribe '/start' para ver la ayuda."
            )
            return

    user_letter = normalize_answer(user_text)
    expected_letter = current["letter"]
    pitch = current["pitch"]
    solfege = current["solfege"]

    # If we're in timed mode, compute response time (if possible)
    rec = None
    if context.user_data.get("mode") == "time":
        last_ts = context.user_data.get("last_shown_ts")
        tsec = None
        if last_ts:
            tsec = max(0.0, time.time() - last_ts)
        # If the user took longer than 60 seconds to answer, stop the timed
        # session automatically and save previous records (do not record
        # this last slow attempt).
        if tsec is not None and tsec > 60:
            records = context.user_data.get("session_records", [])
            username = _safe_username_from_update(update)
            if records:
                try:
                    p = _save_session_records(username, records)
                    await update.message.reply_text(f"Sesión guardada en: {p}")
                except Exception as e:
                    await update.message.reply_text(f"Error guardando la sesión: {e}")
            else:
                await update.message.reply_text("Sesión temporizada terminada por inactividad (más de 60s) — no hay datos para guardar.")

            # Clear session state
            context.user_data.pop("session_records", None)
            context.user_data.pop("mode", None)
            context.user_data.pop("current_note", None)
            context.user_data.pop("last_shown_ts", None)
            context.user_data["invalid_count"] = 0
            await help_command(update, context)
            return

        rec = {
            "timestamp": datetime.now().isoformat(),
            "clef": current.get("clef"),
            "letter": current.get("letter"),
            "solfege": current.get("solfege"),
            "correct": None,  # to be filled below
            "time_seconds": tsec,
        }

    if user_letter is None:
        # Increment consecutive invalid counter (per-user)
        invalid_count = context.user_data.get("invalid_count", 0) + 1
        context.user_data["invalid_count"] = invalid_count

        if invalid_count >= 2:
            # Stop the session: if we were in timed mode, save previous records
            if context.user_data.get("mode") == "time":
                records = context.user_data.get("session_records", [])
                username = _safe_username_from_update(update)
                if records:
                    try:
                        p = _save_session_records(username, records)
                        await update.message.reply_text(f"Sesión guardada en: {p}")
                    except Exception as e:
                        await update.message.reply_text(f"Error guardando la sesión: {e}")
                else:
                    await update.message.reply_text("Sesión temporizada terminada — no hay datos para guardar.")

            context.user_data.pop("current_note", None)
            context.user_data["invalid_count"] = 0
            # clear timed session state
            context.user_data.pop("session_records", None)
            context.user_data.pop("mode", None)
            context.user_data.pop("last_shown_ts", None)
            await update.message.reply_text(
                "Demasiadas respuestas no reconocidas. Reiniciando la sesión."
            )
            await help_command(update, context)
            return

        await update.message.reply_text(
            "No he podido interpretar la respuesta. "
            "Escribe solo la nota, por ejemplo: do, re, mi, fa, sol, la, si "
            "o C, D, E, F, G, A, B. (Si esto ocurre dos veces, la sesión se reiniciará con /help.)"
        )
        return

    if user_letter == expected_letter:
        reply = f"Correcto. Es {pitch} ({solfege})."
        correct = True
    else:
        reply = (
            f"No es correcto.\n"
            f"La nota correcta era {pitch} ({solfege})."
        )
        correct = False

    # Reset invalid counter on a valid attempt
    context.user_data["invalid_count"] = 0

    # If timed mode, finalize and store the record
    if context.user_data.get("mode") == "time":
        try:
            rec["correct"] = correct
            context.user_data.setdefault("session_records", []).append(rec)
        except Exception:
            pass

    await update.message.reply_text(reply)
    await send_new_note(update, context)


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================

def main(token: str | None = None):
    """Start Telegram bot using provided token. If token is None, fall back to
    an embedded TELEGRAM_TOKEN if present.
    """
    script_token = globals().get("TELEGRAM_TOKEN")
    use_token = token or script_token
    app = ApplicationBuilder().token(use_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("play", play_menu_command))
    app.add_handler(CommandHandler("free", free_command))
    app.add_handler(CommandHandler("time", time_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("historial", historial_command))
    app.add_handler(CommandHandler("tiempos", tiempos_command))
    app.add_handler(CommandHandler("aciertos", aciertos_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("set_language", set_language_command))
    app.add_handler(CommandHandler("set_system", set_system_command))
    app.add_handler(CommandHandler("old_games", old_games_command))

    # Cualquier texto que no sea comando se interpreta como respuesta a la nota
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

    app.run_polling()


def choose_random_valid_note():
    """Choose a random clef and staff_index that is valid for the note tables."""
    while True:
        clef = random.choice(["treble", "bass"])
        staff_index = random.randint(-2, 12)
        try:
            note_info = get_note_info(clef, staff_index)
            return clef, staff_index, note_info
        except ValueError:
            continue


def local_run(rounds: int | None = None):
    """Run a simple local loop: show figure in a matplotlib window and ask for guesses in the console.

    rounds: optional number of rounds; if None, runs until user quits (enter 'q').
    """
    print("Modo local de Solfeo — escribe 'q' para salir en cualquier momento.")
    print("Escribe 'play', 'historial' o 'settings' para empezar — también puedes usar /play, /historial o /settings en Telegram.")

    username = "local_" + getpass.getuser()
    # Ensure language is configured for local user; ask and store if missing
    lang = _read_user_language(username)
    if not lang:
        print("No se ha configurado el idioma para el modo local.")
        while True:
            choice = input("Introduce el código de idioma que prefieres (ej. 'es' o 'en'): ").strip().lower()
            if not choice:
                continue
            if choice.startswith('es') or choice.startswith('span'):
                lang = 'es'
            elif choice.startswith('en') or choice.startswith('eng'):
                lang = 'en'
            else:
                lang = choice[:2]
            try:
                _write_user_language(username, lang)
                print(f"Idioma almacenado: {lang}")
                break
            except Exception as e:
                print(f"Error guardando la configuración: {e}")
                continue

    played = 0
    invalid_count = 0
    mode = 'free'
    session_records = []
    current_note = None
    last_shown_ts = None

    def show_note_and_display(clef, staff_index, note_info):
        buf = generate_note_image(clef, staff_index)
        img = plt.imread(buf, format="png")
        fig = plt.figure(figsize=(6, 3))
        ax = fig.add_subplot(111)
        ax.imshow(img)
        ax.axis("off")
        try:
            fig.canvas.manager.set_window_title("Solfeo — Adivina la nota")
        except Exception:
            pass
        plt.show(block=False)
        restore_console_focus()
        return fig

    try:
        while True:
            # If there's no active note, wait for a command to start one
            if current_note is None:
                cmd_input = input("local> ").strip()
                if not cmd_input:
                    continue
                # allow slash or plain commands
                raw = cmd_input.lstrip()
                if raw.lower() in ("q", "quit", "exit"):
                    print("Saliendo. Hasta luego.")
                    return

                c = raw.lstrip('/')
                parts = c.split()
                cmd = parts[0].lower()
                args = parts[1:]

                if cmd in ("help", "start"):
                    # /start behaves like help: show top-level menu
                    print()
                    print(_menu_text_main())
                    continue
                if cmd == 'play':
                    print(_menu_text_play())
                    continue

                if cmd == 'free':
                    mode = 'free'
                    session_records = []
                    invalid_count = 0
                    print("Modo libre activado. Mostrando primera nota...")
                    # start immediately: choose and show first note
                    clef, staff_index, note_info = choose_random_valid_note()
                    fig = show_note_and_display(clef, staff_index, note_info)
                    current_note = {
                        'clef': clef,
                        'staff_index': staff_index,
                        'pitch': note_info.get('pitch'),
                        'letter': note_info.get('letter'),
                        'solfege': note_info.get('solfege'),
                        'fig': fig,
                    }
                    last_shown_ts = time.time()
                    continue

                if cmd == 'time':
                    mode = 'time'
                    session_records = []
                    invalid_count = 0
                    print("Modo temporizado activado. Tus tiempos y aciertos se guardarán al usar 'stop'. Mostrando primera nota...")
                    # start immediately: choose and show first note
                    clef, staff_index, note_info = choose_random_valid_note()
                    fig = show_note_and_display(clef, staff_index, note_info)
                    current_note = {
                        'clef': clef,
                        'staff_index': staff_index,
                        'pitch': note_info.get('pitch'),
                        'letter': note_info.get('letter'),
                        'solfege': note_info.get('solfege'),
                        'fig': fig,
                    }
                    last_shown_ts = time.time()
                    continue

                if cmd == 'stop':
                    if mode != 'time':
                        print("No hay una sesión temporizada en curso.")
                        continue
                    username = "local_" + getpass.getuser()
                    try:
                        p = _save_session_records(username, session_records)
                        print(f"Sesión guardada en: {p}")
                    except Exception as e:
                        print(f"Error guardando la sesión: {e}")
                    mode = 'free'
                    session_records = []
                    invalid_count = 0
                    continue

                if cmd == 'historial':
                    print(_menu_text_historial())
                    continue

                if cmd == 'settings':
                    # Show settings options for local user
                    print(_menu_text_settings())
                    continue

                if cmd == 'set_language':
                    try:
                        plt.close(current_note.get('fig'))
                    except Exception:
                        pass
                    new = input("Introduce el código de idioma que prefieres (ej. 'es' o 'en'): ").strip().lower()
                    if not new:
                        print("No se recibió el idioma. Cancelado.")
                        continue
                    if new.startswith('es') or new.startswith('span'):
                        lang = 'es'
                    elif new.startswith('en') or new.startswith('eng'):
                        lang = 'en'
                    else:
                        print("Opción no válida. Usa 'es' o 'en'.")
                        continue
                    try:
                        _write_user_language(username, lang)
                        print(f"Idioma almacenado: {lang}")
                    except Exception as e:
                        print(f"Error guardando la configuración: {e}")
                    continue

                if cmd == 'set_system':
                    try:
                        plt.close(current_note.get('fig'))
                    except Exception:
                        pass
                    sys_choice = input("¿Qué sistema de notación prefieres? ('letter' o 'solfege'): ").strip().lower()
                    if not sys_choice:
                        print("No se recibió sistema. Cancelado.")
                        continue
                    if sys_choice.startswith('let') or sys_choice in ('abc', 'letters'):
                        system = 'letter'
                    elif sys_choice.startswith('sol') or sys_choice in ('solfege', 'solfeo'):
                        system = 'solfege'
                    else:
                        print("Opción no válida. Responde 'letter' o 'solfege'.")
                        continue
                    try:
                        _write_user_system(username, system)
                        print(f"Sistema almacenado: {system}")
                    except Exception as e:
                        print(f"Error guardando la configuración: {e}")
                    continue

                if cmd == 'old_games':
                    username = "local_" + getpass.getuser()
                    n = 5
                    if args:
                        try:
                            n = max(1, int(args[0]))
                        except Exception:
                            n = 5
                    files = _list_user_sessions(username)[:n]
                    if not files:
                        print("No hay sesiones guardadas para este usuario.")
                    else:
                        print(f"Últimas {len(files)} sesiones:")
                        for p in files:
                            print(p.name)
                    continue

                if cmd == 'tiempos':
                    username = "local_" + getpass.getuser()
                    n = 1
                    if args:
                        try:
                            n = max(1, int(args[0]))
                        except Exception:
                            n = 1
                    files = _list_user_sessions(username)[:n]
                    combined = []
                    for p in files:
                        combined.extend(_read_session_csv(p))
                    if not combined:
                        print("No hay datos para generar graficas.")
                    else:
                        bufp = _make_time_plot(combined)
                        img2 = plt.imread(bufp, format='png')
                        fig2 = plt.figure(figsize=(8,6))
                        ax2 = fig2.add_subplot(111)
                        ax2.imshow(img2)
                        ax2.axis('off')
                        plt.show(block=False)
                        restore_console_focus()
                    continue

                if cmd == 'aciertos':
                    username = "local_" + getpass.getuser()
                    n = 1
                    if args:
                        try:
                            n = max(1, int(args[0]))
                        except Exception:
                            n = 1
                    files = _list_user_sessions(username)[:n]
                    combined = []
                    for p in files:
                        combined.extend(_read_session_csv(p))
                    if not combined:
                        print("No hay datos para generar graficas.")
                    else:
                        bufp = _make_success_plot(combined)
                        img2 = plt.imread(bufp, format='png')
                        fig2 = plt.figure(figsize=(8,6))
                        ax2 = fig2.add_subplot(111)
                        ax2.imshow(img2)
                        ax2.axis('off')
                        plt.show(block=False)
                        restore_console_focus()
                    continue

                # Unknown input when no note is active
                user_letter_try = normalize_answer(cmd_input)
                if user_letter_try is None:
                    invalid_count += 1
                    if invalid_count >= 2:
                        print("Demasiadas respuestas no reconocidas. Mostrando ayuda.")
                        print()
                        print(_menu_text_main())
                        invalid_count = 0
                    else:
                        print("Escribe '/start' para ver la ayuda.")
                    continue

            # If we reach here, current_note is active and we should prompt for a guess
            # current_note is a dict with keys: clef, staff_index, pitch, letter, solfege, fig
            prompt = "¿Qué nota es esta? (do/re/mi... o C/D/...) > "
            user_text = input(prompt)

            # Commands handling during an active note (allow slash or plain)
            if not user_text.strip():
                continue
            raw = user_text.lstrip()
            if raw.lower() in ("q", "quit", "exit"):
                try:
                    plt.close(current_note.get('fig'))
                except Exception:
                    pass
                print("Saliendo. Hasta luego.")
                return

            if raw.startswith('/'):
                c = raw.lstrip('/')
            else:
                c = raw
            parts = c.split()
            cmd = parts[0].lower()
            args = parts[1:]

            # handle the same commands as above when note is active
            if cmd in ("help",):
                print()
                print(
                    "Instrucciones:\n\n"
                    "• Usa 'play' para comenzar una práctica (elige 'free' o 'time').\n"
                    "• Cada imagen muestra una nota en clave de SOL o de FA.\n"
                    "• Responde con el nombre de la nota (do, re, mi, fa, sol, la, si) "
                    "o con letras (C, D, E, F, G, A, B).\n"
                    "• No es necesario indicar la octava.\n"
                )
                continue

            if cmd in ('free', 'time', 'stop', 'historial', 'tiempos', 'aciertos', 'settings'):
                # Close current figure and delegate to the non-active-note logic by
                # clearing current_note and letting the outer loop handle the command
                try:
                    plt.close(current_note.get('fig'))
                except Exception:
                    pass
                # reset current_note so outer loop will accept the command
                current_note = None
                # push the command back into the input stream by simulating it
                # we simply continue so the next loop iteration will prompt and the user
                # can re-enter the command (simpler than programmatically re-invoking)
                continue

            # Regular guess handling
            user_letter = normalize_answer(user_text)
            expected_letter = current_note.get('letter')
            pitch = current_note.get('pitch')
            solfege = current_note.get('solfege')

            if user_letter is None:
                invalid_count += 1
                if invalid_count >= 2:
                    print("Demasiadas respuestas no reconocidas. Reiniciando la sesión.")
                    print()
                    print(_menu_text_main())
                    # If timed session, save before exiting
                    if mode == 'time' and session_records:
                        username = "local_" + getpass.getuser()
                        try:
                            p = _save_session_records(username, session_records)
                            print(f"Sesión guardada en: {p}")
                        except Exception as e:
                            print(f"Error guardando la sesión: {e}")
                    return
                else:
                    print("No he podido interpretar la respuesta. Escribe por ejemplo: do, re, mi o C, D, E.")
                    continue

            # Reset invalid counter on any recognized attempt
            invalid_count = 0
            if user_letter == expected_letter:
                print(f"Correcto. Es {pitch} ({solfege}).")
                correct = True
            else:
                print(f"No es correcto. La nota correcta era {pitch} ({solfege}).")
                correct = False

            # If in timed mode, record result with accurate timing
            if mode == 'time':
                try:
                    tsec = max(0.0, time.time() - last_shown_ts)
                except Exception:
                    tsec = 0.0
                # If the user took longer than 60 seconds to answer,
                # stop the timed session automatically and do NOT record
                # this slow attempt.
                if tsec is not None and tsec > 60:
                    username = "local_" + getpass.getuser()
                    if session_records:
                        try:
                            p = _save_session_records(username, session_records)
                            print(f"Sesión guardada en: {p}")
                        except Exception as e:
                            print(f"Error guardando la sesión: {e}")
                    else:
                        print("Sesión temporizada terminada por inactividad (más de 60s) — no hay datos para guardar.")
                    mode = 'free'
                    session_records = []
                    invalid_count = 0
                    try:
                        plt.close(current_note.get('fig'))
                    except Exception:
                        pass
                    current_note = None
                    continue

                session_records.append({
                    'timestamp': datetime.now().isoformat(),
                    'clef': current_note.get('clef'),
                    'letter': current_note.get('letter'),
                    'solfege': current_note.get('solfege'),
                    'correct': correct,
                    'time_seconds': tsec,
                })

            played += 1

            # After answering, automatically show the next note
            try:
                plt.close(current_note.get('fig'))
            except Exception:
                pass
            # choose and show next
            clef, staff_index, note_info = choose_random_valid_note()
            fig = show_note_and_display(clef, staff_index, note_info)
            current_note = {
                'clef': clef,
                'staff_index': staff_index,
                'pitch': note_info.get('pitch'),
                'letter': note_info.get('letter'),
                'solfege': note_info.get('solfege'),
                'fig': fig,
            }
            last_shown_ts = time.time()

    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario. Adiós.")
        return


def parse_args_and_run():
    parser = argparse.ArgumentParser(description="Solfeo bot runner — local mode by default; use --telegram to run the Telegram bot")
    parser.add_argument(
        "--telegram",
        action="store_true",
        help="Run as Telegram bot (requires this flag). By default the script runs in local interactive mode.",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=None,
        help="Number of rounds to play in local mode (default: infinite until 'q').",
    )
    args = parser.parse_args()

    if args.telegram:
        # Load token from file (create template if missing). If no token is found
        # in the file, and there is a non-empty TELEGRAM_TOKEN in the script, we
        # will warn and use that as a fallback. Otherwise, instruct the user to
        # add the token to telegram_token.txt and exit.
        token_from_file = _load_or_create_telegram_token()
        if token_from_file:
            main(token=token_from_file)
            return

        # No token in file: check whether the script still defines a token
        script_token = globals().get("TELEGRAM_TOKEN")
        if script_token and str(script_token).strip():
            print(
                "Warning: 'telegram_token.txt' did not contain a token. Using the token embedded in the script as a fallback.\n"
                "For better security, please place your token in 'telegram_token.txt' (non-comment line) and re-run."
            )
            main(token=script_token)
            return

        print(
            "A token was not found. A template file 'telegram_token.txt' has been created in the current directory.\n"
            "Open it and paste your bot token on a non-commented line, save, and re-run with --telegram."
        )
        return
    else:
        # Run the local interactive loop (default)
        local_run(rounds=args.rounds)


if __name__ == "__main__":
    parse_args_and_run()
