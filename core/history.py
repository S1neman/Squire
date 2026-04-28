import sqlite3
import os
from datetime import datetime
from core.paths import DATA_DIR, TRANSCRIPTS_DIR, SUMMARIES_DIR

# БД
DB_PATH = os.path.join(DATA_DIR, 'history.db')

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    os.makedirs(SUMMARIES_DIR, exist_ok=True)

def init_db():
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  duration_sec REAL,
                  mode TEXT,
                  mic_device TEXT,
                  sys_device TEXT,
                  transcript TEXT,
                  summary TEXT)''')
    conn.commit()
    conn.close()

def save_session(mode, mic_dev, sys_dev, transcript, summary, duration=0):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO sessions (timestamp, duration_sec, mode, mic_device, sys_device, transcript, summary)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (datetime.now().isoformat(), duration, mode, mic_dev, sys_dev, transcript, summary))
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    return session_id

def get_all_sessions():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, timestamp, duration_sec, mode, transcript, summary FROM sessions ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    return rows

def update_session_transcript(session_id, transcript):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE sessions SET transcript = ? WHERE id = ?', (transcript, session_id))
    conn.commit()
    conn.close()

def update_session_summary(session_id, summary):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE sessions SET summary = ? WHERE id = ?', (summary, session_id))
    conn.commit()
    conn.close()

# Функции для работы с txt-файлами

def save_transcript_to_file(session_id, transcript_text):
    """Сохраняет расшифровку в файл data/transcripts/session_<id>.txt"""
    ensure_dirs()
    filepath = os.path.join(TRANSCRIPTS_DIR, f"session_{session_id}.txt")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(transcript_text)

def save_summary_to_file(session_id, summary_text):
    """Сохраняет саммари в файл data/summaries/session_<id>_summary.txt"""
    ensure_dirs()
    filepath = os.path.join(SUMMARIES_DIR, f"session_{session_id}_summary.txt")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(summary_text)

def load_transcript_from_file(session_id):
    """Загружает расшифровку из txt-файла, если он существует"""
    filepath = os.path.join(TRANSCRIPTS_DIR, f"session_{session_id}.txt")
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def load_summary_from_file(session_id):
    """Загружает саммари из txt-файла, если он существует"""
    filepath = os.path.join(SUMMARIES_DIR, f"session_{session_id}_summary.txt")
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def delete_session(session_id):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    transcript_file = os.path.join(TRANSCRIPTS_DIR, f"session_{session_id}.txt")
    summary_file = os.path.join(SUMMARIES_DIR, f"session_{session_id}_summary.txt")
    if os.path.exists(transcript_file):
        os.remove(transcript_file)
    if os.path.exists(summary_file):
        os.remove(summary_file)