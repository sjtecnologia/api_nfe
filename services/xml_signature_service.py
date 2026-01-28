import os
import tempfile
from lxml import etree
from pynfe.processamento.assinatura import Assinatura
from services.certificate_service import get_active_certificate_for_client

class XMLSignatureService:
    """
    Serviço para assinatura digital de XML usando PyNFe
    """
    
    def __init__(self):
        self.namespaces = {
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'nfe': 'http://www.portalfiscal.inf.br/nfe'
        }
    
    def sign_nfe_xml(self, xml_content, db_session, cliente_id):
        """
        Assina XML da NFe usando PyNFe (biblioteca específica para NFe brasileira)
        Após 118 tentativas de assinatura manual, usa biblioteca testada pela comunidade
        """
        try:
            print("[PYNFE] === ASSINATURA COM PYNFE - BIBLIOTECA NFe BRASIL ===")
            print(f"[PYNFE] Cliente ID: {cliente_id}")
            
            # 1. Buscar certificado
            certificado = get_active_certificate_for_client(db_session, cliente_id)
            if not certificado:
                raise Exception("❌ ERRO: Nenhum certificado ativo encontrado")
            
            print(f"[PYNFE] Certificado: ID={certificado.get('certificado_id')}")
            print(f"[PYNFE] Tipo: {certificado.get('tipo_certificado', 'A1')}")
            
            if certificado.get('modo_simulado'):
                raise Exception("❌ ERRO: Certificado em modo simulado")
            
            # 2. Obter dados do certificado
            cert_arquivo = certificado.get('certificado_arquivo')  # Base64 do .pfx
            cert_senha = certificado.get('certificado_senha')      # Senha (criptografada)
            
            if not cert_arquivo or not cert_senha:
                raise Exception("❌ ERRO: Dados do certificado incompletos")
            
            # 3. USAR PYNFE para assinar
            print("[PYNFE] Criando assinador PyNFe...")
            
            # PyNFe espera: arquivo .pfx (base64) e senha
            assinador = Assinatura(cert_arquivo, cert_senha)
            
            print("[PYNFE] Assinando XML com PyNFe...")
            xml_assinado = assinador.assinar(xml_content)
            
            print(f"[PYNFE] ✅ Assinatura criada: {len(xml_assinado)} caracteres")
            
            # DEBUG: Salvar XML para análise
            try:
                with open('/tmp/last_signed_nfe.xml', 'w', encoding='utf-8') as f:
                    f.write(xml_assinado)
                print(f"[PYNFE] XML salvo em /tmp/last_signed_nfe.xml")
            except:
                pass
            
            return xml_assinado
            
        except Exception as e:
            print(f"[PYNFE] ❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Falha na assinatura: {str(e)}")
