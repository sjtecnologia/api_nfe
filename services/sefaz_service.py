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
    
    def __init__(self, ambiente='homologacao', cert_path=None, key_path=None):
        self.ambiente = ambiente
        self.urls = self.URLS_HOMOLOGACAO if ambiente == 'homologacao' else self.URLS_PRODUCAO
        self.cert_path = cert_path
        self.key_path = key_path
        
        # Usar bundle de certificados que inclui ICP-Brasil
        # Caminho absoluto para o bundle customizado no servidor
        self.ca_bundle = '/home/ubuntu/api_nfe/ca-bundle-icpbrasil.pem'
        if not os.path.exists(self.ca_bundle):
            # Fallback para certificados do sistema se bundle não existir
            self.ca_bundle = True
            
        print(f"[?] SefazService inicializado - Ambiente: {ambiente}")
        print(f"[?] CA Bundle: {self.ca_bundle}")
        if cert_path:
            print(f"[?] Certificado digital configurado")
    
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
            request_kwargs = {
                'data': envelope_soap,
                'headers': headers,
                'timeout': 30,
                'verify': self.ca_bundle  # Usar bundle com ICP-Brasil
            }
            
            # Adicionar certificado digital se disponível
            if self.cert_path and self.key_path:
                request_kwargs['cert'] = (self.cert_path, self.key_path)
                print(f"[?] Usando certificado digital para autenticação")
            else:
                print(f"[!] AVISO: Nenhum certificado digital configurado - SEFAZ pode rejeitar")
            
            response = requests.post(self.urls['autorizacao'], **request_kwargs)
            
            print(f"[?] Status HTTP: {response.status_code}")
            print(f"[?] Resposta recebida: {len(response.text)} chars")
            
            if response.status_code == 200:
                return self._processar_resposta_autorizacao(response.text, chave_acesso)
            else:
                print(f"[X] Erro HTTP: {response.status_code}")
                print(f"[X] Resposta: {response.text[:500]}...")
                
                mensagem_erro = f'Erro HTTP {response.status_code}'
                if response.status_code == 403:
                    mensagem_erro = 'Acesso negado - Certificado digital inválido ou não configurado'
                elif response.status_code == 401:
                    mensagem_erro = 'Não autorizado - Verifique o certificado digital'
                
                return {
                    'status': 'ERRO_HTTP',
                    'codigo': response.status_code,
                    'mensagem': mensagem_erro,
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
            print(f"[DEBUG] Resposta completa (primeiros 1000 chars): {resposta_xml[:1000]}")
            
            # Parse do XML de resposta
            root = ET.fromstring(resposta_xml)
            
            # Namespace pode variar
            namespaces = {
                'soap': 'http://www.w3.org/2003/05/soap-envelope',
                'nfe': 'http://www.portalfiscal.inf.br/nfe'
            }
            
            # Buscar código de status do LOTE (cStat do retorno)
            cstat_lote = root.find('.//nfe:cStat', namespaces)
            xmotivo_lote = root.find('.//nfe:xMotivo', namespaces)
            
            # Buscar código de status da NFE individual (dentro de protNFe)
            cstat_nfe = root.find('.//nfe:protNFe//nfe:infProt//nfe:cStat', namespaces)
            xmotivo_nfe = root.find('.//nfe:protNFe//nfe:infProt//nfe:xMotivo', namespaces)
            protocolo_element = root.find('.//nfe:protNFe//nfe:infProt//nfe:nProt', namespaces)
            
            # Preferir status da NFe individual, senão usar do lote
            codigo_status = None
            motivo = None
            
            if cstat_nfe is not None:
                codigo_status = cstat_nfe.text
                motivo = xmotivo_nfe.text if xmotivo_nfe is not None else 'Sem motivo'
                print(f"[INFO] Status NFe individual: {codigo_status} - {motivo}")
            elif cstat_lote is not None:
                codigo_status = cstat_lote.text
                motivo = xmotivo_lote.text if xmotivo_lote is not None else 'Sem motivo'
                print(f"[INFO] Status Lote: {codigo_status} - {motivo}")
            
            protocolo = protocolo_element.text if protocolo_element is not None else None
            
            if codigo_status:
                print(f"[RESULT] Código final: {codigo_status} - {motivo}")
                
                # Códigos de sucesso da SEFAZ
                # 100 = Autorizada
                # 150 = Autorizada fora de prazo
                codigos_sucesso = ['100', '150']
                
                # Códigos de processamento (não é sucesso nem rejeição final)
                # 103 = Lote recebido com sucesso
                # 104 = Lote processado
                # 105 = Lote em processamento
                codigos_processamento = ['103', '104', '105']
                
                if codigo_status in codigos_sucesso:
                    return {
                        'status': 'AUTORIZADA',
                        'codigo': codigo_status,
                        'mensagem': motivo,
                        'protocolo': protocolo,
                        'chave_acesso': chave_acesso,
                        'data_autorizacao': datetime.now().isoformat(),
                        'resposta_completa': resposta_xml
                    }
                elif codigo_status in codigos_processamento:
                    # Lote em processamento - aguardar consulta posterior
                    return {
                        'status': 'PROCESSANDO',
                        'codigo': codigo_status,
                        'mensagem': f'Lote em processamento - Consulte o status posteriormente. {motivo}',
                        'chave_acesso': chave_acesso,
                        'resposta_completa': resposta_xml
                    }
                else:
                    # Rejeição
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
                print(f"[DEBUG] XML completo: {resposta_xml}")
                return {
                    'status': 'ERRO_RESPOSTA',
                    'mensagem': 'Resposta da SEFAZ inválida - não foi possível extrair status',
                    'resposta_completa': resposta_xml
                }
                
        except Exception as e:
            print(f"[X] Erro ao processar resposta: {e}")
            import traceback
            traceback.print_exc()
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
            
            request_kwargs = {
                'data': envelope,
                'headers': headers,
                'timeout': 30,
                'verify': self.ca_bundle  # Usar bundle com ICP-Brasil
            }
            
            # Adicionar certificado digital se disponível
            if self.cert_path and self.key_path:
                request_kwargs['cert'] = (self.cert_path, self.key_path)
            
            response = requests.post(self.urls['status_servico'], **request_kwargs)
            
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