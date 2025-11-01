import webview
import threading
import time
import speech_recognition as sr
import openai
import uuid
import os
import json
from difflib import SequenceMatcher
import shutil
from difflib import SequenceMatcher
import subprocess
import requests
import sys

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

# 🔑 Ta clé OpenAI
openai.api_key = ""  # Remplace par ta clé

class Assistant:
    def __init__(self, window):
        self.window = window
        self.SILENCE_LIMIT = 0.5
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        self.listening_command = False
        self.phrase = ""
        self.last_speech_time = None
        self.stop_listening = None
        self._mic_lock = threading.Lock()
        self._mic_active = False  # ← NOUVEAU : flag pour savoir si le micro tourne
        self.is_speaking = False
        self.fichier = "data.json"
        self.ancienne_question = ""
        self.data = {
            "api_key": "",
            "keyword": "hey", 
            "voice": "nova",
            "version": "1.0"
        }
        if not os.path.exists(self.fichier):
            with open(self.fichier, "w") as f:
                json.dump(self.data, f, indent=4)

        with open(self.fichier, "r") as f:
            self.data = json.load(f)
            openai.api_key = self.data.get("api_key", "")
            self.TRIGGER = self.data.get("keyword", "hey").lower()
            self.voice = self.data.get("voice", "nova")
            self.version = self.data.get("version", "1.0")
            print(f"[DEBUG] Trigger initial : {self.TRIGGER}")

        threading.Thread(target=self.check_maj, daemon=True).start()

    def check_maj(self):
        while True:
            url = "https://raw.githubusercontent.com/Grivy16/Vocal-assistante/main/version.json"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            print(data)
            
            if data["version"] > self.version:
                print("🔔 Nouvelle version disponible :", data["version"])
                self._call_js_func("showUpdateAvailable")
            time.sleep(6800)

    def update(self):
        url = "https://raw.githubusercontent.com/Grivy16/Vocal-assistante/main/version.json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if data["version"] > self.version:
            file_input = "update"
            current_dir = os.path.dirname(os.path.abspath(__file__))
            possible_files = [f"{file_input}.py", f"{file_input}.exe"]
            found_file = None
            
            # Cherche le fichier update
            for f in possible_files:
                path = os.path.join(current_dir, f)
                if os.path.isfile(path):
                    found_file = path
                    break
            
            if not found_file:
                print(f"Aucun fichier trouvé pour : {file_input}")
                return  # On ne quitte pas le programme si pas de fichier update
            
            base_name, ext = os.path.splitext(os.path.basename(found_file))
            print(f"Nom du fichier trouvé : {base_name}, extension : {ext}")
            
            try:
                # Lancer le fichier update dans un nouveau processus
                if ext.lower() == ".exe":
                    subprocess.Popen([found_file], close_fds=True)
                elif ext.lower() == ".py":
                    subprocess.Popen([sys.executable, found_file], close_fds=True)
                else:
                    print(f"Extension non supportée : {ext}")
                    return
                
                print("[INFO] Update lancé, fermeture de l'application...")
                # Fermer le micro proprement
                self.stop_microphone()
                # Quitter complètement l'application
                os._exit(0)

            except Exception as e:
                print(f"[ERREUR] Impossible de lancer l'update : {e}")


    def restart_pi(self):
        try :
            print("🔄 Redémarrage du Raspberry Pi...")
            subprocess.run(["sudo", "reboot"], check=True)
        except subprocess.CalledProcessError: 
            self._call_js_func("showplateformError")

    def shutdown_pi(self):
        try :
            print("⏻ Extinction du Raspberry Pi...")
            subprocess.run(["sudo", "shutdown", "now"], check=True)
        except subprocess.CalledProcessError: 
            self._call_js_func("showplateformError")    

    def get_api_key(self):
        with open(self.fichier, "r") as f:
            self.data = json.load(f)
        return self.data.get("api_key", "")

    def get_keyword(self):
        with open(self.fichier, "r") as f:
            self.data = json.load(f)
        return self.data.get("keyword", "hey").lower()

    def get_voice(self):
        with open(self.fichier, "r") as f:
            self.data = json.load(f)
        return self.data.get("voice", "nova")

    def change_voice(self, text):
        self.data["voice"] = text
        self.voice = text
        with open(self.fichier, "w") as f:
            json.dump(self.data, f, indent=4)

    def change_api(self, text):
        self.data["api_key"] = text
        openai.api_key = text
        with open(self.fichier, "w") as f:
            json.dump(self.data, f, indent=4)
    
    def change_keyword(self, text):
        self.data["keyword"] = text
        self.TRIGGER = text
        with open(self.fichier, "w") as f:
            json.dump(self.data, f, indent=4)

    def callback(self, recognizer, audio):
        try:
            text = recognizer.recognize_google(audio, language="fr-FR").lower()
        except sr.UnknownValueError:
            return
        except sr.RequestError as e:
            print(f"Erreur API : {e}")
            return

        if not self.listening_command:
            self.listening_command = True
            self.phrase = text
            self.last_speech_time = time.time()
            self.window.evaluate_js("startListening()")
        else:
            self.phrase += " " + text
            self.last_speech_time = time.time()
            print(f"[DEBUG] Collecte : {text}")

    def jouer_audio(self, file_path):
        self.window.evaluate_js("showSpeaking()")
        self.window.evaluate_js(f"playAudioFile('{file_path}')")
        
        def supprimer_fichier():
            time.sleep(15)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"[DEBUG] Fichier supprimé : {file_path}")
                    self.ancienne_question = ""
            except Exception as e:
                print(f"[DEBUG] Erreur suppression fichier : {e}")

        threading.Thread(target=supprimer_fichier, daemon=True).start()
        

    def _safe_eval_js(self, code):
        try:
            self.window.evaluate_js(code)
        except Exception as e:
            print("[DEBUG] evaluate_js failed:", e)

    def _call_js_func(self, name, *args):
        js_args = ",".join(json.dumps(a) for a in args)
        self._safe_eval_js(f"{name}({js_args})")

    def show_api_error(self):
        self._call_js_func("showApiError")

    def show_network_error(self):
        self._call_js_func("showNetworkError")

    def show_tts_error(self):
        self._call_js_func("showTtsError")

    def show_mic_error(self):
        self._call_js_func("showMicError")

    def show_general_error(self, message="Une erreur est survenue."):
        self._call_js_func("showGeneralError", message)
    def show_param_error(self):
        self._call_js_func("showParamError")

    def send_to_ai(self, prompt):
        try:
            self.window.evaluate_js("showThinking()")

            completion = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"Tu es un assistant vocal utile et amical. tu peux recevoir en début de phrase des mot comme hey google qui sont les Trigger pour te parler ou si tu recois dans chose qui peuvent recembler a ca :{self.TRIGGER} (exemple hey chat qui deviient éclater) est bien n'en tien pas compte"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            texte = completion.choices[0].message.content
            texte = texte.replace('. ', ' ')
            print("IA :", texte)

            tts_response = openai.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice=self.voice,
                input=texte
            )

            filename = f"reply_{uuid.uuid4().hex}.mp3"
            with open(filename, "wb") as f:
                f.write(tts_response.read())

            self.jouer_audio(filename)
        except openai.AuthenticationError:
            print("[ERREUR] Clé API invalide ou manquante.")
            print(openai.api_key)
            self.show_api_error()
            return
        except openai.APIConnectionError:
            print("[ERREUR] Problème de connexion réseau.")
            self.show_network_error()
            return
        except openai.OpenAIError as e: 
            print(f"[ERREUR] Erreur OpenAI : {e}")
            self.show_general_error(f"Erreur OpenAI : {e}")
            return
        except Exception as e:
            print(f"[ERREUR] Erreur inattendue : {e}")
            self.show_general_error(f"Error : {e}")
            return

    def run(self):
        # Ajuste le bruit ambiant une seule fois
        with self._mic_lock:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source)

        # Démarre l'écoute
        self.start_microphone()

        try:
            while True:
                time.sleep(0.1)
                if self.listening_command and self.last_speech_time:
                    if time.time() - self.last_speech_time > self.SILENCE_LIMIT:
                        final_phrase = self.phrase.strip()
                        if final_phrase:
                            if final_phrase != self.ancienne_question or "":
                                self.ancienne_question = final_phrase
                                print("Moi :", final_phrase)

                                # Séparer en mots
                                words = final_phrase.lower().split()

                                # Vérifier si le trigger est "assez proche" du début
                                # Si trigger vide → répondre à tout
                                if not self.TRIGGER or self.TRIGGER.strip() == "":
                                    print("[DEBUG] TRIGGER vide → envoie directement à l'IA")
                                    self.send_to_ai(final_phrase)
                                    continue

                                trigger_detected = False
                                cleaned_phrase = final_phrase

                                for w in words[:2]:
                                    if similar(self.TRIGGER, w) > 0.75:
                                        trigger_detected = True
                                        cleaned_phrase = final_phrase.lower().replace(w, "").strip()
                                        print(f"[DEBUG] Trigger fuzzy détecté : {w}")
                                        break

                                if trigger_detected:
                                    print(f"[DEBUG] Message envoyé à l'IA : {cleaned_phrase}")
                                    self.send_to_ai(cleaned_phrase)
                                else:
                                    print("[DEBUG] Aucun trigger détecté → ignore")


                        self.listening_command = False
                        self.last_speech_time = None
                        self.phrase = ""
        except KeyboardInterrupt:
            self.stop_microphone()
            print("\nArrêt demandé. Bye 👋")

    def stop_microphone(self):
        with self._mic_lock:
            if not self._mic_active:
                print("[INFO] Micro déjà arrêté")
                return
            
            if self.stop_listening:
                try:
                    self.stop_listening(wait_for_stop=False)
                    # ← IMPORTANT : attendre un peu que le thread se termine
                    time.sleep(0.3)
                    self.stop_listening = None
                    self._mic_active = False
                    print("[INFO] Micro arrêté")
                except Exception as e:
                    print("[ERREUR] Impossible d'arrêter le micro :", e)

    def start_microphone(self):
        with self._mic_lock:
            if self._mic_active:
                print("[INFO] Micro déjà actif, aucun nouveau thread lancé")
                return
            
            try:
                print("[INFO] Démarrage du micro...")
                
                # ← RECRÉER un nouveau Microphone pour éviter le conflit de contexte
                self.mic = sr.Microphone()
                
                self.stop_listening = self.recognizer.listen_in_background(
                    self.mic, self.callback, phrase_time_limit=5
                )
                self._mic_active = True
                print("[INFO] Micro démarré avec succès")
            except Exception as e:
                print(f"[ERREUR] Impossible de démarrer le micro : {e}")
                self._mic_active = False
                self.show_param_error()

    def get_stockage(self, path: str = None):
        try:
            if path is None:
                drive = os.getenv("SystemDrive")
                path = (drive + os.sep) if drive else os.path.abspath(os.sep)

            usage = shutil.disk_usage(path)
            total = usage.total
            free = usage.free
            used = total - free
            percent = round((used / total) * 100, 2) if total else 0.0

            print(f"[DEBUG] get_stockage -> path={path} total={total} used={used} free={free} percent={percent}")

            def _hr(n):
                for unit in ['B','KB','MB','GB','TB']:
                    if n < 1024:
                        return f"{n:.2f} {unit}"
                    n /= 1024
                return f"{n:.2f} PB"

            return {
                "path": path,
                "total": total,
                "used": used,
                "free": free,
                "percent": percent,
                "total_hr": _hr(total),
                "used_hr": _hr(used),
                "free_hr": _hr(free)
            }
        except Exception as e:
            print("[ERREUR] get_stockage:", e)
            return {"path": path or "", "total": 0, "used": 0, "free": 0, "percent": 0.0, "error": str(e)}


if __name__ == "__main__":
    window = webview.create_window("Vocal Assistant", "index.html", width=800, height=480, frameless=True, resizable=False)
    assistant = Assistant(window)

    window.expose(assistant.stop_microphone)
    window.expose(assistant.start_microphone)
    window.expose(assistant.change_api)
    window.expose(assistant.get_api_key)
    window.expose(assistant.change_keyword)
    window.expose(assistant.get_keyword)
    window.expose(assistant.get_stockage)
    window.expose(assistant.change_voice)
    window.expose(assistant.get_voice)
    window.expose(assistant.shutdown_pi)
    window.expose(assistant.restart_pi)
    window.expose(assistant.update)

    threading.Thread(target=assistant.run, daemon=True).start()
    webview.start()