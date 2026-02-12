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
        'status_servico': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx',
        'inutilizacao': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeinutilizacao4.asmx'
    }
    
    # URLs SEFAZ-SP Produção 
    URLS_PRODUCAO = {
        'autorizacao': 'https://nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx',
        'consulta': 'https://nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx',
        'status_servico': 'https://nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx',
        'inutilizacao': 'https://nfe.fazenda.sp.gov.br/ws/nfeinutilizacao4.asmx'
    }
    
    def __init__(self, ambiente='homologacao', cert_path=None, key_path=None, urls_override=None, cert_pfx_data=None, cert_pfx_password=None):
        self.ambiente = ambiente
        # Permitir override de URLs para contingência SVC-AN/SVC-RS
        if urls_override:
            self.urls = urls_override
            self._modo_contingencia = True
        else:
            self.urls = self.URLS_HOMOLOGACAO if ambiente == 'homologacao' else self.URLS_PRODUCAO
            self._modo_contingencia = False
        self.cert_path = cert_path
        self.key_path = key_path
        self.cert_pfx_data = cert_pfx_data  # Dados originais do .pfx
        self.cert_pfx_password = cert_pfx_password  # Senha do .pfx
        
        # Usar bundle de certificados que inclui ICP-Brasil
        # Caminho absoluto para o bundle customizado no servidor
        self.ca_bundle = '/home/ubuntu/api_nfe/ca-bundle-icpbrasil.pem'
        if not os.path.exists(self.ca_bundle):
            # Fallback para certificados do sistema se bundle não existir
            self.ca_bundle = True
            
        modo_str = 'CONTINGÊNCIA' if self._modo_contingencia else 'NORMAL'
        print(f"[?] SefazService inicializado - Ambiente: {ambiente} - Modo: {modo_str}")
        print(f"[?] URL autorizacao: {self.urls.get('autorizacao', 'N/A')}")
        print(f"[?] CA Bundle: {self.ca_bundle}")
        if cert_path:
            print(f"[?] Certificado digital configurado")
    
    def _assinar_xml(self, xml_content, ref_uri):
        """
        Assina XML usando XMLSigner
        
        Args:
            xml_content: Conteúdo XML a ser assinado
            ref_uri: URI de referência para assinatura (ex: ID da inutilização)
        
        Returns:
            XML assinado ou None em caso de erro
        """
        try:
            from services.xml_signer import XMLSigner
            
            # Preparar certificado como dicionário com dados .pfx originais
            if not self.cert_pfx_data or not self.cert_pfx_password:
                raise Exception("Certificado PFX não disponível para assinatura")
            
            certificado = {
                'cert_data': self.cert_pfx_data,
                'password': self.cert_pfx_password,
                'ref_uri': ref_uri
            }
            
            signer = XMLSigner()
            xml_assinado = signer.assinar_xml(xml_content, certificado)
            
            return xml_assinado
            
        except Exception as e:
            print(f"[X] Erro ao assinar XML: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def enviar_nfe(self, xml_assinado, chave_acesso):
        """
        Envia NFe para autorização na SEFAZ
        """
        try:
            print(f"[OUT] === ENVIANDO NFE REAL PARA SEFAZ ===")
            print(f"[?] Ambiente: {self.ambiente}")
            print(f"[KEY] Chave: {chave_acesso}")
            print(f"[?] XML: {len(xml_assinado)} caracteres")
            print(f"[DEBUG] XML tem Signature: {'<Signature' in xml_assinado}")
            
            # Criar envelope SOAP
            envelope_soap = self._criar_envelope_autorizacao(xml_assinado, chave_acesso)
            
            # Debug: salvar envelope em arquivo temporário
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, dir='/tmp') as f:
                f.write(envelope_soap)
                print(f"[DEBUG] Envelope salvo em: {f.name}")
            
            # Headers para requisição SOAP 1.2
            headers = {
                'Content-Type': 'application/soap+xml; charset=utf-8',
            }
            
            print(f"[?] Enviando para: {self.urls['autorizacao']}")
            
            # Fazer requisição
            request_kwargs = {
                'data': envelope_soap.encode('utf-8'),
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
                print(f"[X] Resposta completa: {response.text}")
                
                mensagem_erro = f'Erro HTTP {response.status_code}'
                if response.status_code == 403:
                    mensagem_erro = 'Acesso negado - Certificado digital inválido ou não configurado'
                elif response.status_code == 401:
                    mensagem_erro = 'Não autorizado - Verifique o certificado digital'
                elif response.status_code == 400:
                    # Tentar extrair mensagem de erro do XML
                    try:
                        import xml.etree.ElementTree as ET
                        root = ET.fromstring(response.text)
                        # Buscar faultstring no SOAP
                        faultstring = root.find('.//{http://www.w3.org/2003/05/soap-envelope}Fault/{http://www.w3.org/2003/05/soap-envelope}Reason/{http://www.w3.org/2003/05/soap-envelope}Text')
                        if faultstring is not None and faultstring.text:
                            mensagem_erro = f'Erro SEFAZ: {faultstring.text}'
                            print(f"[X] Mensagem SEFAZ: {faultstring.text}")
                    except:
                        pass
                
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
        
        # DEBUG: Ver o que está chegando
        print(f"[ENVELOPE-DEBUG] XML recebido tem {len(xml_nfe)} caracteres")
        print(f"[ENVELOPE-DEBUG] XML tem Signature: {'<Signature' in xml_nfe}")
        
        # CRÍTICO: Remover APENAS declaração XML (sem strip que altera canonicalização)
        # .strip() pode remover espaços que fazem parte da assinatura digital
        xml_nfe_limpo = xml_nfe
        if xml_nfe_limpo.startswith('<?xml'):
            # Remove até o final da declaração XML (sem strip!)
            xml_nfe_limpo = xml_nfe_limpo.split('?>', 1)[1]
            # Remover APENAS o primeiro caractere se for quebra de linha após declaração
            if xml_nfe_limpo and xml_nfe_limpo[0] in ['\n', '\r']:
                xml_nfe_limpo = xml_nfe_limpo[1:]
        
        print(f"[ENVELOPE-DEBUG] Após remover declaração: {len(xml_nfe_limpo)} caracteres")
        print(f"[ENVELOPE-DEBUG] Ainda tem Signature: {'<Signature' in xml_nfe_limpo}")
        
        # NÃO REMOVER xmlns do NFe - O XML gerado pelo nfelib está correto
        # A SEFAZ precisa do namespace explícito no elemento NFe
        print(f"[ENVELOPE-DEBUG] ✅ xmlns mantido em NFe (padrão NFe 4.0)")
        
        # CRÍTICO: Envelope SOAP sem formatação (erro 588 causado por \n e espaços)
        envelope = f'<?xml version="1.0" encoding="utf-8"?><soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope"><soap12:Body><nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4"><enviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><idLote>{numero_lote}</idLote><indSinc>1</indSinc>{xml_nfe_limpo}</enviNFe></nfeDadosMsg></soap12:Body></soap12:Envelope>'
        
        print(f"[?] Envelope SOAP criado COMPACTO (sem \\n) - Lote: {numero_lote}")
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
                        'success': True,
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
                        'success': False,
                        'status': 'PROCESSANDO',
                        'codigo': codigo_status,
                        'mensagem': f'Lote em processamento - Consulte o status posteriormente. {motivo}',
                        'chave_acesso': chave_acesso,
                        'resposta_completa': resposta_xml
                    }
                else:
                    # Rejeição
                    return {
                        'success': False,
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
                    'success': False,
                    'status': 'ERRO_RESPOSTA',
                    'mensagem': 'Resposta da SEFAZ inválida - não foi possível extrair status',
                    'resposta_completa': resposta_xml
                }
                
        except Exception as e:
            print(f"[X] Erro ao processar resposta: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'status': 'ERRO_PROCESSAMENTO',
                'mensagem': f'Erro ao processar resposta: {e}',
                'resposta_completa': resposta_xml
            }
    
    def consultar_status_servico(self):
        """Consulta status do serviço SEFAZ"""
        try:
            print(f"[SEARCH] Consultando status do serviço SEFAZ...")
            
            # tpAmb: 1=Produção, 2=Homologação
            tp_amb = '1' if self.ambiente == 'producao' else '2'
            
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
        <tpAmb>{tp_amb}</tpAmb>
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
    
    def inutilizar_numeracao(self, cnpj_emitente, modelo, serie, numero_inicial, numero_final, ano, justificativa):
        """
        Inutiliza numeração de NFe/NFCe na SEFAZ
        
        Args:
            cnpj_emitente: CNPJ do emitente (14 dígitos)
            modelo: 55=NFe, 65=NFCe
            serie: Série da nota
            numero_inicial: Primeiro número a inutilizar
            numero_final: Último número a inutilizar
            ano: Ano com 2 dígitos (ex: 26 para 2026)
            justificativa: Justificativa (mínimo 15 caracteres)
        
        Returns:
            dict com status, protocolo, mensagem, xml_pedido e xml_resposta
        """
        try:
            print(f"[INUTILIZAR] === INUTILIZANDO NUMERAÇÃO ===")
            print(f"[INUTILIZAR] Modelo: {modelo}, Série: {serie}")
            print(f"[INUTILIZAR] Números: {numero_inicial} a {numero_final}")
            print(f"[INUTILIZAR] Justificativa: {justificativa}")
            
            # Validações
            if len(justificativa) < 15:
                return {
                    'success': False,
                    'status': 'ERRO',
                    'mensagem': 'Justificativa deve ter no mínimo 15 caracteres'
                }
            
            if numero_final < numero_inicial:
                return {
                    'success': False,
                    'status': 'ERRO',
                    'mensagem': 'Número final deve ser maior ou igual ao número inicial'
                }
            
            # Gerar ID da inutilização
            # Formato: ID + cUF(2) + AA(2) + CNPJ(14) + mod(2) + serie(3) + nNFIni(9) + nNFFin(9)
            # Total: 43 caracteres
            cuf = '35'  # São Paulo
            cnpj_limpo = cnpj_emitente.replace('.', '').replace('/', '').replace('-', '').zfill(14)
            serie_fmt = str(serie).zfill(3)
            num_ini_fmt = str(numero_inicial).zfill(9)
            num_fin_fmt = str(numero_final).zfill(9)
            
            id_inutilizacao = f"ID{cuf}{ano}{cnpj_limpo}{modelo}{serie_fmt}{num_ini_fmt}{num_fin_fmt}"
            print(f"[INUTILIZAR] ID gerado: {id_inutilizacao}")
            
            # tpAmb: 1=Produção, 2=Homologação
            tp_amb = '1' if self.ambiente == 'producao' else '2'
            
            # Limpar justificativa de caracteres inválidos
            import re
            justificativa_limpa = re.sub(r'[^\w\s\.\,\-]', '', justificativa)  # Remover caracteres especiais
            justificativa_limpa = ' '.join(justificativa_limpa.split())  # Normalizar espaços
            
            # Criar XML de inutilização SEM espaços extras ou indentação
            xml_inutilizacao = f'<?xml version="1.0" encoding="UTF-8"?><inutNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><infInut Id="{id_inutilizacao}"><tpAmb>{tp_amb}</tpAmb><xServ>INUTILIZAR</xServ><cUF>{cuf}</cUF><ano>{ano}</ano><CNPJ>{cnpj_limpo}</CNPJ><mod>{modelo}</mod><serie>{serie}</serie><nNFIni>{numero_inicial}</nNFIni><nNFFin>{numero_final}</nNFFin><xJust>{justificativa_limpa}</xJust></infInut></inutNFe>'
            
            print(f"[INUTILIZAR] XML criado, assinando...")
            
            # Assinar XML
            xml_assinado = self._assinar_xml(xml_inutilizacao, id_inutilizacao)
            if not xml_assinado:
                return {
                    'success': False,
                    'status': 'ERRO',
                    'mensagem': 'Erro ao assinar XML de inutilização'
                }
            
            # Limpar XML assinado de espaços extras e quebras de linha entre tags
            import re
            xml_assinado = re.sub(r'>\s+<', '><', xml_assinado.strip())
            
            print(f"[INUTILIZAR] XML assinado e limpo com sucesso")
            print(f"[DEBUG] XML assinado (primeiros 200 chars): {xml_assinado[:200]}")
            
            # Criar envelope SOAP (limpo, sem espaços desnecessários)
            envelope_soap = f'<?xml version="1.0" encoding="utf-8"?><soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope"><soap12:Header><nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeInutilizacao4"><cUF>{cuf}</cUF><versaoDados>4.00</versaoDados></nfeCabecMsg></soap12:Header><soap12:Body><nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeInutilizacao4">{xml_assinado}</nfeDadosMsg></soap12:Body></soap12:Envelope>'
            
            # URL de inutilização
            url_inutilizacao = self.urls.get('inutilizacao', 
                'https://nfe.fazenda.sp.gov.br/ws/nfeinutilizacao4.asmx' if self.ambiente == 'producao' 
                else 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeinutilizacao4.asmx')
            
            print(f"[INUTILIZAR] Enviando para: {url_inutilizacao}")
            
            # Headers
            headers = {
                'Content-Type': 'application/soap+xml; charset=utf-8',
            }
            
            # Fazer requisição
            request_kwargs = {
                'data': envelope_soap.encode('utf-8'),
                'headers': headers,
                'timeout': 30,
                'verify': self.ca_bundle
            }
            
            # Adicionar certificado digital se disponível
            if self.cert_path and self.key_path:
                request_kwargs['cert'] = (self.cert_path, self.key_path)
            else:
                print(f"[!] AVISO: Certificado digital não configurado")
            
            response = requests.post(url_inutilizacao, **request_kwargs)
            
            print(f"[INUTILIZAR] Status HTTP: {response.status_code}")
            
            if response.status_code == 200:
                return self._processar_resposta_inutilizacao(response.text, xml_assinado, id_inutilizacao)
            else:
                print(f"[X] Erro HTTP: {response.status_code}")
                print(f"[X] Resposta: {response.text[:500]}")
                return {
                    'success': False,
                    'status': 'ERRO',
                    'mensagem': f'Erro HTTP {response.status_code}',
                    'xml_pedido': xml_assinado,
                    'xml_resposta': response.text
                }
                
        except Exception as e:
            print(f"[X] Erro ao inutilizar: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'status': 'ERRO',
                'mensagem': f'Erro ao processar inutilização: {str(e)}'
            }
    
    def _processar_resposta_inutilizacao(self, resposta_xml, xml_pedido, id_inutilizacao):
        """Processa resposta da SEFAZ para inutilização"""
        try:
            print(f"[INUTILIZAR] Processando resposta...")
            print(f"[DEBUG] Resposta (primeiros 500 chars): {resposta_xml[:500]}")
            
            # Parse do XML
            root = ET.fromstring(resposta_xml)
            
            # Namespaces
            ns = {
                'soap': 'http://www.w3.org/2003/05/soap-envelope',
                'nfe': 'http://www.portalfiscal.inf.br/nfe'
            }
            
            # Buscar retorno
            ret_inut = root.find('.//nfe:retInutNFe', ns)
            if ret_inut is None:
                print(f"[X] Tag retInutNFe não encontrada")
                return {
                    'success': False,
                    'status': 'ERRO',
                    'mensagem': 'Resposta da SEFAZ inválida',
                    'xml_pedido': xml_pedido,
                    'xml_resposta': resposta_xml
                }
            
            # Extrair informações  
            cstat_element = ret_inut.find('nfe:infInut/nfe:cStat', ns)
            xmotivo_element = ret_inut.find('nfe:infInut/nfe:xMotivo', ns)
            protocolo_element = ret_inut.find('nfe:infInut/nfe:nProt', ns)
            
            codigo_status = cstat_element.text if cstat_element is not None else None
            motivo = xmotivo_element.text if xmotivo_element is not None else 'Sem motivo'
            protocolo = protocolo_element.text if protocolo_element is not None else None
            
            print(f"[INUTILIZAR] Código: {codigo_status} - {motivo}")
            
            # 102 = Inutilização de número homologado
            if codigo_status == '102':
                return {
                    'success': True,
                    'status': 'AUTORIZADA',
                    'codigo': codigo_status,
                    'mensagem': motivo,
                    'protocolo': protocolo,
                    'chave_inutilizacao': id_inutilizacao,
                    'xml_pedido': xml_pedido,
                    'xml_resposta': resposta_xml
                }
            else:
                return {
                    'success': False,
                    'status': 'REJEITADA',
                    'codigo': codigo_status,
                    'mensagem': motivo,
                    'protocolo': protocolo,
                    'chave_inutilizacao': id_inutilizacao,
                    'xml_pedido': xml_pedido,
                    'xml_resposta': resposta_xml
                }
                
        except Exception as e:
            print(f"[X] Erro ao processar resposta: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'status': 'ERRO',
                'mensagem': f'Erro ao processar resposta: {str(e)}',
                'xml_pedido': xml_pedido,
                'xml_resposta': resposta_xml
            }
