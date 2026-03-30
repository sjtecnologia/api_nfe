"""
Serviço para gerenciamento de certificados A3 (tokens/smartcards) via PKCS#11
"""

import os
import sys
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Lista de bibliotecas PKCS#11 comuns por fabricante/SO
PKCS11_LIBRARIES = {
    'Windows': {
        'SafeNet': [
            r'C:\Windows\System32\eTPKCS11.dll',
            r'C:\Windows\SysWOW64\eTPKCS11.dll',
        ],
        'Certisign': [
            r'C:\Windows\System32\aetpkss1.dll',
            r'C:\Windows\SysWOW64\aetpkss1.dll',
        ],
        'Gemalto': [
            r'C:\Windows\System32\gclib.dll',
            r'C:\Windows\SysWOW64\gclib.dll',
        ],
        'Watchdata': [
            r'C:\Windows\System32\watchdata\Watchdata Brazil CSP v1.0\lib\w64pk11.dll',
            r'C:\Windows\SysWOW64\watchdata\Watchdata Brazil CSP v1.0\lib\w32pk11.dll',
        ],
    },
    'Linux': {
        'SafeNet': [
            '/usr/lib/libeTPkcs11.so',
            '/usr/lib/x86_64-linux-gnu/libeTPkcs11.so',
            '/usr/local/lib/libeTPkcs11.so',
        ],
        'Certisign': [
            '/usr/lib/libaetpkss.so',
            '/usr/lib/x86_64-linux-gnu/libaetpkss.so',
        ],
        'Gemalto': [
            '/usr/lib/libgclib.so',
            '/usr/lib/x86_64-linux-gnu/libgclib.so',
        ],
        'OpenSC': [
            '/usr/lib/opensc-pkcs11.so',
            '/usr/lib/x86_64-linux-gnu/opensc-pkcs11.so',
        ],
    },
    'Darwin': {  # macOS
        'SafeNet': [
            '/Library/Frameworks/eToken.framework/Versions/Current/libeTPkcs11.dylib',
            '/usr/local/lib/libeTPkcs11.dylib',
        ],
        'Gemalto': [
            '/usr/local/lib/libgclib.dylib',
        ],
    }
}


class PKCS11Service:
    """Serviço para interação com tokens A3 via PKCS#11"""
    
    def __init__(self):
        self.pkcs11_available = False
        self.pkcs11_module = None
        self._init_pkcs11()
    
    def _init_pkcs11(self):
        """Inicializa módulo PyKCS11"""
        try:
            import PyKCS11
            self.pkcs11_module = PyKCS11
            self.pkcs11_available = True
            print("[OK] PyKCS11 carregado com sucesso")
        except ImportError:
            print("[!] PyKCS11 não instalado - suporte A3 desabilitado")
            print("[!] Instale com: pip install PyKCS11")
            self.pkcs11_available = False
    
    def detect_libraries(self) -> List[Dict[str, Any]]:
        """
        Detecta bibliotecas PKCS#11 disponíveis no sistema
        
        Returns:
            Lista de bibliotecas encontradas com informações
        """
        if not self.pkcs11_available:
            return []
        
        system = sys.platform
        if system.startswith('win'):
            os_key = 'Windows'
        elif system.startswith('linux'):
            os_key = 'Linux'
        elif system.startswith('darwin'):
            os_key = 'Darwin'
        else:
            print(f"[!] Sistema operacional não suportado: {system}")
            return []
        
        found_libraries = []
        libraries_to_check = PKCS11_LIBRARIES.get(os_key, {})
        
        for fabricante, paths in libraries_to_check.items():
            for lib_path in paths:
                if os.path.exists(lib_path):
                    found_libraries.append({
                        'fabricante': fabricante,
                        'path': lib_path,
                        'nome': os.path.basename(lib_path)
                    })
                    print(f"[OK] Biblioteca encontrada: {fabricante} - {lib_path}")
        
        if not found_libraries:
            print(f"[!] Nenhuma biblioteca PKCS#11 encontrada em {os_key}")
        
        return found_libraries
    
    def list_tokens(self, library_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lista tokens conectados
        
        Args:
            library_path: Caminho da biblioteca PKCS#11 (opcional, auto-detecta se None)
        
        Returns:
            Lista de tokens encontrados
        """
        if not self.pkcs11_available:
            print("[X] PyKCS11 não disponível")
            return []
        
        # Auto-detectar biblioteca se não especificada
        if not library_path:
            libraries = self.detect_libraries()
            if not libraries:
                print("[X] Nenhuma biblioteca PKCS#11 encontrada")
                return []
            library_path = libraries[0]['path']
            print(f"[?] Usando biblioteca auto-detectada: {library_path}")
        
        try:
            pkcs11 = self.pkcs11_module.PyKCS11Lib()
            pkcs11.load(library_path)
            
            slots = pkcs11.getSlotList(tokenPresent=True)
            tokens_info = []
            
            for slot_id in slots:
                try:
                    token_info = pkcs11.getTokenInfo(slot_id)
                    slot_info = pkcs11.getSlotInfo(slot_id)
                    
                    tokens_info.append({
                        'slot_id': slot_id,
                        'label': token_info.label.strip(),
                        'manufacturer': token_info.manufacturerID.strip(),
                        'model': token_info.model.strip(),
                        'serial': token_info.serialNumber.strip(),
                        'slot_description': slot_info.slotDescription.strip(),
                        'library_path': library_path
                    })
                    
                    print(f"[OK] Token encontrado: {token_info.label.strip()} (Slot {slot_id})")
                
                except Exception as e:
                    print(f"[!] Erro ao ler slot {slot_id}: {e}")
                    continue
            
            return tokens_info
        
        except Exception as e:
            print(f"[X] Erro ao listar tokens: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def list_certificates_in_token(
        self, 
        library_path: str, 
        slot_id: int, 
        pin: str
    ) -> List[Dict[str, Any]]:
        """
        Lista certificados disponíveis em um token
        
        Args:
            library_path: Caminho da biblioteca PKCS#11
            slot_id: ID do slot do token
            pin: PIN do token
        
        Returns:
            Lista de certificados no token
        """
        if not self.pkcs11_available:
            return []
        
        try:
            pkcs11 = self.pkcs11_module.PyKCS11Lib()
            pkcs11.load(library_path)
            
            session = pkcs11.openSession(slot_id)
            session.login(pin)
            
            # Buscar certificados
            certificates = []
            objects = session.findObjects([(self.pkcs11_module.CKA_CLASS, self.pkcs11_module.CKO_CERTIFICATE)])
            
            for obj in objects:
                try:
                    # Extrair atributos do certificado
                    attrs = session.getAttributeValue(obj, [
                        self.pkcs11_module.CKA_LABEL,
                        self.pkcs11_module.CKA_ID,
                        self.pkcs11_module.CKA_VALUE
                    ])
                    
                    label = attrs[0]
                    cert_id = attrs[1]
                    cert_der = bytes(attrs[2])
                    
                    # Parse certificado X.509
                    from cryptography import x509
                    from cryptography.hazmat.backends import default_backend
                    from cryptography.hazmat.primitives import hashes
                    
                    cert_obj = x509.load_der_x509_certificate(cert_der, default_backend())
                    
                    # Extrair informações
                    subject = cert_obj.subject
                    issuer = cert_obj.issuer
                    
                    # Common Name
                    cn = None
                    for attr in subject:
                        if attr.oid == x509.oid.NameOID.COMMON_NAME:
                            cn = attr.value
                            break
                    
                    # Datas de validade
                    not_before = cert_obj.not_valid_before
                    not_after = cert_obj.not_valid_after
                    
                    # Fingerprint
                    fingerprint = cert_obj.fingerprint(hashes.SHA256()).hex()
                    
                    certificates.append({
                        'label': label,
                        'cert_id': cert_id.hex() if isinstance(cert_id, bytes) else str(cert_id),
                        'common_name': cn,
                        'subject': subject.rfc4514_string(),
                        'issuer': issuer.rfc4514_string(),
                        'not_before': not_before,
                        'not_after': not_after,
                        'fingerprint': fingerprint,
                        'is_valid': datetime.now() < not_after.replace(tzinfo=None),
                        'cert_der': cert_der
                    })
                    
                    print(f"[OK] Certificado encontrado: {cn} (válido até {not_after.date()})")
                
                except Exception as e:
                    print(f"[!] Erro ao processar certificado: {e}")
                    continue
            
            session.logout()
            session.closeSession()
            
            return certificates
        
        except Exception as e:
            print(f"[X] Erro ao listar certificados no token: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def sign_data_with_token(
        self,
        library_path: str,
        slot_id: int,
        pin: str,
        cert_label: str,
        data_to_sign: bytes
    ) -> Optional[bytes]:
        """
        Assina dados usando chave privada no token
        
        Args:
            library_path: Caminho da biblioteca PKCS#11
            slot_id: ID do slot
            pin: PIN do token
            cert_label: Label do certificado a usar
            data_to_sign: Dados a assinar
        
        Returns:
            Assinatura em bytes ou None se falhar
        """
        if not self.pkcs11_available:
            return None
        
        try:
            pkcs11 = self.pkcs11_module.PyKCS11Lib()
            pkcs11.load(library_path)
            
            session = pkcs11.openSession(slot_id)
            session.login(pin)
            
            # Buscar chave privada associada ao certificado
            private_key_objects = session.findObjects([
                (self.pkcs11_module.CKA_CLASS, self.pkcs11_module.CKO_PRIVATE_KEY),
                (self.pkcs11_module.CKA_LABEL, cert_label)
            ])
            
            if not private_key_objects:
                print(f"[X] Chave privada não encontrada para: {cert_label}")
                session.logout()
                session.closeSession()
                return None
            
            private_key = private_key_objects[0]
            
            # Configurar mecanismo de assinatura (RSA com SHA-256)
            mechanism = self.pkcs11_module.Mechanism(self.pkcs11_module.CKM_SHA256_RSA_PKCS, None)
            
            # Assinar
            signature = session.sign(private_key, data_to_sign, mechanism)
            signature_bytes = bytes(signature)
            
            session.logout()
            session.closeSession()
            
            print(f"[OK] Dados assinados com sucesso - {len(signature_bytes)} bytes")
            return signature_bytes
        
        except Exception as e:
            print(f"[X] Erro ao assinar com token: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_certificate_from_token(
        self,
        library_path: str,
        slot_id: int,
        pin: str,
        cert_label: str
    ) -> Optional[bytes]:
        """
        Extrai certificado do token em formato DER
        
        Args:
            library_path: Caminho da biblioteca PKCS#11
            slot_id: ID do slot
            pin: PIN do token
            cert_label: Label do certificado
        
        Returns:
            Certificado em formato DER ou None
        """
        certificates = self.list_certificates_in_token(library_path, slot_id, pin)
        
        for cert in certificates:
            if cert['label'] == cert_label:
                return cert['cert_der']
        
        return None


# Instância singleton
_pkcs11_service = None

def get_pkcs11_service() -> PKCS11Service:
    """Retorna instância singleton do PKCS11Service"""
    global _pkcs11_service
    if _pkcs11_service is None:
        _pkcs11_service = PKCS11Service()
    return _pkcs11_service
