import subprocess
import sys
import time
import requests

# Проверка сервера ollama
def is_ollama_running():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

def kill_ollama():
    print("[DEBUG] Killing existing Ollama processes...")
    subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"], capture_output=True)
    time.sleep(1)

def start_ollama():
    print("[DEBUG] Starting Ollama...")
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
    subprocess.Popen(
        ["ollama", "serve"],
        startupinfo=startupinfo,
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(3)

def ensure_ollama_running(callback=None):
    print("[DEBUG] ensure_ollama_running called")
    if is_ollama_running():
        print("[DEBUG] Ollama is already responding")
        if callback:
            callback(True)
        return True

    print("[DEBUG] Ollama not responding, killing existing process and restarting...")
    kill_ollama()
    start_ollama()

    # Проверяем в течение 5 секунд
    for i in range(5):
        print(f"[DEBUG] Checking if Ollama started (attempt {i+1}/5)...")
        time.sleep(1)
        if is_ollama_running():
            print("[DEBUG] Ollama started successfully")
            if callback:
                callback(True)
            return True

    print("[DEBUG] Failed to start Ollama")
    if callback:
        callback(False)
    return False