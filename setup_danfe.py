"""
Script para instalar dependências necessárias para geração de DANFE
"""

import os
import sys
import subprocess
import platform
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("setup_danfe.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("setup_danfe")

def check_pip():
    """Verifica se pip está instalado"""
    try:
        import pip
        return True
    except ImportError:
        logger.error("pip não está instalado. Por favor, instale o pip primeiro.")
        return False

def install_packages():
    """Instala os pacotes necessários"""
    logger.info("Instalando pacotes básicos...")
    
    # Pacotes básicos que devem funcionar em todas as plataformas
    base_packages = [
        "reportlab",
        "lxml",
        "Pillow"
    ]
    
    for package in base_packages:
        try:
            logger.info(f"Instalando {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            logger.info(f"{package} instalado com sucesso!")
        except subprocess.CalledProcessError as e:
            logger.error(f"Erro ao instalar {package}: {e}")
    
    # Tentar instalar bibliotecas específicas para NFe
    nfe_packages = []
    
    # Determinar qual pacote de NFe instalar baseado no sistema operacional
    system = platform.system().lower()
    
    if system == "linux":
        logger.info("Sistema Linux detectado - tentando instalar python-nfe...")
        try:
            # python-nfe tem mais chances de funcionar bem no Linux
            subprocess.check_call([sys.executable, "-m", "pip", "install", "python-nfe"])
            logger.info("python-nfe instalado com sucesso!")
        except subprocess.CalledProcessError:
            logger.warning("Não foi possível instalar python-nfe. Tentando alternativas...")
            try:
                # Alternativa: instalar diretamente do GitHub
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", 
                    "git+https://github.com/TadaSoftware/PyNFe.git#egg=pynfe"
                ])
                logger.info("python-nfe instalado do GitHub com sucesso!")
            except subprocess.CalledProcessError:
                logger.error("Não foi possível instalar python-nfe do GitHub.")
    
    elif system == "darwin":  # macOS
        logger.info("Sistema macOS detectado - tentando instalar bibliotecas compatíveis...")
        try:
            # Tentar instalar python-brasil que é mais moderna e compatível
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "python-brasil"
            ])
            logger.info("python-brasil instalado com sucesso!")
        except subprocess.CalledProcessError:
            logger.warning("Não foi possível instalar python-brasil. Tentando pysped...")
            try:
                # Alternativa: instalar pysped do GitHub
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", 
                    "git+https://github.com/akretion/pysped.git#egg=pysped"
                ])
                logger.info("pysped instalado do GitHub com sucesso!")
            except subprocess.CalledProcessError:
                logger.error("Não foi possível instalar pysped.")
    
    elif system == "windows":
        logger.info("Sistema Windows detectado - tentando instalar bibliotecas compatíveis...")
        try:
            # No Windows, tente instalar python-brasil primeiro
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "python-brasil"
            ])
            logger.info("python-brasil instalado com sucesso!")
        except subprocess.CalledProcessError:
            logger.warning("Não foi possível instalar python-brasil no Windows.")
    
    logger.info("Instalação das dependências concluída!")
    logger.info("Se ocorrerem erros durante a geração do DANFE, você pode precisar instalar manualmente as bibliotecas.")

if __name__ == "__main__":
    if not check_pip():
        sys.exit(1)
    
    install_packages()
    
    logger.info("Verificando se as instalações foram bem-sucedidas...")
    
    try:
        import reportlab
        logger.info(f"ReportLab instalado: versão {reportlab.__version__}")
    except ImportError:
        logger.error("ReportLab não foi instalado corretamente.")
    
    try:
        import lxml
        logger.info(f"lxml instalado: versão {lxml.__version__}")
    except ImportError:
        logger.error("lxml não foi instalado corretamente.")
    
    # Verificar se pelo menos uma biblioteca de NFe está disponível
    danfe_lib_found = False
    
    try:
        import pynfe
        logger.info(f"python-nfe instalado")
        danfe_lib_found = True
    except ImportError:
        logger.warning("python-nfe não está disponível.")
    
    try:
        import pysped
        logger.info(f"pysped instalado")
        danfe_lib_found = True
    except ImportError:
        logger.warning("pysped não está disponível.")
    
    try:
        logger.info(f"python-brasil instalado")
        danfe_lib_found = True
    except ImportError:
        logger.warning("python-brasil não está disponível.")
    
    if danfe_lib_found:
        logger.info("Pelo menos uma biblioteca de NFe foi instalada com sucesso!")
    else:
        logger.error("AVISO: Nenhuma biblioteca de NFe foi instalada. O DANFE será gerado em formato simplificado usando ReportLab.")
    
    logger.info("Configuração concluída!")