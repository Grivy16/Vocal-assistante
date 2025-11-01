import webview, requests, subprocess, time, os, json

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

url = "https://raw.githubusercontent.com/Grivy16/Vocal-assistante/main/version.json"
response = requests.get(url)
response.raise_for_status()
data2 = response.json()

with open("data.json", "r") as f:
    data = json.load(f)
    data["version"] = data2["version"]
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)

time.sleep(2)

subprocess.Popen(["start", "cmd", "/k", "python", "app.py"], shell=True)
window.destroy()
os._exit(0)