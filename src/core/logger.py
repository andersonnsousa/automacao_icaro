# src/core/logger.py
import logging
from pathlib import Path
from .config import Config  # Importa a configuração

def setup_logger():
    """Configura o logger centralizado do projeto."""
    # Garante que o diretório de logs existe
    Config.LOGS_DIR.mkdir(exist_ok=True)

    log_file = Config.LOGS_DIR / "analyzer.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logger()