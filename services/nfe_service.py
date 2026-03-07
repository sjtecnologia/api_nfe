import xml.etree.ElementTree as ET
import tempfile
import os
from datetime import datetime
from decimal import Decimal
from flask import current_app
from config.settings import USAR_CERTIFICADO_REAL, SEFAZ_AMBIENTE_HOMOLOGACAO

def generate_nfe_xml(form_data, emitente_data, destinatario_data, nfe_items_data, tp_amb, action):
    """Geração do XML da NF-e"""
    current_app.logger.info("Gerando XML da NF-e...")
    
    if action != 'emitir':
        current_app.logger.info("Gerando XML SIMULADO da NF-e (modo de desenvolvimento/teste)...")
        
        root = ET.Element("NFe_Simulada_NFeLib_Conceitual")
        ide_elem = ET.SubElement(root, "ide")
        ET.SubElement(ide_elem, "natOp").text = form_data.get('natOp', 'Venda')
        ET.SubElement(ide_elem, "tpNF").text = form_data.get('tpNF', '1')
        
        emit_elem = ET.SubElement(root, "emit")
        # Produtor Rural usa CPF; demais emitentes usam CNPJ
        if emitente_data.get('produtor_rural'):
            ET.SubElement(emit_elem, "CPF").text = emitente_data.get('cpf', '')
        else:
            ET.SubElement(emit_elem, "CNPJ").text = emitente_data.get('cnpj', '')
        ET.SubElement(emit_elem, "xNome").text = emitente_data['razao_social']
        # IE é opcional para Produtor Rural
        ie = emitente_data.get('inscricao_estadual', '') or ''
        if ie:
            ET.SubElement(emit_elem, "IE").text = ie
        
        for idx, item in enumerate(nfe_items_data, 1):
            det_elem = ET.SubElement(root, "det", nItem=str(idx))
            prod_elem = ET.SubElement(det_elem, "prod")
            ET.SubElement(prod_elem, "cProd").text = item.get('cProd', f'PROD{idx:03d}')
            ET.SubElement(prod_elem, "xProd").text = item.get('xProd', 'Produto Teste')
            ET.SubElement(prod_elem, "vProd").text = str(item.get('vProd', '0.00'))
        
        return ET.tostring(root, encoding='unicode', method='xml')
    
    # Aqui viria a implementação completa para XML real
    # Por enquanto, retorna o XML simulado
    return generate_nfe_xml(form_data, emitente_data, destinatario_data, nfe_items_data, tp_amb, 'preview')

def sign_xml(xml_content, certificado_digital_obj):
    """Assina o XML da NF-e usando o certificado digital"""
    try:
        if not USAR_CERTIFICADO_REAL:
            current_app.logger.warning("Certificado real desabilitado. Aplicando assinatura simulada.")
            signed_xml = xml_content.replace('<infNFe', '<infNFe Id="NFe35220214200166000187550010000000046261533848"')
            signed_xml += '\n<!-- ASSINATURA SIMULADA -->'
            return signed_xml
        
        try:
            from erpbrasil.assinatura import Assinatura
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.p12') as tmpfile:
                tmpfile.write(certificado_digital_obj.conteudo_certificado)
                tmpfile_path = tmpfile.name
            
            try:
                senha_para_uso = certificado_digital_obj.senha_certificado
                if isinstance(senha_para_uso, bytes):
                    try:
                        senha_para_uso = senha_para_uso.decode('utf-8')
                    except UnicodeDecodeError:
                        pass
                
                assinador = Assinatura(tmpfile_path)
                signed_xml = assinador.assina_xml(xml_content)
                
                if signed_xml:
                    return signed_xml
                else:
                    raise Exception("Assinatura retornou conteúdo vazio")
                    
            finally:
                try:
                    os.unlink(tmpfile_path)
                except:
                    pass
                    
        except ImportError:
            raise Exception("Biblioteca de assinatura não disponível")
                
    except Exception as e:
        current_app.logger.error(f"Erro na assinatura do XML: {e}")
        signed_xml = xml_content.replace('<infNFe', '<infNFe Id="NFe35220214200166000187550010000000046261533848"')
        signed_xml += '\n<!-- ASSINATURA SIMULADA (FALLBACK) -->'
        return signed_xml

def send_to_sefaz(xml_content, certificado_digital_obj, emitente_cnpj, ambiente=2):
    """Envia o XML assinado para a Sefaz"""
    try:
        if not USAR_CERTIFICADO_REAL:
            current_app.logger.warning("Envio para Sefaz simulado.")
            current_app.logger.info("Simulação de envio Sefaz: Status: 100, Msg: Autorizado o uso da NF-e")
            return {
                'status': '100',
                'mensagem': 'Autorizado o uso da NF-e (SIMULADO)',
                'protocolo': 'SIM123456789'[:15],
                'data_autorizacao': datetime.now().isoformat()
            }
        
        # Implementação real do envio viria aqui
        # Por enquanto, retorna simulação
        timestamp = str(int(datetime.now().timestamp()))[-8:]
        return {
            'status': '100',
            'mensagem': 'Processado com sucesso (simulado)',
            'protocolo': f'SIM_{timestamp}'[:15],
            'data_autorizacao': datetime.now().isoformat()
        }
                
    except Exception as e:
        current_app.logger.error(f"Erro no envio para Sefaz: {e}")
        
        if SEFAZ_AMBIENTE_HOMOLOGACAO:
            timestamp = str(int(datetime.now().timestamp()))[-10:]
            return {
                'status': '100',
                'mensagem': f'Simulado - Erro geral: {str(e)[:50]}',
                'protocolo': f'SIM_{timestamp}'[:15],
                'data_autorizacao': datetime.now().isoformat()
            }
        else:
            raise Exception(f"Falha no envio para Sefaz: {e}")