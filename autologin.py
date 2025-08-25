# autologin.py
"""
Script de Login Rápido para o WebContext Analyzer.
Utiliza os módulos src/automation/login_engine e src/core/config.
Execute com: python autologin.py
"""

import sys
import os
# Adiciona o diretório raiz ao sys.path para permitir imports de src/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.automation.login_engine import LoginEngine
from src.automation.browser_manager import BrowserManager
from src.core.config import Config
from src.core.logger import logger
import time

def perform_adaptive_login():
    """Executa o login adaptativo usando a arquitetura modular."""
    logger.info("🔍 Procurando a análise mais recente...")
    
    # (Reutilize a lógica de get_latest_analysis_path do main_window.py ou crie uma função similar)
    # Para manter a simplicidade, vamos assumir que a lógica está aqui
    import glob
    import json
    from pathlib import Path

    analyses_dir = Config.ANALYSES_DIR
    if not analyses_dir.exists():
        logger.error(f"Pasta '{analyses_dir}' não encontrada.")
        return None, None

    all_paths = []
    for domain_dir in analyses_dir.iterdir():
        if domain_dir.is_dir():
            for timestamp_dir in domain_dir.iterdir():
                if timestamp_dir.is_dir():
                    all_paths.append(timestamp_dir)

    if not all_paths:
        logger.error("Nenhuma análise encontrada.")
        return

    latest_analysis = max(all_paths, key=lambda x: x.stat().st_ctime)
    domain = latest_analysis.parent.name
    base_url = f"https://{domain}"
    logger.info(f"📂 Análise encontrada: {latest_analysis}")
    logger.info(f"🌐 URL alvo: {base_url}")

    # Carrega o contexto
    context_file = latest_analysis / "context.json"
    if not context_file.exists():
        logger.error(f"❌ Arquivo context.json não encontrado: {context_file}")
        return

    with open(context_file, "r", encoding="utf-8") as f:
        context = json.load(f)

    # Executa o login
    with BrowserManager() as driver:
        engine = LoginEngine(driver)
        success = engine.adaptive_login(context)
        if success:
            logger.info("🎉 Login bem-sucedido!")
            input("\nPressione ENTER para fechar o navegador...")
        else:
            logger.error("❌ Falha no login.")
            driver.save_screenshot("erro_login.png")
            logger.info("📸 Screenshot salvo.")

if __name__ == "__main__":
    perform_adaptive_login()