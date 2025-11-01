import webview, requests, subprocess, time, os

def get_content(url):
    response = requests.get(url)
    if response.status_code == 200:
        contenu = response.text
        return contenu

window = webview.create_window(
    "Updater",
    "update.html",
    width=800,
    height=480,
    frameless=True,
    resizable=False
)

webview.start()

with open("app.py", "w") as f:
    f.write(get_content("https://raw.githubusercontent.com/Grivy16/Vocal-assistante/refs/heads/main/app.py"))

with open("index.html", "w") as f:
    f.write(get_content("https://raw.githubusercontent.com/Grivy16/Vocal-assistante/refs/heads/main/index.html"))

with open("script.js", "w") as f:
    f.write(get_content("https://raw.githubusercontent.com/Grivy16/Vocal-assistante/refs/heads/main/script.js"))

with open("style.css", "w") as f:
    f.write(get_content("https://raw.githubusercontent.com/Grivy16/Vocal-assistante/refs/heads/main/style.css"))

time.sleep(2)

subprocess.Popen(["python", "app.py"])
os._exit(0)