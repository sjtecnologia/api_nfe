class XMLSigner:
    """
    Classe para assinatura de XML da NFe.
    Usa XMLSignatureService para assinatura real.
    """
    def assinar_xml(self, xml_content, certificado):
        """Assina XML usando XMLSignatureService"""
        try:
            from services.xml_signature_service import XMLSignatureService
            
            signature_service = XMLSignatureService()
            
            # CORREÇÃO: XMLSignatureService usa sign_nfe_xml(), não assinar_xml()
            # Precisa de db_session e cliente_id
            db_session = certificado.get('db_session')
            cliente_id = certificado.get('cliente_id')
            
            if not db_session or not cliente_id:
                print(f"[XMLSigner] AVISO: db_session ou cliente_id faltando, usando fallback")
                return None
            
            xml_assinado = signature_service.sign_nfe_xml(xml_content, db_session, cliente_id)
            
            return xml_assinado
            
        except Exception as e:
            print(f"[XMLSigner] Erro ao assinar: {e}")
            import traceback
            traceback.print_exc()
            # Retornar None para que o fallback seja usado
            return None