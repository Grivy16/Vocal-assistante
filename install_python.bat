@echo off
:: Vérifie si Python est installé
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python n'est pas installé. Installation en cours...
    :: Télécharge et installe Python silencieusement (remplace l'URL par la dernière version si nécessaire)
    powershell -Command "(New-Object Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.4/python-3.11.4-amd64.exe', 'python_installer.exe')"
    :: Installe Python avec les options silencieuses (ajoute Python au PATH)
    python_installer.exe /quiet InstallAllUsers=1 PrependPath=1
    del python_installer.exe
) else (
    echo Python est déjà installé.
)

:: Vérifie et installe les modules Python nécessaires
python -m pip install --upgrade pip
python -m pip install SpeechRecognition openai pywebview

echo download fini