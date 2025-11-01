function startListening() {
    const microEl = document.getElementById("micro");
    if (microEl) microEl.classList.add("listening");
}

function showThinking() {
    const microEl = document.getElementById("micro");
    if (microEl) microEl.classList.add("hidden");
    
    const ref = document.getElementById("reflechit");
    const ia = document.getElementById("ia_parle");
    if (ref) ref.style.display = "block";
    if (ia) ia.style.display = "none";
}

function showSpeaking() {
    const microEl = document.getElementById("micro");
    if (microEl) microEl.classList.add("hidden");
    
    const ref = document.getElementById("reflechit");
    const ia = document.getElementById("ia_parle");
    if (ref) ref.style.display = "none";
    if (ia) ia.style.display = "block";
}

function resetUI() {
    const microEl = document.getElementById("micro");
    if (microEl) microEl.classList.remove("hidden");
    
    const ref = document.getElementById("reflechit");
    const ia = document.getElementById("ia_parle");
    if (ref) ref.style.display = "none";
    if (ia) ia.style.display = "none";

    // cacher le visualizer quand rien ne joue
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

// Fonction pour dessiner un rectangle arrondi
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

// Lire les variables CSS
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

// Redimensionne le canvas (appelé au resize)
function resizeCanvas() {
    if (!canvas) return;
    // utiliser clientWidth / computed height pour correspondre au CSS
    canvas.width = canvas.clientWidth;
    const cssHeight = getComputedStyle(canvas).getPropertyValue('height');
    HEIGHT = parseInt(cssHeight) || Math.round(window.innerHeight * 0.2);
    canvas.height = HEIGHT;
    WIDTH = canvas.width;
    barWidth = Math.max(2, (WIDTH / barCount) - barSpacing);
}

// Initialisation unique du visualizer
function initVisualizer() {
    if (audioContext) return; // déjà initialisé
    readStyles();

    // AudioContext + analyser
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 64; // moins = moins de barres à traiter
    dataArray = new Uint8Array(analyser.frequencyBinCount);

    // Canvas
    canvas = document.getElementById("canvas");
    if (!canvas) return;
    ctx = canvas.getContext("2d");
    resizeCanvas();
    window.addEventListener('resize', () => {
        resizeCanvas();
    });

    // Boucle d'animation unique
    function renderLoop() {
        rafId = requestAnimationFrame(() => setTimeout(renderLoop, 33)); // ~30fps
        // Mettre à jour styles dynamiquement si besoin
        readStyles();

        // Si analyser non défini, afficher barres statiques minHeight
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

// Création / réutilisation de la source audio (une seule fois)
function ensureAudioSource() {
    const audioEl = document.getElementById("audio");
    if (!audioContext || !audioEl) return;
    if (!audioSource) {
        try {
            audioSource = audioContext.createMediaElementSource(audioEl);
            audioSource.connect(analyser);
            analyser.connect(audioContext.destination);
        } catch (e) {
            // Certains navigateurs interdisent la création multiple — on ignore si erreur
            console.warn("ensureAudioSource:", e);
        }
    }
}

// Fonction de lecture appelée depuis Python
function playAudioFile(filePath) {
    // Supprime l'ancien élément audio et sa source
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

    // Crée un nouvel élément audio
    const audio = document.createElement("audio");
    audio.id = "audio";
    audio.preload = "auto";
    // empêcher le cache en ajoutant un timestamp si besoin
    audio.src = `${filePath}?t=${Date.now()}`;
    document.body.appendChild(audio);

    // Afficher le canvas / visualizer
    const canvasEl = document.getElementById("canvas");
    if (canvasEl) {
        canvasEl.style.visibility = "visible";
        canvasEl.style.opacity = "1";
    }

    // Initialise le visualizer si nécessaire
    if (!audioContext) initVisualizer();

    // Crée une nouvelle source et connecte à l'analyser
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

    // Forcer le navigateur à charger la nouvelle ressource
    audio.load();

    // Jouer l'audio une fois que les données sont prêtes
    audio.addEventListener('loadeddata', function () {
        audio.play().catch(() => {});
    }, { once: true });

    // Fin de lecture -> reset UI après délai et cacher le visualizer
    audio.onended = function () {
        setTimeout(() => {
            resetUI();
        }, 750);
    };
}



// Initialiser dès que possible pour afficher les barres min au départ
document.addEventListener('DOMContentLoaded', () => {
    initVisualizer();
});

async function initEntries() {
    const apientry = document.getElementById("apiKey"); 
    const keywordentry = document.getElementById("KeyWord"); 
    const voicemenu = document.getElementById("Voicemenu"); 
    if (!apientry || !keywordentry || !voicemenu) return;

    // Attendre que pywebview.api soit prêt
    while (!window.pywebview?.api) {
        await new Promise(r => setTimeout(r, 100));
    }

    try {
        // Récupérer les valeurs côté Python
        const apiKey = await window.pywebview.api.get_api_key();
        const keyword = await window.pywebview.api.get_keyword();
        const voice = await window.pywebview.api.get_voice();

        // NE PAS TOUCHER aux assignations existantes
        apientry.value = apiKey || "";
        keywordentry.value = keyword || "";

        // Ajouter seulement la voix
        voicemenu.value = voice || "nova";

        console.log("[DEBUG] API Key, Keyword et Voice remplis dans l'UI");
    } catch(e) {
        console.warn("Erreur récupération API/Keyword/Voice:", e);
    }
}

document.addEventListener("DOMContentLoaded", initEntries);

const popup = document.getElementById("popup");
const overlay = document.getElementById("overlay");
const openBtn = document.getElementById("openBtn");
const closeBtn = document.getElementById("closeBtn");
const form = document.getElementById("form");

// Ouvrir
openBtn.addEventListener("click", async () => {
    popup.style.display = "flex";
    overlay.style.display = "block";

    // récupérer et afficher la clé si disponible
    if (window.pywebview && window.pywebview.api && window.pywebview.api.get_api_key && window.pywebview.api.get_keyword) {
        try {
            const apiKey = await window.pywebview.api.get_api_key();
            const apientry = document.getElementById("apiKey");
            if (apientry) apientry.value = apiKey || "";
        } catch (e) {
            console.warn("get_api_key failed:", e);
        }
    }

    // arrêter le micro pendant la config
    try { if (window.pywebview && window.pywebview.api && window.pywebview.api.stop_microphone) await window.pywebview.api.stop_microphone(); } catch(e){}

    // récupérer stockage et mettre à jour la progressbar
    if (window.pywebview && window.pywebview.api && window.pywebview.api.get_stockage) {
        try {
            const info = await window.pywebview.api.get_stockage();
            console.log("get_stockage ->", info); // DEBUG : regarde dans la console JS (et vérifie la console Python pour le print)
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
// Fermer
function closePopup() {
    popup.style.display = "none";
    overlay.style.display = "none";
}

closeBtn.addEventListener("click", () => {
    closePopup();
    if (window.pywebview) window.pywebview.api.start_microphone();
});

overlay.addEventListener("click", () => {
    closePopup();
    if (window.pywebview) window.pywebview.api.start_microphone();
});

// Empêcher la fermeture en cliquant dans le formulaire
form.addEventListener("click", (e) => {
    e.stopPropagation();
});

const restartbtn = document.getElementById("Restart");

restartbtn.addEventListener("click", async () => {
    await window.pywebview.api.restart_pi();
});

const shutdownbtn = document.getElementById("Shutdown");

shutdownbtn.addEventListener("click", async () => {
    await window.pywebview.api.shutdown_pi();
});

const updatebtn = document.getElementById("update");

updatebtn.addEventListener("click", async () => {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.update) {
        try {
            await window.pywebview.api.update();
        } catch(e) {
            console.warn("Erreur lors de l'appel update:", e);
        }
    }
});

const savebtn = document.getElementById("savebtn");

savebtn.addEventListener("click", async () => {
    const apientry = document.getElementById("apiKey");
    const keywordentry = document.getElementById("KeyWord");
    const menuvoix = document.getElementById("Voicemenu");

    const apiKey = apientry.value.trim();
    const keyword = keywordentry.value.trim();
    const voicemenu = menuvoix.value.trim();

    if (window.pywebview && window.pywebview.api) {
        try {
            await window.pywebview.api.change_api(apiKey);
            await window.pywebview.api.change_keyword(keyword);
            await window.pywebview.api.change_voice(voicemenu);
            console.log("API Key et Keyword mis à jour !");
        } catch (e) {
            console.warn("Erreur mise à jour API/Keyword:", e);
        }
    }
});


/**
 * Arrête la lecture, masque le loader/visualizer et nettoie l'audio.
 */
function stopPlaybackAndLoader() {
    try { resetUI(); } catch (e) { console.warn("resetUI absent:", e); }

    // Masquer loader visuel si présent
    const loaderEl = document.querySelector('.loader') || document.getElementById('reflechit');
    if (loaderEl) loaderEl.style.display = 'none';

    // Arrêter et supprimer l'audio courant
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

    // Si AudioContext tourne, le suspendre (optionnel)
    try {
        if (audioContext && audioContext.state !== 'closed') {
            audioContext.suspend().catch(()=>{});
        }
    } catch (e) {
        console.warn("Erreur suspension audioContext:", e);
    }

    // stop animation frames si nécessaire
    try {
        if (typeof rafId !== 'undefined' && rafId) {
            cancelAnimationFrame(rafId);
            rafId = null;
        }
    } catch (e) {}
}

/**
 * Affiche un message d'erreur centralisé et arrête tout ce qui charge/joue.
 * options: { autoHide: true|false, timeout: ms }
 */
function showError(message, options = {}) {
    if (!message) message = "Une erreur est survenue.";
    stopPlaybackAndLoader();

    const el = document.querySelector('.error');
    if (el) {
        el.innerText = message;
        el.style.display = "block";
        el.style.color = "red";
        // possibilité d'ajouter animation / style ici
        if (options.autoHide !== false) {
            const t = typeof options.timeout === 'number' ? options.timeout : 6000;
            setTimeout(() => {
                try { el.style.display = "none"; el.innerText = ""; } catch(e) {}
            }, t);
        }
    } else {
        console.warn("showError: élément .error introuvable — message:", message);
    }

    // log côté console pour debug
    console.error("UI Error:", message);
}

function showInfo(message, options = {}) {

    const el = document.querySelector('.error');
    if (el) {
        el.innerText = message;
        el.style.display = "block";
        el.style.color = "#00ad00ff";
        // possibilité d'ajouter animation / style ici
        if (options.autoHide !== false) {
            const t = typeof options.timeout === 'number' ? options.timeout : 30000;
            setTimeout(() => {
                try { el.style.display = "none"; el.innerText = ""; } catch(e) {}
            }, t);
        }
    } else {
        console.warn("showinfo: élément .error introuvable — message:", message);
    }

    // log côté console pour debug
    console.error("UI Error:", message);
}

/* Helpers spécifiques (appelables depuis Python via evaluate_js) */
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

function setProgress(percent) {
    if (percent < 0) percent = 0;
    if (percent > 100) percent = 100;
    progress = percent;

    const progressBar = document.getElementById("myProgress");
    const progressText = document.getElementById("progressText");

    progressBar.style.width = percent + "%";
    progressText.textContent = percent + "%";
}

