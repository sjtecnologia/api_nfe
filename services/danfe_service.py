import os
import tempfile
from datetime import datetime
import logging
import importlib
import sys
import subprocess
import base64
import json
import traceback
import shutil
from typing import Dict, List, Optional, Any, Union, cast

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_library_version(library_name: str) -> str:
    """Obtém a versão de uma biblioteca instalada"""
    try:
        # Tentar primeiro usando importlib.metadata (Python 3.8+)
        try:
            import importlib.metadata as metadata
            return metadata.version(library_name)
        except (ImportError, AttributeError):
            pass
            
        # Fallback para pkg_resources
        try:
            import pkg_resources
            return pkg_resources.get_distribution(library_name).version
        except (ImportError, Exception):
            pass
        
        # Último recurso - tentar obter diretamente do pacote
        try:
            module = importlib.import_module(library_name)
            return getattr(module, '__version__', 'Desconhecida')
        except ImportError:
            pass
            
        return "Não instalado"
    except Exception:
        return "Erro ao determinar versão"

def check_module_exists(module_name: str) -> bool:
    """Verifica se um módulo está disponível sem importá-lo diretamente"""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False

def safe_import(module_name: str, package: Optional[str] = None) -> Optional[Any]:
    """Importa um módulo de forma segura ou retorna None"""
    try:
        return importlib.import_module(module_name, package)
    except ImportError:
        return None

def install_package(package: str) -> bool:
    """Tenta instalar um pacote usando pip"""
    try:
        logger.info(f"Tentando instalar o pacote: {package}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        logger.error(f"Falha ao instalar o pacote: {package}")
        return False

def extract_basic_info_from_xml(xml_content: Union[str, bytes]) -> Dict[str, str]:
    """
    Extrai informações básicas do XML da NFe usando manipulação de strings
    Este método é um fallback quando lxml não está disponível
    """
    info = {
        "nfe_num": "N/A",
        "serie": "N/A",
        "emitente": "N/A",
        "destinatario": "N/A",
        "valor": "N/A",
        "chave": "N/A"
    }
    
    try:
        # Garantir que estamos trabalhando com uma string
        xml_str = xml_content.decode('utf-8') if isinstance(xml_content, bytes) else xml_content
        
        # Extração básica por string - não é elegante mas é um fallback
        if "<nNF>" in xml_str and "</nNF>" in xml_str:
            start = xml_str.find("<nNF>") + len("<nNF>")
            end = xml_str.find("</nNF>")
            info["nfe_num"] = xml_str[start:end]
            
        if "<serie>" in xml_str and "</serie>" in xml_str:
            start = xml_str.find("<serie>") + len("<serie>")
            end = xml_str.find("</serie>")
            info["serie"] = xml_str[start:end]
        
        if "<xNome>" in xml_str and "</xNome>" in xml_str:
            start = xml_str.find("<emit>")
            end = xml_str.find("</emit>")
            emit_section = xml_str[start:end] if start >= 0 and end >= 0 else ""
            
            if "<xNome>" in emit_section and "</xNome>" in emit_section:
                start = emit_section.find("<xNome>") + len("<xNome>")
                end = emit_section.find("</xNome>")
                info["emitente"] = emit_section[start:end]
        
        if "<dest>" in xml_str and "</dest>" in xml_str:
            start = xml_str.find("<dest>")
            end = xml_str.find("</dest>")
            dest_section = xml_str[start:end] if start >= 0 and end >= 0 else ""
            
            if "<xNome>" in dest_section and "</xNome>" in dest_section:
                start = dest_section.find("<xNome>") + len("<xNome>")
                end = dest_section.find("</xNome>")
                info["destinatario"] = dest_section[start:end]
        
        if "<vNF>" in xml_str and "</vNF>" in xml_str:
            start = xml_str.find("<vNF>") + len("<vNF>")
            end = xml_str.find("</vNF>")
            info["valor"] = xml_str[start:end]
        
        if "<chNFe>" in xml_str and "</chNFe>" in xml_str:
            start = xml_str.find("<chNFe>") + len("<chNFe>")
            end = xml_str.find("</chNFe>")
            info["chave"] = xml_str[start:end]
    
    except Exception as e:
        logger.error(f"Erro ao extrair informações do XML: {str(e)}")
    
    return info

def generate_danfe_nfelib(xml_content: Union[str, bytes], output_pdf_path: str, logo_path: Optional[str] = None, fone_emitente: Optional[str] = None) -> bool:
    """
    Gera o DANFE oficial usando a biblioteca nfelib
    
    Args:
        xml_content: Conteúdo XML da NFe
        output_pdf_path: Caminho para salvar o PDF
        logo_path: Caminho opcional para o logo da empresa
        fone_emitente: Telefone do emitente para injetar no XML se não estiver presente
        
    Returns:
        bool: True se gerado com sucesso, False caso contrário
    """
    try:
        print("\n" + "=" * 80)
        print("DENTRO DE generate_danfe_nfelib")
        print("=" * 80)
        logger.info("[START] Tentando gerar DANFE oficial usando nfelib")
        print("[START] Tentando gerar DANFE oficial usando nfelib")
        
        # Garantir que xml_content é string
        xml_str = xml_content.decode('utf-8') if isinstance(xml_content, bytes) else xml_content
        
        # ⚠️ CORREÇÃO: Remover tags IBS/CBS temporariamente para compatibilidade com nfelib
        # A biblioteca ainda não suporta essas tags da LC 214/2025
        if '<IBSCBS>' in xml_str or '<IBSCBSTot>' in xml_str:
            print("[!] Removendo tags IBS/CBS para compatibilidade com nfelib...")
            logger.info("[!] XML contém tags IBS/CBS - removendo para gerar DANFE")
            
            # Remover tags <IBSCBS> dos itens
            import re
            xml_str = re.sub(r'<IBSCBS>.*?</IBSCBS>', '', xml_str, flags=re.DOTALL)
            
            # Remover tags <IBSCBSTot> e <vNFTot> dos totais
            xml_str = re.sub(r'<IBSCBSTot>.*?</IBSCBSTot>', '', xml_str, flags=re.DOTALL)
            xml_str = re.sub(r'<vNFTot>.*?</vNFTot>', '', xml_str, flags=re.DOTALL)
            
            print("[OK] Tags IBS/CBS removidas para geração do DANFE")
        
        # ⚠️ CORREÇÃO: brazilfiscalreport busca <fone> como filho DIRETO de <dest>,
        # mas o padrão NFe coloca <fone> dentro de <enderDest>.
        # Copiamos o fone de <enderDest> para direto em <dest> (antes de </dest>).
        import re as _re
        def _inject_fone_no_dest(xml_s: str) -> str:
            def _substituir(m):
                bloco_dest = m.group(0)
                # Se já tem <fone> diretamente (não dentro de sub-tag)
                if _re.search(r'<fone>[^<]+</fone>', bloco_dest):
                    return bloco_dest
                # Tentar extrair <fone> de dentro de <enderDest>
                fone_match = _re.search(r'<enderDest>.*?<fone>([^<]+)</fone>.*?</enderDest>', bloco_dest, _re.DOTALL)
                if fone_match:
                    fone_val = fone_match.group(1)
                    # Inserir <fone> antes de </dest>
                    bloco_dest = bloco_dest.replace('</dest>', f'<fone>{fone_val}</fone></dest>', 1)
                    print(f"[OK] fone do destinatário injetado no <dest>: {fone_val}")
                return bloco_dest
            return _re.sub(r'<dest>.*?</dest>', _substituir, xml_s, flags=_re.DOTALL)
        xml_str = _inject_fone_no_dest(xml_str)
        print("[OK] Pré-processamento do fone do destinatário concluído")

        # ⚠️ CORREÇÃO: brazilfiscalreport busca <fone> como filho DIRETO de <emit>,
        # mas o nfelib coloca <fone> dentro de <enderEmit>.
        # Copiamos o fone de <enderEmit> para direto em <emit> (antes de </emit>).
        def _inject_fone_no_emit(xml_s: str) -> str:
            def _substituir_emit(m):
                bloco_emit = m.group(0)
                # Verificar se já tem <fone> diretamente em <emit> (fora de <enderEmit>)
                # Remove bloco enderEmit para checar apenas filhos diretos de emit
                bloco_sem_ender = _re.sub(r'<enderEmit>.*?</enderEmit>', '', bloco_emit, flags=_re.DOTALL)
                if '<fone>' in bloco_sem_ender:
                    return bloco_emit  # já tem fone direto, nada a fazer
                # Usar fone_emitente do banco de dados (passado como parâmetro)
                if fone_emitente:
                    fone_val = ''.join(ch for ch in fone_emitente if ch.isdigit())[:14]
                    if len(fone_val) >= 6:
                        bloco_emit = bloco_emit.replace('</emit>', f'<fone>{fone_val}</fone></emit>', 1)
                        print(f"[OK] fone do emitente injetado no <emit> (via banco): {fone_val}")
                return bloco_emit
            return _re.sub(r'<emit>.*?</emit>', _substituir_emit, xml_s, flags=_re.DOTALL)
        xml_str = _inject_fone_no_emit(xml_str)
        print("[OK] Pré-processamento do fone do emitente concluído")
        
        # Verificar se já é nfeProc ou se precisa extrair NFe
        is_nfeproc = "<nfeProc" in xml_str
        print(f"[?] XML tipo: {'nfeProc (com protocolo)' if is_nfeproc else 'NFe simples'}")
        
        try:
            # Detectar se é NFe ou NFCe pelo modelo
            is_nfce = "<mod>65</mod>" in xml_str
            
            if is_nfce:
                logger.info("[?] Detectada NFCe (modelo 65)")
                # Para NFCe, usar binding específico se disponível
                from nfelib.nfe.bindings.v4_0.proc_nfe_v4_00 import NfeProc
                
                try:
                    nfe_proc = NfeProc.from_xml(xml_str)
                    logger.info("[OK] NFCe carregada com sucesso")
                    
                    # Gerar PDF usando nfelib com engine padrão
                    pdf_bytes = nfe_proc.to_pdf()
                    
                    # Salvar o arquivo
                    with open(output_pdf_path, 'wb') as f:
                        f.write(pdf_bytes)
                    
                    logger.info(f"[OK] DANFE NFCe gerado com sucesso: {output_pdf_path}")
                    return True
                    
                except Exception as e:
                    logger.warning(f"[X] Erro específico com NFCe: {str(e)}")
                    # Continuar com processamento normal de NFe
            
            # Processar como NFe normal
            logger.info("[?] Processando como NFe")
            print("[?] Processando como NFe")
            
            # Importar bindings corretos baseado na versão
            NfeProc = None
            try:
                # Tentar versão 4.0 primeiro (mais comum)
                print("[?] Tentando importar bindings v4.0...")
                from nfelib.nfe.bindings.v4_0.proc_nfe_v4_00 import NfeProc
                logger.info("[?] Usando bindings v4.0")
                print("[OK] Bindings v4.0 importados com sucesso")
            except ImportError as e:
                print(f"[X] Falha ao importar v4.0: {str(e)}")
                try:
                    # Fallback para versão 3.1 (corrigindo o path)
                    print("[?] Tentando importar bindings v3.1...")
                    from nfelib.nfe.bindings.v3_1.proc_nfe_v3_10 import NfeProc  # type: ignore
                    logger.info("[?] Usando bindings v3.1")
                    print("[OK] Bindings v3.1 importados com sucesso")
                except ImportError as e2:
                    print(f"[X] Falha ao importar v3.1: {str(e2)}")
                    logger.error("[X] Não foi possível importar bindings da nfelib")
                    print("[X] Não foi possível importar bindings da nfelib")
                    return False
            
            if NfeProc is None:
                logger.error("[X] Não foi possível definir classe NfeProc")
                return False
            
            # Carregar NFe do XML
            try:
                print("[?] Tentando carregar NFe do XML...")
                print(f"[?] Tamanho do XML: {len(xml_str)} caracteres")
                print(f"[LOG] Primeiros 500 chars: {xml_str[:500]}")
                
                # Limpar XML duplicado se houver
                if xml_str.count('<?xml') > 1:
                    print("[!] XML duplicado detectado, limpando...")
                    # Manter apenas a primeira declaração XML e o conteúdo após ela
                    parts = xml_str.split('<?xml', 2)
                    if len(parts) > 2:
                        xml_str = '<?xml' + parts[1] + parts[2].split('?>', 1)[1] if '?>' in parts[2] else parts[2]
                        print(f"[OK] XML limpo, novo tamanho: {len(xml_str)}")
                
                nfe_proc = NfeProc.from_xml(xml_str)
                logger.info("[OK] NFe carregada do XML com sucesso")
                print("[OK] NFe carregada do XML com sucesso")
                
                # Extrair informações básicas para log
                try:
                    nfe_num = nfe_proc.NFe.infNFe.ide.nNF
                    serie = nfe_proc.NFe.infNFe.ide.serie
                    emitente = nfe_proc.NFe.infNFe.emit.xNome
                    logger.info(f"[LIST] NFe #{nfe_num}, Série {serie}, Emitente: {emitente}")
                    print(f"[LIST] NFe #{nfe_num}, Série {serie}, Emitente: {emitente}")
                except Exception as e:
                    logger.info("[LIST] NFe carregada (detalhes não disponíveis)")
                    print(f"[!] Não foi possível extrair detalhes: {e}")
                
            except Exception as e:
                logger.warning(f"[!] NfeProc.from_xml falhou (usando XML direto): {str(e)}")
                print(f"[!] NfeProc.from_xml falhou (continuando com XML direto): {str(e)}")
                nfe_proc = None
            
            # Gerar PDF usando brazilfiscalreport diretamente com o XML pré-processado
            # (que já tem <fone> injetado). Não usar nfe_proc.to_pdf() pois ele re-serializa
            # o XML via xsdata perdendo o <fone> injetado.
            try:
                logger.info("[?] Gerando PDF com brazilfiscalreport diretamente...")
                print("[?] Gerando PDF com brazilfiscalreport diretamente...")
                
                from brazilfiscalreport.danfe import Danfe as BFRDanfe
                xml_bytes = xml_str.encode('utf-8') if isinstance(xml_str, str) else xml_str
                
                pdf_bytes = None
                used_method = None
                
                # Método 1: Com logo
                if logo_path and os.path.exists(logo_path):
                    try:
                        from brazilfiscalreport.danfe import DanfeConfig
                        config = DanfeConfig(logo=logo_path)
                        pdf_bytes = bytes(BFRDanfe(xml=xml_bytes, config=config).output(dest="S"))
                        used_method = "com logo"
                        print(f"[OK] PDF gerado com logo: {len(pdf_bytes)} bytes")
                    except Exception as e:
                        logger.warning(f"[!] Erro ao gerar com logo: {e}")
                        print(f"[!] Erro ao gerar com logo: {e}")
                
                # Método 2: Sem logo
                if not pdf_bytes:
                    pdf_bytes = bytes(BFRDanfe(xml=xml_bytes).output(dest="S"))
                    used_method = "sem logo"
                    print(f"[OK] PDF gerado sem logo: {len(pdf_bytes)} bytes")
                
                if not pdf_bytes:
                    logger.error("[X] Nenhum método de geração de PDF funcionou")
                    print("[X] Todas as tentativas de gerar PDF falharam")
                    return False
                
                logger.info(f"[OK] PDF gerado ({used_method})")
                print(f"[OK] PDF gerado usando: {used_method}")
                
                # Salvar o arquivo
                with open(output_pdf_path, 'wb') as f:
                    f.write(pdf_bytes)
                
                # Verificar se o arquivo foi criado
                if os.path.exists(output_pdf_path) and os.path.getsize(output_pdf_path) > 0:
                    logger.info(f"[OK] DANFE nfelib gerado com sucesso: {output_pdf_path}")
                    logger.info(f"[DATA] Tamanho do arquivo: {os.path.getsize(output_pdf_path)} bytes")
                    return True
                else:
                    logger.error("[X] Arquivo PDF não foi criado corretamente")
                    return False
                    
            except Exception as e:
                logger.error(f"[X] Erro ao gerar PDF: {str(e)}")
                traceback.print_exc()
                return False
            
        except ImportError as e:
            logger.error(f"[X] Erro ao importar nfelib: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"[X] Erro geral com nfelib: {str(e)}")
            traceback.print_exc()
            return False
            
    except Exception as e:
        logger.error(f"[X] Erro crítico ao usar nfelib: {str(e)}")
        traceback.print_exc()
        return False

def generate_danfe_reportlab_enhanced(xml_content: Union[str, bytes], output_pdf_path: str, logo_path: Optional[str] = None) -> bool:
    """
    Gera um DANFE aprimorado usando ReportLab como fallback
    """
    try:
        logger.info("[?] Gerando DANFE usando ReportLab (versão aprimorada)")
        
        # Tentar instalar ReportLab se não estiver disponível
        if not check_module_exists('reportlab'):
            logger.info("ReportLab não encontrado, tentando instalar...")
            if not install_package('reportlab'):
                return False
        
        # Importar ReportLab
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        
        # Tentar extrair informações do XML
        nfe_info: Dict[str, Any] = {
            'nfe_num': 'N/A',
            'serie': 'N/A',
            'emitente': 'N/A',
            'emit_cnpj': 'N/A',
            'emit_endereco': 'N/A',
            'emit_cidade': 'N/A',
            'emit_uf': 'N/A',
            'destinatario': 'N/A',
            'dest_cnpj': 'N/A',
            'dest_endereco': 'N/A',
            'dest_cidade': 'N/A',
            'dest_uf': 'N/A',
            'valor': 'N/A',
            'data_emissao': 'N/A',
            'nat_op': 'N/A',
            'chave': 'N/A',
            'protocolo': 'N/A',
            'produtos': []
        }
        
        try:
            # Tentar usar lxml se disponível
            if check_module_exists('lxml'):
                try:
                    from lxml import etree  # type: ignore
                    
                    xml_bytes = xml_content
                    if isinstance(xml_content, str):
                        xml_bytes = xml_content.encode('utf-8')
                        
                    root = etree.fromstring(xml_bytes)
                    namespace = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
                    
                    def extract_text(xpath_expr: str) -> str:
                        result = root.xpath(xpath_expr, namespaces=namespace)
                        return result[0] if result else 'N/A'
                    
                    # Extrair dados básicos
                    nfe_info['nfe_num'] = extract_text('//ns:nNF/text()')
                    nfe_info['serie'] = extract_text('//ns:serie/text()')
                    nfe_info['emitente'] = extract_text('//ns:emit/ns:xNome/text()')
                    nfe_info['emit_cnpj'] = extract_text('//ns:emit/ns:CNPJ/text()')
                    nfe_info['emit_endereco'] = extract_text('//ns:emit/ns:enderEmit/ns:xLgr/text()')
                    nfe_info['emit_cidade'] = extract_text('//ns:emit/ns:enderEmit/ns:xMun/text()')
                    nfe_info['emit_uf'] = extract_text('//ns:emit/ns:enderEmit/ns:UF/text()')
                    nfe_info['destinatario'] = extract_text('//ns:dest/ns:xNome/text()')
                    
                    # Tentar CNPJ, se não existir, tentar CPF
                    dest_cnpj = root.xpath('//ns:dest/ns:CNPJ/text()', namespaces=namespace)
                    if dest_cnpj:
                        nfe_info['dest_cnpj'] = dest_cnpj[0]
                    else:
                        dest_cpf = root.xpath('//ns:dest/ns:CPF/text()', namespaces=namespace)
                        nfe_info['dest_cnpj'] = dest_cpf[0] if dest_cpf else 'N/A'
                        
                    nfe_info['dest_endereco'] = extract_text('//ns:dest/ns:enderDest/ns:xLgr/text()')
                    nfe_info['dest_cidade'] = extract_text('//ns:dest/ns:enderDest/ns:xMun/text()')
                    nfe_info['dest_uf'] = extract_text('//ns:dest/ns:enderDest/ns:UF/text()')
                    nfe_info['valor'] = extract_text('//ns:ICMSTot/ns:vNF/text()')
                    nfe_info['data_emissao'] = extract_text('//ns:dhEmi/text()')
                    nfe_info['nat_op'] = extract_text('//ns:natOp/text()')
                    nfe_info['chave'] = extract_text('//ns:chNFe/text()')
                    nfe_info['protocolo'] = extract_text('//ns:nProt/text()')
                    
                    # Extrair produtos
                    produtos: List[Dict[str, str]] = []
                    for i, det in enumerate(root.xpath('//ns:det', namespaces=namespace)):
                        prod = det.xpath('./ns:prod', namespaces=namespace)
                        if prod:
                            prod_elem = prod[0]
                            
                            def extract_prod_text(xpath_expr: str) -> str:
                                result = prod_elem.xpath(xpath_expr, namespaces=namespace)
                                return result[0] if result else 'N/A'
                            
                            produto: Dict[str, str] = {
                                'num': str(i+1),
                                'codigo': extract_prod_text('./ns:cProd/text()'),
                                'descricao': extract_prod_text('./ns:xProd/text()'),
                                'ncm': extract_prod_text('./ns:NCM/text()'),
                                'cfop': extract_prod_text('./ns:CFOP/text()'),
                                'quantidade': extract_prod_text('./ns:qCom/text()'),
                                'unidade': extract_prod_text('./ns:uCom/text()'),
                                'valor_unitario': extract_prod_text('./ns:vUnCom/text()'),
                                'valor_total': extract_prod_text('./ns:vProd/text()'),
                            }
                            produtos.append(produto)
                    
                    nfe_info['produtos'] = produtos
                    
                except Exception as e:
                    logger.warning(f"Erro ao extrair com lxml: {str(e)}")
                    # Fallback para extração manual
                    basic_info = extract_basic_info_from_xml(xml_content)
                    for key, value in basic_info.items():
                        if key in nfe_info:
                            nfe_info[key] = value
            else:
                # Fallback para extração manual
                basic_info = extract_basic_info_from_xml(xml_content)
                for key, value in basic_info.items():
                    if key in nfe_info:
                        nfe_info[key] = value
        
        except Exception as e:
            logger.error(f"Erro ao extrair informações do XML: {str(e)}")
            basic_info = extract_basic_info_from_xml(xml_content)
            for key, value in basic_info.items():
                if key in nfe_info:
                    nfe_info[key] = value
        
        # Criar PDF
        c = canvas.Canvas(output_pdf_path, pagesize=A4)
        width, height = A4
        
        # Desenhar borda da página
        c.rect(10*mm, 10*mm, width-20*mm, height-20*mm, stroke=1, fill=0)
        
        # Adicionar logo se disponível
        y_offset = 0
        if logo_path and os.path.exists(logo_path):
            try:
                c.drawImage(logo_path, 20*mm, height-50*mm, width=30*mm, height=20*mm, preserveAspectRatio=True)
                y_offset = 25*mm
            except Exception as e:
                logger.warning(f"Erro ao adicionar logo: {str(e)}")
        
        # Título
        c.setFont('Helvetica-Bold', 14)
        c.drawCentredString(width/2, height-30*mm-y_offset, "DOCUMENTO AUXILIAR DA NOTA FISCAL ELETRÔNICA")
        c.setFont('Helvetica', 10)
        c.drawCentredString(width/2, height-35*mm-y_offset, "DANFE - SIMPLIFICADO")
        c.drawCentredString(width/2, height-40*mm-y_offset, f"NF-e nº {nfe_info['nfe_num']} - Série {nfe_info['serie']}")
        
        # Dados do emitente
        y_pos = height-55*mm-y_offset
        c.setFont('Helvetica-Bold', 12)
        c.drawString(20*mm, y_pos, "EMITENTE")
        c.setFont('Helvetica', 10)
        c.drawString(20*mm, y_pos-5*mm, f"Razão Social: {nfe_info['emitente']}")
        c.drawString(20*mm, y_pos-10*mm, f"CNPJ: {nfe_info['emit_cnpj']}")
        c.drawString(20*mm, y_pos-15*mm, f"Endereço: {nfe_info['emit_endereco']}, {nfe_info['emit_cidade']}/{nfe_info['emit_uf']}")
        
        # Dados do destinatário
        y_pos -= 25*mm
        c.setFont('Helvetica-Bold', 12)
        c.drawString(20*mm, y_pos, "DESTINATÁRIO")
        c.setFont('Helvetica', 10)
        c.drawString(20*mm, y_pos-5*mm, f"Razão Social: {nfe_info['destinatario']}")
        c.drawString(20*mm, y_pos-10*mm, f"CNPJ/CPF: {nfe_info['dest_cnpj']}")
        c.drawString(20*mm, y_pos-15*mm, f"Endereço: {nfe_info['dest_endereco']}, {nfe_info['dest_cidade']}/{nfe_info['dest_uf']}")
        
        # Dados gerais da nota
        y_pos -= 25*mm
        c.setFont('Helvetica-Bold', 12)
        c.drawString(20*mm, y_pos, "DADOS DA NOTA")
        c.setFont('Helvetica', 10)
        c.drawString(20*mm, y_pos-5*mm, f"Natureza da Operação: {nfe_info['nat_op']}")
        c.drawString(20*mm, y_pos-10*mm, f"Data de Emissão: {nfe_info['data_emissao']}")
        c.drawString(20*mm, y_pos-15*mm, f"Valor Total: R$ {nfe_info['valor']}")
        c.drawString(20*mm, y_pos-20*mm, f"Protocolo de Autorização: {nfe_info['protocolo']}")
        
        # Chave de acesso
        y_pos -= 30*mm
        c.setFont('Helvetica-Bold', 11)
        c.drawString(20*mm, y_pos, "Chave de Acesso:")
        c.setFont('Courier', 10)
        c.drawString(20*mm, y_pos-5*mm, nfe_info['chave'])
        
        # Produtos (se houver espaço)
        produtos = cast(List[Dict[str, str]], nfe_info.get('produtos', []))
        if produtos and y_pos > 100*mm:
            y_pos -= 15*mm
            c.setFont('Helvetica-Bold', 12)
            c.drawString(20*mm, y_pos, "PRODUTOS / SERVIÇOS")
            y_pos -= 10*mm
            
            # Cabeçalho da tabela
            headers = ['#', 'Código', 'Descrição', 'Qtd', 'V.Unit', 'V.Total']
            table_data = [headers]
            
            # Dados dos produtos (limitar para caber na página)
            max_produtos = min(len(produtos), 10)  # Máximo 10 produtos
            for i in range(max_produtos):
                produto = produtos[i]
                table_data.append([
                    produto.get('num', 'N/A'),
                    produto.get('codigo', 'N/A')[:15],  # Limitar tamanho
                    produto.get('descricao', 'N/A')[:40],
                    produto.get('quantidade', 'N/A'),
                    produto.get('valor_unitario', 'N/A'),
                    produto.get('valor_total', 'N/A')
                ])
            
            # Criar tabela
            col_widths = [10*mm, 30*mm, 80*mm, 20*mm, 25*mm, 25*mm]
            table = Table(table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
                ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
            ]))
            
            try:
                table.wrapOn(c, width-40*mm, 200*mm)
                table.drawOn(c, 20*mm, max(y_pos - len(table_data)*8*mm - 20*mm, 40*mm))
            except Exception as e:
                logger.warning(f"Erro ao adicionar tabela de produtos: {str(e)}")
        
        # Rodapé
        c.setFont('Helvetica', 8)
        c.drawString(20*mm, 25*mm, "DOCUMENTO AUXILIAR - CONSULTE A AUTENTICIDADE NO SITE DA SEFAZ")
        c.drawString(20*mm, 20*mm, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        c.drawString(20*mm, 15*mm, "Gerado por nfelib + ReportLab")
        
        # Finalizar PDF
        c.save()
        
        if os.path.exists(output_pdf_path):
            logger.info(f"[OK] DANFE aprimorado gerado com ReportLab: {output_pdf_path}")
            return True
        else:
            logger.error("[X] Erro ao salvar PDF com ReportLab")
            return False
        
    except Exception as e:
        logger.error(f"[X] Erro ao gerar PDF aprimorado: {str(e)}")
        traceback.print_exc()
        return False

def generate_danfe(xml_content: Union[str, bytes], nfe_id: Union[int, str], cliente_id: Optional[int] = None) -> str:
    """
    Gera o DANFE a partir do XML da NFe usando diferentes abordagens,
    priorizando a biblioteca nfelib.
    
    Args:
        xml_content: Conteúdo XML da NFe
        nfe_id: ID da NFe para nomear o arquivo
        cliente_id: ID do cliente (opcional, para buscar logo personalizada)
        
    Returns:
        str: Caminho do arquivo PDF gerado
    """
    try:
        # Verificar/criar diretório para os arquivos DANFE
        danfe_dir = os.path.join('static', 'danfe')
        os.makedirs(danfe_dir, exist_ok=True)
        
        # Caminho de saída para o PDF
        output_pdf_path = os.path.join(danfe_dir, f'danfe_{nfe_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.pdf')
        permanent_path = os.path.join(danfe_dir, f'danfe_{nfe_id}.pdf')
        
        # Buscar logo do cliente (prioridade) ou logo padrão
        logo_path = None
        fone_emitente = None
        
        # 1. Tentar buscar logo e telefone do cliente no banco de dados
        if cliente_id:
            try:
                from database.connection import SessionLocal
                from sqlalchemy import text
                db = SessionLocal()
                
                # Verificar se a coluna logo_path existe antes de consultar
                check_column = db.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'clientes' 
                    AND column_name = 'logo_path'
                """)).fetchone()
                
                if check_column:
                    result = db.execute(text("SELECT logo_path FROM clientes WHERE cliente_id = :cid"), {'cid': cliente_id}).fetchone()
                    if result and result[0]:
                        # result[0] já contém caminho relativo como 'logos/cliente_123.png'
                        cliente_logo = os.path.join('static', result[0])
                        # Converter para caminho absoluto
                        cliente_logo_abs = os.path.abspath(cliente_logo)
                        logger.info(f"[SEARCH] Verificando logo: relativo={cliente_logo}, absoluto={cliente_logo_abs}")
                        print(f"[SEARCH] Verificando logo: relativo={cliente_logo}, absoluto={cliente_logo_abs}")
                        if os.path.exists(cliente_logo_abs):
                            logo_path = cliente_logo_abs
                            logger.info(f"[OK] Logo do cliente encontrada: {logo_path}")
                            print(f"[OK] Logo do cliente encontrada: {logo_path}")
                        else:
                            logger.warning(f"[!] Logo não existe no caminho: {cliente_logo_abs}")
                            print(f"[!] Logo não existe no caminho: {cliente_logo_abs}")
                    else:
                        logger.info(f"ℹ️ Cliente {cliente_id} não tem logo cadastrada")
                        print(f"ℹ️ Cliente {cliente_id} não tem logo cadastrada")
                else:
                    logger.warning(f"[!] Coluna logo_path não existe na tabela clientes - migration não foi executada")
                    print(f"[!] ATENÇÃO: Execute a migration SQL para adicionar logo_path!")
                    
                # Buscar telefone do cliente
                try:
                    fone_row = db.execute(text("SELECT telefone_contato FROM clientes WHERE cliente_id = :cid"), {'cid': cliente_id}).fetchone()
                    if fone_row and fone_row[0]:
                        fone_emitente = fone_row[0]
                        print(f"[OK] Telefone do emitente encontrado: {fone_emitente}")
                except Exception as fe:
                    print(f"[!] Erro ao buscar telefone do cliente: {fe}")
                db.close()
            except Exception as e:
                logger.warning(f"[!] Erro ao buscar logo do cliente: {e}")
                print(f"[!] Erro ao buscar logo do cliente: {e}")
                traceback.print_exc()
        
        # 2. Fallback para logo padrão se não encontrou logo do cliente
        if not logo_path:
            for logo_file in ['logo.png', 'logo.jpg', 'logo_empresa.png', 'logo.jpeg', 'logo.gif']:
                possible_logo = os.path.join('static', 'img', logo_file)
                possible_logo_abs = os.path.abspath(possible_logo)
                if os.path.exists(possible_logo_abs):
                    logo_path = possible_logo_abs
                    logger.info(f"[OK] Logo padrão encontrada: {logo_path}")
                    print(f"[OK] Logo padrão encontrada: {logo_path}")
                    break
            
            if not logo_path:
                logger.warning("[!] Nenhuma logo encontrada (nem do cliente, nem padrão)")
                print("[!] Nenhuma logo encontrada (nem do cliente, nem padrão)")
        
        # Flag para controlar se o DANFE foi gerado
        danfe_generated = False
        
        # MÉTODO 1: Usar nfelib (PRIORIDADE MÁXIMA)
        if not danfe_generated:
            try:
                # Verificar se nfelib está instalada
                print("=" * 80)
                print("INICIANDO GERAÇÃO DE DANFE")
                print(f"NFe ID: {nfe_id}")
                print(f"Output path: {output_pdf_path}")
                print("=" * 80)
                
                nfelib_available = check_module_exists('nfelib')
                print(f"[?] nfelib disponível: {nfelib_available}")
                
                if not nfelib_available:
                    print("[X] nfelib não encontrado, tentando instalar...")
                    logger.info("[?] nfelib não encontrado, tentando instalar...")
                    if install_package('nfelib'):
                        print("[OK] nfelib instalado com sucesso")
                        logger.info("[OK] nfelib instalado com sucesso")
                        nfelib_available = True
                    else:
                        print("[X] Falha ao instalar nfelib")
                        logger.error("[X] Falha ao instalar nfelib")
                else:
                    print("[OK] nfelib está disponível")
                    # Verificar versão
                    nfelib_version = get_library_version('nfelib')
                    print(f"[INFO] nfelib versão: {nfelib_version}")
                
                # Tentar usar nfelib se disponível
                if nfelib_available:
                    print("[START] Chamando generate_danfe_nfelib...")
                    try:
                        resultado = generate_danfe_nfelib(xml_content, output_pdf_path, logo_path, fone_emitente=fone_emitente)
                        print(f"[DATA] Resultado generate_danfe_nfelib: {resultado}")
                        
                        if resultado:
                            # Verificar se arquivo foi realmente criado
                            if os.path.exists(output_pdf_path):
                                file_size = os.path.getsize(output_pdf_path)
                                print(f"[OK] Arquivo PDF criado: {file_size} bytes")
                                
                                if file_size > 1000:
                                    danfe_generated = True
                                    print("[OK] DANFE oficial gerado com sucesso usando nfelib")
                                    logger.info("[OK] DANFE oficial gerado com sucesso usando nfelib")
                                else:
                                    print(f"[X] Arquivo PDF muito pequeno ({file_size} bytes) - provavelmente inválido")
                                    danfe_generated = False
                            else:
                                print("[X] Arquivo PDF não foi criado")
                                danfe_generated = False
                        else:
                            print("[X] generate_danfe_nfelib retornou False")
                            logger.warning("[X] generate_danfe_nfelib retornou False - tentando fallback")
                            danfe_generated = False
                    except Exception as e:
                        print(f"[X] Exceção ao chamar generate_danfe_nfelib: {e}")
                        logger.error(f"[X] Exceção ao chamar generate_danfe_nfelib: {e}")
                        traceback.print_exc()
                        danfe_generated = False
                else:
                    print("[!] nfelib não está disponível após tentativa de instalação")
                    logger.warning("[!] nfelib não está disponível")
                    
            except Exception as e:
                logger.error(f"[X] Erro ao usar nfelib: {str(e)}")
                print(f"[X] Erro geral ao tentar nfelib: {e}")
                traceback.print_exc()
                danfe_generated = False
        
        # MÉTODO 2: API externa se configurada
        if not danfe_generated and check_module_exists('requests'):
            try:
                logger.info("[?] Tentando gerar DANFE usando API externa")
                import requests
                
                api_url = os.environ.get('DANFE_API_URL')
                api_key = os.environ.get('DANFE_API_KEY')
                
                if api_url and api_key:
                    headers = {
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/xml'
                    }
                    
                    response = requests.post(
                        f"{api_url}/generate-danfe",
                        headers=headers,
                        data=xml_content.encode('utf-8') if isinstance(xml_content, str) else xml_content,
                        timeout=30
                    )
                    
                    if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
                        with open(output_pdf_path, 'wb') as f:
                            f.write(response.content)
                        danfe_generated = True
                        logger.info(f"[OK] DANFE gerado com sucesso via API externa")
                    else:
                        logger.warning(f"[X] API retornou status {response.status_code}: {response.text}")
                else:
                    logger.debug("ℹ️ Variáveis de ambiente da API não configuradas")
            except Exception as e:
                logger.error(f"[X] Erro ao usar API externa: {str(e)}")
        
        # MÉTODO 3: ReportLab aprimorado (fallback confiável)
        if not danfe_generated:
            print("[!] DANFE oficial não foi gerado, usando fallback ReportLab (simplificado)")
            logger.warning("[!] Usando fallback ReportLab - DANFE será simplificado")
            try:
                if generate_danfe_reportlab_enhanced(xml_content, output_pdf_path, logo_path):
                    danfe_generated = True
                    logger.info("[OK] DANFE aprimorado gerado com ReportLab")
            except Exception as e:
                logger.error(f"[X] Erro ao usar ReportLab: {str(e)}")
                traceback.print_exc()
        else:
            print("[OK] DANFE oficial gerado - pulando fallbacks")
            logger.info("[OK] DANFE oficial gerado com sucesso - não usando fallbacks")
        
        # MÉTODO 4: Último recurso - arquivo de texto
        if not danfe_generated:
            logger.warning("[!] Todas as tentativas de PDF falharam, criando arquivo de texto")
            txt_path = output_pdf_path.replace('.pdf', '.txt')
            
            try:
                nfe_info = extract_basic_info_from_xml(xml_content)
                
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write("=========================================\n")
                    f.write("DANFE SIMPLIFICADO (ARQUIVO DE TEXTO)\n")
                    f.write("=========================================\n\n")
                    f.write(f"Número da NFe: {nfe_info['nfe_num']}\n")
                    f.write(f"Série: {nfe_info['serie']}\n")
                    f.write(f"Emitente: {nfe_info['emitente']}\n")
                    f.write(f"Destinatário: {nfe_info['destinatario']}\n")
                    f.write(f"Valor: R$ {nfe_info['valor']}\n")
                    f.write(f"ID NFe: {nfe_id}\n")
                    f.write(f"Chave de Acesso: {nfe_info['chave']}\n\n")
                    f.write(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
                    f.write("=========================================\n")
                    f.write("AVISO: Não foi possível gerar o DANFE em formato PDF.\n")
                    f.write("Este arquivo de texto é apenas informativo.\n")
                    f.write("Para visualizar o documento oficial, consulte o site da SEFAZ.\n")
                    f.write("=========================================\n")
                    
                output_pdf_path = txt_path
                logger.info(f"[?] Arquivo de texto gerado: {txt_path}")
            except Exception as e:
                logger.error(f"[X] Erro ao criar arquivo de texto: {str(e)}")
        
        # Se o DANFE foi gerado, criar um link permanente
        if os.path.exists(output_pdf_path):
            try:
                shutil.copy2(output_pdf_path, permanent_path)
                logger.info(f"[OK] DANFE permanente salvo em: {permanent_path}")
            except Exception as e:
                logger.error(f"[X] Erro ao criar link permanente: {str(e)}")
        
        return output_pdf_path
        
    except Exception as e:
        logger.error(f"[X] Erro crítico na geração do DANFE: {str(e)}")
        traceback.print_exc()
        
        # Criar arquivo de erro como último recurso
        error_path = os.path.join('static', 'danfe', f'error_danfe_{nfe_id}.txt')
        os.makedirs(os.path.dirname(error_path), exist_ok=True)
        
        try:
            with open(error_path, 'w', encoding='utf-8') as f:
                f.write(f"ERRO CRÍTICO AO GERAR DANFE - NFe #{nfe_id}\n")
                f.write(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write(f"Erro: {str(e)}\n")
                f.write(f"Detalhes: {traceback.format_exc()}\n")
        except:
            pass
        
        return error_path

def test_service() -> None:
    """Testa se o serviço está configurado corretamente"""
    print("[?] Testando serviço de geração de DANFE...")
    print(f"[?] Python version: {sys.version}")
    print("\n[?] Verificando bibliotecas disponíveis:")
    
    # Bibliotecas prioritárias para DANFE
    priority_libs = [
        ("nfelib", "Biblioteca oficial para NFe - PRIORIDADE 1"),
        ("BrazilFiscalReport", "Engine de PDF para nfelib"),
        ("erpbrasil.edoc.pdf", "Engine alternativa de PDF"),
    ]
    
    # Bibliotecas de apoio
    support_libs = [
        ("reportlab", "Geração de PDF fallback"),
        ("lxml", "Parse de XML"),
        ("requests", "API externa"),
    ]
    
    print("\n[?] Bibliotecas para DANFE:")
    for lib, desc in priority_libs:
        status = "[OK] Disponível" if check_module_exists(lib) else "[X] Não disponível"
        version = get_library_version(lib) if check_module_exists(lib) else ""
        version_str = f" (v{version})" if version and version != "Não instalado" else ""
        print(f"  - {lib}: {status}{version_str} - {desc}")
    
    print("\n[?]️ Bibliotecas de apoio:")
    for lib, desc in support_libs:
        status = "[OK] Disponível" if check_module_exists(lib) else "[X] Não disponível"
        version = get_library_version(lib) if check_module_exists(lib) else ""
        version_str = f" (v{version})" if version and version != "Não instalado" else ""
        print(f"  - {lib}: {status}{version_str} - {desc}")
    
    print(f"\n[?]️ Sistema: {os.name}")
    if check_module_exists('platform'):
        import platform
        print(f"[BUILD] Plataforma: {platform.system()} {platform.release()}")
    
    print(f"\n[?] Diretório de saída: {os.path.abspath(os.path.join('static', 'danfe'))}")
    
    # Verificar logos
    logo_dir = os.path.join('static', 'img')
    if os.path.exists(logo_dir):
        logos = [f for f in os.listdir(logo_dir) if f.lower().startswith('logo')]
        if logos:
            print(f"[?] Logos encontrados: {', '.join(logos)}")
        else:
            print("[?] Nenhum logo encontrado em static/img/")
    else:
        print("[?] Diretório de imagens não encontrado")
    
    print("\n[OK] Teste concluído!")
    
    # Recomendações
    if not check_module_exists('nfelib'):
        print("\n[?] RECOMENDAÇÃO PRINCIPAL:")
        print("   pip install nfelib")
        print("   pip install BrazilFiscalReport  # Para geração de PDF")
    
    if not check_module_exists('lxml'):
        print("\n[?] RECOMENDAÇÃO ADICIONAL:")
        print("   pip install lxml  # Para melhor parse de XML")

# Executar teste quando o script for rodado diretamente
if __name__ == "__main__":
    test_service()