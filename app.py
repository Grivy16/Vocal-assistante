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
import subprocess
import requests
import sys
sys.stdout.reconfigure(encoding='utf-8')

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

openai.api_key = ""

class Assistant:
    def __init__(self, window):
        self.window = window
        # MODIFICATION : Augmenter le temps de silence pour mieux capter les phrases
        self.SILENCE_LIMIT = 1.5  # ← Augmenté à 1.5 seconde
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        
        # NOUVEAU : Configurer le recognizer pour plus de sensibilité
        self.recognizer.energy_threshold = 300  # ← Seuil d'énergie très bas
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8   # ← Temps d'attente plus court
        
        self.listening_command = False
        self.phrase = ""
        self.last_speech_time = None
        self.stop_listening = None
        self._mic_lock = threading.Lock()
        self._mic_active = False
        self.is_speaking = False
        self.fichier = "data.json"
        self.ancienne_question = ""
        self.conversation_history = []
        self.max_history_length = 10
        
        # ========== CONFIGURATION CENTRALISÉE DES SETTINGS ==========
        # Pour ajouter un nouveau setting, il suffit d'ajouter une ligne ici !
        self.settings_config = {
            "api_key": {"default": "", "attr": "api_key"},
            "keyword": {"default": "maxt", "attr": "TRIGGER", "transform": lambda x: x.lower()},
            "voice": {"default": "nova", "attr": "voice"},
            "mode": {"default": "Voice", "attr": "mode"},
            "version": {"default": "1.0", "attr": "version", "readonly": True},
            "name": {"default": "", "attr": "name"},
            "job": {"default": "", "attr": "job"},
            "other": {"default": "", "attr": "other"},
            "test": {"default": "", "attr": "test"}
        }
        
        self.load_settings()
        threading.Thread(target=self.check_maj, daemon=True).start()

    # ========== GESTION CENTRALISÉE DES SETTINGS ==========
    
    def load_settings(self):
        """Charge tous les settings depuis le fichier JSON avec vérification automatique"""
        # Configuration des settings avec leurs valeurs par défaut
        default_data = {key: config["default"] for key, config in self.settings_config.items()}
        
        # Créer le fichier avec valeurs par défaut s'il n'existe pas
        if not os.path.exists(self.fichier):
            with open(self.fichier, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
            self.data = default_data.copy()
        else:
            # Charger les données existantes
            try:
                with open(self.fichier, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                print(f"[ERREUR] Lecture data.json: {e}, utilisation des valeurs par défaut")
                self.data = default_data.copy()
            
            # Vérifier et corriger les clés
            data_modified = False
            
            # Ajouter les clés manquantes
            for key in default_data:
                if key not in self.data:
                    self.data[key] = default_data[key]
                    print(f"[DEBUG] Clé ajoutée: {key} = {default_data[key]}")
                    data_modified = True
            
            # Supprimer les clés obsolètes
            keys_to_remove = []
            for key in self.data:
                if key not in default_data:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.data[key]
                print(f"[DEBUG] Clé obsolète supprimée: {key}")
                data_modified = True
            
            # Sauvegarder si modifications
            if data_modified:
                try:
                    with open(self.fichier, "w", encoding="utf-8") as f:
                        json.dump(self.data, f, indent=4)
                    print("[DEBUG] data.json corrigé et sauvegardé")
                except Exception as e:
                    print(f"[ERREUR] Sauvegarde data.json: {e}")

        # Appliquer les valeurs aux attributs avec gestion des valeurs vides
        for key, config in self.settings_config.items():
            value = self.data.get(key, config["default"])
            
            # Si la valeur est vide, utiliser la valeur par défaut pour l'attribut
            if value == "" or value is None:
                attr_value = config["default"]
            else:
                attr_value = value
                
            # Appliquer la transformation si définie
            if "transform" in config:
                attr_value = config["transform"](attr_value)
            
            # Setter l'attribut
            if "attr" in config:
                setattr(self, config["attr"], attr_value)

        # Cas spécial : API key pour OpenAI
        openai.api_key = self.api_key

        print(f"[DEBUG] Settings chargés : Trigger={self.TRIGGER}, Mode={self.mode}, Voice={self.voice}")

    def save_settings(self):
        """Sauvegarde tous les settings dans le fichier JSON"""
        with open(self.fichier, "w") as f:
            json.dump(self.data, f, indent=4)

    def get_setting(self, key):
        """Récupère une valeur de setting"""
        config = self.settings_config.get(key)
        if not config:
            return None
        return self.data.get(key, config["default"])

    def set_setting(self, key, value):
        """Modifie une valeur de setting"""
        config = self.settings_config.get(key)
        if not config:
            print(f"[ERREUR] Setting inconnu : {key}")
            return
        
        if config.get("readonly", False):
            print(f"[ERREUR] Setting en lecture seule : {key}")
            return
        
        # Appliquer la transformation si définie
        if "transform" in config:
            value = config["transform"](value)
        
        # Modifier le data
        self.data[key] = value
        
        # Modifier l'attribut
        if "attr" in config:
            setattr(self, config["attr"], value)
        
        # Cas spécial : API key pour OpenAI
        if key == "api_key":
            openai.api_key = value
        
        # Sauvegarder
        self.save_settings()
        print(f"[DEBUG] Setting '{key}' modifié : {value}")

    # ========== MÉTHODES GET/SET EXPOSÉES À JS ==========
    
    def get_api_key(self):
        return self.get_setting("api_key")
    
    def change_api(self, text):
        self.set_setting("api_key", text)
    
    def get_keyword(self):
        return self.get_setting("keyword")
    
    def change_keyword(self, text):
        self.set_setting("keyword", text)
    
    def get_voice(self):
        return self.get_setting("voice")
    
    def change_voice(self, text):
        self.set_setting("voice", text)
    
    def get_mode(self):
        return self.get_setting("mode")
    
    def change_mode(self, text):
        self.set_setting("mode", text)

    def get_status(self):
        return self.mode
    
    def get_name(self):
        return self.get_setting("name")

    def change_name(self, text):
        self.set_setting("name", text)

    def get_job(self):
        return self.get_setting("job")

    def change_job(self, text):
        self.set_setting("job", text)

    def get_other(self):
        return self.get_setting("other")

    def change_other(self, text):
        self.set_setting("other", text)

    # ========== RESTE DU CODE ==========

    def check_maj(self):
        while True:
            try:
                url = "https://raw.githubusercontent.com/Grivy16/Vocal-assistante/main/version.json"
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                print(data)
                
                if data["version"] > self.version:
                    print("🔔 Nouvelle version disponible :", data["version"])
                    self._call_js_func("showUpdateAvailable")
            except Exception as e:
                print(f"[ERREUR] Vérification MAJ : {e}")
            time.sleep(6800)

    def update(self):
        try:
            url = "https://raw.githubusercontent.com/Grivy16/Vocal-assistante/main/version.json"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if data["version"] > self.version:
                try:
                    with open("log.txt", "w", encoding="utf-8") as f:
                        subprocess.Popen(["python", "update.py"], stdout=f, stderr=f, creationflags=subprocess.CREATE_NO_WINDOW)

                    self.stop_microphone()
                    self.window.destroy()
                    os._exit(0)

                except Exception as e:
                    print(f"[ERREUR] Impossible de lancer l'update : {e}")
        except Exception as e:
            print(f"[ERREUR] Update : {e}")

    def restart_pi(self):
        try:
            print("🔄 Redémarrage du Raspberry Pi...")
            subprocess.run(["sudo", "reboot"], check=True)
        except subprocess.CalledProcessError: 
            self._call_js_func("showplateformError")

    def shutdown_pi(self):
        try:
            print("⏻ Extinction du Raspberry Pi...")
            subprocess.run(["sudo", "shutdown", "now"], check=True)
        except subprocess.CalledProcessError: 
            self._call_js_func("showplateformError")

    def callback(self, recognizer, audio):
        try:
            # MODIFICATION : Essayer plusieurs fois la reconnaissance
            text = recognizer.recognize_google(audio, language="fr-FR").lower()
            print(f"[DEBUG] Audio capturé : '{text}'")  # ← Log pour debug
        except sr.UnknownValueError:
            # MODIFICATION : Même si incompréhensible, considérer qu'il y a eu du son
            print("[DEBUG] Audio détecté mais non compris")
            if not self.listening_command:
                self.listening_command = True
                self.last_speech_time = time.time()
                self.window.evaluate_js("startListening()")
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

    def afficher_texte(self, texte):
        """Affiche le texte mot par mot dans l'UI"""
        self.window.evaluate_js("showSpeaking()")
        texte_escape = texte.replace("'", "\\'").replace('"', '\\"')
        self.window.evaluate_js(f"displayTextWordByWord('{texte_escape}')")

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

            # Ajouter le nouveau message à l'historique
            self.conversation_history.append({"role": "user", "content": prompt})
            
            # Limiter la taille de l'historique pour ne pas dépasser les tokens
            if len(self.conversation_history) > self.max_history_length:
                # Garder le message système et les messages les plus récents
                self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-self.max_history_length+1:]

            # Préparer les messages pour l'API
            messages = [
                {"role": "system", "content": f"""
                Voici le prompt que tu dois toujours suivre (s'en forcément y faire référence) :

                1. Tu es un assistant vocal utile et amical. 
                2. Tu peux recevoir en début de phrase des mots comme hey google qui sont les Trigger pour te parler ou si tu reçois des choses qui peuvent ressembler à ca :{self.TRIGGER} est bien n'en tien pas compte. Réponds de manière naturelle et conversationnelle.
                3. Le nom l'utilisateur est : {self.name}. (si vide, ignorer cette ligne).
                4. Le travail de l'utilisateur est : {self.job}. (si vide, ignorer cette ligne).
                5. Informations supplémentaires sur l'utilisateur : {self.other}. (si vide, ignorer cette ligne).

                 """}
            ] + self.conversation_history

            completion = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            texte = completion.choices[0].message.content
            texte = texte.replace('. ', ' ')
            print("IA :", texte)

            # Ajouter la réponse de l'IA à l'historique
            self.conversation_history.append({"role": "assistant", "content": texte})

            if self.mode == "Voice":
                tts_response = openai.audio.speech.create(
                    model="gpt-4o-mini-tts",
                    voice=self.voice,
                    input=texte
                )

                filename = f"reply_{uuid.uuid4().hex}.mp3"
                with open(filename, "wb") as f:
                    f.write(tts_response.read())

                self.jouer_audio(filename)
            
            elif self.mode == "Text":
                self.afficher_texte(texte)

        except openai.AuthenticationError:
            print("[ERREUR] Clé API invalide ou manquante.")
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

    # Ajouter une méthode pour réinitialiser l'historique si nécessaire
    def reset_conversation(self):
        """Réinitialise l'historique de conversation"""
        self.conversation_history = []
        print("[DEBUG] Historique de conversation réinitialisé")

    def run(self):
        with self._mic_lock:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

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

                                words = final_phrase.lower().split()

                                if not self.TRIGGER or self.TRIGGER.strip() == "":
                                    print("[DEBUG] TRIGGER vide → envoie directement à l'IA")
                                    self.send_to_ai(final_phrase)
                                    continue

                                trigger_detected = False
                                cleaned_phrase = final_phrase

                                # MODIFICATION : Seuil de similarité encore plus bas
                                for w in words[:3]:  # ← Vérifier 3 mots au lieu de 2
                                    if similar(self.TRIGGER, w) > 0.4:  # ← Seuil très bas à 0.4
                                        trigger_detected = True
                                        cleaned_phrase = final_phrase.lower().replace(w, "").strip()
                                        print(f"[DEBUG] Trigger fuzzy détecté : {w} (similarité: {similar(self.TRIGGER, w):.2f})")
                                        break

                                # MODIFICATION : Détection par inclusion plus agressive
                                if not trigger_detected and self.TRIGGER:
                                    # Vérifier si une partie du trigger est dans la phrase
                                    trigger_words = self.TRIGGER.split()
                                    if len(trigger_words) > 1:
                                        # Pour les triggers multiples comme "maxt assistant"
                                        for trigger_word in trigger_words:
                                            if any(similar(trigger_word, w) > 0.5 for w in words[:2]):
                                                trigger_detected = True
                                                cleaned_phrase = final_phrase
                                                print(f"[DEBUG] Trigger partiel détecté : {trigger_word}")
                                                break
                                    else:
                                        # Pour les triggers simples
                                        if any(similar(self.TRIGGER, w) > 0.4 for w in words):
                                            trigger_detected = True
                                            cleaned_phrase = final_phrase
                                            print(f"[DEBUG] Trigger dans la phrase détecté")

                                # MODIFICATION : Mode "toujours écouter" si trigger vide
                                if not self.TRIGGER.strip():
                                    trigger_detected = True
                                    cleaned_phrase = final_phrase

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
                self.mic = sr.Microphone()
                
                # MODIFICATION : Ajustement plus sensible au bruit ambiant
                with self.mic as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)  # ← Durée réduite
                    # Configurer des paramètres plus sensibles
                    self.recognizer.energy_threshold = 300
                    self.recognizer.pause_threshold = 0.8
                    self.recognizer.phrase_threshold = 0.1  # ← Seuil de phrase très bas
                
                # MODIFICATION : Réduire le phrase_time_limit pour capturer plus vite
                self.stop_listening = self.recognizer.listen_in_background(
                    self.mic, self.callback, phrase_time_limit=3  # ← Réduit à 3 secondes
                )
                self._mic_active = True
                print("[INFO] Micro démarré avec succès (mode sensible)")
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

    def test_microphone_sensitivity(self):
        """Teste et affiche la sensibilité actuelle du microphone"""
        print("[DEBUG] Test de sensibilité du microphone...")
        print(f"[DEBUG] Energy threshold: {self.recognizer.energy_threshold}")
        print(f"[DEBUG] Pause threshold: {self.recognizer.pause_threshold}")
        print(f"[DEBUG] Phrase threshold: {self.recognizer.phrase_threshold}")
        print(f"[DEBUG] Silence limit: {self.SILENCE_LIMIT}")

if __name__ == "__main__":
    window = webview.create_window("Vocal Assistant", "index.html", width=800, height=480, frameless=True, resizable=False)
    assistant = Assistant(window)

    # Exposer les méthodes
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
    window.expose(assistant.get_status)
    window.expose(assistant.get_mode)
    window.expose(assistant.change_mode)
    window.expose(assistant.reset_conversation)

    window.expose(assistant.get_name)
    window.expose(assistant.change_name)
    window.expose(assistant.get_job)
    window.expose(assistant.change_job)
    window.expose(assistant.get_other)
    window.expose(assistant.change_other)

    threading.Thread(target=assistant.run, daemon=True).start()

    webview.start()
