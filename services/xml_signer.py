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
            xml_assinado = signature_service.assinar_xml(xml_content, certificado)
            
            return xml_assinado
            
        except Exception as e:
            print(f"[XMLSigner] Erro ao assinar: {e}")
            import traceback
            traceback.print_exc()
            # Retornar None para que o fallback seja usado
            return None