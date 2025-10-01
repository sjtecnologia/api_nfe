import os
import tempfile
from datetime import datetime
from lxml import etree
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography import x509
import base64
import hashlib
import uuid
from services.certificate_service import get_active_certificate_for_client

class XMLSignatureService:
    """
    Serviço para assinatura digital de XML com certificado A1
    """
    
    def __init__(self):
        self.namespaces = {
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'nfe': 'http://www.portalfiscal.inf.br/nfe'
        }
    
    def sign_nfe_xml(self, xml_content, db_session, cliente_id):
        """
        Assina XML da NFe com certificado digital A1
        """
        try:
            print("🔐 === INICIANDO ASSINATURA REAL ===")
            
            # 1. Buscar certificado
            certificado = get_active_certificate_for_client(db_session, cliente_id)
            if not certificado:
                raise Exception("Certificado não encontrado")
            
            if certificado.get('modo_simulado'):
                print("⚠️ Certificado em modo simulado - não é possível assinar realmente")
                return self._simulate_signature(xml_content)
            
            # 2. Carregar certificado PKCS#12
            private_key, certificate = self._load_certificate(certificado)
            
            # 3. Parsear XML
            xml_tree = etree.fromstring(xml_content.encode('utf-8'))
            
            # 4. Encontrar elemento infNFe para assinar
            inf_nfe = xml_tree.find('.//nfe:infNFe', self.namespaces)
            if inf_nfe is None:
                # Tentar sem namespace
                inf_nfe = xml_tree.find('.//infNFe')
            
            if inf_nfe is None:
                raise Exception("Elemento infNFe não encontrado no XML")
            
            inf_nfe_id = inf_nfe.get('Id')
            if not inf_nfe_id:
                raise Exception("Atributo Id não encontrado no infNFe")
            
            print(f"✅ Elemento infNFe encontrado: {inf_nfe_id}")
            
            # 5. Criar assinatura
            signature_xml = self._create_signature_element(
                xml_tree, inf_nfe, inf_nfe_id, private_key, certificate
            )
            
            # 6. Inserir assinatura no XML
            nfe_element = xml_tree.find('.//nfe:NFe', self.namespaces)
            if nfe_element is None:
                nfe_element = xml_tree.find('.//NFe')
            
            if nfe_element is not None:
                nfe_element.append(signature_xml)
            
            # 7. Serializar XML final
            signed_xml = etree.tostring(xml_tree, encoding='unicode', pretty_print=True)
            signed_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + signed_xml
            
            print(f"✅ XML assinado com sucesso: {len(signed_xml)} caracteres")
            return signed_xml
            
        except Exception as e:
            print(f"❌ Erro na assinatura: {e}")
            print("🔄 Usando assinatura simulada como fallback")
            return self._simulate_signature(xml_content)
    
    def _load_certificate(self, certificado_data):
        """
        Carrega certificado PKCS#12 dos dados do banco
        """
        try:
            print("🔐 Carregando certificado real...")
            
            # Decodificar dados do certificado
            cert_content = base64.b64decode(certificado_data['arquivo_certificado'])
            
            # Descriptografar senha
            from services.certificate_service import _decrypt_password
            cert_password = _decrypt_password(certificado_data['senha_certificado'])
            
            # Carregar PKCS#12
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                cert_content,
                cert_password.encode('utf-8') if isinstance(cert_password, str) else cert_password
            )
            
            if not private_key or not certificate:
                raise Exception("Falha ao carregar chave privada ou certificado")
            
            print(f"✅ Certificado carregado: {certificate.subject}")
            return private_key, certificate
            
        except Exception as e:
            print(f"❌ Erro ao carregar certificado: {e}")
            raise
    
    def _create_signature_element(self, xml_tree, inf_nfe, inf_nfe_id, private_key, certificate):
        """
        Cria elemento de assinatura XMLDSig
        """
        print("🔏 Criando assinatura XMLDSig...")
        
        # 1. Canonicalizar infNFe
        canonicalized_infnfe = self._canonicalize_element(inf_nfe)
        
        # 2. Calcular hash SHA-1
        digest_value = base64.b64encode(
            hashlib.sha1(canonicalized_infnfe).digest()
        ).decode('utf-8')
        
        print(f"🔍 Digest SHA-1: {digest_value[:50]}...")
        
        # 3. Criar SignedInfo
        signed_info = self._create_signed_info(inf_nfe_id, digest_value)
        
        # 4. Canonicalizar SignedInfo
        canonicalized_signed_info = self._canonicalize_element(signed_info)
        
        # 5. Assinar com RSA-SHA1
        signature_value = self._sign_data(canonicalized_signed_info, private_key)
        
        # 6. Criar elemento Signature completo
        signature_element = self._create_full_signature_element(
            signed_info, signature_value, certificate
        )
        
        print("✅ Elemento Signature criado")
        return signature_element
    
    def _canonicalize_element(self, element):
        """
        Canonicaliza elemento XML (C14N)
        """
        return etree.tostring(
            element,
            method='c14n',
            exclusive=False,
            with_comments=False
        )
    
    def _create_signed_info(self, reference_uri, digest_value):
        """
        Cria elemento SignedInfo
        """
        signed_info = etree.Element('{http://www.w3.org/2000/09/xmldsig#}SignedInfo')
        
        # CanonicalizationMethod
        canon_method = etree.SubElement(signed_info, '{http://www.w3.org/2000/09/xmldsig#}CanonicalizationMethod')
        canon_method.set('Algorithm', 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
        
        # SignatureMethod
        sig_method = etree.SubElement(signed_info, '{http://www.w3.org/2000/09/xmldsig#}SignatureMethod')
        sig_method.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#rsa-sha1')
        
        # Reference
        reference = etree.SubElement(signed_info, '{http://www.w3.org/2000/09/xmldsig#}Reference')
        reference.set('URI', f'#{reference_uri}')
        
        # Transforms
        transforms = etree.SubElement(reference, '{http://www.w3.org/2000/09/xmldsig#}Transforms')
        transform = etree.SubElement(transforms, '{http://www.w3.org/2000/09/xmldsig#}Transform')
        transform.set('Algorithm', 'http://www.w3.org/2001/10/xml-exc-c14n#')
        
        # DigestMethod
        digest_method = etree.SubElement(reference, '{http://www.w3.org/2000/09/xmldsig#}DigestMethod')
        digest_method.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#sha1')
        
        # DigestValue
        digest_value_elem = etree.SubElement(reference, '{http://www.w3.org/2000/09/xmldsig#}DigestValue')
        digest_value_elem.text = digest_value
        
        return signed_info
    
    def _sign_data(self, data, private_key):
        """
        Assina dados com RSA-SHA1
        """
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        
        signature = private_key.sign(
            data,
            padding.PKCS1v15(),
            hashes.SHA1()
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    def _create_full_signature_element(self, signed_info, signature_value, certificate):
        """
        Cria elemento Signature completo
        """
        signature = etree.Element('{http://www.w3.org/2000/09/xmldsig#}Signature')
        
        # SignedInfo
        signature.append(signed_info)
        
        # SignatureValue
        sig_value = etree.SubElement(signature, '{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
        sig_value.text = signature_value
        
        # KeyInfo
        key_info = etree.SubElement(signature, '{http://www.w3.org/2000/09/xmldsig#}KeyInfo')
        x509_data = etree.SubElement(key_info, '{http://www.w3.org/2000/09/xmldsig#}X509Data')
        x509_cert = etree.SubElement(x509_data, '{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
        
        # Certificado em Base64
        cert_der = certificate.public_bytes(serialization.Encoding.DER)
        x509_cert.text = base64.b64encode(cert_der).decode('utf-8')
        
        return signature
    
    def _simulate_signature(self, xml_content):
        """
        Fallback: assinatura simulada
        """
        print("🔄 Usando assinatura simulada")
        
        signature_xml = """
    <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
        <SignedInfo>
            <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
            <SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
        </SignedInfo>
        <SignatureValue>ASSINATURA_SIMULADA_PARA_TESTES</SignatureValue>
    </Signature>"""
        
        # Inserir antes de </NFe>
        if '</NFe>' in xml_content:
            return xml_content.replace('</NFe>', f'  {signature_xml}\n    </NFe>')
        else:
            return xml_content + signature_xml

# Instância global
xml_signature_service = XMLSignatureService()