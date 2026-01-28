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
from pynfe.processamento.assinatura import Assinatura
from services.certificate_service import get_active_certificate_for_client

class XMLSignatureService:
    """
    Serviço para assinatura digital de XML com certificados A1 e A3
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
            cert_arquivo = certificado.get('certificado_arquivo')
            cert_senha = certificado.get('certificado_senha')
            
            if not cert_arquivo or not cert_senha:
                raise Exception("❌ ERRO: Dados do certificado incompletos")
            
            # 3. USAR PYNFE para assinar
            # PyNFe espera: arquivo .pfx (base64) e senha
            print("[PYNFE] Criando assinador PyNFe...")
            
            assinador = Assinatura(cert_arquivo, cert_senha)
            
            print("[PYNFE] Assinando XML com PyNFe...")
            xml_assinado = assinador.assinar(xml_content)
            
            print(f"[PYNFE] ✅ Assinatura criada: {len(xml_assinado)} caracteres")
                    nfe_element = xml_tree.find('.//NFe')
                if nfe_element is None:
                    # Última tentativa: buscar qualquer elemento que termine com NFe
                    for elem in xml_tree.iter():
                        if elem.tag.endswith('NFe'):
                            nfe_element = elem
                            break
            
            if nfe_element is None:
                print(f"[ERRO] Estrutura do XML:")
                print(etree.tostring(xml_tree, encoding='unicode', pretty_print=True)[:500])
                raise Exception("Elemento NFe não encontrado no XML")
            
            print(f"[OK] Elemento NFe encontrado: {nfe_element.tag}")
            
            # Encontrar elemento infNFe para assinar (filho direto de NFe)
            inf_nfe = nfe_element.find('{http://www.portalfiscal.inf.br/nfe}infNFe')
            if inf_nfe is None:
                inf_nfe = nfe_element.find('infNFe')
            if inf_nfe is None:
                # Buscar em qualquer nível
                for elem in nfe_element.iter():
                    if elem.tag.endswith('infNFe'):
                        inf_nfe = elem
                        break
            
            if inf_nfe is None:
                raise Exception("Elemento infNFe não encontrado no XML")
            
            inf_nfe_id = inf_nfe.get('Id')
            if not inf_nfe_id:
                raise Exception("Atributo Id não encontrado no infNFe")
            
            print(f"[OK] Elemento infNFe encontrado: {inf_nfe_id}")
            
            # ========================================================================
            # ASSINATURA MANUAL - signxml não permite SHA1 por padrão
            # NFe exige SHA1 conforme padrão da SEFAZ
            # ========================================================================
            
            # 1. Canonicalizar o elemento infNFe usando tostring com method='c14n'
            inf_nfe_c14n = etree.tostring(inf_nfe, method='c14n', exclusive=False, with_comments=False)
            
            print(f"[OK] infNFe canonicalizado: {len(inf_nfe_c14n)} bytes")
            
            # 2. Calcular digest SHA1
            digest_value = base64.b64encode(hashlib.sha1(inf_nfe_c14n).digest()).decode()
            print(f"[OK] Digest calculado: {digest_value[:20]}...")
            
            # 3. Construir Signature com namespace DEFAULT (sem prefixo)
            # CRÍTICO: nsmap={None: DS_NS} cria namespace default: <Signature xmlns="...">
            # NÃO usar nsmap={'ds': DS_NS} ou QName, pois criam prefixo: <ds:Signature> ou <ns0:Signature>
            DS_NS = "http://www.w3.org/2000/09/xmldsig#"
            
            # Criar Signature com namespace DEFAULT (sem prefixo)
            sig_elem = etree.Element(f"{{{DS_NS}}}Signature", nsmap={None: DS_NS})
            
            # Criar elementos filhos (herdam namespace do pai)
            signed_info = etree.SubElement(sig_elem, f"{{{DS_NS}}}SignedInfo")
            
            canon_method = etree.SubElement(signed_info, f"{{{DS_NS}}}CanonicalizationMethod")
            canon_method.set("Algorithm", "http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
            
            sig_method = etree.SubElement(signed_info, f"{{{DS_NS}}}SignatureMethod")
            sig_method.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#rsa-sha1")
            
            reference = etree.SubElement(signed_info, f"{{{DS_NS}}}Reference")
            reference.set("URI", f"#{inf_nfe_id}")
            
            transforms = etree.SubElement(reference, f"{{{DS_NS}}}Transforms")
            
            transform1 = etree.SubElement(transforms, f"{{{DS_NS}}}Transform")
            transform1.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#enveloped-signature")
            
            transform2 = etree.SubElement(transforms, f"{{{DS_NS}}}Transform")
            transform2.set("Algorithm", "http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
            
            digest_method = etree.SubElement(reference, f"{{{DS_NS}}}DigestMethod")
            digest_method.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#sha1")
            
            digest_value_elem = etree.SubElement(reference, f"{{{DS_NS}}}DigestValue")
            digest_value_elem.text = digest_value
            
            # 4. Inserir Signature no XML ANTES de canonicalizar SignedInfo
            # CRÍTICO: SignedInfo deve ser canonicalizado COM o contexto do documento NFe
            nfe_element.append(sig_elem)
            
            # 5. AGORA canonicalizar o SignedInfo DO XML COMPLETO (com contexto NFe)
            signed_info_elem = sig_elem[0]  # Pega SignedInfo filho de Signature
            signed_info_c14n = etree.tostring(signed_info_elem, method='c14n', exclusive=False, with_comments=False)
            print(f"[DEBUG] SignedInfo canonicalizado COM contexto NFe: {len(signed_info_c14n)} bytes")
            print(f"[DEBUG] SignedInfo C14N (primeiros 400 chars): {signed_info_c14n[:400]}")
            print(f"[DEBUG] SignedInfo C14N (últimos 100 chars): {signed_info_c14n[-100:]}")
            
            # 6. Assinar o SignedInfo canonicalizado
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            
            signature = private_key.sign(
                signed_info_c14n,
                padding.PKCS1v15(),
                hashes.SHA1()
            )
            signature_value = base64.b64encode(signature).decode()
            print(f"[OK] Assinatura gerada: {len(signature_value)} caracteres")
            
            # 7. Remover Signature temporariamente para adicionar SignatureValue e KeyInfo
            nfe_element.remove(sig_elem)
            
            # 8. Adicionar SignatureValue e KeyInfo
            sig_value_elem = etree.SubElement(sig_elem, f"{{{DS_NS}}}SignatureValue")
            sig_value_elem.text = signature_value
            
            # 9. Obter certificado X509 em base64
            cert_der = certificate.public_bytes(serialization.Encoding.DER)
            cert_base64 = base64.b64encode(cert_der).decode()
            
            key_info_elem = etree.SubElement(sig_elem, f"{{{DS_NS}}}KeyInfo")
            x509_data_elem = etree.SubElement(key_info_elem, f"{{{DS_NS}}}X509Data")
            
            # IMPORTANTE: Schema XSD da NFe permite apenas UM certificado em X509Data
            x509_cert_elem = etree.SubElement(x509_data_elem, f"{{{DS_NS}}}X509Certificate")
            x509_cert_elem.text = cert_base64
            print(f"[OK] Certificado do usuário incluído no XML")
            
            # Log da cadeia para debug (não incluída no XML)
            if additional_certificates:
                print(f"[INFO] Cadeia disponível no PKCS#12: {len(additional_certificates)} certificado(s) adicional(is)")
                for i, add_cert in enumerate(additional_certificates, 1):
                    print(f"  - Certificado {i}: {add_cert.subject.rfc4514_string()[:80]}")
            
            # 10. Reinserir Signature completa no documento NFe
            nfe_element.append(sig_elem)
            
            # 9. Serializar XML completo COM assinatura
            signed_xml = etree.tostring(xml_tree, encoding='unicode', xml_declaration=False)
            signed_xml = '<?xml version="1.0" encoding="UTF-8"?>' + signed_xml
            
            # DEBUG: Salvar XML em arquivo para análise
            try:
                with open('/tmp/last_signed_nfe.xml', 'w', encoding='utf-8') as f:
                    f.write(signed_xml)
                print(f"[DEBUG] XML salvo em /tmp/last_signed_nfe.xml para análise")
            except:
                pass
            
            print(f"[OK] XML assinado com sucesso manualmente: {len(signed_xml)} caracteres (compacto)")
            return signed_xml
            
        except Exception as e:
            # NÃO USA FALLBACK SIMULADO - PROPAGA O ERRO
            print(f"[X] ERRO CRÍTICO na assinatura: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Falha na assinatura digital: {str(e)}")
    
    def _load_certificate(self, certificado_data):
        """
        Carrega certificado PKCS#12 dos dados do banco
        """
        try:
            print("[AUTH] Carregando certificado real...")
            
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
            
            # Contar certificados na cadeia
            num_additional = len(additional_certificates) if additional_certificates else 0
            print(f"[OK] Certificado carregado: {certificate.subject}")
            print(f"[OK] Cadeia de certificação: {num_additional} certificado(s) adicional(is)")
            
            return private_key, certificate, additional_certificates
            
        except Exception as e:
            print(f"[X] Erro ao carregar certificado: {e}")
            raise
    
    def _create_signature_element(self, xml_tree, inf_nfe, inf_nfe_id, private_key, certificate):
        """
        Cria elemento de assinatura XMLDSig
        """
        print("[?] Criando assinatura XMLDSig...")
        
        # 1. Canonicalizar infNFe com Exclusive C14N
        canonicalized_infnfe = self._canonicalize_element_exclusive(inf_nfe)
        
        # 2. Calcular hash SHA-1
        digest_value = base64.b64encode(
            hashlib.sha1(canonicalized_infnfe).digest()
        ).decode('utf-8')
        
        print(f"[SEARCH] Digest SHA-1: {digest_value[:50]}...")
        
        # 3. Criar SignedInfo
        signed_info = self._create_signed_info(inf_nfe_id, digest_value)
        
        # 4. Canonicalizar SignedInfo com C14N normal (conforme CanonicalizationMethod)
        canonicalized_signed_info = self._canonicalize_element_normal(signed_info)
        
        # 5. Assinar com RSA-SHA1
        signature_value = self._sign_data(canonicalized_signed_info, private_key)
        
        # 6. Criar elemento Signature completo
        signature_element = self._create_full_signature_element(
            signed_info, signature_value, certificate
        )
        
        print("[OK] Elemento Signature criado")
        return signature_element
    
    def _canonicalize_element_exclusive(self, element):
        """
        Canonicaliza elemento XML com Exclusive C14N
        Usado para: infNFe (conforme Transform Algorithm)
        """
        return etree.tostring(
            element,
            method='c14n',
            exclusive=True,
            with_comments=False
        )
    
    def _canonicalize_element_normal(self, element):
        """
        Canonicaliza elemento XML com C14N normal
        Usado para: SignedInfo (conforme CanonicalizationMethod)
        """
        return etree.tostring(
            element,
            method='c14n',
            exclusive=False,
            with_comments=False
        )
    
    def _create_signed_info(self, reference_uri, digest_value):
        """
        Cria elemento SignedInfo com namespace padrão (sem prefixo)
        """
        DSIG_NS = 'http://www.w3.org/2000/09/xmldsig#'
        nsmap = {None: DSIG_NS}
        
        signed_info = etree.Element('SignedInfo', nsmap=nsmap)
        
        # CanonicalizationMethod
        canon_method = etree.SubElement(signed_info, 'CanonicalizationMethod')
        canon_method.set('Algorithm', 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
        
        # SignatureMethod
        sig_method = etree.SubElement(signed_info, 'SignatureMethod')
        sig_method.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#rsa-sha1')
        
        # Reference
        reference = etree.SubElement(signed_info, 'Reference')
        reference.set('URI', f'#{reference_uri}')
        
        # Transforms
        transforms = etree.SubElement(reference, 'Transforms')
        transform = etree.SubElement(transforms, 'Transform')
        transform.set('Algorithm', 'http://www.w3.org/2001/10/xml-exc-c14n#')
        
        # DigestMethod
        digest_method = etree.SubElement(reference, 'DigestMethod')
        digest_method.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#sha1')
        
        # DigestValue
        digest_value_elem = etree.SubElement(reference, 'DigestValue')
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
        Cria elemento Signature completo com namespace padrão (sem prefixo)
        """
        # Criar o elemento Signature com namespace padrão
        DSIG_NS = 'http://www.w3.org/2000/09/xmldsig#'
        nsmap = {None: DSIG_NS}  # None = namespace padrão (sem prefixo)
        
        signature = etree.Element('Signature', nsmap=nsmap)
        
        # SignedInfo - copiar do signed_info já criado
        # Precisamos remover o namespace prefix dele também
        signed_info_copy = self._remove_namespace_prefix(signed_info, DSIG_NS)
        signature.append(signed_info_copy)
        
        # SignatureValue
        sig_value = etree.SubElement(signature, 'SignatureValue')
        sig_value.text = signature_value
        
        # KeyInfo
        key_info = etree.SubElement(signature, 'KeyInfo')
        x509_data = etree.SubElement(key_info, 'X509Data')
        x509_cert = etree.SubElement(x509_data, 'X509Certificate')
        
        # Certificado em Base64
        cert_der = certificate.public_bytes(serialization.Encoding.DER)
        x509_cert.text = base64.b64encode(cert_der).decode('utf-8')
        
        return signature
    
    def _remove_namespace_prefix(self, element, namespace):
        """
        Remove prefixo de namespace de um elemento e seus filhos,
        mantendo o namespace como padrão
        """
        nsmap = {None: namespace}
        
        # Criar novo elemento sem prefixo
        new_elem = etree.Element(etree.QName(element).localname, nsmap=nsmap)
        
        # Copiar atributos
        for key, value in element.attrib.items():
            new_elem.set(etree.QName(key).localname, value)
        
        # Copiar texto
        if element.text:
            new_elem.text = element.text
        if element.tail:
            new_elem.tail = element.tail
        
        # Copiar filhos recursivamente
        for child in element:
            new_child = self._remove_namespace_prefix(child, namespace)
            new_elem.append(new_child)
        
        return new_elem
        return signature
    
    def _sign_with_a3_token(self, xml_content, certificado):
        """
        Assina XML usando certificado A3 (token/smartcard)
        
        Args:
            xml_content: Conteúdo XML a assinar
            certificado: Dict com informações do certificado A3
        
        Returns:
            XML assinado
        """
        try:
            from services.pkcs11_service import get_pkcs11_service
            from services.certificate_service import _decrypt_password
            
            print("[A3] Iniciando assinatura com token A3")
            
            # Extrair informações do token
            library_path = certificado.get('pkcs11_library')
            slot_id = certificado.get('token_slot_id')
            cert_label = certificado.get('token_label')
            encrypted_pin = certificado.get('senha_certificado')
            
            if not all([library_path, slot_id is not None, cert_label, encrypted_pin]):
                raise Exception("Informações do token A3 incompletas")
            
            # Descriptografar PIN
            pin = _decrypt_password(encrypted_pin)
            
            # Parsear XML
            xml_tree = etree.fromstring(xml_content.encode('utf-8'))
            
            # Encontrar elemento infNFe
            inf_nfe = xml_tree.find('.//nfe:infNFe', self.namespaces)
            if inf_nfe is None:
                inf_nfe = xml_tree.find('.//infNFe')
            
            if inf_nfe is None:
                raise Exception("Elemento infNFe não encontrado")
            
            inf_nfe_id = inf_nfe.get('Id')
            print(f"[A3] Assinando elemento: {inf_nfe_id}")
            
            # Canonicalizar infNFe
            canonicalized_infnfe = self._canonicalize_element(inf_nfe)
            
            # Calcular hash SHA-1 do conteúdo canonicalizado
            digest_value = base64.b64encode(
                hashlib.sha1(canonicalized_infnfe.encode('utf-8')).digest()
            ).decode('utf-8')
            
            # Criar SignedInfo
            signed_info_template = f"""<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#">
    <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
    <SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
    <Reference URI="#{inf_nfe_id}">
        <Transforms>
            <Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
            <Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
        </Transforms>
        <DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
        <DigestValue>{digest_value}</DigestValue>
    </Reference>
</SignedInfo>"""
            
            # Canonicalizar SignedInfo
            signed_info_element = etree.fromstring(signed_info_template)
            canonicalized_signed_info = self._canonicalize_element(signed_info_element)
            
            # Assinar com token
            pkcs11 = get_pkcs11_service()
            signature_bytes = pkcs11.sign_data_with_token(
                library_path,
                slot_id,
                pin,
                cert_label,
                canonicalized_signed_info.encode('utf-8')
            )
            
            if not signature_bytes:
                raise Exception("Falha ao assinar com token A3")
            
            signature_value = base64.b64encode(signature_bytes).decode('utf-8')
            
            # Obter certificado do token
            cert_der = pkcs11.get_certificate_from_token(library_path, slot_id, pin, cert_label)
            if not cert_der:
                raise Exception("Falha ao obter certificado do token")
            
            cert_base64 = base64.b64encode(cert_der).decode('utf-8')
            
            # Montar elemento Signature
            signature_xml = etree.fromstring(f"""<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
    {signed_info_template.replace('<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#">', '<SignedInfo>')}
    <SignatureValue>{signature_value}</SignatureValue>
    <KeyInfo>
        <X509Data>
            <X509Certificate>{cert_base64}</X509Certificate>
        </X509Data>
    </KeyInfo>
</Signature>""")
            
            # Inserir assinatura no XML
            nfe_element = xml_tree.find('.//nfe:NFe', self.namespaces)
            if nfe_element is None:
                nfe_element = xml_tree.find('.//NFe')
            
            if nfe_element is not None:
                nfe_element.append(signature_xml)
            
            # Serializar XML final (SEM pretty_print para manter compacto)
            signed_xml = etree.tostring(xml_tree, encoding='unicode', pretty_print=False)
            signed_xml = '<?xml version="1.0" encoding="UTF-8"?>' + signed_xml
            
            print(f"[OK] XML assinado com token A3: {len(signed_xml)} caracteres (compacto)")
            return signed_xml
        
        except Exception as e:
            print(f"[X] Erro ao assinar com token A3: {e}")
            import traceback
            traceback.print_exc()
            raise

# Instância global
xml_signature_service = XMLSignatureService()