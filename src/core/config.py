# src/core/config.py
from pathlib import Path
from dotenv import load_dotenv
import os

# Carrega as variáveis do .env
load_dotenv()

class Config:
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    LOGS_DIR = DATA_DIR / "logs"
    ANALYSES_DIR = DATA_DIR / "analyses"
    SESSIONS_DIR = DATA_DIR / "sessions"
    TEMPLATES_DIR = PROJECT_ROOT / "templates"

    # Cria os diretórios necessários
    for directory in [DATA_DIR, LOGS_DIR, ANALYSES_DIR, SESSIONS_DIR]:
        directory.mkdir(exist_ok=True)

    # Credenciais do usuário
    EMAIL = os.getenv("EMAIL")
    PASSWORD = os.getenv("PASSWORD")

    # Configurações do navegador
    CHROME_HEADLESS = os.getenv("CHROME_HEADLESS", "true").lower() == "true"
