import importlib
import subprocess
import sys
import os

def ensure_package(package_name, pip_name=None):
    pip_name = pip_name or package_name
    try:
        importlib.import_module(package_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])

# Exemple : installer les paquets si manquants
ensure_package("speech_recognition", "SpeechRecognition")
ensure_package("openai")
ensure_package("webview", "pywebview")

si = subprocess.STARTUPINFO()
si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
si.wShowWindow = subprocess.SW_HIDE

subprocess.run("install_python.bat", startupinfo=si)

# Lancer l'application en arrière-plan et log
log_file = os.path.join(os.getcwd(), "log.txt")
with open(log_file, "w", encoding="utf-8") as f:
    subprocess.Popen(
        [sys.executable, "app.py"],
        stdout=f,
        stderr=f,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
