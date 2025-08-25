# src/core/logger.py
import logging
from .config import Config

def setup_logger():
    """Configura o logger centralizado do projeto."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(Config.LOGS_DIR / "analyzer.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Instância global do logger
logger = setup_logger()
