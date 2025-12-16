import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import os

class SefazService:
    """Serviço para comunicação com SEFAZ real"""
    
    # URLs SEFAZ-SP Homologação
    URLS_HOMOLOGACAO = {
        'autorizacao': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx',
        'consulta': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx',
        'status_servico': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx'
    }
    
    # URLs SEFAZ-SP Produção 
    URLS_PRODUCAO = {
        'autorizacao': 'https://nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx',
        'consulta': 'https://nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx',
        'status_servico': 'https://nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx'
    }
    
    def __init__(self, ambiente='homologacao'):
        self.ambiente = ambiente
        self.urls = self.URLS_HOMOLOGACAO if ambiente == 'homologacao' else self.URLS_PRODUCAO
        print(f"[?] SefazService inicializado - Ambiente: {ambiente}")
    
    def enviar_nfe(self, xml_assinado, chave_acesso):
        """
        Envia NFe para autorização na SEFAZ
        """
        try:
            print(f"[OUT] === ENVIANDO NFE REAL PARA SEFAZ ===")
            print(f"[?] Ambiente: {self.ambiente}")
            print(f"[KEY] Chave: {chave_acesso}")
            print(f"[?] XML: {len(xml_assinado)} caracteres")
            
            # Criar envelope SOAP
            envelope_soap = self._criar_envelope_autorizacao(xml_assinado, chave_acesso)
            
            # Headers para requisição
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote'
            }
            
            print(f"[?] Enviando para: {self.urls['autorizacao']}")
            
            # Fazer requisição
            response = requests.post(
                self.urls['autorizacao'],
                data=envelope_soap,
                headers=headers,
                timeout=30,
                verify=True  # Verificar certificados SSL
            )
            
            print(f"[?] Status HTTP: {response.status_code}")
            print(f"[?] Resposta recebida: {len(response.text)} chars")
            
            if response.status_code == 200:
                return self._processar_resposta_autorizacao(response.text, chave_acesso)
            else:
                print(f"[X] Erro HTTP: {response.status_code}")
                print(f"[X] Resposta: {response.text[:500]}...")
                return {
                    'status': 'ERRO_HTTP',
                    'codigo': response.status_code,
                    'mensagem': f'Erro HTTP {response.status_code}',
                    'resposta_completa': response.text
                }
                
        except Exception as e:
            print(f"[X] Erro ao enviar NFe: {e}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'ERRO_ENVIO',
                'mensagem': f'Erro na comunicação: {e}'
            }
    
    def _criar_envelope_autorizacao(self, xml_nfe, chave_acesso):
        """Cria envelope SOAP para autorização"""
        
        # Gerar número do lote (timestamp)
        numero_lote = datetime.now().strftime("%Y%m%d%H%M%S")
        
        envelope = f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Header>
    <nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4">
      <cUF>35</cUF>
      <versaoDados>4.00</versaoDados>
    </nfeCabecMsg>
  </soap12:Header>
  <soap12:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4">
      <enviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
        <idLote>{numero_lote}</idLote>
        <indSinc>1</indSinc>
        {xml_nfe}
      </enviNFe>
    </nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>'''
        
        print(f"[?] Envelope SOAP criado - Lote: {numero_lote}")
        return envelope
    
    def _processar_resposta_autorizacao(self, resposta_xml, chave_acesso):
        """Processa resposta da SEFAZ"""
        try:
            print(f"[SEARCH] Processando resposta da SEFAZ...")
            
            # Parse do XML de resposta
            root = ET.fromstring(resposta_xml)
            
            # Buscar elementos de retorno
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            # Buscar código de status
            cstat_element = root.find('.//nfe:cStat', ns)
            xmotivo_element = root.find('.//nfe:xMotivo', ns)
            protocolo_element = root.find('.//nfe:nProt', ns)
            
            if cstat_element is not None:
                codigo_status = cstat_element.text
                motivo = xmotivo_element.text if xmotivo_element is not None else 'Sem motivo'
                protocolo = protocolo_element.text if protocolo_element is not None else None
                
                print(f"[LIST] Status SEFAZ: {codigo_status} - {motivo}")
                
                # Status de sucesso: 100 = Autorizado
                if codigo_status == '100':
                    return {
                        'status': 'AUTORIZADA',
                        'codigo': codigo_status,
                        'mensagem': motivo,
                        'protocolo': protocolo,
                        'chave_acesso': chave_acesso,
                        'data_autorizacao': datetime.now().isoformat(),
                        'resposta_completa': resposta_xml
                    }
                else:
                    return {
                        'status': 'REJEITADA',
                        'codigo': codigo_status,
                        'mensagem': motivo,
                        'protocolo': protocolo,
                        'chave_acesso': chave_acesso,
                        'resposta_completa': resposta_xml
                    }
            else:
                print(f"[X] Não foi possível extrair status da resposta")
                return {
                    'status': 'ERRO_RESPOSTA',
                    'mensagem': 'Resposta da SEFAZ inválida',
                    'resposta_completa': resposta_xml
                }
                
        except Exception as e:
            print(f"[X] Erro ao processar resposta: {e}")
            return {
                'status': 'ERRO_PROCESSAMENTO',
                'mensagem': f'Erro ao processar resposta: {e}',
                'resposta_completa': resposta_xml
            }
    
    def consultar_status_servico(self):
        """Consulta status do serviço SEFAZ"""
        try:
            print(f"[SEARCH] Consultando status do serviço SEFAZ...")
            
            envelope = f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Header>
    <nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeStatusServico4">
      <cUF>35</cUF>
      <versaoDados>4.00</versaoDados>
    </nfeCabecMsg>
  </soap12:Header>
  <soap12:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeStatusServico4">
      <consStatServ xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
        <tpAmb>2</tpAmb>
        <cUF>35</cUF>
        <xServ>STATUS</xServ>
      </consStatServ>
    </nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>'''
            
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'http://www.portalfiscal.inf.br/nfe/wsdl/NFeStatusServico4/nfeStatusServicoNF'
            }
            
            response = requests.post(
                self.urls['status_servico'],
                data=envelope,
                headers=headers,
                timeout=30,
                verify=True
            )
            
            if response.status_code == 200:
                # Parse básico da resposta
                if 'Serviço em Operação' in response.text or '107' in response.text:
                    print(f"[OK] Serviço SEFAZ operacional")
                    return {'status': 'OK', 'mensagem': 'Serviço em operação'}
                else:
                    print(f"[!] Serviço SEFAZ com problemas")
                    return {'status': 'PROBLEMA', 'mensagem': 'Serviço indisponível'}
            else:
                print(f"[X] Erro ao consultar status: {response.status_code}")
                return {'status': 'ERRO', 'mensagem': f'HTTP {response.status_code}'}
                
        except Exception as e:
            print(f"[X] Erro na consulta de status: {e}")
            return {'status': 'ERRO', 'mensagem': str(e)}