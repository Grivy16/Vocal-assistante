import webview
import requests
import subprocess
import time
import os
import json
import threading

def get_content(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def update_files():
    try:
        # 🔄 Mise à jour
        print("Mise à jour en cours...")

        # Écriture des fichiers avec UTF-8
        files_to_update = {
            "app.py": "https://raw.githubusercontent.com/Grivy16/Vocal-assistante/refs/heads/main/app.py",
            "index.html": "https://raw.githubusercontent.com/Grivy16/Vocal-assistante/refs/heads/main/index.html",
            "script.js": "https://raw.githubusercontent.com/Grivy16/Vocal-assistante/refs/heads/main/script.js",
            "style.css": "https://raw.githubusercontent.com/Grivy16/Vocal-assistante/refs/heads/main/style.css"
        }

        for filename, url in files_to_update.items():
            content = get_content(url)
            with open(filename, "w", encoding="utf-8", newline='') as f:
                f.write(content)
            print(f"{filename} mis à jour.")

        # Mettre à jour la version dans data.json
        version_url = "https://raw.githubusercontent.com/Grivy16/Vocal-assistante/main/version.json"
        response = requests.get(version_url)
        response.raise_for_status()
        data2 = response.json()

        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        data["version"] = data2.get("version", data.get("version", "1.0"))
        with open("data.json", "w", encoding="utf-8", newline='') as f:
            json.dump(data, f, indent=4)
        print("data.json mis à jour.")

        time.sleep(2)

        # Lancer app.py en arrière-plan sans console et avec log
        log_file = os.path.join(os.getcwd(), "log.txt")
        with open(log_file, "w", encoding="utf-8") as f:
            subprocess.Popen(
                ["python", "app.py"],
                stdout=f,
                stderr=f,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

        print("Application relancée. Fermeture du programme updater...")
        window.destroy()
        os._exit(0)

    except Exception as e:
        print("Erreur lors de la mise à jour :", e)
        window.destroy()
        os._exit(1)

# Crée la fenêtre WebView
window = webview.create_window(
    "Updater",
    "update.html",
    width=800,
    height=480,
    frameless=True,
    resizable=False
)

# Démarre la mise à jour dans un thread pour que WebView puisse s'afficher
threading.Thread(target=update_files, daemon=True).start()

webview.start()
