# main.py

from src.core.config import Config
from src.core.logger import logger
from src.analyzer.scraper import WebScraper
from src.automation.browser_manager import BrowserManager
from src.automation.login_engine import LoginEngine
from urllib.parse import urlparse
from datetime import datetime
import json
import sys

def main():
    if len(sys.argv) < 2:
        print("Uso: python main.py <url> [login]")
        print("Exemplo: python main.py 'https://icaro.eslcloud.com.br/users/sign_in' login")
        sys.exit(1)

    url = sys.argv[1]
    do_login = len(sys.argv) > 2 and sys.argv[2].lower() == "login"

    with BrowserManager() as driver:
        # 1. Análise da Página
        scraper = WebScraper(driver)
        context = scraper.scrape(url)

        # 2. Salva o Contexto
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        analysis_dir = Config.ANALYSES_DIR / domain / timestamp
        analysis_dir.mkdir(parents=True, exist_ok=True)

        context_file = analysis_dir / "context.json"
        with open(context_file, "w", encoding="utf-8") as f:
            json.dump(context, f, ensure_ascii=False, indent=2)
        logger.info(f"Contexto salvo em: {context_file}")

        # 3. Login Adaptativo (Opcional)
        if do_login:
            if not Config.EMAIL or not Config.PASSWORD:
                logger.warning("Credenciais não definidas no .env. Pulando login.")
            else:
                engine = LoginEngine(driver)
                success = engine.adaptive_login(context)
                logger.info(f"Resultado do login: {'Sucesso' if success else 'Falha'}")

if __name__ == "__main__":
    main()
