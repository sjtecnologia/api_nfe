from datetime import datetime, timezone
import uuid
from utils.helpers import get_uf_ibge_code, limpar_cnpj_cpf
from decimal import Decimal
import re
import json
from flask import current_app
from typing import Optional, Dict, Any, Union, Callable
import os

# ✅ IMPORTAÇÕES XML TOTALMENTE CORRIGIDAS
XML_PARSER = None
etree = None
ET = None

try:
    import lxml.etree as lxml_etree
    import xml.etree.ElementTree as xml_ET
    XML_PARSER = 'lxml'
    etree = lxml_etree
    ET = xml_ET
    print("✅ lxml carregado com sucesso")
except ImportError:
    try:
        import xml.etree.ElementTree as xml_etree
        XML_PARSER = 'etree'
        etree = xml_etree
        ET = xml_etree
        print("⚠️ lxml não disponível, usando xml.etree.ElementTree")
    except ImportError:
        print("❌ Nenhum parser XML disponível!")
        raise ImportError("Instale lxml com: pip install lxml")

# ✅ IMPORTAÇÃO CONDICIONAL PARA NFELIB
NFELIB_DISPONIVEL = False
NfeProc = None
try:
    from nfelib.nfe.bindings.v4_0.proc_nfe_v4_00 import NfeProc
    NFELIB_DISPONIVEL = True
    print("✅ nfelib carregado com sucesso")
except ImportError:
    print("⚠️ nfelib não disponível - funcionalidades avançadas limitadas")

# ✅ IMPORTAÇÃO CONDICIONAL PARA SEFAZ
SEFAZ_DISPONIVEL = False
SefazService = None
try:
    from services.sefaz_service import SefazService
    SEFAZ_DISPONIVEL = True
    print("✅ SefazService carregado com sucesso")
except ImportError:
    print("⚠️ SefazService não disponível - usando apenas simulação")

# ✅ FUNÇÃO PARA CARREGAR NFE PARA EDIÇÃO - ADICIONADA
def carregar_nfe_para_edicao(nfe_id: int, db_session=None) -> Dict[str, Any]:
    """
    Carrega NFe existente para edição
    """
    try:
        print(f"📖 Carregando NFe {nfe_id} para edição...")
        
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
        
        # ✅ CONVERSÃO SEGURA PARA DICIONÁRIO
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
            print(f"❌ Erro na conversão do resultado: {e}")
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
        
        print(f"✅ NFe {nfe_id} carregada: {nfe_data.get('status', 'N/A')}")
        
        # ✅ PROCESSAR JSON_NFE COM SEGURANÇA
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
                    print(f"⚠️ json_nfe em formato inesperado: {type(json_nfe)}")
                    json_data = {}
                
                form_data = json_data.get('form_data', {})
                items_data = json_data.get('items', [])
                
            except (json.JSONDecodeError, TypeError) as e:
                print(f"⚠️ Erro ao decodificar JSON: {e}")
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
                    # ✅ CONVERSÃO SEGURA PARA CLIENTE
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
                        print(f"⚠️ Erro na conversão cliente: {e}")
                        # Fallback manual
                        cliente_data = {
                            'cliente_id': cliente_result[0] if len(cliente_result) > 0 else None,
                            'razao_social': cliente_result[1] if len(cliente_result) > 1 else '',
                            'cnpj_cpf': cliente_result[2] if len(cliente_result) > 2 else '',
                        }
                        
            except Exception as e:
                print(f"⚠️ Erro ao buscar cliente: {e}")
        
        return {
            'success': True,
            'nfe_data': nfe_data,
            'form_data': form_data,
            'items_data': items_data,
            'cliente_data': cliente_data
        }
        
    except Exception as e:
        print(f"❌ Erro ao carregar NFe: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': f'Erro ao carregar NFe: {str(e)}'}

# ✅ FUNÇÃO DE CONEXÃO DE BANCO COM FALLBACKS SEGUROS
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
        
        print("⚠️ Nenhuma conexão de banco disponível")
        return None
        
    except Exception as e:
        print(f"⚠️ Erro ao conectar com banco: {e}")
        return None

# ✅ DEFINIÇÃO DE TIPOS E INTERFACES
CertificateFunction = Optional[Callable[[Optional[Any], int], Dict[str, Any]]]

# ✅ CLASSE BASE PARA XML SIGNER
class BaseXMLSigner:
    """Classe base para assinatura de XML"""
    def assinar_xml(self, xml_content: str, certificado: Dict[str, Any]) -> str:
        """Interface padrão para assinatura"""
        return self._sign_xml_fallback(xml_content, certificado)
    
    def _sign_xml_fallback(self, xml_content: str, certificado: Dict[str, Any]) -> str:
        """Fallback para assinatura simulada"""
        print("✍️ Usando assinatura simulada...")
        
        assinatura_simulada = '''
    <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
        <SignedInfo>
            <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
            <SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
        </SignedInfo>
        <SignatureValue>ASSINATURA_SIMULADA_PARA_TESTES</SignatureValue>
    </Signature>'''
        
        xml_assinado = xml_content.replace('</NFe>', f'{assinatura_simulada}</NFe>')
        print("✅ XML assinado (simulado)")
        return xml_assinado

# ✅ IMPORTAÇÕES DE SERVIÇOS COM FALLBACKS
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
                    print(f"⚠️ Erro ao inicializar XMLSigner externo: {e}")
                    self._external_signer = None
            
            def assinar_xml(self, xml_content: str, certificado: Dict[str, Any]) -> str:
                if self._external_signer:
                    try:
                        return self._external_signer.assinar_xml(xml_content, certificado)
                    except Exception as e:
                        print(f"⚠️ Erro na assinatura externa, usando fallback: {e}")
                        return self._sign_xml_fallback(xml_content, certificado)
                else:
                    return self._sign_xml_fallback(xml_content, certificado)
        
        xml_signer_instance = XMLSignerWrapper()
        
    except ImportError:
        print("⚠️ XMLSigner externo não disponível, usando fallback")
        xml_signer_instance = BaseXMLSigner()
    
    SERVICES_DISPONIVEL = True
    print("✅ Serviços locais carregados com sucesso")
    
except ImportError as e:
    print(f"⚠️ Serviços locais não disponíveis: {e}")
    
    # ✅ FALLBACK PARA CERTIFICADO
    def fallback_certificate_function(db, cliente_id):
        """Fallback para certificado simulado"""
        return {
            'nome_arquivo_original': 'certificado_simulado.pfx',
            'private_key': 'SIMULADO',
            'modo_simulado': True
        }
    
    certificate_service_function = fallback_certificate_function
    xml_signer_instance = BaseXMLSigner()

# ✅ CLASSE PRINCIPAL DO SERVIÇO
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
            print(f"🚀 === PROCESSAMENTO NFE ===")
            print(f"🎯 Cliente ID: {cliente_id}")
            print(f"📝 NFe ID: {nfe_id if nfe_id else 'Nova NFe'}")
            
            # Garantir conexão de banco
            if not self.db:
                self.db = get_db_connection()
            
            if not self.db:
                return {'success': False, 'message': 'Conexão de banco não disponível'}
            
            # Import text function for SQLAlchemy
            from sqlalchemy import text
            
            # Buscar dados do emitente e destinatário
            # Buscar emitente (empresa)
            emitente_query = text("""
                SELECT razao_social, nome_fantasia, cnpj, inscricao_estadual,
                       logradouro, numero, bairro, cep, nome_municipio, 
                       codigo_municipio, uf
                FROM empresas 
                WHERE ativo = true 
                LIMIT 1
            """)
            emitente_result = self.db.execute(emitente_query).fetchone()
            
            if not emitente_result:
                return {'success': False, 'message': 'Dados do emitente não encontrados'}
            
            # ✅ CONVERSÃO SEGURA PARA EMITENTE
            try:
                if hasattr(emitente_result, '_asdict'):
                    emitente_data = emitente_result._asdict()
                elif hasattr(emitente_result, '_mapping'):
                    emitente_data = dict(emitente_result._mapping)
                else:
                    emitente_cols = ['razao_social', 'nome_fantasia', 'cnpj', 'inscricao_estadual',
                                   'logradouro', 'numero', 'bairro', 'cep', 'nome_municipio', 
                                   'codigo_municipio', 'uf']
                    emitente_data = {col: emitente_result[i] for i, col in enumerate(emitente_cols)}
            except Exception as e:
                print(f"⚠️ Erro conversão emitente: {e}")
                emitente_data = {'razao_social': 'EMPRESA TESTE', 'cnpj': '12345678000100', 'uf': 'SP'}
            
            # Buscar destinatário
            destinatario_query = text("""
                SELECT razao_social as nome_razao_social, cnpj_cpf as cpf_cnpj,
                       logradouro, numero, bairro, cep, nome_municipio,
                       codigo_municipio, uf
                FROM clientes 
                WHERE cliente_id = :cliente_id
            """)
            destinatario_result = self.db.execute(destinatario_query, {'cliente_id': cliente_id}).fetchone()
            
            if not destinatario_result:
                return {'success': False, 'message': 'Cliente não encontrado'}
            
            # ✅ CONVERSÃO SEGURA PARA DESTINATÁRIO
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
                print(f"⚠️ Erro conversão destinatário: {e}")
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
            print(f"❌ Erro no processamento NFe: {e}")
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
                # Atualizar com sucesso
                update_query = text("""
                    UPDATE nfe_emitidas 
                    SET status = 'AUTORIZADA',
                        chave_acesso = :chave_acesso,
                        protocolo_sefaz = :protocolo,
                        data_autorizacao = :data_autorizacao,
                        mensagem_sefaz = :mensagem,
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
                    'json_nfe': json.dumps(json_nfe)
                })
                self.db.commit()
                
                return {
                    'success': True,
                    'message': 'NFe atualizada e autorizada com sucesso!',
                    'nfe_id': nfe_id,
                    'chave_acesso': resultado.get('chave_acesso'),
                    'protocolo': resultado.get('protocolo')
                }
            else:
                # Atualizar com erro
                update_query = text("""
                    UPDATE nfe_emitidas 
                    SET status = 'REJEITADA',
                        mensagem_sefaz = :mensagem
                    WHERE nfe_emitida_id = :nfe_id
                """)
                
                self.db.execute(update_query, {
                    'nfe_id': nfe_id,
                    'mensagem': resultado.get('message', 'Erro na SEFAZ')
                })
                self.db.commit()
                
                return {
                    'success': False,
                    'message': resultado.get('message', 'Erro na SEFAZ'),
                    'nfe_id': nfe_id
                }
                
        except Exception as e:
            print(f"❌ Erro ao atualizar NFe: {e}")
            return {'success': False, 'message': f'Erro ao atualizar: {str(e)}'}
    
    def _criar_nova_nfe(self, resultado: Dict[str, Any], dados_nfe: Dict[str, Any], itens: list, cliente_id: int, emitente_data: Dict[str, Any], destinatario_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria nova NFe no banco"""
        try:
            if not self.db:
                return {'success': False, 'message': 'Conexão de banco não disponível'}
                
            from sqlalchemy import text
            
            # Calcular valores
            valor_total = sum(float(item.get('valor_total', 0)) for item in itens)
            
            # Inserir nova NFe
            insert_query = text("""
                INSERT INTO nfe_emitidas (
                    cliente_id, numero_nfe, serie, chave_acesso, protocolo_sefaz,
                    data_emissao, data_autorizacao, status, valor_total,
                    natureza_operacao, tipo_nfe, finalidade_emissao,
                    destinatario_razao_social, destinatario_cnpj_cpf,
                    informacoes_adicionais, mensagem_sefaz, json_nfe
                ) VALUES (
                    :cliente_id, :numero_nfe, :serie, :chave_acesso, :protocolo_sefaz,
                    :data_emissao, :data_autorizacao, :status, :valor_total,
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
            
            json_nfe = {
                'form_data': dados_nfe,
                'items': itens,
                'ambiente': resultado.get('ambiente', 'homologacao'),
                'xml_content': resultado.get('xml_final')
            }
            
            nfe_result = self.db.execute(insert_query, {
                'cliente_id': cliente_id,
                'numero_nfe': 1,  # Seria incrementado em produção
                'serie': dados_nfe.get('serie', '1'),
                'chave_acesso': resultado.get('chave_acesso'),
                'protocolo_sefaz': resultado.get('protocolo'),
                'data_emissao': dt,
                'data_autorizacao': datetime.now() if resultado['success'] else None,
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
            print(f"❌ Erro ao criar NFe: {e}")
            return {'success': False, 'message': f'Erro ao salvar: {str(e)}'}
    
    def processar_emissao_completa(self, dados_form: Dict[str, Any], emitente_data: Dict[str, Any], destinatario_data: Dict[str, Any], items_data: list, cliente_id: int, ambiente: str = 'homologacao') -> Dict[str, Any]:
        """
        Processamento completo: Gera XML -> Assina -> Envia SEFAZ -> Salva
        """
        try:
            print(f"🚀 === PROCESSAMENTO COMPLETO NFE ===")
            print(f"🎯 Cliente ID: {cliente_id}")
            print(f"🌍 Ambiente: {ambiente}")
            
            # 1. GERAR XML
            tp_amb = 2 if ambiente == 'homologacao' else 1
            xml_nfe = generate_nfe_xml(dados_form, emitente_data, destinatario_data, items_data, tp_amb)
            
            if not xml_nfe:
                return {'success': False, 'errors': ['Falha na geração do XML']}
            
            print(f"✅ XML gerado: {len(xml_nfe)} caracteres")
            
            # 2. BUSCAR CERTIFICADO
            certificado = certificate_service_function(self.db, cliente_id) if certificate_service_function else None
            if not certificado:
                return {'success': False, 'errors': ['Certificado não encontrado']}
            
            print(f"✅ Certificado encontrado: {certificado.get('nome_arquivo_original', 'N/A')}")
            
            # 3. ASSINAR XML
            xml_assinado = self._assinar_xml_real(xml_nfe, certificado)
            if not xml_assinado:
                return {'success': False, 'errors': ['Falha na assinatura']}
            
            print(f"✅ XML assinado: {len(xml_assinado)} caracteres")
            
            # 4. ENVIAR PARA SEFAZ
            resultado_sefaz = self._processar_envio_sefaz(xml_assinado, certificado, ambiente)
            
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
            print(f"❌ Erro no processamento completo: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'errors': [f'Erro interno: {str(e)}']}
    
    def _assinar_xml_real(self, xml_content: str, certificado: Dict[str, Any]) -> Optional[str]:
        """Assina XML com certificado real ou simulado"""
        try:
            print("✍️ === ASSINANDO XML ===")
            
            if self.xml_signer:
                return self.xml_signer.assinar_xml(xml_content, certificado)
            else:
                print("🔄 === USANDO ASSINATURA SIMULADA DIRETA ===")
                return sign_xml(xml_content, certificado)
                
        except Exception as e:
            print(f"❌ Erro na assinatura: {e}")
            return None
    
    def _processar_envio_sefaz(self, xml_assinado: str, certificado: Dict[str, Any], ambiente: str) -> Dict[str, Any]:
        """Processa envio para SEFAZ real ou simulado"""
        try:
            print(f"📤 === PROCESSANDO ENVIO SEFAZ ===")
            
            # Extrair chave de acesso
            chave_acesso = self._extrair_chave_acesso(xml_assinado)
            if not chave_acesso:
                return {'success': False, 'message': 'Chave de acesso não encontrada'}
            
            # Decidir se usa SEFAZ real
            usar_sefaz_real = self._deve_usar_sefaz_real(certificado, ambiente)
            
            if usar_sefaz_real and SEFAZ_DISPONIVEL:
                print("🌐 === ENVIANDO PARA SEFAZ REAL ===")
                return self._enviar_sefaz_real(xml_assinado, chave_acesso, ambiente)
            else:
                print("🔄 === USANDO SIMULAÇÃO SEFAZ ===")
                return self._enviar_sefaz_simulado(xml_assinado, chave_acesso, ambiente)
                
        except Exception as e:
            print(f"❌ Erro no envio SEFAZ: {e}")
            return {'success': False, 'message': f'Erro no envio: {str(e)}'}
    
    def _deve_usar_sefaz_real(self, certificado: Dict[str, Any], ambiente: str) -> bool:
        """Determina se deve usar SEFAZ real"""
        
        # Verificar se SefazService está disponível
        if not SEFAZ_DISPONIVEL or SefazService is None:
            print("🔄 SefazService não disponível")
            return False
        
        # Verificar configuração global
        try:
            force_simulation = current_app.config.get('FORCE_SEFAZ_SIMULATION', False)
            if force_simulation:
                print("🔄 Simulação forçada por configuração")
                return False
        except:
            print("🔄 current_app não disponível, usando simulação")
            return False
        
        # Verificar se certificado é real
        if certificado.get('modo_simulado', True):
            print("🔄 Certificado em modo simulado")
            return False
        
        if not certificado.get('private_key') or certificado.get('private_key') == 'SIMULADO':
            print("🔄 Chave privada não disponível")
            return False
        
        print("✅ Condições OK para SEFAZ real")
        return True
    
    def _enviar_sefaz_real(self, xml_assinado: str, chave_acesso: str, ambiente: str) -> Dict[str, Any]:
        """Envia para SEFAZ real"""
        try:
            print(f"🌐 Conectando com SEFAZ real - Ambiente: {ambiente}")
            
            # Verificar se SefazService está disponível
            if not SEFAZ_DISPONIVEL or SefazService is None:
                print("❌ SefazService não está disponível")
                return self._enviar_sefaz_simulado(xml_assinado, chave_acesso, ambiente,
                                                 motivo="SefazService não disponível")
            
            # Inicializar serviço SEFAZ com tratamento de erro
            try:
                sefaz = SefazService(ambiente=ambiente)
            except Exception as e:
                print(f"❌ Erro ao inicializar SefazService: {e}")
                return self._enviar_sefaz_simulado(xml_assinado, chave_acesso, ambiente,
                                                 motivo="Erro na inicialização do SefazService")
            
            # Verificar status do serviço
            status_servico = sefaz.consultar_status_servico()
            if status_servico.get('status') != 'OK':
                print(f"⚠️ SEFAZ indisponível: {status_servico.get('mensagem')}")
                return self._enviar_sefaz_simulado(xml_assinado, chave_acesso, ambiente, 
                                                 motivo="SEFAZ indisponível")
            
            print("✅ SEFAZ operacional, enviando NFe...")
            
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
                return {
                    'success': False,
                    'status': resultado.get('status', 'ERRO'),
                    'message': resultado.get('mensagem', 'Erro desconhecido'),
                    'ambiente_real': True
                }
                
        except Exception as e:
            print(f"❌ Erro SEFAZ real: {e}")
            # Fallback para simulação
            return self._enviar_sefaz_simulado(xml_assinado, chave_acesso, ambiente,
                                             motivo=f"Erro: {str(e)}")
    
    def _enviar_sefaz_simulado(self, xml_assinado: str, chave_acesso: str, ambiente: str, motivo: Optional[str] = None) -> Dict[str, Any]:
        """Envia para SEFAZ simulado"""
        try:
            if motivo:
                print(f"🔄 Simulação SEFAZ - Motivo: {motivo}")
            else:
                print("🔄 Usando simulação SEFAZ")
            
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
            print(f"❌ Erro na simulação: {e}")
            return {'success': False, 'message': f'Erro na simulação: {str(e)}'}
        
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
                            print(f"✅ Chave extraída via nfelib: {chave}")
                            return chave
                        
                except Exception as e:
                    print(f"⚠️ Falha ao extrair com nfelib: {str(e)}")
                    # Continuar com os métodos regex
                    
            # Método regex caso o nfelib falhe
            # Método 1: buscar NFe seguido por 44 dígitos
            match = re.search(r'NFe(\d{44})', xml_content)
            if match:
                chave = match.group(1)
                print(f"✅ Chave extraída via regex: {chave}")
                return chave
            
            # Método 2: procurar pelo Id em qualquer formato
            match = re.search(r'Id=[\'"]\s*NFe(\d{44})\s*[\'"]', xml_content)
            if match:
                chave = match.group(1)
                print(f"✅ Chave extraída via regex alternativo: {chave}")
                return chave
                
            # Método 3: remover espaços e tentar novamente
            xml_sem_espacos = re.sub(r'\s', '', xml_content)
            match = re.search(r'NFe(\d{44})', xml_sem_espacos)
            if match:
                chave = match.group(1)
                print(f"✅ Chave extraída via regex sem espaços: {chave}")
                return chave
                    
            # Se nenhum método funcionou
            print("❌ Chave de acesso não encontrada no XML!")
            print(f"🔍 Primeiros 200 caracteres: {xml_content[:200]}")
            
            return None
        except Exception as e:
            print(f"❌ Erro ao extrair chave: {e}")
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
            
            if nfe_element is not None:
                nfe_xml = ET.tostring(nfe_element, encoding='unicode')
            else:
                nfe_xml = xml_assinado
            
            xml_protocolo = f'''<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
{nfe_xml}
  <protNFe versao="4.00">
    <infProt>
      <tpAmb>2</tpAmb>
      <verAplic>SP_NFE_PL_008i2</verAplic>
      <chNFe>{resultado.get('chave_acesso', '')}</chNFe>
      <dhRecbto>{resultado.get('data_autorizacao', datetime.now().isoformat())}</dhRecbto>
      <nProt>{resultado.get('protocolo', '')}</nProt>
      <digVal>SIMULADO</digVal>
      <cStat>{resultado.get('status', '100')}</cStat>
      <xMotivo>{resultado.get('mensagem', 'Autorizado o uso da NF-e')}</xMotivo>
    </infProt>
  </protNFe>
</nfeProc>'''
            
            return xml_protocolo
            
        except Exception as e:
            print(f"❌ Erro ao gerar protocolo: {e}")
            return xml_assinado

# ✅ FUNÇÕES AUXILIARES CORRIGIDAS
def generate_nfe_xml(form_data: Dict[str, Any], emitente_data: Dict[str, Any], 
                    destinatario_data: Dict[str, Any], items: list, 
                    tp_amb: int = 2, finalidade: str = 'emitir') -> str:
    """
    Gerar XML da NFe com validações e formatação adequada
    """
    try:
        print(f"🔧 === GERANDO XML NFE ===")
        print(f"📋 Form data: {form_data}")
        print(f"📦 Items: {len(items)} itens")
        
        # ✅ CORREÇÃO: Verificar e processar CFOP nos itens
        for i, item in enumerate(items, 1):
            cfop_original = item.get('cfop', '')
            print(f"📦 Item {i} - CFOP original: '{cfop_original}' (tipo: {type(cfop_original)})")
            
            # ✅ CORREÇÃO: Garantir que CFOP seja string e tenha 4 dígitos
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
                    print(f"✅ Item {i} - CFOP corrigido: '{cfop_str}'")
                else:
                    print(f"⚠️ Item {i} - CFOP inválido: '{cfop_original}' -> usando padrão '5102'")
                    item['cfop'] = '5102'  # CFOP padrão para venda
            else:
                print(f"⚠️ Item {i} - CFOP vazio -> usando padrão '5102'")
                item['cfop'] = '5102'
        
        # Importar bibliotecas necessárias (corrigido para fallback caso lxml não esteja instalado)
        try:
            import lxml.etree as etree
        except ImportError:
            import xml.etree.ElementTree as etree
        from datetime import datetime, timezone
        import uuid
        
        # ✅ PROCESSAR DADOS BÁSICOS DA NFE
        serie = form_data.get('serie', '1')
        numero_nfe = 1  # Será determinado pelo banco
        tp_nf = form_data.get('tpNF', '1')  # 1=Saída
        fin_nfe = form_data.get('finNFe', '1')  # 1=Normal
        nat_op = form_data.get('natOp', 'Venda de Mercadorias')
        
        # Data de emissão
        data_emissao_str = form_data.get('dataEmissao')
        if data_emissao_str:
            try:
                data_emissao = datetime.fromisoformat(data_emissao_str.replace('Z', '+00:00'))
            except:
                data_emissao = datetime.now(timezone.utc)
        else:
            data_emissao = datetime.now(timezone.utc)
        
        # Formatação da data para o XML
        dh_emi = data_emissao.strftime('%Y-%m-%dT%H:%M:%S%z')
        if not dh_emi.endswith(('Z', '+00:00', '-03:00')):
            dh_emi = data_emissao.strftime('%Y-%m-%dT%H:%M:%S-03:00')
        
        print(f"📅 Data emissão: {dh_emi}")
        
        # ✅ GERAR CHAVE DE ACESSO
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
        
        print(f"🔑 Chave de acesso: {chave_acesso}")
        
        # ✅ PROCESSAR CNPJ/CPF DO DESTINATÁRIO
        dest_cpf_cnpj = destinatario_data.get('cpf_cnpj', '').replace('.', '').replace('/', '').replace('-', '')
        
        # Determinar se é CPF ou CNPJ
        if len(dest_cpf_cnpj) == 11:
            dest_tag = 'CPF'
        elif len(dest_cpf_cnpj) == 14:
            dest_tag = 'CNPJ'
        else:
            raise ValueError(f"CPF/CNPJ do destinatário inválido: {dest_cpf_cnpj}")
        
        # ✅ CALCULAR TOTAIS DA NFE
        total_produtos = 0
        total_icms = 0
        total_ipi = 0
        total_pis = 0
        total_cofins = 0
        
        for item in items:
            try:
                valor_total_item = float(item.get('valor_total', 0))
                valor_icms_item = float(item.get('valor_icms', 0))
                
                total_produtos += valor_total_item
                total_icms += valor_icms_item
                
                print(f"📦 Item: {item.get('descricao', 'N/A')[:30]} - Valor: R$ {valor_total_item:.2f} - CFOP: {item.get('cfop', 'N/A')}")
            except (ValueError, TypeError) as e:
                print(f"⚠️ Erro ao processar valores do item: {e}")
                continue
        
        total_nfe = total_produtos
        
        print(f"💰 Totais - Produtos: R$ {total_produtos:.2f}, ICMS: R$ {total_icms:.2f}, NFe: R$ {total_nfe:.2f}")
        
        # ✅ CRIAR ESTRUTURA XML
        nsmap = {
            None: "http://www.portalfiscal.inf.br/nfe"
        }
        
        # Uso unificado sem nsmap para evitar erro de tipagem quando lxml não está disponível
        namespace = nsmap[None]
        root = etree.Element("NFe")
        root.set("xmlns", namespace)
        
        # infNFe
        inf_nfe = etree.SubElement(root, "infNFe")
        inf_nfe.set("Id", f"NFe{chave_acesso}")
        inf_nfe.set("versao", "4.00")
        
        # ide
        ide = etree.SubElement(inf_nfe, "ide")
        etree.SubElement(ide, "cUF").text = str(uf_code)
        etree.SubElement(ide, "cNF").text = codigo_numerico
        etree.SubElement(ide, "natOp").text = nat_op
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
        etree.SubElement(ide, "indPres").text = "9"  # 9=Operação não presencial
        
        # emit
        emit = etree.SubElement(inf_nfe, "emit")
        etree.SubElement(emit, "CNPJ").text = cnpj_emit
        etree.SubElement(emit, "xNome").text = emitente_data.get('razao_social', '')
        if emitente_data.get('nome_fantasia'):
            etree.SubElement(emit, "xFant").text = emitente_data['nome_fantasia']
        
        # Endereço do emitente
        ender_emit = etree.SubElement(emit, "enderEmit")
        etree.SubElement(ender_emit, "xLgr").text = emitente_data.get('logradouro', '')
        etree.SubElement(ender_emit, "nro").text = str(emitente_data.get('numero', ''))
        etree.SubElement(ender_emit, "xBairro").text = emitente_data.get('bairro', '')
        etree.SubElement(ender_emit, "cMun").text = str(emitente_data.get('codigo_municipio', '3550308'))
        etree.SubElement(ender_emit, "xMun").text = emitente_data.get('nome_municipio', 'São Paulo')
        etree.SubElement(ender_emit, "UF").text = emitente_data.get('uf', 'SP')
        
        cep_emit = emitente_data.get('cep', '').replace('-', '')
        etree.SubElement(ender_emit, "CEP").text = cep_emit
        etree.SubElement(ender_emit, "cPais").text = "1058"
        etree.SubElement(ender_emit, "xPais").text = "Brasil"
        
        etree.SubElement(emit, "IE").text = emitente_data.get('inscricao_estadual', '')
        etree.SubElement(emit, "CNAE").text = "6201500"  # Desenvolvimento de programas de computador sob encomenda
        etree.SubElement(emit, "CRT").text = "3"  # 3=Regime Normal
        
        # dest
        dest = etree.SubElement(inf_nfe, "dest")
        etree.SubElement(dest, dest_tag).text = dest_cpf_cnpj
        etree.SubElement(dest, "xNome").text = destinatario_data.get('nome_razao_social', '')
        
        # Endereço do destinatário
        ender_dest = etree.SubElement(dest, "enderDest")
        etree.SubElement(ender_dest, "xLgr").text = destinatario_data.get('logradouro', '')
        etree.SubElement(ender_dest, "nro").text = str(destinatario_data.get('numero', ''))
        etree.SubElement(ender_dest, "xBairro").text = destinatario_data.get('bairro', '')
        etree.SubElement(ender_dest, "cMun").text = str(destinatario_data.get('codigo_municipio', '3550308'))
        etree.SubElement(ender_dest, "xMun").text = destinatario_data.get('nome_municipio', 'São Paulo')
        etree.SubElement(ender_dest, "UF").text = destinatario_data.get('uf', 'SP')
        
        cep_dest = destinatario_data.get('cep', '').replace('-', '')
        etree.SubElement(ender_dest, "CEP").text = cep_dest
        etree.SubElement(ender_dest, "cPais").text = "1058"
        etree.SubElement(ender_dest, "xPais").text = "Brasil"
        
        etree.SubElement(dest, "indIEDest").text = "9"  # 9=Não contribuinte
        
        # ✅ ITENS DA NFE COM CFOP CORRETO
        det_list = []
        for i, item in enumerate(items, 1):
            det = etree.SubElement(inf_nfe, "det")
            det.set("nItem", str(i))
            
            # prod
            prod = etree.SubElement(det, "prod")
            etree.SubElement(prod, "cProd").text = str(item.get('codigo_produto', f'PROD{i:03d}'))
            etree.SubElement(prod, "cEAN").text = "SEM GTIN"
            etree.SubElement(prod, "xProd").text = str(item.get('descricao', f'Produto {i}'))
            etree.SubElement(prod, "NCM").text = str(item.get('ncm', '99999999'))
            
            # ✅ CFOP CORRIGIDO - garantir que está presente e correto
            cfop_item = item.get('cfop', '5102')
            print(f"📦 Item {i} - CFOP final no XML: '{cfop_item}'")
            etree.SubElement(prod, "CFOP").text = str(cfop_item)
            
            etree.SubElement(prod, "uCom").text = str(item.get('unidade', 'UN'))
            
            # Quantidades e valores
            quantidade = float(item.get('quantidade', 1))
            valor_unitario = float(item.get('valor_unitario', 0))
            valor_total = float(item.get('valor_total', 0))
            
            etree.SubElement(prod, "qCom").text = f"{quantidade:.2f}"
            etree.SubElement(prod, "vUnCom").text = f"{valor_unitario:.2f}"
            etree.SubElement(prod, "vProd").text = f"{valor_total:.2f}"
            etree.SubElement(prod, "cEANTrib").text = "SEM GTIN"
            etree.SubElement(prod, "uTrib").text = str(item.get('unidade', 'UN'))
            etree.SubElement(prod, "qTrib").text = f"{quantidade:.2f}"
            etree.SubElement(prod, "vUnTrib").text = f"{valor_unitario:.2f}"
            etree.SubElement(prod, "indTot").text = "1"  # 1=Valor do item compõe valor total da NF-e
            
            # imposto
            imposto = etree.SubElement(det, "imposto")
            
            # ICMS
            icms = etree.SubElement(imposto, "ICMS")
            cst_icms = item.get('cst_icms', '00')
            
            if cst_icms in ['00', '10', '20']:
                icms_tributado = etree.SubElement(icms, f"ICMS{cst_icms}")
                etree.SubElement(icms_tributado, "orig").text = str(item.get('origem', '0'))
                etree.SubElement(icms_tributado, "CST").text = cst_icms
                
                if cst_icms == '00':  # Tributada integralmente
                    bc_icms = float(item.get('bc_icms', valor_total))
                    aliq_icms = float(item.get('aliquota_icms', 18))
                    valor_icms = float(item.get('valor_icms', bc_icms * aliq_icms / 100))
                    
                    etree.SubElement(icms_tributado, "modBC").text = "0"  # 0=Margem Valor Agregado (%)
                    etree.SubElement(icms_tributado, "vBC").text = f"{bc_icms:.2f}"
                    etree.SubElement(icms_tributado, "pICMS").text = f"{aliq_icms:.2f}"
                    etree.SubElement(icms_tributado, "vICMS").text = f"{valor_icms:.2f}"
            else:
                # CST não tributado
                icms_nt = etree.SubElement(icms, "ICMS40")
                etree.SubElement(icms_nt, "orig").text = str(item.get('origem', '0'))
                etree.SubElement(icms_nt, "CST").text = "40"  # Isenta
            
            # PIS
            pis = etree.SubElement(imposto, "PIS")
            pis_nt = etree.SubElement(pis, "PISNT")
            etree.SubElement(pis_nt, "CST").text = "07"  # Operação isenta da contribuição
            
            # COFINS
            cofins = etree.SubElement(imposto, "COFINS")
            cofins_nt = etree.SubElement(cofins, "COFINSNT")
            etree.SubElement(cofins_nt, "CST").text = "07"  # Operação isenta da contribuição
            
            det_list.append(det)
        
        # total
        total = etree.SubElement(inf_nfe, "total")
        
        # ICMSTot
        icms_tot = etree.SubElement(total, "ICMSTot")
        etree.SubElement(icms_tot, "vBC").text = f"{total_produtos:.2f}"
        etree.SubElement(icms_tot, "vICMS").text = f"{total_icms:.2f}"
        etree.SubElement(icms_tot, "vICMSDeson").text = "0.00"
        etree.SubElement(icms_tot, "vFCP").text = "0.00"
        etree.SubElement(icms_tot, "vBCST").text = "0.00"
        etree.SubElement(icms_tot, "vST").text = "0.00"
        etree.SubElement(icms_tot, "vFCPST").text = "0.00"
        etree.SubElement(icms_tot, "vFCPSTRet").text = "0.00"
        etree.SubElement(icms_tot, "vProd").text = f"{total_produtos:.2f}"
        etree.SubElement(icms_tot, "vFrete").text = "0.00"
        etree.SubElement(icms_tot, "vSeg").text = "0.00"
        etree.SubElement(icms_tot, "vDesc").text = "0.00"
        etree.SubElement(icms_tot, "vII").text = "0.00"
        etree.SubElement(icms_tot, "vIPI").text = f"{total_ipi:.2f}"
        etree.SubElement(icms_tot, "vIPIDevol").text = "0.00"
        etree.SubElement(icms_tot, "vPIS").text = f"{total_pis:.2f}"
        etree.SubElement(icms_tot, "vCOFINS").text = f"{total_cofins:.2f}"
        etree.SubElement(icms_tot, "vOutro").text = "0.00"
        etree.SubElement(icms_tot, "vNF").text = f"{total_nfe:.2f}"
        
        # transp
        transp = etree.SubElement(inf_nfe, "transp")
        etree.SubElement(transp, "modFrete").text = str(form_data.get('modFrete', '9'))  # 9=Sem Ocorrência de Transporte
        
        # pag
        pag = etree.SubElement(inf_nfe, "pag")
        det_pag = etree.SubElement(pag, "detPag")
        etree.SubElement(det_pag, "tPag").text = str(form_data.get('formaPagamento', '01'))  # 01=Dinheiro
        etree.SubElement(det_pag, "vPag").text = f"{total_nfe:.2f}"
        
        # infAdic
        inf_adic = etree.SubElement(inf_nfe, "infAdic")
        inf_compl = form_data.get('infCpl', '')
        if inf_compl:
            etree.SubElement(inf_adic, "infCpl").text = str(inf_compl)
        
        # Converter para string XML (compatível com lxml ou xml.etree)
        try:
            # lxml suporta pretty_print e xml_declaration
            xml_bytes = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')  # type: ignore[arg-type]
        except TypeError:
            # xml.etree.ElementTree não suporta pretty_print/xml_declaration
            xml_bytes_no_decl = etree.tostring(root, encoding='utf-8')
            if not xml_bytes_no_decl.startswith(b'<?xml'):
                xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes_no_decl
            else:
                xml_bytes = xml_bytes_no_decl
        xml_string = xml_bytes.decode('utf-8')
        
        print(f"✅ XML gerado com sucesso: {len(xml_string)} caracteres")
        print(f"🔍 XML preview (primeiros 500 chars): {xml_string[:500]}...")
        
        # ✅ VERIFICAR SE CFOP ESTÁ NO XML FINAL
        if 'CFOP' in xml_string:
            import re
            cfops_encontrados = re.findall(r'<CFOP>(\d{4})</CFOP>', xml_string)
            print(f"✅ CFOPs encontrados no XML: {cfops_encontrados}")
        else:
            print(f"❌ CFOP não encontrado no XML final!")
        
        return xml_string
        
    except Exception as e:
        print(f"❌ Erro ao gerar XML: {e}")
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
        
        print(f"🔑 Chave gerada: {chave_completa}")
        return chave_completa
        
    except Exception as e:
        print(f"❌ Erro ao gerar chave: {e}")
        # Chave de fallback
        return "35" + datetime.now().strftime('%y%m') + "12345678000100" + "55" + "001" + "000000001" + "12345678" + "1"

def sign_xml(xml_content: str, certificado_data: Dict[str, Any]) -> str:
    """Assina o XML da NFe (simulado)"""
    print("✍️ Simulando assinatura do XML...")
    
    assinatura_simulada = '''
    <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
        <SignedInfo>
            <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
            <SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
        </SignedInfo>
        <SignatureValue>ASSINATURA_SIMULADA_PARA_TESTES</SignatureValue>
    </Signature>'''
    
    xml_assinado = xml_content.replace('</NFe>', f'{assinatura_simulada}</NFe>')
    
    print("✅ XML assinado (simulado)")
    return xml_assinado

def send_to_sefaz(xml_assinado: str, certificado_data: Dict[str, Any], cnpj_emitente: str, tp_amb: int = 2) -> Dict[str, Any]:
    """Envia XML para SEFAZ (simulado)"""
    print("📤 Simulando envio para SEFAZ...")
    
    resultado = {
        'status': '100',
        'mensagem': 'Autorizado o uso da NF-e',
        'chave_acesso': gerar_chave_nfe({'uf': 'SP', 'cnpj': cnpj_emitente}, {'serie': '1'}),
        'protocolo': f'135{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'data_autorizacao': datetime.now().isoformat(),
        'xml_protocolo': xml_assinado
    }
    
    print(f"✅ Resposta SEFAZ simulada: {resultado['status']} - {resultado['mensagem']}")
    return resultado

# ✅ FUNÇÃO AUXILIAR PARA COMPATIBILIDADE
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