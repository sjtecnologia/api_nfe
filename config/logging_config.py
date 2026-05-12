"""
Configuração centralizada de logging.
Substitui os 239+ print() espalhados por routes e services.
"""
import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    """
    Configura o logging da aplicação.
    Deve ser chamado em app.py antes de registrar blueprints.

    Uso em app.py:
        from config.logging_config import configure_logging
        configure_logging()

    Uso nos módulos (em vez de print()):
        import logging
        logger = logging.getLogger(__name__)

        logger.info("Operação bem-sucedida: %s", descricao)
        logger.warning("Atenção: %s", aviso)
        logger.error("Falha em %s: %s", operacao, e, exc_info=True)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Silenciar logs excessivamente verbosos de libs externas
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
