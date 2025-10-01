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

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_pynfe_version():
    """Obtém a versão exata do PyNFe instalado"""
    try:
        import pkg_resources
        return pkg_resources.get_distribution("pynfe").version
    except:
        try:
            import pynfe
            return getattr(pynfe, '__version__', 'Desconhecida')
        except:
            return "Não instalado"

def check_module_exists(module_name):
    """Verifica se um módulo está disponível sem importá-lo diretamente"""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False

def safe_import(module_name, package=None):
    """Importa um módulo de forma segura ou retorna None"""
    try:
        return importlib.import_module(module_name, package)
    except ImportError:
        return None

def install_package(package):
    """Tenta instalar um pacote usando pip"""
    try:
        logger.info(f"Tentando instalar o pacote: {package}")
        # Remover a flag --user que causa problemas em ambientes virtuais
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        logger.error(f"Falha ao instalar o pacote: {package}")
        return False

def extract_basic_info_from_xml(xml_content):
    """
    Extrai informações básicas do XML da NFe usando manipulação de strings
    Este método é um fallback quando lxml não está disponível
    """
    info = {
        "nfe_num": "N/A",
        "emitente": "N/A",
        "destinatario": "N/A",
        "valor": "N/A",
        "chave": "N/A"
    }
    
    try:
        if isinstance(xml_content, bytes):
            xml_content = xml_content.decode('utf-8')
        
        # Extração básica por string - não é elegante mas é um fallback
        if "<nNF>" in xml_content and "</nNF>" in xml_content:
            start = xml_content.find("<nNF>") + 5
            end = xml_content.find("</nNF>")
            info["nfe_num"] = xml_content[start:end]
        
        if "<xNome>" in xml_content and "</xNome>" in xml_content:
            start = xml_content.find("<emit>")
            end = xml_content.find("</emit>")
            emit_section = xml_content[start:end]
            
            if "<xNome>" in emit_section and "</xNome>" in emit_section:
                start = emit_section.find("<xNome>") + 7
                end = emit_section.find("</xNome>")
                info["emitente"] = emit_section[start:end]
        
        if "<dest>" in xml_content and "</dest>" in xml_content:
            start = xml_content.find("<dest>")
            end = xml_content.find("</dest>")
            dest_section = xml_content[start:end]
            
            if "<xNome>" in dest_section and "</xNome>" in dest_section:
                start = dest_section.find("<xNome>") + 7
                end = dest_section.find("</xNome>")
                info["destinatario"] = dest_section[start:end]
        
        if "<vNF>" in xml_content and "</vNF>" in xml_content:
            start = xml_content.find("<vNF>") + 5
            end = xml_content.find("</vNF>")
            info["valor"] = xml_content[start:end]
        
        if "<chNFe>" in xml_content and "</chNFe>" in xml_content:
            start = xml_content.find("<chNFe>") + 7
            end = xml_content.find("</chNFe>")
            info["chave"] = xml_content[start:end]
    
    except Exception as e:
        logger.error(f"Erro ao extrair informações do XML: {str(e)}")
    
    return info

def generate_danfe_pynfe(xml_content, output_pdf_path, logo_path=None):
    """
    Gera o DANFE oficial usando a biblioteca PyNFe
    
    Args:
        xml_content: Conteúdo XML da NFe
        output_pdf_path: Caminho para salvar o PDF
        logo_path: Caminho opcional para o logo da empresa
        
    Returns:
        bool: True se gerado com sucesso, False caso contrário
    """
    try:
        # Garantir que a biblioteca PyNFe está instalada
        if not check_module_exists('pynfe'):
            install_package('pynfe')
            
        # Importar módulos do PyNFe - Ajustado para a versão 0.4.1
        from pynfe.processamento.danfe import Danfe
        
        # Verificar se o XML é string ou bytes
        if isinstance(xml_content, str):
            xml_bytes = xml_content.encode('utf-8')
        else:
            xml_bytes = xml_content
        
        # Salvar XML temporariamente
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as temp_xml:
            temp_xml_path = temp_xml.name
            temp_xml.write(xml_bytes)
        
        # Configurar e gerar o DANFE - Ajustado para usar a classe Danfe
        danfe = Danfe(
            arquivo_xml=temp_xml_path,
            logo=logo_path,
            orientacao_retrato=True  # True para retrato (padrão SEFAZ)
        )
        
        # Gerar o DANFE
        danfe.gerar_danfe()
        danfe.salvar_arquivo_pdf(output_pdf_path)
        
        # Remover arquivo temporário
        os.unlink(temp_xml_path)
        
        # Verificar se o PDF foi gerado
        if os.path.exists(output_pdf_path):
            return True
        return False
        
    except Exception as e:
        logger.error(f"Erro ao gerar DANFE com PyNFe: {str(e)}")
        traceback.print_exc()
        return False

def generate_danfe(xml_content, nfe_id):
    """
    Gera o DANFE a partir do XML da NFe usando diferentes abordagens,
    priorizando o DANFE oficial da SEFAZ.
    
    Args:
        xml_content (str): Conteúdo XML da NFe
        nfe_id (int): ID da NFe para nomear o arquivo
        
    Returns:
        str: Caminho do arquivo PDF gerado
    """
    try:
        # Verificar/criar diretório para os arquivos DANFE
        danfe_dir = os.path.join('static', 'danfe')
        os.makedirs(danfe_dir, exist_ok=True)
        
        # Caminho de saída para o PDF
        output_pdf_path = os.path.join(danfe_dir, f'danfe_{nfe_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.pdf')
        
        # Flag para controlar se o DANFE foi gerado
        danfe_generated = False
        
        # MÉTODO 1: Usar PyNFe (prioridade principal para DANFE oficial)
        if not danfe_generated:
            try:
                logger.info("Tentando gerar DANFE oficial usando PyNFe")
                
                # Verificar se PyNFe está instalado, se não, instalar
                if not check_module_exists('pynfe'):
                    logger.info("PyNFe não encontrado, tentando instalar...")
                    install_package('pynfe')
                
                # Verificar novamente se a instalação foi bem-sucedida
                if check_module_exists('pynfe'):
                    # Procurar logo da empresa (opcional)
                    logo_path = None
                    for logo_file in ['logo.png', 'logo.jpg', 'logo_empresa.png']:
                        possible_logo = os.path.join('static', 'img', logo_file)
                        if os.path.exists(possible_logo):
                            logo_path = possible_logo
                            break
                    
                    # Tentar gerar DANFE oficial usando Danfe em vez de DanfeNfe
                    try:
                        from pynfe.processamento.danfe import Danfe
                        
                        # Verificar se o XML é string ou bytes
                        if isinstance(xml_content, str):
                            xml_bytes = xml_content.encode('utf-8')
                        else:
                            xml_bytes = xml_content
                        
                        # Salvar XML temporariamente
                        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as temp_xml:
                            temp_xml_path = temp_xml.name
                            temp_xml.write(xml_bytes)
                        
                        # Configurar e gerar o DANFE
                        danfe = Danfe(
                            arquivo_xml=temp_xml_path,
                            logo=logo_path,
                            orientacao_retrato=True  # True para retrato (padrão SEFAZ)
                        )
                        
                        # Gerar o DANFE
                        danfe.gerar_danfe()
                        danfe.salvar_arquivo_pdf(output_pdf_path)
                        
                        # Remover arquivo temporário
                        os.unlink(temp_xml_path)
                        
                        # Verificar se foi gerado
                        if os.path.exists(output_pdf_path):
                            danfe_generated = True
                            logger.info(f"DANFE oficial gerado com sucesso usando PyNFe: {output_pdf_path}")
                    except Exception as e:
                        logger.error(f"Erro ao gerar DANFE com PyNFe (método direto): {str(e)}")
                        traceback.print_exc()
                        
                        # Tentar método alternativo - algumas versões do PyNFe usam um módulo diferente
                        try:
                            from pynfe.utils.danfe import gerar_danfe
                            
                            # Gerar DANFE diretamente
                            gerar_danfe(
                                lista_xml=[xml_content],
                                logo=logo_path,
                                salvar_arquivo=True,
                                path_output=output_pdf_path
                            )
                            
                            # Verificar se foi gerado
                            if os.path.exists(output_pdf_path):
                                danfe_generated = True
                                logger.info(f"DANFE oficial gerado com sucesso usando PyNFe (método alternativo): {output_pdf_path}")
                        except Exception as e2:
                            logger.error(f"Erro ao gerar DANFE com PyNFe (método alternativo): {str(e2)}")
                else:
                    logger.warning("Não foi possível instalar o PyNFe")
            except Exception as e:
                logger.error(f"Erro ao usar PyNFe: {str(e)}")
                traceback.print_exc()
        
        # MÉTODO 2: Usar Brasil-DFE se disponível
        if not danfe_generated:
            try:
                logger.info("Tentando gerar DANFE oficial usando Brasil-DFE")
                
                # Verificar se brasil.dfe está instalado, se não, tentar instalar
                if not check_module_exists('brasil.dfe'):
                    logger.info("Brasil-DFE não encontrado, tentando instalar...")
                    install_package('brasil.dfe')
                
                if check_module_exists('brasil.dfe'):
                    # Importar Brasil-DFE
                    brasil_dfe = safe_import('brasil.dfe.nfe')
                    
                    if brasil_dfe:
                        # Salvar XML temporariamente
                        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as temp_xml:
                            temp_xml_path = temp_xml.name
                            temp_xml.write(xml_content.encode('utf-8') if isinstance(xml_content, str) else xml_content)
                        
                        # Gerar DANFE
                        danfe = brasil_dfe.danfe.DanfeNFe(temp_xml_path)
                        danfe.gerar_pdf(output_pdf_path)
                        
                        # Verificar se foi gerado
                        if os.path.exists(output_pdf_path):
                            danfe_generated = True
                            logger.info(f"DANFE oficial gerado com sucesso usando Brasil-DFE: {output_pdf_path}")
                        
                        # Remover arquivo temporário
                        os.unlink(temp_xml_path)
            except Exception as e:
                logger.error(f"Erro ao usar Brasil-DFE: {str(e)}")
                traceback.print_exc()
        
        # MÉTODO 3: Usar API externa se configurada
        if not danfe_generated and check_module_exists('requests'):
            try:
                logger.info("Tentando gerar DANFE usando API externa")
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
                        logger.info(f"DANFE gerado com sucesso via API externa: {output_pdf_path}")
                    else:
                        logger.warning(f"API retornou status {response.status_code}: {response.text}")
            except Exception as e:
                logger.error(f"Erro ao usar API externa: {str(e)}")
        
        # MÉTODO 4: Verificar ferramentas externas do sistema
        if not danfe_generated and os.name == 'posix':
            try:
                logger.info("Tentando gerar DANFE usando ferramentas do sistema")
                
                # Verificar ferramentas comuns
                external_tools = [
                    ('/usr/bin/sefaz-tools', 'sefaz-tools --gerar-danfe "{input}" --saida "{output}"'),
                    ('/usr/local/bin/nfe-tools', 'nfe-tools -d "{input}" -o "{output}"'),
                    ('/opt/nfe/danfe-gen', 'danfe-gen "{input}" "{output}"')
                ]
                
                # Salvar XML temporariamente
                with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as temp_xml:
                    temp_xml_path = temp_xml.name
                    temp_xml.write(xml_content.encode('utf-8') if isinstance(xml_content, str) else xml_content)
                
                for tool_path, cmd_template in external_tools:
                    if os.path.exists(tool_path):
                        cmd = cmd_template.format(input=temp_xml_path, output=output_pdf_path)
                        logger.info(f"Executando comando: {cmd}")
                        
                        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        
                        if result.returncode == 0 and os.path.exists(output_pdf_path):
                            danfe_generated = True
                            logger.info(f"DANFE gerado com sucesso usando ferramenta externa: {output_pdf_path}")
                            break
                
                # Remover arquivo temporário
                os.unlink(temp_xml_path)
                
            except Exception as e:
                logger.error(f"Erro ao usar ferramentas externas: {str(e)}")
        
        # MÉTODO 5: Gerar PDF simples com ReportLab como fallback (melhorado)
        if not danfe_generated:
            try:
                logger.info("Tentando gerar PDF usando ReportLab (versão aprimorada)")
                
                # Tentar instalar ReportLab se não estiver disponível
                if not check_module_exists('reportlab'):
                    logger.info("ReportLab não encontrado, tentando instalar...")
                    install_package('reportlab')
                
                # Importar ReportLab
                if check_module_exists('reportlab'):
                    from reportlab.pdfgen import canvas
                    from reportlab.lib.pagesizes import letter, A4
                    from reportlab.lib.units import mm, inch
                    from reportlab.lib import colors
                    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, Image
                    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                    
                    # Tentar extrair informações do XML
                    nfe_info = None
                    try:
                        # Tentar usar lxml se disponível
                        if check_module_exists('lxml'):
                            from lxml import etree
                            root = etree.fromstring(xml_content.encode('utf-8') if isinstance(xml_content, str) else xml_content)
                            namespace = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
                            
                            nfe_info = {
                                'nfe_num': root.xpath('//ns:nNF/text()', namespaces=namespace),
                                'serie': root.xpath('//ns:serie/text()', namespaces=namespace),
                                'emitente': root.xpath('//ns:emit/ns:xNome/text()', namespaces=namespace),
                                'emit_cnpj': root.xpath('//ns:emit/ns:CNPJ/text()', namespaces=namespace),
                                'emit_endereco': root.xpath('//ns:emit/ns:enderEmit/ns:xLgr/text()', namespaces=namespace),
                                'emit_cidade': root.xpath('//ns:emit/ns:enderEmit/ns:xMun/text()', namespaces=namespace),
                                'emit_uf': root.xpath('//ns:emit/ns:enderEmit/ns:UF/text()', namespaces=namespace),
                                'destinatario': root.xpath('//ns:dest/ns:xNome/text()', namespaces=namespace),
                                'dest_cnpj': root.xpath('//ns:dest/ns:CNPJ/text()', namespaces=namespace) or root.xpath('//ns:dest/ns:CPF/text()', namespaces=namespace),
                                'dest_endereco': root.xpath('//ns:dest/ns:enderDest/ns:xLgr/text()', namespaces=namespace),
                                'dest_cidade': root.xpath('//ns:dest/ns:enderDest/ns:xMun/text()', namespaces=namespace),
                                'dest_uf': root.xpath('//ns:dest/ns:enderDest/ns:UF/text()', namespaces=namespace),
                                'valor': root.xpath('//ns:ICMSTot/ns:vNF/text()', namespaces=namespace),
                                'data_emissao': root.xpath('//ns:dhEmi/text()', namespaces=namespace),
                                'nat_op': root.xpath('//ns:natOp/text()', namespaces=namespace),
                                'chave': root.xpath('//ns:chNFe/text()', namespaces=namespace),
                                'protocolo': root.xpath('//ns:nProt/text()', namespaces=namespace)
                            }
                            
                            # Extrair produtos
                            produtos = []
                            for i, det in enumerate(root.xpath('//ns:det', namespaces=namespace)):
                                prod = det.xpath('./ns:prod', namespaces=namespace)[0]
                                produto = {
                                    'num': i+1,
                                    'codigo': prod.xpath('./ns:cProd/text()', namespaces=namespace)[0] if prod.xpath('./ns:cProd', namespaces=namespace) else 'N/A',
                                    'descricao': prod.xpath('./ns:xProd/text()', namespaces=namespace)[0] if prod.xpath('./ns:xProd', namespaces=namespace) else 'N/A',
                                    'ncm': prod.xpath('./ns:NCM/text()', namespaces=namespace)[0] if prod.xpath('./ns:NCM', namespaces=namespace) else 'N/A',
                                    'quantidade': prod.xpath('./ns:qCom/text()', namespaces=namespace)[0] if prod.xpath('./ns:qCom', namespaces=namespace) else '0',
                                    'unidade': prod.xpath('./ns:uCom/text()', namespaces=namespace)[0] if prod.xpath('./ns:uCom', namespaces=namespace) else 'UN',
                                    'valor_unitario': prod.xpath('./ns:vUnCom/text()', namespaces=namespace)[0] if prod.xpath('./ns:vUnCom', namespaces=namespace) else '0',
                                    'valor_total': prod.xpath('./ns:vProd/text()', namespaces=namespace)[0] if prod.xpath('./ns:vProd', namespaces=namespace) else '0',
                                }
                                produtos.append(produto)
                            
                            nfe_info['produtos'] = produtos
                            
                            # Converter listas em valores ou padrão
                            for key in nfe_info:
                                if key != 'produtos':
                                    nfe_info[key] = nfe_info[key][0] if nfe_info[key] else 'N/A'
                        else:
                            # Fallback para extração manual
                            nfe_info = extract_basic_info_from_xml(xml_content)
                            nfe_info['produtos'] = []
                    
                    except Exception as e:
                        logger.error(f"Erro ao extrair informações do XML: {str(e)}")
                        nfe_info = {
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
                    
                    # Criar PDF mais elaborado que se assemelha a um DANFE
                    c = canvas.Canvas(output_pdf_path, pagesize=A4)
                    width, height = A4
                    
                    # Estilos para parágrafos
                    styles = getSampleStyleSheet()
                    title_style = ParagraphStyle(
                        'DanfeTitle',
                        parent=styles['Heading1'],
                        fontSize=14,
                        alignment=1,  # Centralizado
                    )
                    
                    # Desenhar borda da página
                    c.rect(10*mm, 10*mm, width-20*mm, height-20*mm, stroke=1, fill=0)
                    
                    # Título
                    c.setFont('Helvetica-Bold', 14)
                    c.drawCentredString(width/2, height-30*mm, "DOCUMENTO AUXILIAR DA NOTA FISCAL ELETRÔNICA")
                    c.setFont('Helvetica', 10)
                    c.drawCentredString(width/2, height-35*mm, "DANFE - SIMPLIFICADO")
                    c.drawCentredString(width/2, height-40*mm, f"NF-e nº {nfe_info['nfe_num']} - Série {nfe_info['serie']}")
                    
                    # Dados do emitente
                    c.setFont('Helvetica-Bold', 12)
                    c.drawString(20*mm, height-50*mm, "EMITENTE")
                    c.setFont('Helvetica', 10)
                    c.drawString(20*mm, height-55*mm, f"Razão Social: {nfe_info['emitente']}")
                    c.drawString(20*mm, height-60*mm, f"CNPJ: {nfe_info['emit_cnpj']}")
                    c.drawString(20*mm, height-65*mm, f"Endereço: {nfe_info['emit_endereco']}, {nfe_info['emit_cidade']}/{nfe_info['emit_uf']}")
                    
                    # Dados do destinatário
                    c.setFont('Helvetica-Bold', 12)
                    c.drawString(20*mm, height-75*mm, "DESTINATÁRIO")
                    c.setFont('Helvetica', 10)
                    c.drawString(20*mm, height-80*mm, f"Razão Social: {nfe_info['destinatario']}")
                    c.drawString(20*mm, height-85*mm, f"CNPJ/CPF: {nfe_info['dest_cnpj']}")
                    c.drawString(20*mm, height-90*mm, f"Endereço: {nfe_info['dest_endereco']}, {nfe_info['dest_cidade']}/{nfe_info['dest_uf']}")
                    
                    # Dados gerais da nota
                    c.setFont('Helvetica-Bold', 12)
                    c.drawString(20*mm, height-100*mm, "DADOS DA NOTA")
                    c.setFont('Helvetica', 10)
                    c.drawString(20*mm, height-105*mm, f"Natureza da Operação: {nfe_info['nat_op']}")
                    c.drawString(20*mm, height-110*mm, f"Data de Emissão: {nfe_info['data_emissao']}")
                    c.drawString(20*mm, height-115*mm, f"Valor Total: R$ {nfe_info['valor']}")
                    c.drawString(20*mm, height-120*mm, f"Protocolo de Autorização: {nfe_info['protocolo']}")
                    
                    # Chave de acesso
                    c.setFont('Helvetica-Bold', 11)
                    c.drawString(20*mm, height-130*mm, "Chave de Acesso:")
                    c.setFont('Courier', 10)
                    c.drawString(20*mm, height-135*mm, nfe_info['chave'])
                    
                    # Produtos
                    y_pos = height-145*mm
                    
                    if nfe_info['produtos']:
                        c.setFont('Helvetica-Bold', 12)
                        c.drawString(20*mm, y_pos, "PRODUTOS / SERVIÇOS")
                        y_pos -= 10*mm
                        
                        # Cabeçalho da tabela
                        headers = ['#', 'Código', 'Descrição', 'NCM', 'Qtd', 'Un', 'V.Unit', 'V.Total']
                        table_data = [headers]
                        
                        # Dados dos produtos
                        for produto in nfe_info['produtos']:
                            table_data.append([
                                str(produto['num']),
                                produto['codigo'],
                                produto['descricao'][:30],  # Limitar tamanho
                                produto['ncm'],
                                produto['quantidade'],
                                produto['unidade'],
                                produto['valor_unitario'],
                                produto['valor_total']
                            ])
                            
                        # Criar tabela
                        col_widths = [10*mm, 25*mm, 60*mm, 20*mm, 15*mm, 10*mm, 20*mm, 20*mm]
                        table = Table(table_data, colWidths=col_widths)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
                            ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('ALIGN', (2, 1), (2, -1), 'LEFT'),  # Alinhar descrição à esquerda
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
                        ]))
                        
                        table.wrapOn(c, width-40*mm, 500)
                        table.drawOn(c, 20*mm, y_pos - len(nfe_info['produtos'])*8*mm - 20*mm)
                    
                    # Rodapé
                    c.setFont('Helvetica', 8)
                    c.drawString(20*mm, 20*mm, "DOCUMENTO AUXILIAR - CONSULTE A AUTENTICIDADE NO SITE DA SEFAZ")
                    c.drawString(20*mm, 15*mm, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                    
                    # Finalizar PDF
                    c.save()
                    danfe_generated = True
                    logger.info(f"DANFE aprimorado gerado com ReportLab: {output_pdf_path}")
                else:
                    logger.error("ReportLab não está disponível e não foi possível instalá-lo")
                
            except Exception as e:
                logger.error(f"Erro ao gerar PDF aprimorado: {str(e)}")
                traceback.print_exc()
        
        # MÉTODO 6: Último recurso - criar arquivo de texto
        if not danfe_generated:
            logger.warning("Todas as tentativas anteriores falharam, criando arquivo de texto")
            txt_path = output_pdf_path.replace('.pdf', '.txt')
            
            try:
                # Tentar extrair informações do XML para o arquivo de texto
                nfe_info = extract_basic_info_from_xml(xml_content)
                
                with open(txt_path, 'w') as f:
                    f.write("=========================================\n")
                    f.write("DANFE SIMPLIFICADO (ARQUIVO DE TEXTO)\n")
                    f.write("=========================================\n\n")
                    f.write(f"Número da NFe: {nfe_info['nfe_num']}\n")
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
                    
                output_pdf_path = txt_path
                logger.info(f"Arquivo de texto gerado: {txt_path}")
            except Exception as e:
                logger.error(f"Erro ao criar arquivo de texto: {str(e)}")
        
        return output_pdf_path
        
    except Exception as e:
        logger.error(f"Erro crítico na geração do DANFE: {str(e)}")
        traceback.print_exc()
        
        # Criar arquivo de erro como último recurso
        error_path = os.path.join('static', 'danfe', f'error_danfe_{nfe_id}.txt')
        os.makedirs(os.path.dirname(error_path), exist_ok=True)
        
        try:
            with open(error_path, 'w') as f:
                f.write(f"ERRO CRÍTICO AO GERAR DANFE - NFe #{nfe_id}\n")
                f.write(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write(f"Erro: {str(e)}\n")
                f.write(f"Detalhes: {traceback.format_exc()}\n")
        except:
            pass
        
        return error_path

# Função para testar se o módulo está funcionando
def test_service():
    """Testa se o serviço está configurado corretamente"""
    print("Testando serviço de geração de DANFE...")
    print(f"Python version: {sys.version}")
    print("\nVerificando bibliotecas disponíveis:")
    
    libs = [
        "reportlab", "lxml", "pynfe", "requests"
    ]
    
    for lib in libs:
        status = "✅ Disponível" if check_module_exists(lib) else "❌ Não disponível"
        if lib == "pynfe" and check_module_exists(lib):
            status += f" (versão: {get_pynfe_version()})"
        print(f"- {lib}: {status}")
    
    # Verificar estrutura do módulo PyNFe se disponível
    if check_module_exists('pynfe'):
        print("\nVerificando estrutura do PyNFe:")
        try:
            import pynfe.processamento.danfe
            danfe_members = dir(pynfe.processamento.danfe)
            print(f"Classes/funções disponíveis em pynfe.processamento.danfe: {danfe_members}")
        except Exception as e:
            print(f"Erro ao inspecionar módulo danfe: {str(e)}")
    
    print("\nSistema operacional:", os.name)
    
    if check_module_exists('platform'):
        import platform
        print(f"Plataforma: {platform.system()} {platform.release()}")
    
    print("\nDiretório de saída:", os.path.abspath(os.path.join('static', 'danfe')))
    print("\nTeste concluído!")

# Executar teste quando o script for rodado diretamente
if __name__ == "__main__":
    test_service()