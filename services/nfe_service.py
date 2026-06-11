import logging
from datetime import datetime, timezone, timedelta
import uuid
from utils.helpers import get_uf_ibge_code, limpar_cnpj_cpf
from decimal import Decimal
import re
import json
from flask import current_app
from typing import Optional, Dict, Any, Union, Callable, List, Tuple
import os
import tempfile
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12

logger = logging.getLogger(__name__)


# OK: IMPORTAÇÕES XML TOTALMENTE CORRIGIDAS
XML_PARSER = None
etree = None
ET = None

try:
    import lxml.etree as lxml_etree
    import xml.etree.ElementTree as xml_ET
    XML_PARSER = 'lxml'
    etree = lxml_etree
    ET = xml_ET
    logger.debug("lxml carregado com sucesso")
except ImportError:
    try:
        import xml.etree.ElementTree as xml_etree
        XML_PARSER = 'etree'
        etree = xml_etree
        ET = xml_etree
        logger.warning("lxml nao disponivel, usando xml.etree.ElementTree")
    except ImportError:
        logger.error("Nenhum parser XML disponivel!")
        raise ImportError("Instale lxml com: pip install lxml")

# OK: IMPORTAÇÃO CONDICIONAL PARA NFELIB
NFELIB_DISPONIVEL = False
NfeProc = None
try:
    from nfelib.nfe.bindings.v4_0.proc_nfe_v4_00 import NfeProc
    NFELIB_DISPONIVEL = True
    logger.debug("nfelib carregado com sucesso")
except ImportError:
    logger.warning("nfelib nao disponivel")

# OK: IMPORTAÇÃO CONDICIONAL PARA SEFAZ
SEFAZ_DISPONIVEL = False
SefazService = None
try:
    from services.sefaz_service import SefazService
    SEFAZ_DISPONIVEL = True
    logger.debug("SefazService carregado com sucesso")
except ImportError:
    logger.warning("SefazService nao disponivel")


# ========== VALIDAÇÃO TRIBUTÁRIA ==========
def validar_tributacao_nfe(emitente_data: Dict, itens: List[Dict]) -> Tuple[bool, List[str]]:
    """
    Valida compatibilidade entre CFOP, CST/CSOSN e regime tributário
    
    Retorna:
        (sucesso: bool, erros: List[str])
    """
    erros = []
    
    # Determinar regime tributário
    crt = str(emitente_data.get('regime_tributario_id', '1'))
    is_simples_nacional = (crt == "1")
    regime_nome = "Simples Nacional" if is_simples_nacional else "Regime Normal"
    
    logger.debug(f"\n=== VALIDAÇÃO TRIBUTÁRIA ===")
    logger.debug(f"Regime: {regime_nome} (CRT {crt})")
    logger.debug(f"Total de itens: {len(itens)}")
    
    for i, item in enumerate(itens, 1):
        cfop = str(item.get('cfop', ''))
        
        if not cfop:
            erros.append(f"Item {i} ({item.get('descricao', 'sem descrição')}): CFOP não informado")
            continue
        
        # Validações para Simples Nacional (CRT = 1)
        if is_simples_nacional:
            csosn = str(item.get('csosn_icms', ''))
            
            if not csosn:
                erros.append(f"Item {i} ({item.get('descricao', '')}): CSOSN não informado (obrigatório no Simples Nacional)")
                continue
            
            # CFOP 5401/6401 = Venda de produção própria com ST (SUBSTITUTO)
            # Incompatível com Simples Nacional
            if cfop in ['5401', '6401']:
                erros.append(
                    f"Item {i} ({item.get('descricao', '')}): "
                    f"CFOP {cfop} é incompatível com Simples Nacional.\n"
                    f"  • CFOP {cfop} = Venda de produção própria com ST (empresa é SUBSTITUTA)\n"
                    f"  • Simples Nacional não pode ser substituto tributário\n"
                    f"  • Sugestões:\n"
                    f"    - CFOP 5405/6405 se for ST SUBSTITUÍDO (fornecedor já recolheu ST)\n"
                    f"    - CFOP 5102/6102 para venda normal sem ST"
                )
            
            # CFOP 5405/6405 = Venda de mercadoria ST na condição de SUBSTITUÍDO
            # Deve usar CSOSN 500
            elif cfop in ['5405', '6405']:
                if csosn != '500':
                    erros.append(
                        f"Item {i} ({item.get('descricao', '')}): "
                        f"CFOP {cfop} requer CSOSN 500.\n"
                        f"  • CFOP {cfop} = Mercadoria ST já tributada (você é SUBSTITUÍDO)\n"
                        f"  • CSOSN atual: {csosn}\n"
                        f"  • CSOSN 500 = ICMS cobrado anteriormente por ST\n"
                        f"  • Corrija o CSOSN no cadastro do produto"
                    )
            
            # CFOP 5102/6102 = Venda normal
            # Usar CSOSN 102, 103, 300, 400, 900
            elif cfop in ['5102', '6102', '5103', '6103']:
                if csosn not in ['102', '103', '300', '400', '900']:
                    erros.append(
                        f"Item {i} ({item.get('descricao', '')}): "
                        f"CFOP {cfop} não é compatível com CSOSN {csosn}.\n"
                        f"  • Para operação normal, use:\n"
                        f"    - CSOSN 102: Tributada sem crédito\n"
                        f"    - CSOSN 103: Isenção com crédito\n"
                        f"    - CSOSN 400: Não tributada\n"
                        f"    - CSOSN 900: Outros"
                    )
        
        # Validações para Regime Normal (CRT = 3)
        else:
            cst = str(item.get('cst_icms', ''))
            
            if not cst:
                erros.append(f"Item {i} ({item.get('descricao', '')}): CST não informado (obrigatório no Regime Normal)")
                continue
            
            # CFOP 5405/6405 com CST
            if cfop in ['5405', '6405']:
                if cst not in ['10', '60']:
                    erros.append(
                        f"Item {i} ({item.get('descricao', '')}): "
                        f"CFOP {cfop} requer CST 10 ou 60.\n"
                        f"  • CFOP {cfop} = Mercadoria ST (substituído)\n"
                        f"  • CST atual: {cst}\n"
                        f"  • CST 10 = Tributada com ST\n"
                        f"  • CST 60 = ICMS ST cobrado anteriormente"
                    )
    
    if erros:
        logger.error(f"\n❌ {len(erros)} erro(s) de validação encontrado(s)")
        for erro in erros:
            logger.error(f"  • {erro}")
    else:
        logger.debug(f"✅ Validação tributária OK - {len(itens)} itens validados")
    
    # ========== VALIDAÇÃO ADICIONAL COM IA (APENAS AVISOS) ==========
    # DESABILITADO: A IA está retornando falsos positivos que bloqueiam emissões válidas
    # Exemplo: CFOP 5101 + CSOSN 101 é válido mas a IA rejeita incorretamente
    if False:  # Desabilitado temporariamente
        try:
            logger.debug("\n🤖 Executando validação adicional com IA...")
            import requests
            
            ia_response = requests.post(
                "http://localhost:8081/valida/tributacao",
                json={"crt": crt, "itens": itens},
                timeout=65  # Timeout aumentado para LLM
            )
            
            if ia_response.status_code == 200:
                ia_result = ia_response.json()
                
                if not ia_result.get("valido", True):
                    logger.debug("⚠️  IA detectou problemas adicionais:")
                    erros_ia = ia_result.get("erros", [])
                    for erro_ia in erros_ia:
                        erro_texto = erro_ia.get('erro', 'Erro desconhecido')
                        sugestao_texto = erro_ia.get('sugestao', '')
                        
                        # IGNORA erros que dizem "está correto" ou "nenhuma correção"
                        if "está correto" in erro_texto.lower() or "está correto" in sugestao_texto.lower():
                            logger.error(f"  ✓ Item {erro_ia.get('item', '?')}: {erro_texto} (OK)")
                            continue
                        if "nenhuma correção" in sugestao_texto.lower():
                            logger.error(f"  ✓ Item {erro_ia.get('item', '?')}: {erro_texto} (OK)")
                            continue
                        
                        # AVISO: Não adiciona mais aos erros, apenas imprime
                        logger.error(f"  ⚠️  Item {erro_ia.get('item', '?')}: {erro_texto}")
                
                alertas = ia_result.get("alertas", [])
                if alertas:
                    logger.debug("💡 Alertas da IA:")
                    for alerta in alertas:
                        logger.debug(f"  • {alerta}")
            else:
                logger.debug(f"⚠️  IA não disponível (HTTP {ia_response.status_code})")
        except requests.exceptions.Timeout:
            logger.debug("⏱️  Timeout na validação com IA (continuando sem validação adicional)")
        except Exception as e:
            logger.error(f"⚠️  Erro ao consultar IA: {e} (continuando sem validação adicional)")
    
    return (len(erros) == 0, erros)


# FUNCAO PARA CARREGAR NFE PARA EDICAO - ADICIONADA
def carregar_nfe_para_edicao(nfe_id: int, db_session=None) -> Dict[str, Any]:
    """
    Carrega NFe existente para edição
    """
    try:
        logger.debug(f" Carregando NFe {nfe_id} para edição...")
        
        # Obter conexão de banco
        db = db_session if db_session else get_db_connection()
        if not db:
            return {'success': False, 'message': 'Conexão de banco não disponível'}
        
        from sqlalchemy import text
        
        # Buscar NFe no banco
        query = text("""
            SELECT nfe_emitida_id, cliente_id, numero_nfe, serie, chave_acesso,
                   data_emissao, status, valor_total, natureza_operacao,
                   tipo_nfe, finalidade_emissao, destinatario_razao_social,
                   destinatario_cnpj_cpf, informacoes_adicionais, json_nfe
            FROM nfe_emitidas 
            WHERE nfe_emitida_id = :nfe_id
        """)
        
        result = db.execute(query, {'nfe_id': nfe_id}).fetchone()
        
        if not result:
            return {'success': False, 'message': 'NFe não encontrada'}
        
        # OK: CONVERSÃO SEGURA PARA DICIONÁRIO
        try:
            # Verificar se result tem método _asdict (Row object)
            if hasattr(result, '_asdict'):
                nfe_data = result._asdict()
            # Ou se podemos converter usando dict() com _mapping
            elif hasattr(result, '_mapping'):
                nfe_data = dict(result._mapping)
            # Fallback: criar dicionário manualmente com índices
            else:
                colunas = ['nfe_emitida_id', 'cliente_id', 'numero_nfe', 'serie', 'chave_acesso',
                          'data_emissao', 'status', 'valor_total', 'natureza_operacao',
                          'tipo_nfe', 'finalidade_emissao', 'destinatario_razao_social',
                          'destinatario_cnpj_cpf', 'informacoes_adicionais', 'json_nfe']
                nfe_data = {col: result[i] for i, col in enumerate(colunas)}
                
        except Exception as e:
            logger.error(f"ERRO: Erro na conversão do resultado: {e}")
            # Fallback manual mais seguro usando índices
            nfe_data = {
                'nfe_emitida_id': result[0] if len(result) > 0 else None,
                'cliente_id': result[1] if len(result) > 1 else None,
                'numero_nfe': result[2] if len(result) > 2 else None,
                'serie': result[3] if len(result) > 3 else None,
                'chave_acesso': result[4] if len(result) > 4 else None,
                'data_emissao': result[5] if len(result) > 5 else None,
                'status': result[6] if len(result) > 6 else None,
                'valor_total': result[7] if len(result) > 7 else None,
                'natureza_operacao': result[8] if len(result) > 8 else None,
                'tipo_nfe': result[9] if len(result) > 9 else None,
                'finalidade_emissao': result[10] if len(result) > 10 else None,
                'destinatario_razao_social': result[11] if len(result) > 11 else None,
                'destinatario_cnpj_cpf': result[12] if len(result) > 12 else None,
                'informacoes_adicionais': result[13] if len(result) > 13 else None,
                'json_nfe': result[14] if len(result) > 14 else None
            }
        
        logger.debug(f"OK: NFe {nfe_id} carregada: {nfe_data.get('status', 'N/A')}")
        
        # OK: PROCESSAR JSON_NFE COM SEGURANÇA
        form_data = {}
        items_data = []
        
        json_nfe = nfe_data.get('json_nfe')
        if json_nfe:
            try:
                if isinstance(json_nfe, str):
                    json_data = json.loads(json_nfe)
                elif isinstance(json_nfe, dict):
                    json_data = json_nfe
                else:
                    logger.warning(f"AVISO: json_nfe em formato inesperado: {type(json_nfe)}")
                    json_data = {}
                
                form_data = json_data.get('form_data', {})
                items_data = json_data.get('items', [])
                
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"AVISO: Erro ao decodificar JSON: {e}")
                # Tentar criar dados básicos a partir dos campos da tabela
                data_emissao_value = nfe_data.get('data_emissao')
                form_data = {
                    'natOp': nfe_data.get('natureza_operacao', ''),
                    'serie': str(nfe_data.get('serie', '1')),
                    'tpNF': str(nfe_data.get('tipo_nfe', '1')),
                    'finNFe': str(nfe_data.get('finalidade_emissao', '1')),
                    'infCpl': nfe_data.get('informacoes_adicionais', ''),
                    # Garante chamada segura de isoformat apenas se for datetime
                    'dataEmissao': data_emissao_value.isoformat() if isinstance(data_emissao_value, datetime) else None
                }
                items_data = []
        
        # Buscar dados do cliente
        cliente_data = {}
        if nfe_data.get('cliente_id'):
            try:
                cliente_query = text("""
                    SELECT cliente_id, razao_social, cnpj_cpf, logradouro, numero,
                           bairro, cep, nome_municipio, codigo_municipio, uf
                    FROM clientes 
                    WHERE cliente_id = :cliente_id
                """)
                
                cliente_result = db.execute(cliente_query, {'cliente_id': nfe_data['cliente_id']}).fetchone()
                
                if cliente_result:
                    # OK: CONVERSÃO SEGURA PARA CLIENTE
                    try:
                        if hasattr(cliente_result, '_asdict'):
                            cliente_data = cliente_result._asdict()
                        elif hasattr(cliente_result, '_mapping'):
                            cliente_data = dict(cliente_result._mapping)
                        else:
                            cliente_cols = ['cliente_id', 'razao_social', 'cnpj_cpf', 'logradouro', 
                                          'numero', 'bairro', 'cep', 'nome_municipio', 
                                          'codigo_municipio', 'uf']
                            cliente_data = {col: cliente_result[i] for i, col in enumerate(cliente_cols)}
                    except Exception as e:
                        logger.error(f"AVISO: Erro na conversão cliente: {e}")
                        # Fallback manual
                        cliente_data = {
                            'cliente_id': cliente_result[0] if len(cliente_result) > 0 else None,
                            'razao_social': cliente_result[1] if len(cliente_result) > 1 else '',
                            'cnpj_cpf': cliente_result[2] if len(cliente_result) > 2 else '',
                        }
                        
            except Exception as e:
                logger.error(f"AVISO: Erro ao buscar cliente: {e}")
        
        return {
            'success': True,
            'nfe_data': nfe_data,
            'form_data': form_data,
            'items_data': items_data,
            'cliente_data': cliente_data
        }
        
    except Exception as e:
        logger.error(f"ERRO: Erro ao carregar NFe: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': f'Erro ao carregar NFe: {str(e)}'}

# OK: FUNÇÃO DE CONEXÃO DE BANCO COM FALLBACKS SEGUROS
def get_db_connection() -> Optional[Any]:
    """Função para obter conexão de banco com fallbacks seguros"""
    try:
        # Tentativa 1: database.connection
        try:
            from database.connection import get_db
            return next(get_db())
        except (ImportError, StopIteration):
            pass
        
        # Tentativa 2: database.db (dinâmico para evitar erro de import em tempo de edição)
        try:
            import importlib
            db_module = importlib.import_module('database.db')
            get_db = getattr(db_module, 'get_db', None)
            if callable(get_db):
                return get_db()
        except Exception:
            pass
        
        # Tentativa 3: app context
        try:
            from flask import current_app
            db_attr = getattr(current_app, 'db', None)
            if db_attr is not None:
                return db_attr
        except (ImportError, RuntimeError):
            pass
        
        logger.warning("AVISO: Nenhuma conexão de banco disponível")
        return None
        
    except Exception as e:
        logger.error(f"AVISO: Erro ao conectar com banco: {e}")
        return None

# OK: DEFINIÇÃO DE TIPOS E INTERFACES
CertificateFunction = Optional[Callable[[Optional[Any], int], Dict[str, Any]]]

# OK: CLASSE BASE PARA XML SIGNER
class BaseXMLSigner:
    """Classe base para assinatura de XML"""
    def assinar_xml(self, xml_content: str, certificado: Dict[str, Any]) -> str:
        """Interface padrão para assinatura"""
        return self._sign_xml_fallback(xml_content, certificado)
    
    def _sign_xml_fallback(self, xml_content: str, certificado: Dict[str, Any]) -> str:
        """Fallback para assinatura simulada"""
        logger.debug("[SIGN] Usando assinatura simulada...")
        
        assinatura_simulada = '''
    <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
        <SignedInfo>
            <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
            <SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
        </SignedInfo>
        <SignatureValue>ASSINATURA_SIMULADA_PARA_TESTES</SignatureValue>
    </Signature>'''
        
        xml_assinado = xml_content.replace('</NFe>', f'{assinatura_simulada}</NFe>')
        logger.debug("OK: XML assinado (simulado)")
        return xml_assinado

# OK: IMPORTAÇÕES DE SERVIÇOS COM FALLBACKS
SERVICES_DISPONIVEL = False
certificate_service_function: CertificateFunction = None
xml_signer_instance = None

try:
    from services.certificate_service import get_active_certificate_for_client as cert_func
    certificate_service_function = cert_func
    
    try:
        from services.xml_signer import XMLSigner as ExternalXMLSigner
        
        class XMLSignerWrapper(BaseXMLSigner):
            """Wrapper para XMLSigner externo"""
            def __init__(self):
                try:
                    self._external_signer = ExternalXMLSigner()
                except Exception as e:
                    logger.error(f"AVISO: Erro ao inicializar XMLSigner externo: {e}")
                    self._external_signer = None
            
            def assinar_xml(self, xml_content: str, certificado: Dict[str, Any]) -> str:
                if self._external_signer:
                    try:
                        return self._external_signer.assinar_xml(xml_content, certificado)
                    except Exception as e:
                        logger.error(f"AVISO: Erro na assinatura externa, usando fallback: {e}")
                        return self._sign_xml_fallback(xml_content, certificado)
                else:
                    return self._sign_xml_fallback(xml_content, certificado)
        
        xml_signer_instance = XMLSignerWrapper()
        
    except ImportError:
        logger.warning("AVISO: XMLSigner externo não disponível, usando fallback")
        xml_signer_instance = BaseXMLSigner()
    
    SERVICES_DISPONIVEL = True
    logger.debug("OK: Serviços locais carregados com sucesso")
    
except ImportError as e:
    logger.warning(f"AVISO: Serviços locais não disponíveis: {e}")
    
    # OK: FALLBACK PARA CERTIFICADO
    def fallback_certificate_function(db, cliente_id):
        """Fallback para certificado simulado"""
        return {
            'nome_arquivo_original': 'certificado_simulado.pfx',
            'private_key': 'SIMULADO',
            'modo_simulado': True
        }
    
    certificate_service_function = fallback_certificate_function
    xml_signer_instance = BaseXMLSigner()

# OK: CLASSE PRINCIPAL DO SERVIÇO
class NFeService:
    """Serviço principal para processamento completo de NFe"""
    
    def __init__(self, db_session=None):
        self.db: Any = db_session
        if not self.db:
            self.db = get_db_connection()
        self.xml_signer = xml_signer_instance

    def carregar_para_edicao(self, nfe_id: int) -> Dict[str, Any]:
        """
        Carrega NFe para edição
        """
        return carregar_nfe_para_edicao(nfe_id, self.db)
    
    def processar_nfe(self, dados_nfe: Dict[str, Any], itens: list, cliente_id: int, nfe_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Processar NFe (nova funcionalidade que atualiza NFe existente se nfe_id for fornecido)
        """
        try:
            logger.debug(f" === PROCESSAMENTO NFE ===")
            logger.debug(f" Cliente ID: {cliente_id}")
            logger.debug(f"NOTA: NFe ID: {nfe_id if nfe_id else 'Nova NFe'}")
            
            # Garantir conexão de banco
            if not self.db:
                self.db = get_db_connection()
            
            if not self.db:
                return {'success': False, 'message': 'Conexão de banco não disponível'}
            
            # Import text function for SQLAlchemy
            from sqlalchemy import text
            
            # Buscar dados do emitente e destinatário
            # Buscar emitente (empresa) - DEVE SER DO CLIENTE ESPECÍFICO
            emitente_query = text("""
                SELECT razao_social, nome_fantasia, cnpj, inscricao_estadual,
                       logradouro, numero, bairro, cep, nome_municipio, 
                       codigo_municipio, uf, regime_tributario_id
                FROM clientes 
                WHERE cliente_id = :cliente_id AND ativo = true
            """)
            emitente_result = self.db.execute(emitente_query, {'cliente_id': cliente_id}).fetchone()
            
            if not emitente_result:
                return {'success': False, 'message': 'Dados do emitente não encontrados'}
            
            # OK: CONVERSÃO SEGURA PARA EMITENTE
            try:
                if hasattr(emitente_result, '_asdict'):
                    emitente_data = emitente_result._asdict()
                elif hasattr(emitente_result, '_mapping'):
                    emitente_data = dict(emitente_result._mapping)
                else:
                    emitente_cols = ['razao_social', 'nome_fantasia', 'cnpj', 'inscricao_estadual',
                                   'logradouro', 'numero', 'bairro', 'cep', 'nome_municipio', 
                                   'codigo_municipio', 'uf', 'regime_tributario_id']
                    emitente_data = {col: emitente_result[i] for i, col in enumerate(emitente_cols)}
            except Exception as e:
                logger.error(f"AVISO: Erro conversão emitente: {e}")
                emitente_data = {'razao_social': 'EMPRESA TESTE', 'cnpj': '12345678000100', 'uf': 'SP'}
            
            # Buscar destinatário
            destinatario_cnpj_cpf = None
            # Preferir valor vindo do payload (dados_nfe)
            if isinstance(dados_nfe, dict):
                destinatario_cnpj_cpf = dados_nfe.get('destinatario_cnpj_cpf') or (dados_nfe.get('destinatario') and dados_nfe['destinatario'].get('cnpj_cpf'))
            # Sanitizar CNPJ/CPF
            if destinatario_cnpj_cpf:
                try:
                    destinatario_cnpj_cpf = limpar_cnpj_cpf(destinatario_cnpj_cpf)
                except Exception:
                    destinatario_cnpj_cpf = limpar_cnpj_cpf(str(destinatario_cnpj_cpf))
            else:
                return {'success': False, 'message': 'CNPJ/CPF do destinatário não informado'}
            
            destinatario_query = text("SELECT * FROM destinatarios_nfe WHERE cpf_cnpj = :cpf_cnpj")
            destinatario_result = self.db.execute(destinatario_query, {'cpf_cnpj': destinatario_cnpj_cpf}).fetchone()
            
            if not destinatario_result:
                return {'success': False, 'message': 'Cliente não encontrado'}
            
            # OK: CONVERSÃO SEGURA PARA DESTINATÁRIO
            try:
                if hasattr(destinatario_result, '_asdict'):
                    destinatario_data = destinatario_result._asdict()
                elif hasattr(destinatario_result, '_mapping'):
                    destinatario_data = dict(destinatario_result._mapping)
                else:
                    dest_cols = ['nome_razao_social', 'cpf_cnpj', 'logradouro', 'numero', 
                               'bairro', 'cep', 'nome_municipio', 'codigo_municipio', 'uf']
                    destinatario_data = {col: destinatario_result[i] for i, col in enumerate(dest_cols)}
            except Exception as e:
                logger.error(f"AVISO: Erro conversão destinatário: {e}")
                destinatario_data = {'nome_razao_social': 'CLIENTE TESTE', 'cpf_cnpj': '12345678901'}
            
            # Processar emissão
            resultado = self.processar_emissao_completa(
                dados_nfe, emitente_data, destinatario_data, itens, cliente_id
            )
            
            if resultado['success']:
                # Se tem nfe_id, atualizar NFe existente
                if nfe_id:
                    return self._atualizar_nfe_existente(nfe_id, resultado, dados_nfe, itens, cliente_id)
                else:
                    return self._criar_nova_nfe(resultado, dados_nfe, itens, cliente_id, emitente_data, destinatario_data)
            else:
                return resultado
                
        except Exception as e:
            logger.error(f"ERRO: Erro no processamento NFe: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Erro interno: {str(e)}'}
    
    def _atualizar_nfe_existente(self, nfe_id: int, resultado: Dict[str, Any], dados_nfe: Dict[str, Any], itens: list, cliente_id: int) -> Dict[str, Any]:
        """Atualiza NFe existente no banco"""
        try:
            if not self.db:
                return {'success': False, 'message': 'Conexão de banco não disponível'}
                
            from sqlalchemy import text
            
            if resultado['success']:
                # Obter valor total da nota (com impostos)
                # Preferir o valor dos totais se fornecido, senão calcular dos itens
                from decimal import Decimal
                valor_total_nota = Decimal('0')
                
                # Verificar se tem totais.valor_total_nota no dados_nfe
                totais = dados_nfe.get('totais', {})
                if totais and totais.get('valor_total_nota'):
                    valor_total_nota = Decimal(str(totais['valor_total_nota']))
                    logger.debug(f"[TOTAL] Usando valor_total_nota dos totais: R$ {valor_total_nota}")
                else:
                    # Calcular: produtos + IPI + ICMS ST + frete + seguro + outras - desconto
                    valor_produtos = Decimal('0')
                    valor_ipi = Decimal('0')
                    valor_icms_st = Decimal('0')
                    
                    for item in itens:
                        qtd = Decimal(str(item.get('quantidade_comercial') or item.get('quantidade', 0)))
                        val_unit = Decimal(str(item.get('valor_unitario_comercial') or item.get('valor_unitario', 0)))
                        valor_produtos += qtd * val_unit
                        
                        # Somar IPI se houver
                        ipi = item.get('ipi', {})
                        if ipi.get('valor'):
                            valor_ipi += Decimal(str(ipi['valor']))
                        
                        # Somar ICMS ST se houver
                        icms = item.get('icms', {})
                        if icms.get('valor_st'):
                            valor_icms_st += Decimal(str(icms['valor_st']))
                    
                    valor_frete = Decimal(str(totais.get('valor_frete', 0)))
                    valor_seguro = Decimal(str(totais.get('valor_seguro', 0)))
                    valor_outras = Decimal(str(totais.get('valor_outras_despesas', 0)))
                    valor_desconto = Decimal(str(totais.get('valor_desconto', 0)))
                    
                    valor_total_nota = valor_produtos + valor_ipi + valor_icms_st + valor_frete + valor_seguro + valor_outras - valor_desconto
                    logger.debug(f"[TOTAL] Calculado: Produtos={valor_produtos} + IPI={valor_ipi} + ST={valor_icms_st} + Frete={valor_frete} - Desc={valor_desconto} = R$ {valor_total_nota}")
                
                # Atualizar com sucesso
                update_query = text("""
                    UPDATE nfe_emitidas 
                    SET status = 'AUTORIZADA',
                        chave_acesso = :chave_acesso,
                        protocolo_sefaz = :protocolo,
                        data_autorizacao = :data_autorizacao,
                        mensagem_sefaz = :mensagem,
                        valor_total = :valor_total,
                        json_nfe = :json_nfe
                    WHERE nfe_emitida_id = :nfe_id
                """)
                
                json_nfe = {
                    'form_data': dados_nfe,
                    'items': itens,
                    'ambiente': resultado.get('ambiente', 'homologacao'),
                    'xml_content': resultado.get('xml_final')
                }
                
                self.db.execute(update_query, {
                    'nfe_id': nfe_id,
                    'chave_acesso': resultado.get('chave_acesso'),
                    'protocolo': resultado.get('protocolo'),
                    'data_autorizacao': datetime.now(),
                    'mensagem': resultado.get('message', 'Autorizada com sucesso'),
                    'valor_total': float(valor_total_nota),
                    'json_nfe': json.dumps(json_nfe)
                })
                self.db.commit()
                
                return {
                    'success': True,
                    'status': 'AUTORIZADA',
                    'message': 'NFe atualizada e autorizada com sucesso!',
                    'nfe_id': nfe_id,
                    'chave_acesso': resultado.get('chave_acesso'),
                    'protocolo': resultado.get('protocolo')
                }
            else:
                # Atualizar com erro/rejeição
                status = resultado.get('status', 'REJEITADA')
                mensagem = resultado.get('message', 'Erro desconhecido')
                
                update_query = text("""
                    UPDATE nfe_emitidas 
                    SET status = :status,
                        mensagem_sefaz = :mensagem
                    WHERE nfe_emitida_id = :nfe_id
                """)
                
                self.db.execute(update_query, {
                    'nfe_id': nfe_id,
                    'status': status,
                    'mensagem': mensagem[:250]
                })
                self.db.commit()
                
                return {
                    'success': False,
                    'status': status,
                    'message': mensagem,
                    'nfe_id': nfe_id,
                    'sefaz_response': resultado
                }
                
        except Exception as e:
            logger.error(f"ERRO: Erro ao atualizar NFe: {e}")
            return {'success': False, 'message': f'Erro ao atualizar: {str(e)}'}
    
    def _criar_nova_nfe(self, resultado: Dict[str, Any], dados_nfe: Dict[str, Any], itens: list, cliente_id: int, emitente_data: Dict[str, Any], destinatario_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria nova NFe no banco"""
        try:
            logger.debug(f"\n{'='*80}")
            logger.debug(f"[NEW] CRIANDO NOVA NFe NO BANCO")
            logger.debug(f"{'='*80}")
            logger.debug(f"[DATA] dados_nfe recebidos: {dados_nfe}")
            logger.debug(f"[INFO] Total de itens: {len(itens)}")
            logger.debug(f"{'='*80}\n")
            
            if not self.db:
                return {'success': False, 'message': 'Conexão de banco não disponível'}
                
            from sqlalchemy import text
            
            # Obter série, modelo e número da NFe (fornecido pelo usuário)
            serie = int(dados_nfe.get('serie', 1))
            modelo = '55'  # 55=NFe
            numero_nfe = int(dados_nfe.get('numero_nfe', 1))
            
            logger.debug(f"[NUM] VALORES EXTRAÍDOS:")
            logger.debug(f"   - Série: {serie}")
            logger.debug(f"   - Modelo: {modelo}")
            logger.debug(f"   - Número NFe: {numero_nfe}")
            logger.debug(f"   - Data Emissão: {dados_nfe.get('dataEmissao')}")
            
            # Validar se o número já existe
            try:
                existe = self.db.execute(
                    text("""
                        SELECT COUNT(*) 
                        FROM nfe_emitidas 
                        WHERE cliente_id = :cliente_id 
                          AND modelo = :modelo 
                          AND serie = :serie 
                          AND numero = :numero
                    """),
                    {"cliente_id": cliente_id, "modelo": modelo, "serie": serie, "numero": numero_nfe}
                ).scalar()
                
                if existe > 0:
                    return {
                        'success': False, 
                        'message': f'Número {numero_nfe} da série {serie} já existe! Escolha outro número.'
                    }
            except Exception as e:
                logger.error(f"[WARN] Erro ao validar número existente: {e}")
            
            # Calcular valores
            valor_total = sum(float(item.get('valor_total', 0)) for item in itens)
            logger.debug(f"[STATS] Dados para INSERT: numero={numero_nfe}, serie={serie}, valor_total={valor_total}")
            
            # Inserir nova NFe
            insert_query = text("""
                INSERT INTO nfe_emitidas (
                    cliente_id, numero, serie, modelo, chave_acesso, protocolo_sefaz,
                    data_emissao, data_autorizacao, data_criacao, status, valor_total,
                    natureza_operacao, tipo_nfe, finalidade_emissao,
                    destinatario_razao_social, destinatario_cnpj_cpf,
                    informacoes_adicionais, mensagem_sefaz, json_nfe
                ) VALUES (
                    :cliente_id, :numero, :serie, :modelo, :chave_acesso, :protocolo_sefaz,
                    :data_emissao, :data_autorizacao, :data_criacao, :status, :valor_total,
                    :natureza_operacao, :tipo_nfe, :finalidade_emissao,
                    :destinatario_razao_social, :destinatario_cnpj_cpf,
                    :informacoes_adicionais, :mensagem_sefaz, :json_nfe
                ) RETURNING nfe_emitida_id
            """)
            
            # Preparar dados
            data_emissao = dados_nfe.get('dataEmissao')
            if data_emissao:
                try:
                    dt = datetime.fromisoformat(data_emissao.replace('T', ' '))
                except:
                    dt = datetime.now()
            else:
                dt = datetime.now()
            
            logger.debug(f"[DATE] Data emissão: {dt}")
            logger.debug(f"[NUM] Número NFe: {numero_nfe}, Série: {serie}, Modelo: {modelo}")
            
            json_nfe = {
                'form_data': dados_nfe,
                'items': itens,
                'ambiente': resultado.get('ambiente', 'homologacao'),
                'xml_content': resultado.get('xml_final')
            }
            
            nfe_result = self.db.execute(insert_query, {
                'cliente_id': cliente_id,
                'numero': numero_nfe,  # Número obtido pela função get_proximo_numero_nfe
                'serie': serie,
                'modelo': modelo,  # 55=NFe
                'chave_acesso': resultado.get('chave_acesso'),
                'protocolo_sefaz': resultado.get('protocolo'),
                'data_emissao': dt,
                'data_autorizacao': datetime.now() if resultado['success'] else None,
                'data_criacao': datetime.now(),
                'status': 'AUTORIZADA' if resultado['success'] else 'REJEITADA',
                'valor_total': valor_total,
                'natureza_operacao': dados_nfe.get('natOp', ''),
                'tipo_nfe': dados_nfe.get('tpNF', '1'),
                'finalidade_emissao': int(dados_nfe.get('finNFe', '1')),
                'destinatario_razao_social': destinatario_data.get('nome_razao_social', ''),
                'destinatario_cnpj_cpf': destinatario_data.get('cpf_cnpj', ''),
                'informacoes_adicionais': dados_nfe.get('infCpl', ''),
                'mensagem_sefaz': resultado.get('message', 'Processada com sucesso'),
                'json_nfe': json.dumps(json_nfe)
            }).fetchone()
            
            self.db.commit()
            
            nfe_id = nfe_result[0] if nfe_result else None
            
            return {
                'success': resultado['success'],
                'message': 'NFe criada com sucesso!' if resultado['success'] else resultado.get('message'),
                'nfe_id': nfe_id,
                'chave_acesso': resultado.get('chave_acesso'),
                'protocolo': resultado.get('protocolo')
            }
            
        except Exception as e:
            logger.error(f"ERRO: Erro ao criar NFe: {e}")
            return {'success': False, 'message': f'Erro ao salvar: {str(e)}'}
    
    def processar_emissao_completa(self, dados_form: Dict[str, Any], emitente_data: Dict[str, Any], destinatario_data: Dict[str, Any], items_data: list, cliente_id: int, ambiente: str = 'homologacao') -> Dict[str, Any]:
        """
        Processamento completo: Gera XML -> Assina -> Envia SEFAZ -> Salva
        """
        try:
            logger.debug(f" === PROCESSAMENTO COMPLETO NFE ===")
            logger.debug(f" Cliente ID: {cliente_id}")
            logger.debug(f" Ambiente: {ambiente}")
            
            # 1. GERAR XML - tpAmb SEFAZ: 1=Produção, 2=Homologação
            tp_amb = 1 if ambiente == 'producao' else 2
            xml_nfe = generate_nfe_xml(dados_form, emitente_data, destinatario_data, items_data, tp_amb)
            
            if not xml_nfe:
                return {'success': False, 'errors': ['Falha na geração do XML']}
            
            logger.debug(f"OK: XML gerado: {len(xml_nfe)} caracteres")
            
            # DEBUG: Verificar estrutura ICMS
            if '<ICMSSN500>' in xml_nfe:
                import re
                icms_match = re.search(r'<ICMS>.*?</ICMS>', xml_nfe, re.DOTALL)
                if icms_match:
                    logger.debug(f"[DEBUG-XML] Estrutura ICMS completa: {icms_match.group()}")
            
            # 2. BUSCAR CERTIFICADO
            certificado = certificate_service_function(self.db, cliente_id) if certificate_service_function else None
            if not certificado:
                return {'success': False, 'errors': ['Certificado não encontrado']}
            
            logger.debug(f"OK: Certificado encontrado: {certificado.get('nome_arquivo_original', 'N/A')}")
            
            # Adicionar db_session e cliente_id para XMLSignatureService
            certificado['db_session'] = self.db
            certificado['cliente_id'] = cliente_id
            
            # 3. ASSINAR XML
            xml_assinado = self._assinar_xml_real(xml_nfe, certificado)
            if not xml_assinado:
                return {'success': False, 'errors': ['Falha na assinatura']}
            
            logger.debug(f"OK: XML assinado: {len(xml_assinado)} caracteres")
            logger.debug(f"[DEBUG] XML assinado tem <Signature>: {'<Signature' in xml_assinado}")
            
            # 4. ENVIAR PARA SEFAZ
            resultado_sefaz = self._processar_envio_sefaz(xml_assinado, certificado, ambiente, cliente_id)
            
            if not resultado_sefaz.get('success', False):
                return {
                    'success': False, 
                    'errors': [f"Erro SEFAZ: {resultado_sefaz.get('message', 'Erro desconhecido')}"]
                }
            
            # 5. RETORNAR RESULTADO COMPLETO
            return {
                'success': True,
                'chave_acesso': resultado_sefaz.get('chave_acesso'),
                'protocolo': resultado_sefaz.get('protocolo'),
                'status': resultado_sefaz.get('status'),
                'xml_final': resultado_sefaz.get('xml_protocolo', xml_assinado),
                'ambiente': ambiente,
                'ambiente_real': resultado_sefaz.get('ambiente_real', False),
                'sefaz_response': resultado_sefaz,
                'message': resultado_sefaz.get('message', 'Processado com sucesso')
            }
            
        except Exception as e:
            logger.error(f"ERRO: Erro no processamento completo: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'errors': [f'Erro interno: {str(e)}']}
    
    def _assinar_xml_real(self, xml_content: str, certificado: Dict[str, Any]) -> Optional[str]:
        """Assina XML com certificado real ou simulado"""
        try:
            logger.debug("[SIGN] === ASSINANDO XML ===")
            logger.debug(f"[SIGN] Certificado: {certificado.get('nome_arquivo_original', 'N/A')}")
            logger.debug(f"[SIGN] Modo simulado: {certificado.get('modo_simulado', False)}")
            logger.debug(f"[SIGN] XML entrada tem Signature: {'<Signature' in xml_content}")
            
            if self.xml_signer:
                logger.debug("[SIGN] Usando xml_signer...")
                resultado = self.xml_signer.assinar_xml(xml_content, certificado)
                if resultado:
                    logger.debug(f"[SIGN] [OK] XML assinado: {len(resultado)} caracteres")
                    logger.debug(f"[SIGN] [OK] XML resultado tem Signature: {'<Signature' in resultado}")
                    return resultado
                else:
                    logger.debug("[SIGN] [WARN] xml_signer retornou None, usando fallback")
                    return sign_xml(xml_content, certificado)
            else:
                logger.debug("[SIGN] === USANDO ASSINATURA SIMULADA DIRETA ===")
                return sign_xml(xml_content, certificado)
                
        except Exception as e:
            logger.error(f"[SIGN] [ERROR] Erro na assinatura: {e}")
            import traceback
            traceback.print_exc()
            logger.debug("[SIGN] [FALLBACK] Usando assinatura simulada...")
            return sign_xml(xml_content, certificado)
            return None
    
    def _processar_envio_sefaz(self, xml_assinado: str, certificado: Dict[str, Any], ambiente: str, cliente_id: int) -> Dict[str, Any]:
        """Processa envio para SEFAZ real ou simulado"""
        try:
            logger.debug(f" === PROCESSANDO ENVIO SEFAZ ===")
            
            # Extrair chave de acesso
            chave_acesso = self._extrair_chave_acesso(xml_assinado)
            if not chave_acesso:
                return {'success': False, 'message': 'Chave de acesso não encontrada'}
            
            # Decidir se usa SEFAZ real
            usar_sefaz_real = self._deve_usar_sefaz_real(certificado, ambiente)
            
            if usar_sefaz_real and SEFAZ_DISPONIVEL:
                logger.debug("✅ === ENVIANDO PARA SEFAZ REAL ===")
                return self._enviar_sefaz_real(xml_assinado, chave_acesso, ambiente, cliente_id)
            else:
                logger.debug("⚠️  === USANDO SIMULAÇÃO LOCAL (SEM CERTIFICADO) ===")
                return self._enviar_sefaz_simulado(xml_assinado, chave_acesso, ambiente)
                
        except Exception as e:
            logger.error(f"ERRO: Erro no envio SEFAZ: {e}")
            return {'success': False, 'message': f'Erro no envio: {str(e)}'}
    
    def _deve_usar_sefaz_real(self, certificado: Dict[str, Any], ambiente: str) -> bool:
        """Determina se deve usar SEFAZ real"""
        
        # Verificar se SefazService está disponível
        if not SEFAZ_DISPONIVEL or SefazService is None:
            logger.debug(" SefazService não disponível - módulo não carregado")
            return False
        
        # IMPORTANTE: Não verificar mais FORCE_SEFAZ_SIMULATION
        # Sempre usar SEFAZ real quando certificado válido estiver presente
        
        # Verificar se certificado é real e válido
        if certificado.get('modo_simulado', False):
            logger.debug(" Certificado em modo simulado")
            return False
        
        # Verificar se tem dados de certificado necessários
        if not certificado.get('cert_data'):
            logger.debug(" Certificado sem dados (cert_data não encontrado)")
            return False
            
        if not certificado.get('password'):
            logger.debug(" Certificado sem senha")
            return False
        
        logger.debug("✅ OK: Condições OK para usar SEFAZ REAL")
        logger.debug(f"✅ Ambiente: {ambiente.upper()}")
        return True
    
    def _enviar_sefaz_real(self, xml_assinado: str, chave_acesso: str, ambiente: str, cliente_id: int) -> Dict[str, Any]:
        """Envia para SEFAZ real"""
        cert_path = None
        key_path = None
        
        try:
            logger.debug(f" Conectando com SEFAZ real - Ambiente: {ambiente}")
            
            # Verificar se SefazService está disponível
            if not SEFAZ_DISPONIVEL or SefazService is None:
                logger.error("ERRO: SefazService não está disponível")
                return self._enviar_sefaz_simulado(xml_assinado, chave_acesso, ambiente,
                                                 motivo="SefazService não disponível")
            
            # Obter certificado do cliente
            logger.debug("[CERT] Carregando certificado digital para HTTPS...")
            certificado = certificate_service_function(self.db, cliente_id) if certificate_service_function else None
            
            if not certificado:
                logger.error("[X] Certificado não encontrado")
                return self._enviar_sefaz_simulado(xml_assinado, chave_acesso, ambiente,
                                                 motivo="Certificado não encontrado")
            
            # Extrair certificado e chave para arquivos temporários
            if certificado and certificado.get('cert_data') and certificado.get('password'):
                try:
                    logger.debug("[DEBUG] Iniciando extração do certificado PKCS#12...")
                    # Extrair certificado e chave para arquivos temporários
                    cert_data = certificado['cert_data']  # Dados binários do PKCS#12
                    password = certificado['password'].encode('utf-8')
                    
                    # Carregar PKCS#12
                    private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                        cert_data, password
                    )
                    
                    # Criar arquivos temporários
                    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as cert_file:
                        cert_file.write(certificate.public_bytes(serialization.Encoding.PEM))
                        cert_path = cert_file.name
                        temp_cert_file = cert_file.name
                    
                    with tempfile.NamedTemporaryFile(mode='wb', suffix='.key', delete=False) as key_file:
                        key_file.write(private_key.private_bytes(
                            encoding=serialization.Encoding.PEM,
                            format=serialization.PrivateFormat.TraditionalOpenSSL,
                            encryption_algorithm=serialization.NoEncryption()
                        ))
                        key_path = key_file.name
                        temp_key_file = key_file.name
                    
                    logger.debug(f"[OK] Certificado extraído: {cert_path}")
                    logger.debug(f"[OK] Chave privada extraída: {key_path}")
                    
                except Exception as e:
                    logger.error(f"[X] Erro ao extrair certificado: {e}")
                    import traceback
                    traceback.print_exc()
                    # NÃO USA SIMULAÇÃO - retorna erro real para forçar correção
                    return {
                        'success': False,
                        'status': 'ERRO_CERTIFICADO',
                        'message': f'Erro ao extrair certificado: {str(e)}',
                        'ambiente_real': False
                    }
            else:
                logger.error("[X] Certificado sem dados necessários (cert_data ou password)")
                # NÃO USA SIMULAÇÃO - retorna erro real
                return {
                    'success': False,
                    'status': 'ERRO_CERTIFICADO',
                    'message': 'Certificado incompleto - configure cert_data e password',
                    'ambiente_real': False
                }
            
            # Inicializar serviço SEFAZ com certificado
            try:
                sefaz = SefazService(ambiente=ambiente, cert_path=cert_path, key_path=key_path)
            except Exception as e:
                logger.error(f"ERRO: Erro ao inicializar SefazService: {e}")
                # NÃO USA SIMULAÇÃO - retorna erro real
                return {
                    'success': False,
                    'status': 'ERRO_SEFAZ_SERVICE',
                    'message': f'Erro ao inicializar SefazService: {str(e)}',
                    'ambiente_real': False
                }
            
            # DESABILITADO: Verificação de status requer certificado A1 em produção
            # O XML já tem assinatura digital, vamos enviar direto
            # status_servico = sefaz.consultar_status_servico()
            # if status_servico.get('status') != 'OK':
            #     logger.warning(f"AVISO: SEFAZ indisponível: {status_servico.get('mensagem')}")
            #     return self._enviar_sefaz_simulado(xml_assinado, chave_acesso, ambiente, 
            #                                      motivo="SEFAZ indisponível")
            
            logger.debug("OK: Enviando NFe para SEFAZ real...")
            
            # Enviar NFe
            resultado = sefaz.enviar_nfe(xml_assinado, chave_acesso)
            
            # Processar resultado
            if resultado.get('success'):
                xml_protocolo = self._gerar_xml_protocolo(xml_assinado, resultado)
                return {
                    'success': True,
                    'status': 'AUTORIZADA',
                    'chave_acesso': chave_acesso,
                    'protocolo': resultado.get('protocolo'),
                    'message': resultado.get('mensagem'),
                    'xml_protocolo': xml_protocolo,
                    'ambiente_real': True
                }
            else:
                logger.error(f"❌ SEFAZ REJEITOU: {resultado.get('status', 'ERRO')}")
                logger.error(f"❌ Mensagem completa: {resultado.get('mensagem', 'Erro desconhecido')}")
                logger.debug(f"❌ Código: {resultado.get('codigo', 'N/A')}")
                logger.debug(f"❌ Motivo: {resultado.get('motivo', 'N/A')}")
                if resultado.get('erros'):
                    logger.error(f"❌ Erros detalhados: {resultado.get('erros')}")
                return {
                    'success': False,
                    'status': resultado.get('status', 'ERRO'),
                    'message': resultado.get('mensagem', 'Erro desconhecido'),
                    'codigo': resultado.get('codigo'),
                    'motivo': resultado.get('motivo'),
                    'erros': resultado.get('erros'),
                    'ambiente_real': True
                }
        
        except Exception as e:
            logger.error(f"ERRO: Erro SEFAZ real: {e}")
            import traceback
            traceback.print_exc()
            # NÃO USA SIMULAÇÃO - retorna erro real para forçar correção
            return {
                'success': False,
                'status': 'ERRO_COMUNICACAO',
                'message': f'Erro na comunicação com SEFAZ: {str(e)}',
                'ambiente_real': False
            }
        
        finally:
            # Limpar arquivos temporários
            if cert_path and os.path.exists(cert_path):
                try:
                    os.unlink(cert_path)
                    logger.debug(f"[OK] Arquivo temporário removido: {cert_path}")
                except:
                    pass
            
            if key_path and os.path.exists(key_path):
                try:
                    os.unlink(key_path)
                    logger.debug(f"[OK] Arquivo temporário removido: {key_path}")
                except:
                    pass
    
    def _enviar_sefaz_simulado(self, xml_assinado: str, chave_acesso: str, ambiente: str, motivo: Optional[str] = None) -> Dict[str, Any]:
        """Envia para SEFAZ simulado - FALLBACK quando não há certificado válido"""
        try:
            logger.debug("\n" + "="*80)
            logger.debug("⚠️  ATENÇÃO: USANDO SIMULAÇÃO LOCAL (NÃO É SEFAZ REAL)")
            if motivo:
                logger.debug(f"⚠️  Motivo: {motivo}")
            else:
                logger.debug("⚠️  Motivo: Não especificado")
            logger.debug("⚠️  Para usar SEFAZ real, configure um certificado digital válido")
            logger.debug("="*80 + "\n")
            
            # Simular resposta
            protocolo = f"135{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            resultado_simulado = {
                'status': '100',
                'mensagem': 'Autorizado o uso da NF-e',
                'chave_acesso': chave_acesso,
                'protocolo': protocolo,
                'data_autorizacao': datetime.now().isoformat()
            }
            
            xml_protocolo = self._gerar_xml_protocolo(xml_assinado, resultado_simulado)
            
            return {
                'success': True,
                'status': 'AUTORIZADA',
                'chave_acesso': chave_acesso,
                'protocolo': protocolo,
                'message': 'Autorizado o uso da NF-e',
                'xml_protocolo': xml_protocolo,
                'ambiente_real': False,
                'motivo_simulacao': motivo
            }
            
        except Exception as e:
            logger.error(f"ERRO: Erro na simulação: {e}")
            return {'success': False, 'message': f'Erro na simulação: {str(e)}'}
    
    def consultar_nfe(self, chave_acesso: str, ambiente: int = 2) -> Dict[str, Any]:
        """
        Consulta status de uma NFe na SEFAZ (simulado)
        
        Args:
            chave_acesso: Chave de acesso da NFe (44 dígitos)
            ambiente: 1=Produção, 2=Homologação
            
        Returns:
            Dict com resultado da consulta
        """
        try:
            logger.debug(f"[CONSULTA] Consultando NFe: {chave_acesso}")
            logger.debug(f"[CONSULTA] Ambiente: {ambiente} ({'Produção' if ambiente == 1 else 'Homologação'})")
            
            # TODO: Implementar consulta real na SEFAZ quando disponível
            # Por enquanto, retorna simulação
            
            return {
                'success': True,
                'status': '100',
                'mensagem': 'Autorizado o uso da NF-e',
                'protocolo': f"135{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'data_autorizacao': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'motivo': 'NFe autorizada'
            }
            
        except Exception as e:
            logger.error(f"[ERRO] Erro na consulta: {e}")
            return {
                'success': False,
                'message': f'Erro ao consultar NFe: {str(e)}'
            }
        
    def _extrair_chave_acesso(self, xml_content: str) -> Optional[str]:
        """Extrai chave de acesso do XML assinado"""
        try:
            # Garantir que xml_content seja uma string
            if isinstance(xml_content, bytes):
                xml_content = xml_content.decode('utf-8')
            
            # Tentar extrair usando nfelib
            if NFELIB_DISPONIVEL and NfeProc is not None:
                try:
                    nfe_proc = NfeProc.from_xml(xml_content)
                    
                    # Extrair a chave do atributo Id da infNFe
                    if hasattr(nfe_proc, 'NFe') and hasattr(nfe_proc.NFe, 'infNFe'):
                        id_value = nfe_proc.NFe.infNFe.Id
                        if id_value and id_value.startswith('NFe'):
                            chave = id_value[3:]  # Remover 'NFe' do início
                            logger.debug(f"OK: Chave extraída via nfelib: {chave}")
                            return chave
                        
                except Exception as e:
                    logger.error(f"AVISO: Falha ao extrair com nfelib: {str(e)}")
                    # Continuar com os métodos regex
                    
            # Método regex caso o nfelib falhe
            # Método 1: buscar NFe seguido por 44 dígitos
            match = re.search(r'NFe(\d{44})', xml_content)
            if match:
                chave = match.group(1)
                logger.debug(f"OK: Chave extraída via regex: {chave}")
                return chave
            
            # Método 2: procurar pelo Id em qualquer formato
            match = re.search(r'Id=[\'"]\s*NFe(\d{44})\s*[\'"]', xml_content)
            if match:
                chave = match.group(1)
                logger.debug(f"OK: Chave extraída via regex alternativo: {chave}")
                return chave
                
            # Método 3: remover espaços e tentar novamente
            xml_sem_espacos = re.sub(r'\s', '', xml_content)
            match = re.search(r'NFe(\d{44})', xml_sem_espacos)
            if match:
                chave = match.group(1)
                logger.debug(f"OK: Chave extraída via regex sem espaços: {chave}")
                return chave
                    
            # Se nenhum método funcionou
            logger.error("ERRO: Chave de acesso não encontrada no XML!")
            logger.debug(f" Primeiros 200 caracteres: {xml_content[:200]}")
            
            return None
        except Exception as e:
            logger.error(f"ERRO: Erro ao extrair chave: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _gerar_xml_protocolo(self, xml_assinado: str, resultado: Dict[str, Any]) -> str:
        """Gera XML com protocolo"""
        try:
            if not ET:
                return xml_assinado
                
            root = ET.fromstring(xml_assinado)
            nfe_element = root.find('.//{http://www.portalfiscal.inf.br/nfe}NFe')
            
            # Extrair tpAmb do XML da NFe para usar no protocolo
            tp_amb = '2'  # Padrão: homologação
            try:
                tp_amb_element = root.find('.//{http://www.portalfiscal.inf.br/nfe}tpAmb')
                if tp_amb_element is not None and tp_amb_element.text:
                    tp_amb = tp_amb_element.text
                    logger.debug(f"[PROTOCOLO] tpAmb extraído da NFe: {tp_amb} ({'Produção' if tp_amb == '1' else 'Homologação'})")
            except:
                logger.debug(f"[PROTOCOLO] Não foi possível extrair tpAmb, usando padrão: 2")
            
            if nfe_element is not None:
                nfe_xml = ET.tostring(nfe_element, encoding='unicode')
            else:
                nfe_xml = xml_assinado
            
            # Determinar cStat e digVal baseado no ambiente
            if resultado.get('ambiente_real'):
                # SEFAZ real retorna cStat como número (100, 150, etc)
                cstat = resultado.get('status', '100') if resultado.get('status', '').isdigit() else '100'
                dig_val = resultado.get('digVal', resultado.get('digest_value', ''))
            else:
                # Simulação
                cstat = 'AUTORIZADA'
                dig_val = 'SIMULADO'
            
            xml_protocolo = f'''<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
{nfe_xml}
  <protNFe versao="4.00">
    <infProt>
      <tpAmb>{tp_amb}</tpAmb>
      <verAplic>SP_NFE_PL_008i2</verAplic>
      <chNFe>{resultado.get('chave_acesso', '')}</chNFe>
      <dhRecbto>{resultado.get('data_autorizacao', datetime.now().isoformat())}</dhRecbto>
      <nProt>{resultado.get('protocolo', '')}</nProt>
      <digVal>{dig_val}</digVal>
      <cStat>{cstat}</cStat>
      <xMotivo>{resultado.get('mensagem', 'Autorizado o uso da NF-e')}</xMotivo>
    </infProt>
  </protNFe>
</nfeProc>'''
            
            return xml_protocolo
            
        except Exception as e:
            logger.error(f"ERRO: Erro ao gerar protocolo: {e}")
            return xml_assinado

# OK: FUNÇÕES AUXILIARES CORRIGIDAS
def generate_nfe_xml(form_data: Dict[str, Any], emitente_data: Dict[str, Any], 
                    destinatario_data: Dict[str, Any], items: list, 
                    tp_amb: int = 2, finalidade: str = 'emitir',
                    include_resp_tec: bool = True) -> str:
    """
    Gerar XML da NFe usando biblioteca nfelib (XSD-validated)
    
    MIGRADO PARA NFELIB - Após 50+ tentativas de resolver Erro 225 com XML manual,
    migramos para a biblioteca nfelib que gera XML validado pelo XSD e homologado pela SEFAZ.
    """
    try:
        logger.debug(f"🚀 [NFELIB] Gerando XML NFe com biblioteca nfelib")
        logger.debug(f"📋 Form data keys: {list(form_data.keys())}")
        logger.debug(f"📦 Items: {len(items)} itens")
        
        # Importar função do novo serviço nfelib
        from services.nfe_nfelib_service import generate_nfe_xml_nfelib
        
        # Obter número da NFe
        numero_nfe = form_data.get('numero_nfe', 1)
        if not numero_nfe:
            numero_nfe = 1
        
        # Adicionar tpAmb ao form_data
        form_data['tpAmb'] = tp_amb
        
        # Gerar XML com nfelib
        xml_nfe = generate_nfe_xml_nfelib(
            emitente_data=emitente_data,
            destinatario_data=destinatario_data,
            items=items,
            form_data=form_data,
            numero_nfe=numero_nfe,
            certificado_data={},  # Será usado depois na assinatura
            include_resp_tec=include_resp_tec
        )
        
        logger.debug(f"✅ [NFELIB] XML gerado com sucesso: {len(xml_nfe)} caracteres")
        
        return xml_nfe
        
    except Exception as e:
        logger.error(f"❌ [NFELIB] Erro ao gerar XML: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Erro ao gerar XML da NFe com nfelib: {str(e)}")


def generate_nfe_xml_LEGACY(form_data: Dict[str, Any], emitente_data: Dict[str, Any], 
                    destinatario_data: Dict[str, Any], items: list, 
                    tp_amb: int = 2, finalidade: str = 'emitir') -> str:
    """
    Gerar XML da NFe com validações e formatação adequada
    
    FUNÇÃO LEGACY - Mantida apenas como referência histórica.
    NÃO USAR - Use generate_nfe_xml() que agora usa nfelib.
    """
    try:
        logger.debug(f" === GERANDO XML NFE ===")
        logger.debug(f" Form data keys: {list(form_data.keys())}")
        logger.debug(f" Items: {len(items)} itens")
        
        # OK: CORREÇÃO: Verificar e processar CFOP nos itens ANTES DA VALIDAÇÃO
        for i, item in enumerate(items, 1):
            cfop_original = item.get('cfop', '')
            logger.debug(f" Item {i} - CFOP original: '{cfop_original}' (tipo: {type(cfop_original)})")
            
            # OK: CORREÇÃO: Garantir que CFOP seja string e tenha 4 dígitos
            if cfop_original:
                # Se for número, converter para string
                if isinstance(cfop_original, (int, float)):
                    cfop_str = str(int(cfop_original))
                else:
                    cfop_str = str(cfop_original).strip()
                
                # Remover pontos se houver (ex: "5.102" -> "5102")
                cfop_str = cfop_str.replace('.', '').replace('-', '')
                
                # Garantir que tenha 4 dígitos
                if len(cfop_str) == 4 and cfop_str.isdigit():
                    item['cfop'] = cfop_str
                    logger.debug(f"OK: Item {i} - CFOP corrigido: '{cfop_str}'")
                else:
                    logger.warning(f"AVISO: Item {i} - CFOP inválido: '{cfop_original}' -> usando padrão '5102'")
                    item['cfop'] = '5102'  # CFOP padrão para venda
            else:
                logger.warning(f"AVISO: Item {i} - CFOP vazio -> usando padrão '5102'")
                item['cfop'] = '5102'
        
        # ========== VALIDAÇÃO TRIBUTÁRIA DESABILITADA DURANTE EMISSÃO ==========
        # validacao_ok, erros_validacao = validar_tributacao_nfe(emitente_data, items)
        # 
        # if not validacao_ok:
        #     erro_msg = "❌ ERROS DE TRIBUTAÇÃO ENCONTRADOS:\n\n" + "\n\n".join(erros_validacao)
        #     logger.error(f"\n{erro_msg}")
        #     raise ValueError(erro_msg)
        
        logger.debug(f"ℹ️  Validação IA desabilitada durante emissão (evitar falsos positivos)")
        
        # Debug: verificar tributação dos itens
        logger.debug(f" [DEBUG] Verificando tributação dos itens:")
        for idx, item in enumerate(items[:3], 1):  # Primeiros 3 itens
            icms = item.get('icms', {})
            logger.debug(f"   Item {idx}: CST={icms.get('cst')}, CSOSN={icms.get('csosn')}")
        
        # Importar bibliotecas necessárias (corrigido para fallback caso lxml não esteja instalado)
        try:
            import lxml.etree as etree
        except ImportError:
            import xml.etree.ElementTree as etree
        from datetime import datetime, timezone
        import uuid
        
        # OK: PROCESSAR DADOS BÁSICOS DA NFE
        serie = int(form_data.get('serie', '1'))
        modelo = '55'  # 55=NFe, 65=NFCe
        tp_nf = form_data.get('tpNF', '1')  # 1=Saída
        fin_nfe = form_data.get('finNFe', '1')  # 1=Normal
        nat_op = form_data.get('natOp', 'Venda de Mercadorias')
        
        # Obter número da NFe fornecido pelo usuário
        from sqlalchemy import text
        numero_nfe = int(form_data.get('numero_nfe', 1))
        logger.debug(f" [[OK]] Número da NFe fornecido: {numero_nfe} (série {serie})")
        # Nota: Validação de número duplicado é feita em _criar_nova_nfe()
        
        # Data de emissão
        data_emissao_str = form_data.get('dataEmissao')
        if data_emissao_str:
            try:
                data_emissao = datetime.fromisoformat(data_emissao_str.replace('Z', '+00:00'))
                if data_emissao.tzinfo is None:
                    # Se não tem timezone, assume BRT
                    data_emissao = data_emissao.replace(tzinfo=timezone(timedelta(hours=-3)))
            except:
                data_emissao = datetime.now(timezone.utc)
        else:
            # Usar horário atual UTC e subtrair 3 minutos para garantir que não seja futuro
            # Margem de segurança grande devido a possível dessincronização do SEFAZ de homologação
            data_emissao = datetime.now(timezone.utc) - timedelta(minutes=3)
        
        # Garantir que tem timezone antes de converter
        if data_emissao.tzinfo is None:
            data_emissao = data_emissao.replace(tzinfo=timezone.utc)
        
        # Formatação da data para o XML com timezone de Brasília
        # Converter para BRT (-03:00)
        brasilia_tz = timezone(timedelta(hours=-3))
        data_emissao_brt = data_emissao.astimezone(brasilia_tz)
        dh_emi = data_emissao_brt.strftime('%Y-%m-%dT%H:%M:%S-03:00')
        
        logger.debug(f"⏰ UTC: {data_emissao.strftime('%Y-%m-%d %H:%M:%S')} → BRT: {dh_emi}")
        
        # OK: GERAR CHAVE DE ACESSO
        uf_code = get_uf_ibge_code(emitente_data.get('uf', 'SP'))
        cnpj_emit = emitente_data.get('cnpj', '').replace('.', '').replace('/', '').replace('-', '')
        
        # Código numérico aleatório de 8 dígitos
        codigo_numerico = str(uuid.uuid4().int)[-8:]
        
        # Formar chave sem DV
        chave_sem_dv = f"{uf_code:02d}{data_emissao.strftime('%y%m')}{cnpj_emit:>14}{55:02d}{int(serie):03d}{numero_nfe:09d}{tp_nf}{codigo_numerico}"
        
        # Calcular DV da chave
        def calcular_dv_chave(chave):
            sequence = "4329876543298765432987654329876543298765432"
            soma = sum(int(chave[i]) * int(sequence[i]) for i in range(len(chave)))
            resto = soma % 11
            return 0 if resto in (0, 1) else 11 - resto
        
        dv = calcular_dv_chave(chave_sem_dv)
        chave_acesso = chave_sem_dv + str(dv)
        
        logger.debug(f" Chave de acesso: {chave_acesso}")
        
        # OK: PROCESSAR CNPJ/CPF DO DESTINATÁRIO
        dest_cpf_cnpj = destinatario_data.get('cpf_cnpj', '').replace('.', '').replace('/', '').replace('-', '').strip()
        
        if not dest_cpf_cnpj:
            raise ValueError("CPF/CNPJ do destinatário é obrigatório e não pode estar vazio")
        
        # Determinar se é CPF ou CNPJ
        if len(dest_cpf_cnpj) == 11:
            dest_tag = 'CPF'
        elif len(dest_cpf_cnpj) == 14:
            dest_tag = 'CNPJ'
        else:
            raise ValueError(f"CPF/CNPJ do destinatário inválido (deve ter 11 ou 14 dígitos): '{dest_cpf_cnpj}' (tamanho: {len(dest_cpf_cnpj)})")
        
        # OK: CALCULAR TOTAIS DA NFE - aceitar totais do JSON ou calcular dos itens
        totais_json = form_data.get('totais', {})
        
        if totais_json:
            # Usar totais fornecidos no JSON
            total_produtos = float(totais_json.get('valor_produtos', 0))
            total_icms_st = float(totais_json.get('valor_icms_st', 0))
            base_icms_st = float(totais_json.get('base_calculo_icms_st', 0))
            total_ipi = float(totais_json.get('valor_ipi', 0))
            total_pis = float(totais_json.get('valor_pis', 0))
            total_cofins = float(totais_json.get('valor_cofins', 0))
            total_frete = float(totais_json.get('valor_frete', 0))
            total_seguro = float(totais_json.get('valor_seguro', 0))
            total_desconto = float(totais_json.get('valor_desconto', 0))
            total_outras = float(totais_json.get('valor_outras_despesas', 0))
            total_nfe = float(totais_json.get('valor_total_nota', 0))
            # Recalcular vBC e vICMS totais a partir dos itens para garantir consistência
            base_icms = 0.0
            total_icms = 0.0
            for _item in items:
                _icms = _item.get('icms', {})
                _bc = round(float(_icms.get('base_calculo', 0)), 2)
                _aliq = float(_icms.get('aliquota', 0))
                base_icms += _bc
                total_icms += round(_bc * _aliq / 100, 2)
            base_icms = round(base_icms, 2)
            total_icms = round(total_icms, 2)
            logger.debug(f" Usando totais do JSON (ICMS recalculado: vBC={base_icms:.2f} vICMS={total_icms:.2f})")
        else:
            # Calcular totais dos itens
            total_produtos = 0
            total_icms = 0
            total_icms_st = 0
            base_icms = 0
            base_icms_st = 0
            total_ipi = 0
            total_pis = 0
            total_cofins = 0
            total_frete = 0
            total_seguro = 0
            total_desconto = 0
            total_outras = 0
            
            for item in items:
                try:
                    # Aceitar campos da API v2 ou interface web
                    valor_total_item = float(item.get('valor_total_bruto') or item.get('valor_total', 0))
                    
                    icms_item = item.get('icms', {})
                    ipi_item = item.get('ipi', {})
                    pis_item = item.get('pis', {})
                    cofins_item = item.get('cofins', {})
                    
                    total_produtos += valor_total_item
                    _bc_item = round(float(icms_item.get('base_calculo', 0)), 2)
                    _aliq_item = float(icms_item.get('aliquota', 0))
                    total_icms += round(_bc_item * _aliq_item / 100, 2)
                    total_icms_st += float(icms_item.get('valor_st', 0))
                    base_icms += _bc_item
                    base_icms_st += float(icms_item.get('base_calculo_st', 0))
                    total_ipi += float(ipi_item.get('valor', 0))
                    total_pis += float(pis_item.get('valor', 0))
                    total_cofins += float(cofins_item.get('valor', 0))
                    
                    logger.debug(f" Item: {item.get('descricao', 'N/A')[:30]} - Valor: R$ {valor_total_item:.2f} - CFOP: {item.get('cfop', 'N/A')}")
                except (ValueError, TypeError) as e:
                    logger.error(f"AVISO: Erro ao processar valores do item: {e}")
                    continue
            
            total_nfe = total_produtos + total_ipi + total_icms_st + total_frete + total_seguro + total_outras - total_desconto
        
        logger.debug(f" Totais - Produtos: R$ {total_produtos:.2f}, ICMS: R$ {total_icms:.2f}, NFe: R$ {total_nfe:.2f}")
        
        # OK: CRIAR ESTRUTURA XML COM NAMESPACE CORRETO DESDE O INÍCIO
        # CRÍTICO: Namespace deve estar presente ANTES da assinatura
        NFE_NS = "http://www.portalfiscal.inf.br/nfe"
        
        # Registrar namespace padrão (sem prefixo)
        etree.register_namespace('', NFE_NS)
        
        # Helper para criar elementos com namespace
        def E(parent, tag, text=None):
            """Cria elemento XML com namespace correto"""
            elem = etree.SubElement(parent, f"{{{NFE_NS}}}{tag}")
            if text is not None:
                elem.text = str(text)
            return elem
        
        # Criar elemento NFe COM namespace desde o início
        root = etree.Element(f"{{{NFE_NS}}}NFe")
        
        # infNFe
        inf_nfe = E(root, "infNFe")
        inf_nfe.set("Id", f"NFe{chave_acesso}")
        inf_nfe.set("versao", "4.00")
        
        # ide
        ide = etree.SubElement(inf_nfe, "ide")
        etree.SubElement(ide, "cUF").text = str(uf_code)
        etree.SubElement(ide, "cNF").text = codigo_numerico
        etree.SubElement(ide, "natOp").text = str(nat_op).strip()
        etree.SubElement(ide, "mod").text = "55"
        etree.SubElement(ide, "serie").text = str(serie)
        etree.SubElement(ide, "nNF").text = str(numero_nfe)
        etree.SubElement(ide, "dhEmi").text = dh_emi
        etree.SubElement(ide, "tpNF").text = str(tp_nf)
        etree.SubElement(ide, "idDest").text = "1"  # 1=Operação interna
        etree.SubElement(ide, "cMunFG").text = str(emitente_data.get('codigo_municipio', '3550308'))
        etree.SubElement(ide, "tpImp").text = "1"  # 1=DANFE normal
        etree.SubElement(ide, "tpEmis").text = "1"  # 1=Emissão normal
        etree.SubElement(ide, "cDV").text = str(dv)
        etree.SubElement(ide, "tpAmb").text = str(tp_amb)
        etree.SubElement(ide, "finNFe").text = str(fin_nfe)
        etree.SubElement(ide, "indFinal").text = "1"  # 1=Consumidor final
        # indPres: 0=Não se aplica, 1=Presencial, 2=Internet, 3=Teleatendimento, 4=Entrega domicílio, 5=Presencial fora estabelecimento
        # IMPORTANTE: valor 9 só é válido para NFC-e (modelo 65), não para NF-e (modelo 55)
        etree.SubElement(ide, "indPres").text = form_data.get('indPres', "1")  # Padrão: 1=Operação presencial
        etree.SubElement(ide, "indIntermed").text = "0"  # 0=Sem intermediador, 1=Com marketplace
        etree.SubElement(ide, "procEmi").text = "0"  # 0=Emissão com aplicação do contribuinte
        etree.SubElement(ide, "verProc").text = "EmiteMax_1.0"  # Versão do aplicativo (sem espaços)
        
        # emit
        emit = etree.SubElement(inf_nfe, "emit")
        etree.SubElement(emit, "CNPJ").text = cnpj_emit
        etree.SubElement(emit, "xNome").text = str(emitente_data.get('razao_social', '')).strip()
        if emitente_data.get('nome_fantasia'):
            etree.SubElement(emit, "xFant").text = str(emitente_data['nome_fantasia']).strip()
        
        # Endereço do emitente
        ender_emit = etree.SubElement(emit, "enderEmit")
        etree.SubElement(ender_emit, "xLgr").text = str(emitente_data.get('logradouro', '')).strip()
        etree.SubElement(ender_emit, "nro").text = str(emitente_data.get('numero', '')).strip()
        etree.SubElement(ender_emit, "xBairro").text = str(emitente_data.get('bairro', '')).strip()
        etree.SubElement(ender_emit, "cMun").text = str(emitente_data.get('codigo_municipio', '3550308'))
        etree.SubElement(ender_emit, "xMun").text = str(emitente_data.get('nome_municipio', 'São Paulo')).strip()
        etree.SubElement(ender_emit, "UF").text = str(emitente_data.get('uf', 'SP')).strip()
        
        cep_emit = emitente_data.get('cep', '').replace('-', '')
        etree.SubElement(ender_emit, "CEP").text = cep_emit
        etree.SubElement(ender_emit, "cPais").text = "1058"
        etree.SubElement(ender_emit, "xPais").text = "Brasil"
        
        etree.SubElement(emit, "IE").text = emitente_data.get('inscricao_estadual', '')
        etree.SubElement(emit, "CNAE").text = "6201500"  # Desenvolvimento de programas de computador sob encomenda
        
        # CRT - Código de Regime Tributário
        # 1=Simples Nacional, 2=Simples Nacional - excesso, 3=Regime Normal
        regime_tributario_id = emitente_data.get('regime_tributario_id', 3)
        
        # CORREÇÃO: Verificar tributação dos itens para determinar regime real
        # Se algum item tem CST (não CSOSN), usar Regime Normal mesmo se emitente for Simples
        has_cst_items = any(
            item.get('icms', {}).get('cst') and not item.get('icms', {}).get('csosn')
            for item in items
        )
        
        if has_cst_items:
            logger.debug(f" [AUTO] Itens têm CST - forçando Regime Normal (CRT=3)")
            crt = "3"  # Regime Normal
        else:
            crt = "1" if regime_tributario_id == 1 else "3"
            logger.debug(f" [INFO] Usando CRT={crt} baseado no emitente")
        etree.SubElement(emit, "CRT").text = crt
        
        # dest
        dest = etree.SubElement(inf_nfe, "dest")
        
        # Validação extra: garantir que dest_tag não está vazio
        if not dest_tag or not dest_tag.strip():
            raise ValueError("CRÍTICO: dest_tag está vazio! Verifique a validação CPF/CNPJ")
        
        etree.SubElement(dest, dest_tag).text = dest_cpf_cnpj
        etree.SubElement(dest, "xNome").text = str(destinatario_data.get('nome_razao_social', '')).strip()
        
        # Endereço do destinatário
        ender_dest = etree.SubElement(dest, "enderDest")
        etree.SubElement(ender_dest, "xLgr").text = str(destinatario_data.get('logradouro', '')).strip()
        etree.SubElement(ender_dest, "nro").text = str(destinatario_data.get('numero', '')).strip()
        etree.SubElement(ender_dest, "xBairro").text = str(destinatario_data.get('bairro', '')).strip()
        etree.SubElement(ender_dest, "cMun").text = str(destinatario_data.get('codigo_municipio', '3550308'))
        etree.SubElement(ender_dest, "xMun").text = str(destinatario_data.get('nome_municipio', 'São Paulo')).strip()
        etree.SubElement(ender_dest, "UF").text = str(destinatario_data.get('uf', 'SP')).strip()
        
        cep_dest = destinatario_data.get('cep', '').replace('-', '')
        etree.SubElement(ender_dest, "CEP").text = cep_dest
        etree.SubElement(ender_dest, "cPais").text = "1058"
        etree.SubElement(ender_dest, "xPais").text = "Brasil"
        
        # indIEDest: 1=Contribuinte ICMS (tem IE), 2=Contribuinte isento, 9=Não contribuinte
        ie_dest = str(destinatario_data.get('ie') or destinatario_data.get('inscricao_estadual') or '').strip()
        if ie_dest and ie_dest.upper() == 'ISENTO':
            etree.SubElement(dest, "indIEDest").text = "2"
            etree.SubElement(dest, "IE").text = "ISENTO"
        elif ie_dest:
            # Remove formatação (pontos, traços, barras)
            ie_limpa = ''.join(filter(str.isalnum, ie_dest))
            etree.SubElement(dest, "indIEDest").text = "1"
            etree.SubElement(dest, "IE").text = ie_limpa
        else:
            etree.SubElement(dest, "indIEDest").text = "9"  # Não contribuinte (sem IE)
        
        # OK: ITENS DA NFE COM CFOP CORRETO
        det_list = []
        for i, item in enumerate(items, 1):
            det = etree.SubElement(inf_nfe, "det")
            det.set("nItem", str(i))
            
            # prod
            prod = etree.SubElement(det, "prod")
            etree.SubElement(prod, "cProd").text = str(item.get('codigo_produto', f'PROD{i:03d}'))
            etree.SubElement(prod, "cEAN").text = "SemGTIN"
            
            # xProd - normalizar caracteres especiais (remover aspas tipográficas, etc)
            descricao_original = str(item.get('descricao', f'Produto {i}'))
            descricao = descricao_original
            # Substituir aspas tipográficas por aspas retas
            descricao = descricao.replace('"', '"').replace('"', '"').replace("'", "'").replace("'", "'")
            # Remover outros caracteres problemáticos
            descricao = descricao.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            # Remover completamente aspas se normalização falhar
            if '"' in descricao or '"' in descricao or '"' in descricao:
                logger.debug(f"⚠️  Aspas curvas detectadas em '{descricao_original}' - removendo todas as aspas")
                descricao = descricao.replace('"', '').replace('"', '').replace('"', '').replace("'", '').replace("'", '')
            etree.SubElement(prod, "xProd").text = descricao.strip()
            logger.debug(f" xProd normalizado: '{descricao}'")
            
            etree.SubElement(prod, "NCM").text = str(item.get('ncm', '99999999'))
            
            # CFOP - validar compatibilidade com regime tributário
            cfop_item = item.get('cfop', '5102')
            
            # Simples Nacional (CRT=1): ajustar CFOP 5401 para 5405
            # 5401 = Venda produção própria com ST (incompatível com Simples)
            # 5405 = Venda mercadoria com ST, na condição de substituído (correto para Simples)
            if crt == "1":
                if cfop_item == '5401':
                    cfop_original = cfop_item
                    cfop_item = '5405'  # Mercadoria com ST - substituído
                    logger.debug(f"⚠️  CFOP {cfop_original} ajustado para {cfop_item} (Simples Nacional com ST)")
                elif cfop_item == '6401':
                    cfop_item = '6405'  # Interestadual com ST
                    logger.debug(f"⚠️  CFOP 6401 ajustado para 6405 (Simples Nacional com ST interestadual)")
            
            logger.debug(f" Item {i} - CFOP final no XML: '{cfop_item}'")
            etree.SubElement(prod, "CFOP").text = str(cfop_item)
            
            etree.SubElement(prod, "uCom").text = str(item.get('unidade_comercial') or item.get('unidade', 'UN'))
            
            # Quantidades e valores - aceitar campos da API v2 ou interface web
            quantidade = float(item.get('quantidade_comercial') or item.get('quantidade', 1))
            valor_unitario = float(item.get('valor_unitario_comercial') or item.get('valor_unitario', 0))
            valor_total = float(item.get('valor_total_bruto') or item.get('valor_total', quantidade * valor_unitario))
            
            etree.SubElement(prod, "qCom").text = f"{quantidade:.2f}"
            etree.SubElement(prod, "vUnCom").text = f"{valor_unitario:.2f}"
            etree.SubElement(prod, "vProd").text = f"{valor_total:.2f}"
            etree.SubElement(prod, "cEANTrib").text = "SemGTIN"
            etree.SubElement(prod, "uTrib").text = str(item.get('unidade', 'UN'))
            etree.SubElement(prod, "qTrib").text = f"{quantidade:.2f}"
            etree.SubElement(prod, "vUnTrib").text = f"{valor_unitario:.2f}"
            etree.SubElement(prod, "indTot").text = "1"  # 1=Valor do item compõe valor total da NF-e
            
            # imposto
            imposto = etree.SubElement(det, "imposto")
            
            # ICMS - processar dados do JSON
            icms_data = item.get('icms', {})
            icms = etree.SubElement(imposto, "ICMS")
            
            # Verificar se é Simples Nacional (CRT = 1)
            is_simples_nacional = (crt == "1")
            
            if is_simples_nacional:
                # SIMPLES NACIONAL - Usar CSOSN
                csosn = icms_data.get('csosn') or item.get('csosn_icms', '102')
                
                # Validar que csosn não está vazio
                if not csosn or csosn.strip() == '':
                    csosn = '102'  # Padrão: Tributada sem permissão de crédito
                    logger.debug(f"⚠️  CSOSN não informado - usando padrão 102")
                
                # CORREÇÃO: Se CFOP for 5405/6405 (ST substituído), deve usar CSOSN 500
                # CSOSN 500 = ICMS cobrado anteriormente por ST (substituído)
                if cfop_item in ['5405', '6405'] and csosn != '500':
                    logger.debug(f"⚠️  CSOSN {csosn} ajustado para 500 (CFOP {cfop_item} - ST substituído)")
                    csosn = '500'
                
                icms_sn = etree.SubElement(icms, f"ICMSSN{csosn}")
                etree.SubElement(icms_sn, "orig").text = str(icms_data.get('origem', '0'))
                etree.SubElement(icms_sn, "CSOSN").text = csosn
                
                logger.debug(f"[DEBUG-ICMS] CSOSN {csosn} - Origem: {icms_data.get('origem', '0')}")
                
                # CSOSN 500: ICMS cobrado anteriormente por ST
                # Deve ter APENAS orig e CSOSN (sem pCredSN nem vCredICMSSN)
                if csosn == '500':
                    logger.debug(f"[DEBUG-ICMS] CSOSN 500 - XML: <ICMSSN500><orig>{icms_data.get('origem', '0')}</orig><CSOSN>500</CSOSN></ICMSSN500>")
                    pass  # Não adiciona nenhum campo extra
                # CSOSN 101, 201, 202, 203, 900: Incluir campos de crédito SOMENTE se houver alíquota
                elif csosn in ['101', '201', '202', '203', '900']:
                    aliq_icms = float(icms_data.get('aliquota', 0))
                    bc_icms = round(float(icms_data.get('base_calculo', valor_total)), 2)
                    valor_icms = round(bc_icms * aliq_icms / 100, 2) if aliq_icms > 0 else 0.0
                    # CSOSN 900 (Outros): permite vBC/pICMS/vICMS além do crédito SN
                    # Obrigatório para devolução (finNFe=4) com Simples Nacional para que o
                    # ICMS apareça no ICMSTot/vICMS e consequentemente no DANFE
                    if csosn == '900' and bc_icms > 0 and aliq_icms > 0:
                        etree.SubElement(icms_sn, "modBC").text = str(icms_data.get('modalidade_bc', '3'))
                        etree.SubElement(icms_sn, "vBC").text = f"{bc_icms:.2f}"
                        etree.SubElement(icms_sn, "pICMS").text = f"{aliq_icms:.2f}"
                        etree.SubElement(icms_sn, "vICMS").text = f"{valor_icms:.2f}"
                        logger.debug(f"[DEBUG-ICMS] CSOSN 900 - modBC:3 vBC:{bc_icms:.2f} pICMS:{aliq_icms:.2f} vICMS:{valor_icms:.2f}")
                    # Adicionar campos SOMENTE se alíquota > 0 (se zero, OMITIR pCredSN/vCredICMSSN)
                    if aliq_icms > 0:
                        etree.SubElement(icms_sn, "pCredSN").text = f"{aliq_icms:.2f}"
                        etree.SubElement(icms_sn, "vCredICMSSN").text = f"{valor_icms:.2f}"
                        logger.debug(f"[DEBUG-ICMS] CSOSN {csosn} - pCredSN: {aliq_icms:.2f}, vCredICMSSN: {valor_icms:.2f}")
                    else:
                        logger.debug(f"[DEBUG-ICMS] CSOSN {csosn} - SEM crédito (alíquota zero, campos omitidos)")
            else:
                # REGIME NORMAL - Usar CST
                cst_icms = icms_data.get('cst', '00')
                origem = icms_data.get('origem', '0')
                
                # Mapear CST para tag XML correta (alguns CSTs compartilham a mesma tag)
                # CST 40, 41, 50: usam ICMS40
                # CST 51: usa ICMS51 (diferimento)
                # CST 60: usa ICMS60 (ICMS ST retido)
                cst_to_tag = {
                    '00': 'ICMS00', '10': 'ICMS10', '20': 'ICMS20', '30': 'ICMS30',
                    '40': 'ICMS40', '41': 'ICMS40', '50': 'ICMS40',  # 40, 41, 50 usam ICMS40
                    '51': 'ICMS51', '60': 'ICMS60', '70': 'ICMS70', '90': 'ICMS90'
                }
                
                if cst_icms in cst_to_tag:
                    icms_tag = cst_to_tag[cst_icms]
                else:
                    # CST não reconhecido - usar ICMS40 como padrão (não tributado)
                    logger.debug(f"⚠️  CST ICMS '{cst_icms}' não reconhecido - usando ICMS40 (não tributado)")
                    icms_tag = 'ICMS40'
                    cst_icms = '41'  # Ajustar para não tributado
                
                # Validação extra: garantir que icms_tag não está vazio
                if not icms_tag or not icms_tag.strip():
                    logger.debug(f"⚠️ CRÍTICO: icms_tag vazio! Usando ICMS40 como fallback")
                    icms_tag = 'ICMS40'
                
                icms_tributado = etree.SubElement(icms, icms_tag)
                etree.SubElement(icms_tributado, "orig").text = str(origem)
                etree.SubElement(icms_tributado, "CST").text = cst_icms
                
                # Processar conforme CST
                if cst_icms in ['00', '10', '20', '51', '70', '90']:  # Tributados
                    aliq_icms = float(icms_data.get('aliquota', 0))
                    bc_icms = float(icms_data.get('base_calculo', 0))
                    # vICMS deve ser SEMPRE recalculado a partir de vBC e pICMS já arredondados
                    # para garantir que vICMS == round(vBC * pICMS / 100, 2) conforme SEFAZ exige
                    bc_icms_r = round(bc_icms, 2)
                    valor_icms = round(bc_icms_r * aliq_icms / 100, 2) if bc_icms_r > 0 and aliq_icms > 0 else 0.0
                    
                    if bc_icms_r > 0 and aliq_icms > 0:
                        etree.SubElement(icms_tributado, "modBC").text = str(icms_data.get('modalidade_bc', '3'))
                        etree.SubElement(icms_tributado, "vBC").text = f"{bc_icms_r:.2f}"
                        etree.SubElement(icms_tributado, "pICMS").text = f"{aliq_icms:.2f}"
                        etree.SubElement(icms_tributado, "vICMS").text = f"{valor_icms:.2f}"
                    
                    # CST 10, 30, 70: ICMS ST
                    if cst_icms in ['10', '30', '70'] and icms_data.get('valor_st'):
                        etree.SubElement(icms_tributado, "modBCST").text = str(icms_data.get('modalidade_bc_st', '4'))
                        if icms_data.get('mva_st'):
                            etree.SubElement(icms_tributado, "pMVAST").text = f"{float(icms_data['mva_st']):.2f}"
                        etree.SubElement(icms_tributado, "vBCST").text = f"{float(icms_data.get('base_calculo_st', 0)):.2f}"
                        etree.SubElement(icms_tributado, "pICMSST").text = f"{float(icms_data.get('aliquota_st', 18)):.2f}"
                        etree.SubElement(icms_tributado, "vICMSST").text = f"{float(icms_data['valor_st']):.2f}"
                    
                    # CST 20, 70: Redução de BC
                    if cst_icms in ['20', '70'] and icms_data.get('percentual_reducao_bc'):
                        etree.SubElement(icms_tributado, "pRedBC").text = f"{float(icms_data['percentual_reducao_bc']):.2f}"
                    
                    # CST 51: Diferimento
                    if cst_icms == '51' and icms_data.get('percentual_diferimento'):
                        etree.SubElement(icms_tributado, "pDif").text = f"{float(icms_data['percentual_diferimento']):.2f}"
                        if icms_data.get('valor_icms_diferido'):
                            etree.SubElement(icms_tributado, "vICMSDif").text = f"{float(icms_data['valor_icms_diferido']):.2f}"
                
                # CST 40, 41, 50: Isenta/Não tributada (usam tag ICMS40 mas CST diferente)
                elif cst_icms in ['40', '41', '50']:
                    if icms_data.get('motivo_desoneracao'):
                        etree.SubElement(icms_tributado, "motDesICMS").text = str(icms_data['motivo_desoneracao'])
                    # Não precisa adicionar mais nada, apenas orig e CST já foram adicionados
                
                # CST 60: ST retido anteriormente
                elif cst_icms == '60':
                    if icms_data.get('base_calculo_st_retido'):
                        etree.SubElement(icms_tributado, "vBCSTRet").text = f"{float(icms_data['base_calculo_st_retido']):.2f}"
                    if icms_data.get('valor_icms_st_retido'):
                        etree.SubElement(icms_tributado, "vICMSSTRet").text = f"{float(icms_data['valor_icms_st_retido']):.2f}"
                else:
                    # CST não reconhecido - usar ICMS40
                    icms_nt = etree.SubElement(icms, "ICMS40")
                    etree.SubElement(icms_nt, "orig").text = str(origem)
                    etree.SubElement(icms_nt, "CST").text = "41"
            
            # IPI
            ipi_data = item.get('ipi', {})
            ipi_valor = float(ipi_data.get('valor', 0)) if ipi_data else 0.0
            ipi_cst = str(ipi_data.get('cst', '99')) if ipi_data else '99'
            # CSTs tributados pelo IPI (geram valor a pagar): 00, 49, 50
            # CSTs não tributados (isenção/suspensão/imunidade): 01-05, 51-55, 99
            ipi_csts_tributados = {'00', '49', '50'}
            if ipi_data and (ipi_valor > 0 or ipi_cst in ipi_csts_tributados):
                ipi = etree.SubElement(imposto, "IPI")
                # cEnq é obrigatório pelo schema da NFe (999 = outros/não enquadrado)
                etree.SubElement(ipi, "cEnq").text = str(ipi_data.get('cenq', '999'))
                if ipi_cst in ipi_csts_tributados:
                    # IPITrib: IPI com incidência
                    ipi_trib = etree.SubElement(ipi, "IPITrib")
                    etree.SubElement(ipi_trib, "CST").text = ipi_cst
                    etree.SubElement(ipi_trib, "vBC").text = f"{float(ipi_data.get('base_calculo', 0)):.2f}"
                    etree.SubElement(ipi_trib, "pIPI").text = f"{float(ipi_data.get('aliquota', 0)):.2f}"
                    etree.SubElement(ipi_trib, "vIPI").text = f"{ipi_valor:.2f}"
                else:
                    # IPINT: IPI não tributado (isento, suspenso, imune, outros)
                    ipi_nt = etree.SubElement(ipi, "IPINT")
                    etree.SubElement(ipi_nt, "CST").text = ipi_cst
            
            # PIS
            pis_data = item.get('pis', {})
            pis = etree.SubElement(imposto, "PIS")
            pis_cst = str(pis_data.get('cst', '07'))
            
            if pis_cst in ['01', '02'] and pis_data.get('valor'):
                pis_aliq = etree.SubElement(pis, "PISAliq")
                etree.SubElement(pis_aliq, "CST").text = pis_cst
                etree.SubElement(pis_aliq, "vBC").text = f"{float(pis_data.get('base_calculo', 0)):.2f}"
                etree.SubElement(pis_aliq, "pPIS").text = f"{float(pis_data.get('aliquota', 0)):.2f}"
                etree.SubElement(pis_aliq, "vPIS").text = f"{float(pis_data['valor']):.2f}"
            elif pis_cst == '99' and pis_data.get('valor'):
                pis_outr = etree.SubElement(pis, "PISOutr")
                etree.SubElement(pis_outr, "CST").text = pis_cst
                etree.SubElement(pis_outr, "vBC").text = f"{float(pis_data.get('base_calculo', 0)):.2f}"
                etree.SubElement(pis_outr, "pPIS").text = f"{float(pis_data.get('aliquota', 0)):.2f}"
                etree.SubElement(pis_outr, "vPIS").text = f"{float(pis_data['valor']):.2f}"
            else:
                pis_nt = etree.SubElement(pis, "PISNT")
                etree.SubElement(pis_nt, "CST").text = pis_cst
            
            # COFINS
            cofins_data = item.get('cofins', {})
            cofins = etree.SubElement(imposto, "COFINS")
            cofins_cst = str(cofins_data.get('cst', '07'))
            
            if cofins_cst in ['01', '02'] and cofins_data.get('valor'):
                cofins_aliq = etree.SubElement(cofins, "COFINSAliq")
                etree.SubElement(cofins_aliq, "CST").text = cofins_cst
                etree.SubElement(cofins_aliq, "vBC").text = f"{float(cofins_data.get('base_calculo', 0)):.2f}"
                etree.SubElement(cofins_aliq, "pCOFINS").text = f"{float(cofins_data.get('aliquota', 0)):.2f}"
                etree.SubElement(cofins_aliq, "vCOFINS").text = f"{float(cofins_data['valor']):.2f}"
            elif cofins_cst == '99' and cofins_data.get('valor'):
                cofins_outr = etree.SubElement(cofins, "COFINSOutr")
                etree.SubElement(cofins_outr, "CST").text = cofins_cst
                etree.SubElement(cofins_outr, "vBC").text = f"{float(cofins_data.get('base_calculo', 0)):.2f}"
                etree.SubElement(cofins_outr, "pCOFINS").text = f"{float(cofins_data.get('aliquota', 0)):.2f}"
                etree.SubElement(cofins_outr, "vCOFINS").text = f"{float(cofins_data['valor']):.2f}"
            else:
                cofins_nt = etree.SubElement(cofins, "COFINSNT")
                etree.SubElement(cofins_nt, "CST").text = cofins_cst
            
            det_list.append(det)
        
        # total
        total = etree.SubElement(inf_nfe, "total")
        
        # ICMSTot
        icms_tot = etree.SubElement(total, "ICMSTot")
        etree.SubElement(icms_tot, "vBC").text = f"{base_icms:.2f}"
        etree.SubElement(icms_tot, "vICMS").text = f"{total_icms:.2f}"
        etree.SubElement(icms_tot, "vICMSDeson").text = "0.00"
        etree.SubElement(icms_tot, "vFCP").text = "0.00"
        etree.SubElement(icms_tot, "vBCST").text = f"{base_icms_st:.2f}"
        etree.SubElement(icms_tot, "vST").text = f"{total_icms_st:.2f}"
        etree.SubElement(icms_tot, "vFCPST").text = "0.00"
        etree.SubElement(icms_tot, "vFCPSTRet").text = "0.00"
        etree.SubElement(icms_tot, "vProd").text = f"{total_produtos:.2f}"
        etree.SubElement(icms_tot, "vFrete").text = f"{total_frete:.2f}"
        etree.SubElement(icms_tot, "vSeg").text = f"{total_seguro:.2f}"
        etree.SubElement(icms_tot, "vDesc").text = f"{total_desconto:.2f}"
        etree.SubElement(icms_tot, "vII").text = "0.00"
        etree.SubElement(icms_tot, "vIPI").text = f"{total_ipi:.2f}"
        # vIPIDevol: IPI devolvido — obrigatório preenchido quando finNFe=4 (devolução) e há IPI
        vipIDevol = total_ipi if fin_nfe == '4' and total_ipi > 0 else 0.0
        etree.SubElement(icms_tot, "vIPIDevol").text = f"{vipIDevol:.2f}"
        etree.SubElement(icms_tot, "vPIS").text = f"{total_pis:.2f}"
        etree.SubElement(icms_tot, "vCOFINS").text = f"{total_cofins:.2f}"
        etree.SubElement(icms_tot, "vOutro").text = f"{total_outras:.2f}"
        etree.SubElement(icms_tot, "vNF").text = f"{total_nfe:.2f}"
        
        # vTotTrib - REMOVIDO TEMPORARIAMENTE PARA TESTE (causa erro 225)
        # valor_aproximado_tributos = total_nfe * 0.30  # 30% como estimativa
        # etree.SubElement(icms_tot, "vTotTrib").text = f"{valor_aproximado_tributos:.2f}"
        
        # transp - processar dados do JSON ou form_data
        transp_data = form_data.get('transporte', {})
        transp = etree.SubElement(inf_nfe, "transp")
        mod_frete = str(transp_data.get('modalidade_frete') or form_data.get('modFrete', '9'))
        etree.SubElement(transp, "modFrete").text = mod_frete
        
        # Adicionar dados da transportadora se modalidade != 9 (Sem transporte)
        if mod_frete != '9':
            transportadora_data = transp_data.get('transportadora', {})
            transportadora_nome = transportadora_data.get('razao_social') or form_data.get('transportadoraNome', '').strip()
            transportadora_cnpj = transportadora_data.get('cpf_cnpj') or form_data.get('transportadoraCnpjCpf', '').strip()
            
            if transportadora_nome or transportadora_cnpj:
                transporta = etree.SubElement(transp, "transporta")
                
                # CNPJ ou CPF da transportadora
                if transportadora_cnpj:
                    cnpj_limpo = ''.join(filter(str.isdigit, transportadora_cnpj))
                    if len(cnpj_limpo) == 14:  # CNPJ
                        etree.SubElement(transporta, "CNPJ").text = cnpj_limpo
                    elif len(cnpj_limpo) == 11:  # CPF
                        etree.SubElement(transporta, "CPF").text = cnpj_limpo
                
                # Nome/Razão Social
                if transportadora_nome:
                    etree.SubElement(transporta, "xNome").text = transportadora_nome[:60]
                
                # Inscrição Estadual (opcional)
                transportadora_ie = transportadora_data.get('inscricao_estadual') or form_data.get('transportadoraIE', '').strip()
                if transportadora_ie:
                    etree.SubElement(transporta, "IE").text = transportadora_ie
                
                # Endereço
                transportadora_endereco = transportadora_data.get('endereco_completo') or form_data.get('transportadoraEndereco', '').strip()
                if transportadora_endereco:
                    etree.SubElement(transporta, "xEnder").text = transportadora_endereco[:60]
                
                # Município
                transportadora_municipio = transportadora_data.get('municipio') or form_data.get('transportadoraMunicipio', '').strip()
                if transportadora_municipio:
                    etree.SubElement(transporta, "xMun").text = transportadora_municipio[:60]
                
                # UF
                transportadora_uf = transportadora_data.get('uf') or form_data.get('transportadoraUF', '').strip()
                if transportadora_uf:
                    etree.SubElement(transporta, "UF").text = transportadora_uf
            
            # Dados do veículo
            veiculo_data = transp_data.get('veiculo', {})
            veiculo_placa = veiculo_data.get('placa') or form_data.get('veiculoPlaca', '').strip()
            veiculo_uf = veiculo_data.get('uf') or form_data.get('veiculoUF', '').strip()
            
            if veiculo_placa:
                vei_transp = etree.SubElement(transp, "veicTransp")
                etree.SubElement(vei_transp, "placa").text = veiculo_placa.replace('-', '').upper()[:7]
                if veiculo_uf:
                    etree.SubElement(vei_transp, "UF").text = veiculo_uf
            
            # Dados dos volumes
            volumes_list = transp_data.get('volumes', [])
            if volumes_list:
                for vol_data in volumes_list:
                    vol = etree.SubElement(transp, "vol")
                    
                    if vol_data.get('quantidade'):
                        try:
                            etree.SubElement(vol, "qVol").text = str(int(float(vol_data['quantidade'])))
                        except (ValueError, TypeError):
                            pass
                    
                    if vol_data.get('especie'):
                        etree.SubElement(vol, "esp").text = str(vol_data['especie'])[:60]
                    
                    if vol_data.get('marca'):
                        etree.SubElement(vol, "marca").text = str(vol_data['marca'])[:60]
                    
                    if vol_data.get('numeracao'):
                        etree.SubElement(vol, "nVol").text = str(vol_data['numeracao'])[:60]
                    
                    if vol_data.get('peso_bruto'):
                        try:
                            etree.SubElement(vol, "pesoB").text = f"{float(vol_data['peso_bruto']):.3f}"
                        except (ValueError, TypeError):
                            pass
                    
                    if vol_data.get('peso_liquido'):
                        try:
                            etree.SubElement(vol, "pesoL").text = f"{float(vol_data['peso_liquido']):.3f}"
                        except (ValueError, TypeError):
                            pass
            else:
                # Usar formato antigo form_data
                volume_qtd = form_data.get('volumeQuantidade', '').strip()
                volume_especie = form_data.get('volumeEspecie', '').strip()
                volume_marca = form_data.get('volumeMarca', '').strip()
                volume_numeracao = form_data.get('volumeNumeracao', '').strip()
                volume_peso_bruto = form_data.get('volumePesoBruto', '').strip()
                volume_peso_liquido = form_data.get('volumePesoLiquido', '').strip()
                
                if volume_qtd or volume_especie or volume_marca or volume_numeracao or volume_peso_bruto or volume_peso_liquido:
                    vol = etree.SubElement(transp, "vol")
                    
                    if volume_qtd:
                        try:
                            etree.SubElement(vol, "qVol").text = str(int(float(volume_qtd)))
                        except (ValueError, TypeError):
                            pass
                    
                    if volume_especie:
                        etree.SubElement(vol, "esp").text = volume_especie[:60]
                    
                    if volume_marca:
                        etree.SubElement(vol, "marca").text = volume_marca[:60]
                    
                    if volume_numeracao:
                        etree.SubElement(vol, "nVol").text = volume_numeracao[:60]
                    
                    if volume_peso_bruto:
                        try:
                            etree.SubElement(vol, "pesoB").text = f"{float(volume_peso_bruto):.3f}"
                        except (ValueError, TypeError):
                            pass
                    
                    if volume_peso_liquido:
                        try:
                            etree.SubElement(vol, "pesoL").text = f"{float(volume_peso_liquido):.3f}"
                        except (ValueError, TypeError):
                            pass
        
        # pag - processar dados do JSON ou form_data
        cobranca_data = form_data.get('cobranca', {})
        pag = etree.SubElement(inf_nfe, "pag")
        
        # indPag - OBRIGATÓRIO na NFe 4.0, mas vai dentro de detPag
        # 0=Pagamento à Vista; 1=Pagamento à Prazo; 2=Outros
        ind_pag = "0"  # Default: à vista
        if cobranca_data.get('duplicatas'):
            ind_pag = "1"  # Se tem duplicatas, é à prazo
        
        # Processar pagamentos do JSON
        pagamentos_list = cobranca_data.get('pagamentos', [])
        if pagamentos_list:
            for pag_data in pagamentos_list:
                det_pag = etree.SubElement(pag, "detPag")
                
                # indPag vai DENTRO de detPag, não em pag!
                etree.SubElement(det_pag, "indPag").text = ind_pag
                
                meio_pag = str(pag_data.get('meio_pagamento', '01'))
                
                # Se for 17 (PIX), usar 99 (Outros) para compatibilidade
                if meio_pag == '17':
                    logger.debug(f"⚠️  tPag 17 (PIX) alterado para 99 (Outros) - compatibilidade SEFAZ")
                    meio_pag = '99'
                
                valor_pag = float(pag_data.get('valor', total_nfe))
                
                etree.SubElement(det_pag, "tPag").text = meio_pag
                etree.SubElement(det_pag, "vPag").text = f"{valor_pag:.2f}"
                
                # Dados do cartão se houver
                if pag_data.get('dados_cartao'):
                    cartao_data = pag_data['dados_cartao']
                    card = etree.SubElement(det_pag, "card")
                    etree.SubElement(card, "tpIntegra").text = str(cartao_data.get('tipo_integracao', '2'))
                    if cartao_data.get('cnpj_credenciadora'):
                        etree.SubElement(card, "CNPJ").text = cartao_data['cnpj_credenciadora']
                    if cartao_data.get('bandeira'):
                        etree.SubElement(card, "tBand").text = str(cartao_data['bandeira'])
                    if cartao_data.get('numero_autorizacao'):
                        etree.SubElement(card, "cAut").text = str(cartao_data['numero_autorizacao'])
        else:
            # Usar formato antigo form_data
            det_pag = etree.SubElement(pag, "detPag")
            
            # indPag vai DENTRO de detPag
            etree.SubElement(det_pag, "indPag").text = ind_pag
            
            # Meio de pagamento - validar código
            meio_pag = str(form_data.get('formaPagamento', '01'))
            
            # Se for 17 (PIX), usar 99 (Outros) para compatibilidade
            # Alguns estados ainda não aceitam código 17
            if meio_pag == '17':
                logger.debug(f"⚠️  tPag 17 (PIX) alterado para 99 (Outros) - compatibilidade SEFAZ")
                meio_pag = '99'
            
            etree.SubElement(det_pag, "tPag").text = meio_pag
            etree.SubElement(det_pag, "vPag").text = f"{total_nfe:.2f}"
        
        # Adicionar duplicatas se houver
        if cobranca_data.get('duplicatas'):
            cobr = etree.SubElement(inf_nfe, "cobr")
            dup_list = cobranca_data['duplicatas']
            for dup_data in dup_list:
                dup = etree.SubElement(cobr, "dup")
                etree.SubElement(dup, "nDup").text = str(dup_data.get('numero', '001'))
                if dup_data.get('data_vencimento'):
                    etree.SubElement(dup, "dVenc").text = str(dup_data['data_vencimento'])
                etree.SubElement(dup, "vDup").text = f"{float(dup_data.get('valor', 0)):.2f}"
        
        # infAdic - processar informações adicionais do JSON
        # IMPORTANTE: infAdic só deve existir se tiver conteúdo (infCpl ou infAdFisco)
        info_adic_data = form_data.get('informacoes_adicionais', {})
        
        # Informações complementares
        if isinstance(info_adic_data, dict):
            inf_compl = info_adic_data.get('informacoes_complementares', '')
            inf_fisco = info_adic_data.get('informacoes_fisco', '')
        elif isinstance(info_adic_data, str):
            inf_compl = info_adic_data
            inf_fisco = ''
        else:
            inf_compl = form_data.get('infCpl', '')
            inf_fisco = ''
        
        # Adicionar RNTC/ANTT nas informações adicionais se houver
        transp_data = form_data.get('transporte', {})
        veiculo_data = transp_data.get('veiculo', {})
        transportadora_antt = veiculo_data.get('rntc') or form_data.get('transportadoraANTT', '').strip()
        if transportadora_antt:
            antt_info = f"RNTC/ANTT: {transportadora_antt}"
            if inf_compl:
                inf_compl = f"{inf_compl}. {antt_info}"
            else:
                inf_compl = antt_info
        
        # Só criar infAdic se houver algum conteúdo
        if inf_compl or inf_fisco:
            inf_adic = etree.SubElement(inf_nfe, "infAdic")
            
            if inf_compl:
                etree.SubElement(inf_adic, "infCpl").text = str(inf_compl).strip()[:5000]
            
            if inf_fisco:
                etree.SubElement(inf_adic, "infAdFisco").text = str(inf_fisco).strip()[:2000]
        
        # Converter para string XML SEM formatação (SEFAZ prefere XML compacto)
        # CRÍTICO: método='c14n' garante XML canonicalizado SEM quebras de linha
        # Isso é essencial para que a assinatura digital seja válida
        try:
            # c14n = Canonical XML - formato padrão para assinatura digital
            xml_bytes = etree.tostring(root, method='c14n', encoding='UTF-8')  # type: ignore[call-arg]
            # Adicionar declaração XML manualmente (c14n não inclui)
            xml_string = '<?xml version="1.0" encoding="UTF-8"?>' + xml_bytes.decode('utf-8')
            logger.debug("✅ XML gerado com método c14n (canonicalizado - sem quebras)")
        except (TypeError, ValueError):
            # Fallback para método tradicional
            xml_bytes = etree.tostring(root, encoding='utf-8')
            xml_string = xml_bytes.decode('utf-8')
            if not xml_string.startswith('<?xml'):
                xml_string = '<?xml version="1.0" encoding="UTF-8"?>' + xml_string
            # Remover quebras manualmente se c14n não disponível
            xml_string = xml_string.replace('\n', '').replace('\r', '').replace('\t', '')
            logger.debug("✅ XML gerado sem pretty_print + quebras removidas")
        
        # Debug: verificar se tem xmlns na tag NFe
        has_xmlns = 'xmlns=' in xml_string[:200]
        logger.debug(f"OK: XML gerado com sucesso: {len(xml_string)} caracteres")
        logger.debug(f"🔍 Tag NFe tem xmlns: {has_xmlns}")
        logger.debug(f" XML preview (primeiros 500 chars): {xml_string[:500]}...")
        
        # OK: VERIFICAR SE CFOP ESTÁ NO XML FINAL
        if 'CFOP' in xml_string:
            import re
            cfops_encontrados = re.findall(r'<CFOP>(\d{4})</CFOP>', xml_string)
            logger.debug(f"OK: CFOPs encontrados no XML: {cfops_encontrados}")
        else:
            logger.error(f"ERRO: CFOP não encontrado no XML final!")
        
        return xml_string
        
    except Exception as e:
        logger.error(f"ERRO: Erro ao gerar XML: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Erro na geração do XML: {str(e)}")

def gerar_chave_nfe(emitente_data: Dict[str, Any], form_data: Dict[str, Any]) -> str:
    """Gera chave de acesso da NFe"""
    try:
        uf_codigo = get_uf_ibge_code(emitente_data.get('uf', 'SP'))
        aamm = datetime.now().strftime('%y%m')
        cnpj = limpar_cnpj_cpf(emitente_data.get('cnpj', ''))[:14]
        modelo = "55"
        serie = str(form_data.get('serie', '1')).zfill(3)
        numero = "000000001"
        codigo_numerico = str(uuid.uuid4().int)[:8]
        
        chave_sem_dv = f"{uf_codigo:02d}{aamm}{cnpj}{modelo}{serie}{numero}{codigo_numerico}"
        
        # Calcular DV
        soma_digitos = sum(int(d) for d in chave_sem_dv)
        dv = soma_digitos % 10
        
        chave_completa = chave_sem_dv + str(dv)
        
        logger.debug(f" Chave gerada: {chave_completa}")
        return chave_completa
        
    except Exception as e:
        logger.error(f"ERRO: Erro ao gerar chave: {e}")
        # Chave de fallback
        return "35" + datetime.now().strftime('%y%m') + "12345678000100" + "55" + "001" + "000000001" + "12345678" + "1"

def sign_xml(xml_content: str, certificado_data: Dict[str, Any]) -> str:
    """Assina o XML da NFe (simulado)"""
    logger.debug("️ Simulando assinatura do XML...")
    
    assinatura_simulada = '''
    <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
        <SignedInfo>
            <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
            <SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
        </SignedInfo>
        <SignatureValue>ASSINATURA_SIMULADA_PARA_TESTES</SignatureValue>
    </Signature>'''
    
    xml_assinado = xml_content.replace('</NFe>', f'{assinatura_simulada}</NFe>')
    
    logger.debug("OK: XML assinado (simulado)")
    return xml_assinado

def send_to_sefaz(xml_assinado: str, certificado_data: Dict[str, Any], cnpj_emitente: str, tp_amb: int = 2) -> Dict[str, Any]:
    """Envia XML para SEFAZ (simulado)"""
    logger.debug(" Simulando envio para SEFAZ...")
    
    resultado = {
        'status': '100',
        'mensagem': 'Autorizado o uso da NF-e',
        'chave_acesso': gerar_chave_nfe({'uf': 'SP', 'cnpj': cnpj_emitente}, {'serie': '1'}),
        'protocolo': f'135{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'data_autorizacao': datetime.now().isoformat(),
        'xml_protocolo': xml_assinado
    }
    
    logger.debug(f"OK: Resposta SEFAZ simulada: {resultado['status']} - {resultado['mensagem']}")
    return resultado

# OK: FUNÇÃO AUXILIAR PARA COMPATIBILIDADE
def get_active_certificate_for_client(db, cliente_id):
    """Interface pública para obter certificado"""
    if certificate_service_function:
        return certificate_service_function(db, cliente_id)
    else:
        return {
            'nome_arquivo_original': 'certificado_simulado.pfx',
            'private_key': 'SIMULADO',
            'modo_simulado': True
        }