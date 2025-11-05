// ========== SYSTÈME CENTRALISÉ DE GESTION DES SETTINGS ==========

/**
 * Configuration des champs de settings
 * Pour ajouter un nouveau champ, il suffit d'ajouter une ligne ici !
 */
const SETTINGS_CONFIG = {
    apiKey: {
        elementId: 'apiKey',
        getPythonFunc: 'get_api_key',
        setPythonFunc: 'change_api',
        defaultValue: ''
    },
    keyword: {
        elementId: 'KeyWord',
        getPythonFunc: 'get_keyword',
        setPythonFunc: 'change_keyword',
        defaultValue: 'maxt'
    },
    voice: {
        elementId: 'Voicemenu',
        getPythonFunc: 'get_voice',
        setPythonFunc: 'change_voice',
        defaultValue: 'nova'
    },
    mode: {
        elementId: 'Modemenu',
        getPythonFunc: 'get_mode',
        setPythonFunc: 'change_mode',
        defaultValue: 'Voice'
    },
    name: {
        elementId: 'name',
        getPythonFunc: 'get_name',
        setPythonFunc: 'change_name',
        defaultValue: ''
    },
    job: {
        elementId: 'job',
        getPythonFunc: 'get_job',
        setPythonFunc: 'change_job',
        defaultValue: ''
    },
    other: {
        elementId: 'other',
        getPythonFunc: 'get_other',
        setPythonFunc: 'change_other',
        defaultValue: ''
    }
};

/**
 * Charge TOUTES les valeurs depuis Python et remplit les champs
 */
async function loadAllSettings() {
    // Attendre que pywebview.api soit prêt
    while (!window.pywebview?.api) {
        await new Promise(r => setTimeout(r, 100));
    }

    for (const [key, config] of Object.entries(SETTINGS_CONFIG)) {
        try {
            const element = document.getElementById(config.elementId);
            if (!element) {
                console.warn(`[loadAllSettings] Élément '${config.elementId}' introuvable`);
                continue;
            }

            const value = await window.pywebview.api[config.getPythonFunc]();
            // Si la valeur est vide, afficher une chaîne vide dans l'input
            // au lieu de la valeur par défaut
            element.value = value || "";
            console.log(`[DEBUG] ${key} chargé: "${value}" (affiché: "${element.value}")`);
        } catch (e) {
            console.warn(`[loadAllSettings] Erreur pour '${key}':`, e);
        }
    }
}

/**
 * Sauvegarde TOUTES les valeurs vers Python
 */
async function saveAllSettings() {
    if (!window.pywebview?.api) {
        console.error("[saveAllSettings] pywebview.api non disponible");
        return;
    }

    for (const [key, config] of Object.entries(SETTINGS_CONFIG)) {
        try {
            const element = document.getElementById(config.elementId);
            if (!element) {
                console.warn(`[saveAllSettings] Élément '${config.elementId}' introuvable`);
                continue;
            }

            const value = element.value.trim();
            // Sauvegarder même si vide (permet de vider un champ volontairement)
            await window.pywebview.api[config.setPythonFunc](value);
            console.log(`[DEBUG] ${key} sauvegardé: "${value}"`);
        } catch (e) {
            console.warn(`[saveAllSettings] Erreur pour '${key}':`, e);
        }
    }
}

// ========== FONCTIONS D'AFFICHAGE ==========

function displayTextWordByWord(text) {
    const textDisplay = document.getElementById("text_display");
    if (!textDisplay) return;

    textDisplay.textContent = "";
    textDisplay.style.display = "block";
    textDisplay.style.opacity = "1";

    const words = text.split(" ");
    let index = 0;

    function showNextWord() {
        if (index < words.length) {
            textDisplay.textContent += (index > 0 ? " " : "") + words[index];
            index++;
            setTimeout(showNextWord, 150);
        } else {
            setTimeout(() => {
                textDisplay.style.opacity = "0";
                setTimeout(() => {
                    textDisplay.style.display = "none";
                    textDisplay.textContent = "";
                    resetUI();
                }, 500);
            }, 3000);
        }
    }

    showNextWord();
}

function startListening() {
    const microEl = document.getElementById("micro");
    if (microEl) microEl.classList.add("listening");
}

function showThinking() {
    const microEl = document.getElementById("micro");
    if (microEl) microEl.classList.add("hidden");
    
    const ref = document.getElementById("reflechit");
    const ia = document.getElementById("ia_parle");
    const textDisplay = document.getElementById("text_display");
    
    if (ref) ref.style.display = "block";
    if (ia) ia.style.display = "none";
    if (textDisplay) {
        textDisplay.style.display = "none";
        textDisplay.textContent = "";
    }
}

async function showSpeaking() {
    try {
        const statut = await window.pywebview.api.get_status();
        
        const microEl = document.getElementById("micro");
        if (microEl) microEl.classList.add("hidden");
        
        const ref = document.getElementById("reflechit");
        const ia = document.getElementById("ia_parle");
        
        if (statut === "Voice") {
            if (ref) ref.style.display = "none";
            if (ia) ia.style.display = "block";
        } else if (statut === "Text") {
            if (ref) ref.style.display = "none";
            if (ia) ia.style.display = "none";
        }
    } catch (e) {
        console.error("Erreur showSpeaking:", e);
    }
}

function resetUI() {
    const microEl = document.getElementById("micro");
    if (microEl) microEl.classList.remove("hidden");
    
    const ref = document.getElementById("reflechit");
    const ia = document.getElementById("ia_parle");
    const textDisplay = document.getElementById("text_display");
    
    if (ref) ref.style.display = "none";
    if (ia) ia.style.display = "none";
    if (textDisplay) {
        textDisplay.style.display = "none";
        textDisplay.textContent = "";
    }

    const canvasEl = document.getElementById("canvas");
    if (canvasEl) {
        canvasEl.style.opacity = "0";
        canvasEl.style.visibility = "hidden";
    }
}

// Variables globales pour l'audio / visualizer
let audioContext = null;
let audioSource = null;
let analyser = null;

let canvas = null;
let ctx = null;
let WIDTH = 0;
let HEIGHT = 0;

let barCount = 24;
let barSpacing = 8;
let barRadius = 12;
let barWidth = 1;
let primaryColor = "#ffffff";
let secondaryColor = "#ffffff";
let opacity = 1;
let heightMultiplier = 1.8;
let minHeight = 0;
let maxHeight = 150;

let dataArray = null;
let rafId = null;

function roundRect(ctx, x, y, width, height, radius) {
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    ctx.lineTo(x + radius, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
    ctx.fill();
}

function readStyles() {
    const style = getComputedStyle(document.documentElement);
    barSpacing = parseInt(style.getPropertyValue('--visualizer-bar-spacing')) || 8;
    barRadius = parseInt(style.getPropertyValue('--visualizer-bar-radius')) || 12;
    barCount = parseInt(style.getPropertyValue('--visualizer-bar-count')) || 24;
    primaryColor = style.getPropertyValue('--visualizer-bar-color-primary')?.trim() || "#ffffff";
    secondaryColor = style.getPropertyValue('--visualizer-bar-color-secondary')?.trim() || primaryColor;
    opacity = parseFloat(style.getPropertyValue('--visualizer-bar-opacity')) || 1;
    heightMultiplier = parseFloat(style.getPropertyValue('--visualizer-multiplier')) || 1.8;
    minHeight = parseInt(style.getPropertyValue('--visualizer-bar-min-height')) || 20;
    maxHeight = parseInt(style.getPropertyValue('--visualizer-bar-max-height')) || 150;
}

function resizeCanvas() {
    if (!canvas) return;
    canvas.width = canvas.clientWidth;
    const cssHeight = getComputedStyle(canvas).getPropertyValue('height');
    HEIGHT = parseInt(cssHeight) || Math.round(window.innerHeight * 0.2);
    canvas.height = HEIGHT;
    WIDTH = canvas.width;
    barWidth = Math.max(2, (WIDTH / barCount) - barSpacing);
}

function initVisualizer() {
    if (audioContext) return;
    readStyles();

    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 64;
    dataArray = new Uint8Array(analyser.frequencyBinCount);

    canvas = document.getElementById("canvas");
    if (!canvas) return;
    ctx = canvas.getContext("2d");
    resizeCanvas();
    window.addEventListener('resize', () => {
        resizeCanvas();
    });

    function renderLoop() {
        rafId = requestAnimationFrame(() => setTimeout(renderLoop, 33));
        readStyles();

        if (!analyser) return;

        analyser.getByteFrequencyData(dataArray);
        ctx.clearRect(0, 0, WIDTH, HEIGHT);

        let x = 0;
        for (let i = 0; i < barCount; i++) {
            const val = dataArray[i] || 0;
            const rawHeight = val * heightMultiplier;
            const barH = Math.max(minHeight, Math.min(maxHeight, rawHeight));

            const gradient = ctx.createLinearGradient(x, HEIGHT - barH, x, HEIGHT);
            gradient.addColorStop(0, primaryColor);
            gradient.addColorStop(1, secondaryColor);

            ctx.globalAlpha = opacity;
            ctx.fillStyle = gradient;
            roundRect(ctx, x, HEIGHT - barH, barWidth, barH, barRadius);

            x += barWidth + barSpacing;
        }
    }

    renderLoop();
}

function playAudioFile(filePath) {
    const oldAudio = document.getElementById("audio");
    if (oldAudio) {
        try {
            oldAudio.pause();
            oldAudio.src = "";
            oldAudio.remove();
        } catch (e) {
            console.warn("Erreur suppression ancien audio :", e);
        }
    }

    const audio = document.createElement("audio");
    audio.id = "audio";
    audio.preload = "auto";
    audio.src = `${filePath}?t=${Date.now()}`;
    document.body.appendChild(audio);

    const canvasEl = document.getElementById("canvas");
    if (canvasEl) {
        canvasEl.style.visibility = "visible";
        canvasEl.style.opacity = "1";
    }

    if (!audioContext) initVisualizer();

    if (audioContext) {
        try {
            audioSource = audioContext.createMediaElementSource(audio);
            audioSource.connect(analyser);
            analyser.connect(audioContext.destination);
        } catch (e) {
            console.warn("Erreur création MediaElementSource :", e);
        }

        if (audioContext.state === 'suspended') {
            audioContext.resume().catch(() => {});
        }
    }

    audio.load();

    audio.addEventListener('loadeddata', function () {
        audio.play().catch(() => {});
    }, { once: true });

    audio.onended = function () {
        setTimeout(() => {
            resetUI();
        }, 750);
    };
}

document.addEventListener('DOMContentLoaded', () => {
    initVisualizer();
    loadAllSettings(); // ← Charge tous les settings au démarrage
});

// ========== POPUP SETTINGS ==========

const popup = document.getElementById("popup");
const overlay = document.getElementById("overlay");
const openBtn = document.getElementById("openBtn");
const closeBtn = document.getElementById("closeBtn");
const form = document.getElementById("form");

openBtn.addEventListener("click", async () => {
    popup.style.display = "flex";
    overlay.style.display = "block";

    // Recharger tous les settings
    await loadAllSettings();

    // Arrêter le micro
    try { 
        if (window.pywebview?.api?.stop_microphone) {
            await window.pywebview.api.stop_microphone();
        }
    } catch(e) {
        console.warn("Erreur stop_microphone:", e);
    }

    // Charger le stockage
    if (window.pywebview?.api?.get_stockage) {
        try {
            const info = await window.pywebview.api.get_stockage();
            console.log("get_stockage ->", info);
            const percent = (info && typeof info.percent === "number") ? info.percent : 0;
            setProgress(percent);
        } catch (e) {
            console.warn("get_stockage failed:", e);
            setProgress(0);
        }
    } else {
        setProgress(0);
    }
});

function closePopup() {
    popup.style.display = "none";
    overlay.style.display = "none";
}

closeBtn.addEventListener("click", () => {
    closePopup();
    if (window.pywebview?.api?.start_microphone) {
        window.pywebview.api.start_microphone();
    }
});

overlay.addEventListener("click", () => {
    closePopup();
    if (window.pywebview?.api?.start_microphone) {
        window.pywebview.api.start_microphone();
    }
});

form.addEventListener("click", (e) => {
    e.stopPropagation();
});

// ========== BOUTONS D'ACTION ==========

const restartbtn = document.getElementById("Restart");
restartbtn.addEventListener("click", async () => {
    await window.pywebview.api.restart_pi();
});

const shutdownbtn = document.getElementById("Shutdown");
shutdownbtn.addEventListener("click", async () => {
    await window.pywebview.api.shutdown_pi();
});

const newchatbtn = document.getElementById("newchat");
newchatbtn.addEventListener("click", async () => {
    await window.pywebview.api.reset_conversation();
    showNewchat();
});


const updatebtn = document.getElementById("update");
updatebtn.addEventListener("click", async () => {
    if (window.pywebview?.api?.update) {
        try {
            await window.pywebview.api.update();
        } catch(e) {
            console.warn("Erreur lors de l'appel update:", e);
        }
    }
});

const savebtn = document.getElementById("savebtn");
savebtn.addEventListener("click", async () => {
    await saveAllSettings(); // ← Sauvegarde tous les settings en une ligne !
    console.log("✅ Tous les paramètres sauvegardés !");
});

// ========== GESTION DES ERREURS ==========

function stopPlaybackAndLoader() {
    try { resetUI(); } catch (e) { console.warn("resetUI absent:", e); }

    const loaderEl = document.querySelector('.loader') || document.getElementById('reflechit');
    if (loaderEl) loaderEl.style.display = 'none';

    const audio = document.getElementById('audio');
    if (audio) {
        try {
            audio.pause();
            audio.currentTime = 0;
            audio.src = "";
            audio.remove();
        } catch (e) {
            console.warn("Erreur arrêt audio:", e);
        }
    }

    try {
        if (audioContext && audioContext.state !== 'closed') {
            audioContext.suspend().catch(()=>{});
        }
    } catch (e) {
        console.warn("Erreur suspension audioContext:", e);
    }

    try {
        if (typeof rafId !== 'undefined' && rafId) {
            cancelAnimationFrame(rafId);
            rafId = null;
        }
    } catch (e) {}
}

function showError(message, options = {}) {
    if (!message) message = "Une erreur est survenue.";
    stopPlaybackAndLoader();

    const el = document.querySelector('.error');
    if (el) {
        el.innerText = message;
        el.style.display = "block";
        el.style.color = "red";
        if (options.autoHide !== false) {
            const t = typeof options.timeout === 'number' ? options.timeout : 10000;
            setTimeout(() => {
                try { el.style.display = "none"; el.innerText = ""; } catch(e) {}
            }, t);
        }
    } else {
        console.warn("showError: élément .error introuvable — message:", message);
    }

    console.error("UI Error:", message);
}

function showInfo(message, options = {}) {
    const el = document.querySelector('.error');
    if (el) {
        el.innerText = message;
        el.style.display = "block";
        el.style.color = "#00ad00ff";
        if (options.autoHide !== false) {
            const t = typeof options.timeout === 'number' ? options.timeout : 10000;
            setTimeout(() => {
                try { el.style.display = "none"; el.innerText = ""; } catch(e) {}
            }, t);
        }
    } else {
        console.warn("showinfo: élément .error introuvable — message:", message);
    }

    console.error("UI Error:", message);
}

function showApiError() {
    showError("Invalid API key. Please check your key and try again.");
}
function showNetworkError() {
    showError("Network error. Please check your internet connection.");
}
function showTtsError() {
    showError("Error generating speech. Please try again later.");
}
function showMicError() {
    showError("Microphone error. Please check your microphone settings.");
}
function showParamError() {
    showError("Micro reload error. Please open setting and close it to reload the microphone.");
}
function showGeneralError(msg) {
    showError(msg || "An unexpected error occurred.");
}
function showplateformError(msg) {
    showError(msg || "Execute this command in a Linux platform.");
}
function showUpdateAvailable() {
    showInfo("A new version of the application is available! Please update to the latest version in the settings.");
}
function showNewchat() {
    showInfo("New conversation started.");
}

function setProgress(percent) {
    if (percent < 0) percent = 0;
    if (percent > 100) percent = 100;

    const progressBar = document.getElementById("myProgress");
    const progressText = document.getElementById("progressText");

    progressBar.style.width = percent + "%";
    progressText.textContent = percent + "%";
}

// ========== CLAVIER VIRTUEL ==========

class VirtualKeyboard {
    constructor() {
        this.isUppercase = false;
        this.currentInput = null;
        this.init();
    }

    init() {
        this.createKeyboard();
        this.attachEventListeners();
    }

    createKeyboard() {
        const keyboardHTML = `
            <div class="virtual-keyboard" id="virtualKeyboard">
                <button class="keyboard-close">×</button>
                
                <div class="keyboard-row">
                    ${this.createKeys(['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'])}
                </div>
                
                <div class="keyboard-row">
                    ${this.createKeys(['a', 'z', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'])}
                </div>
                
                <div class="keyboard-row">
                    ${this.createKeys(['q', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm'])}
                </div>
                
                <div class="keyboard-row">
                    <button class="keyboard-key shift" data-action="shift">⇧</button>
                    ${this.createKeys(['w', 'x', 'c', 'v', 'b', 'n'])}
                    <button class="keyboard-key" data-action="backspace">⌫</button>
                </div>
                
                <div class="keyboard-row">
                    <button class="keyboard-key" data-char="-">-</button>
                    <button class="keyboard-key" data-char=".">.</button>
                    <button class="keyboard-key space" data-char=" ">Espace</button>
                    <button class="keyboard-key" data-action="enter">Entrer</button>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', keyboardHTML);
        this.keyboard = document.getElementById('virtualKeyboard');
    }

    createKeys(keys) {
        return keys.map(key => 
            `<button class="keyboard-key" data-char="${key}">${key}</button>`
        ).join('');
    }

    attachEventListeners() {
        // Fermeture du clavier
        this.keyboard.querySelector('.keyboard-close').addEventListener('click', () => {
            this.hide();
        });

        // Touches du clavier
        this.keyboard.addEventListener('click', (e) => {
            if (e.target.classList.contains('keyboard-key')) {
                const char = e.target.getAttribute('data-char');
                const action = e.target.getAttribute('data-action');

                if (char) {
                    this.insertCharacter(char);
                } else if (action === 'shift') {
                    this.toggleShift();
                } else if (action === 'backspace') {
                    this.backspace();
                } else if (action === 'enter') {
                    this.hide();
                }
            }
        });

        // Fermer en cliquant à l'extérieur
        document.addEventListener('click', (e) => {
            if (this.isVisible() && !this.keyboard.contains(e.target) && 
                !e.target.matches('input[type="text"]')) {
                this.hide();
            }
        });
    }

    show(inputElement) {
        this.currentInput = inputElement;
        this.keyboard.style.display = 'flex';
        
        // Positionner le clavier
        const rect = inputElement.getBoundingClientRect();
        if (rect.bottom + 200 > window.innerHeight) {
            this.keyboard.style.bottom = '0';
        } else {
            this.keyboard.style.bottom = '0';
        }
    }

    hide() {
        this.keyboard.style.display = 'none';
        this.currentInput = null;
        this.resetShift();
    }

    isVisible() {
        return this.keyboard.style.display === 'flex';
    }

    insertCharacter(char) {
        if (!this.currentInput) return;

        const start = this.currentInput.selectionStart;
        const end = this.currentInput.selectionEnd;
        const value = this.currentInput.value;
        
        // Caractère avec gestion de la casse
        const finalChar = this.isUppercase ? char.toUpperCase() : char;
        
        // Insérer le caractère
        this.currentInput.value = value.substring(0, start) + finalChar + value.substring(end);
        
        // Positionner le curseur
        this.currentInput.selectionStart = this.currentInput.selectionEnd = start + 1;
        
        // Déclencher l'événement input
        this.currentInput.dispatchEvent(new Event('input', { bubbles: true }));
        
        // Réinitialiser shift après une touche (comportement standard)
        if (this.isUppercase) {
            this.resetShift();
        }
    }

    backspace() {
        if (!this.currentInput) return;

        const start = this.currentInput.selectionStart;
        const end = this.currentInput.selectionEnd;
        const value = this.currentInput.value;

        if (start === end && start > 0) {
            // Supprimer un caractère
            this.currentInput.value = value.substring(0, start - 1) + value.substring(end);
            this.currentInput.selectionStart = this.currentInput.selectionEnd = start - 1;
        } else if (start !== end) {
            // Supprimer la sélection
            this.currentInput.value = value.substring(0, start) + value.substring(end);
            this.currentInput.selectionStart = this.currentInput.selectionEnd = start;
        }
        
        this.currentInput.dispatchEvent(new Event('input', { bubbles: true }));
    }

    toggleShift() {
        this.isUppercase = !this.isUppercase;
        this.updateKeysCase();
        
        const shiftKey = this.keyboard.querySelector('[data-action="shift"]');
        shiftKey.classList.toggle('active', this.isUppercase);
    }

    resetShift() {
        this.isUppercase = false;
        this.updateKeysCase();
        
        const shiftKey = this.keyboard.querySelector('[data-action="shift"]');
        shiftKey.classList.remove('active');
    }

    updateKeysCase() {
        const keys = this.keyboard.querySelectorAll('[data-char]');
        keys.forEach(key => {
            const char = key.getAttribute('data-char');
            if (char && char.length === 1 && /[a-z]/.test(char)) {
                key.textContent = this.isUppercase ? char.toUpperCase() : char;
            }
        });
    }
}

// Initialisation du clavier virtuel
let virtualKeyboard;

document.addEventListener('DOMContentLoaded', () => {
    virtualKeyboard = new VirtualKeyboard();
    
    // Attacher le clavier virtuel à tous les inputs de texte
    const textInputs = document.querySelectorAll('input[type="text"]');
    textInputs.forEach(input => {
        input.addEventListener('focus', (e) => {
            virtualKeyboard.show(e.target);
        });
        
        // Empêcher l'ouverture du clavier physique sur mobile
        input.addEventListener('touchstart', (e) => {
            e.preventDefault();
            virtualKeyboard.show(e.target);
        });
    });
});