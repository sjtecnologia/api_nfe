import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import base64
import tempfile
from xml.sax.saxutils import escape
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption


def _resolve_ca_bundle():
    """Resolve o bundle CA mais adequado para a comunicação com a SEFAZ."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_bundle = os.getenv('SEFAZ_CA_BUNDLE') or os.getenv('REQUESTS_CA_BUNDLE') or os.getenv('SSL_CERT_FILE')
    ca_candidates = [
        env_bundle,
        os.path.join(project_root, 'ca-bundle-icpbrasil.pem'),
        '/home/ubuntu/api_nfe/ca-bundle-icpbrasil.pem',
        '/etc/ssl/certs/ca-certificates.crt',
        '/etc/pki/tls/certs/ca-bundle.crt',
    ]

    for ca_path in ca_candidates:
        if ca_path and os.path.exists(ca_path):
            return ca_path

    return True

class SefazService:
    """Serviço para comunicação com SEFAZ real"""
    
    # URLs SEFAZ-SP Homologação
    URLS_HOMOLOGACAO = {
        'autorizacao': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx',
        'consulta': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx',
        'status_servico': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx',
        'recepcao_evento': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx',
        'inutilizacao': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeinutilizacao4.asmx'
    }
    
    # URLs SEFAZ-SP Produção 
    URLS_PRODUCAO = {
        'autorizacao': 'https://nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx',
        'consulta': 'https://nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx',
        'status_servico': 'https://nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx',
        'recepcao_evento': 'https://nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx',
        'inutilizacao': 'https://nfe.fazenda.sp.gov.br/ws/nfeinutilizacao4.asmx'
    }
    
    def __init__(self, ambiente='homologacao', cert_path=None, key_path=None, urls_override=None):
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
        self.ca_bundle = _resolve_ca_bundle()
            
        modo_str = 'CONTINGÊNCIA' if self._modo_contingencia else 'NORMAL'
        print(f"[?] SefazService inicializado - Ambiente: {ambiente} - Modo: {modo_str}")
        print(f"[?] URL autorizacao: {self.urls.get('autorizacao', 'N/A')}")
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

    def cancelar_nfe(self, chave_nfe, protocolo, justificativa, cnpj_emitente,
                     certificado_pem=None, certificado_pfx=None, senha_certificado=None):
        """Envia evento de cancelamento (110111) para a SEFAZ."""
        cert_temp_path = None
        key_temp_path = None
        pfx_temp_path = None
        try:
            if not chave_nfe or len(chave_nfe) != 44:
                return {
                    'success': False,
                    'status': 'ERRO_VALIDACAO',
                    'message': 'Chave de acesso inválida para cancelamento'
                }

            if not protocolo:
                return {
                    'success': False,
                    'status': 'ERRO_VALIDACAO',
                    'message': 'Protocolo de autorização não informado'
                }

            if not justificativa or len(justificativa.strip()) < 15:
                return {
                    'success': False,
                    'status': 'ERRO_VALIDACAO',
                    'message': 'Justificativa deve ter no mínimo 15 caracteres'
                }

            cert_path = self.cert_path
            key_path = self.key_path

            if (not cert_path or not key_path) and certificado_pfx and not senha_certificado:
                return {
                    'success': False,
                    'status': 'ERRO_CERTIFICADO',
                    'message': 'Senha do certificado do cliente não informada para cancelamento'
                }

            # Fluxo de cancelamento pode receber apenas PKCS#12 do banco.
            # Se PEM não estiver pronto, converte o PFX para arquivos temporários.
            if (not cert_path or not key_path) and certificado_pfx and senha_certificado:
                cert_bytes = certificado_pfx
                if isinstance(cert_bytes, str):
                    cert_bytes = base64.b64decode(cert_bytes)

                private_key, certificate, _additional = pkcs12.load_key_and_certificates(
                    cert_bytes,
                    senha_certificado.encode('utf-8')
                )

                if not private_key or not certificate:
                    return {
                        'success': False,
                        'status': 'ERRO_CERTIFICADO',
                        'message': 'Não foi possível extrair certificado/chave do arquivo PFX'
                    }

                with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as cert_file:
                    cert_file.write(certificate.public_bytes(Encoding.PEM))
                    cert_temp_path = cert_file.name

                with tempfile.NamedTemporaryFile(mode='wb', suffix='.key', delete=False) as key_file:
                    key_file.write(private_key.private_bytes(
                        encoding=Encoding.PEM,
                        format=PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=NoEncryption()
                    ))
                    key_temp_path = key_file.name

                cert_path = cert_temp_path
                key_path = key_temp_path

            # Suporte a PEM sem senha (arquivo único com cert/chave) vindo do banco.
            if not cert_path and certificado_pem:
                pem_bytes = certificado_pem
                if isinstance(pem_bytes, str):
                    if 'BEGIN' in pem_bytes:
                        pem_bytes = pem_bytes.encode('utf-8')
                    else:
                        pem_bytes = base64.b64decode(pem_bytes)

                with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as pem_file:
                    pem_file.write(pem_bytes)
                    cert_temp_path = pem_file.name

                cert_path = cert_temp_path

            if not cert_path:
                return {
                    'success': False,
                    'status': 'ERRO_CERTIFICADO',
                    'message': 'Certificado do cliente não configurado para comunicação com a SEFAZ'
                }

            cert_request = (cert_path, key_path) if key_path else cert_path

            endpoint = self.urls.get('recepcao_evento')
            if not endpoint:
                return {
                    'success': False,
                    'status': 'ERRO_CONFIG',
                    'message': 'Endpoint de recepção de evento não configurado'
                }

            c_uf = chave_nfe[0:2]
            tp_amb = '1' if self.ambiente == 'producao' else '2'
            id_lote = datetime.now().strftime('%Y%m%d%H%M%S')
            sequencia_evento = '1'
            id_evento = 'ID110111' + chave_nfe + sequencia_evento.zfill(2)
            dh_evento = datetime.now().astimezone().isoformat(timespec='seconds')

            NFE_NS = 'http://www.portalfiscal.inf.br/nfe'
            evento_xml = (
                '<envEvento xmlns="' + NFE_NS + '" versao="1.00">'
                + '<idLote>' + id_lote + '</idLote>'
                + '<evento versao="1.00">'
                + '<infEvento Id="' + id_evento + '">'
                + '<cOrgao>' + c_uf + '</cOrgao>'
                + '<tpAmb>' + tp_amb + '</tpAmb>'
                + '<CNPJ>' + cnpj_emitente + '</CNPJ>'
                + '<chNFe>' + chave_nfe + '</chNFe>'
                + '<dhEvento>' + dh_evento + '</dhEvento>'
                + '<tpEvento>110111</tpEvento>'
                + '<nSeqEvento>' + sequencia_evento + '</nSeqEvento>'
                + '<verEvento>1.00</verEvento>'
                + '<detEvento versao="1.00">'
                + '<descEvento>Cancelamento</descEvento>'
                + '<nProt>' + str(protocolo) + '</nProt>'
                + '<xJust>' + justificativa.strip() + '</xJust>'
                + '</detEvento>'
                + '</infEvento>'
                + '</evento>'
                + '</envEvento>'
            )

            # Assinar XML do evento com PyNFe - igual ao fluxo de emissão
            from pynfe.processamento.assinatura import AssinaturaA1
            from lxml import etree as _etree

            pfx_bytes = certificado_pfx
            if isinstance(pfx_bytes, str):
                pfx_bytes = base64.b64decode(pfx_bytes)

            with tempfile.NamedTemporaryFile(suffix='.pfx', delete=False) as _pfx_f:
                _pfx_f.write(pfx_bytes)
                pfx_temp_path = _pfx_f.name

            assinador = AssinaturaA1(pfx_temp_path, senha_certificado)
            # Assinar <evento> (não <envEvento>) para que <Signature> fique
            # dentro de <evento> como irmão de <infEvento>, conforme schema SEFAZ.
            _NFE_NS = 'http://www.portalfiscal.inf.br/nfe'
            _xml_envelope = _etree.fromstring(evento_xml.encode('utf-8'))
            _evento_el = _xml_envelope.find(f'{{{_NFE_NS}}}evento')
            _evento_assinado = assinador.assinar(_evento_el, retorna_string=False)
            # Substituir <evento> original pelo assinado na envelope
            _xml_envelope.remove(_xml_envelope.find(f'{{{_NFE_NS}}}evento'))
            _xml_envelope.append(_evento_assinado)
            evento_xml_assinado = _etree.tostring(_xml_envelope, encoding='unicode')
            print('[CANCELAMENTO] XML do evento assinado: ' + str(len(evento_xml_assinado)) + ' chars')

            envelope = (
                '<?xml version="1.0" encoding="utf-8"?>'
                '<soap12:Envelope'
                ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
                ' xmlns:xsd="http://www.w3.org/2001/XMLSchema"'
                ' xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
                '<soap12:Header>'
                '<nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4">'
                + '<cUF>' + c_uf + '</cUF>'
                + '<versaoDados>1.00</versaoDados>'
                + '</nfeCabecMsg>'
                + '</soap12:Header>'
                + '<soap12:Body>'
                + '<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4">'
                + evento_xml_assinado
                + '</nfeDadosMsg>'
                + '</soap12:Body>'
                + '</soap12:Envelope>'
            )

            headers = {
                'Content-Type': (
                    'application/soap+xml; charset=utf-8;'
                    ' action="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4/nfeRecepcaoEventoNF"'
                ),
            }

            response = requests.post(
                endpoint,
                data=envelope.encode('utf-8'),
                headers=headers,
                timeout=30,
                verify=self.ca_bundle,
                cert=cert_request
            )

            if response.status_code != 200:
                return {
                    'success': False,
                    'status': 'ERRO_HTTP',
                    'codigo': response.status_code,
                    'message': f'Erro HTTP {response.status_code} no cancelamento',
                    'resposta_completa': response.text
                }

            return self._processar_resposta_cancelamento(response.text)

        except Exception as e:
            print(f"[X] Erro ao cancelar NFe: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'status': 'ERRO_CANCELAMENTO',
                'message': f'Erro ao cancelar NFe: {e}'
            }
        finally:
            if cert_temp_path and os.path.exists(cert_temp_path):
                try:
                    os.unlink(cert_temp_path)
                except Exception:
                    pass
            if key_temp_path and os.path.exists(key_temp_path):
                try:
                    os.unlink(key_temp_path)
                except Exception:
                    pass
            if pfx_temp_path and os.path.exists(pfx_temp_path):
                try:
                    os.unlink(pfx_temp_path)
                except Exception:
                    pass

    def _processar_resposta_cancelamento(self, resposta_xml):
        """Processa resposta do evento de cancelamento da SEFAZ."""
        try:
            root = ET.fromstring(resposta_xml)
            namespaces = {
                'nfe': 'http://www.portalfiscal.inf.br/nfe'
            }

            cstat_lote = root.find('.//nfe:retEnvEvento//nfe:cStat', namespaces)
            xmotivo_lote = root.find('.//nfe:retEnvEvento//nfe:xMotivo', namespaces)

            cstat_evento = root.find('.//nfe:retEvento//nfe:infEvento//nfe:cStat', namespaces)
            xmotivo_evento = root.find('.//nfe:retEvento//nfe:infEvento//nfe:xMotivo', namespaces)
            protocolo_evento = root.find('.//nfe:retEvento//nfe:infEvento//nfe:nProt', namespaces)

            codigo = cstat_evento.text if cstat_evento is not None else (
                cstat_lote.text if cstat_lote is not None else None
            )
            motivo = xmotivo_evento.text if xmotivo_evento is not None else (
                xmotivo_lote.text if xmotivo_lote is not None else 'Sem motivo retornado pela SEFAZ'
            )
            protocolo = protocolo_evento.text if protocolo_evento is not None else None

            if codigo in ['135', '155']:
                return {
                    'success': True,
                    'status': 'CANCELADA',
                    'codigo': codigo,
                    'message': motivo,
                    'protocolo': protocolo,
                    'data_cancelamento': datetime.now().isoformat(),
                    'resposta_completa': resposta_xml
                }

            return {
                'success': False,
                'status': 'REJEITADA',
                'codigo': codigo,
                'message': motivo,
                'protocolo': protocolo,
                'resposta_completa': resposta_xml
            }

        except Exception as e:
            return {
                'success': False,
                'status': 'ERRO_PROCESSAMENTO',
                'message': f'Erro ao processar resposta de cancelamento: {e}',
                'resposta_completa': resposta_xml
            }

    def carta_correcao_nfe(self, chave_nfe, texto_correcao, cnpj_emitente, sequencia_evento=1,
                           certificado_pem=None, certificado_pfx=None, senha_certificado=None):
        """Envia evento de Carta de Correção Eletrônica (110110) para a SEFAZ."""
        cert_temp_path = None
        key_temp_path = None
        pfx_temp_path = None
        try:
            if not chave_nfe or len(chave_nfe) != 44:
                return {
                    'success': False,
                    'status': 'ERRO_VALIDACAO',
                    'message': 'Chave de acesso inválida para CC-e'
                }

            x_correcao = (texto_correcao or '').strip()
            if len(x_correcao) < 15 or len(x_correcao) > 1000:
                return {
                    'success': False,
                    'status': 'ERRO_VALIDACAO',
                    'message': 'Texto da CC-e deve ter entre 15 e 1000 caracteres'
                }
            x_correcao = escape(x_correcao)

            seq = int(sequencia_evento or 1)
            if seq < 1 or seq > 20:
                return {
                    'success': False,
                    'status': 'ERRO_VALIDACAO',
                    'message': 'Sequência do evento deve estar entre 1 e 20'
                }

            cert_path = self.cert_path
            key_path = self.key_path

            if (not cert_path or not key_path) and certificado_pfx and not senha_certificado:
                return {
                    'success': False,
                    'status': 'ERRO_CERTIFICADO',
                    'message': 'Senha do certificado do cliente não informada para CC-e'
                }

            if (not cert_path or not key_path) and certificado_pfx and senha_certificado:
                cert_bytes = certificado_pfx
                if isinstance(cert_bytes, str):
                    cert_bytes = base64.b64decode(cert_bytes)

                private_key, certificate, _additional = pkcs12.load_key_and_certificates(
                    cert_bytes,
                    senha_certificado.encode('utf-8')
                )

                if not private_key or not certificate:
                    return {
                        'success': False,
                        'status': 'ERRO_CERTIFICADO',
                        'message': 'Não foi possível extrair certificado/chave do arquivo PFX'
                    }

                with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as cert_file:
                    cert_file.write(certificate.public_bytes(Encoding.PEM))
                    cert_temp_path = cert_file.name

                with tempfile.NamedTemporaryFile(mode='wb', suffix='.key', delete=False) as key_file:
                    key_file.write(private_key.private_bytes(
                        encoding=Encoding.PEM,
                        format=PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=NoEncryption()
                    ))
                    key_temp_path = key_file.name

                cert_path = cert_temp_path
                key_path = key_temp_path

            if not cert_path and certificado_pem:
                pem_bytes = certificado_pem
                if isinstance(pem_bytes, str):
                    if 'BEGIN' in pem_bytes:
                        pem_bytes = pem_bytes.encode('utf-8')
                    else:
                        pem_bytes = base64.b64decode(pem_bytes)

                with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as pem_file:
                    pem_file.write(pem_bytes)
                    cert_temp_path = pem_file.name

                cert_path = cert_temp_path

            if not cert_path:
                return {
                    'success': False,
                    'status': 'ERRO_CERTIFICADO',
                    'message': 'Certificado do cliente não configurado para comunicação com a SEFAZ'
                }

            cert_request = (cert_path, key_path) if key_path else cert_path

            endpoint = self.urls.get('recepcao_evento')
            if not endpoint:
                return {
                    'success': False,
                    'status': 'ERRO_CONFIG',
                    'message': 'Endpoint de recepção de evento não configurado'
                }

            c_uf = chave_nfe[0:2]
            tp_amb = '1' if self.ambiente == 'producao' else '2'
            id_lote = datetime.now().strftime('%Y%m%d%H%M%S')
            id_evento = 'ID110110' + chave_nfe + str(seq).zfill(2)
            dh_evento = datetime.now().astimezone().isoformat(timespec='seconds')

            x_cond_uso = (
                'A Carta de Correcao e disciplinada pelo paragrafo 1o-A do art. 7o do Convenio S/N, '
                'de 15 de dezembro de 1970 e pode ser utilizada para regularizacao de erro ocorrido '
                'na emissao de documento fiscal, desde que o erro nao esteja relacionado com: I - as '
                'variaveis que determinam o valor do imposto tais como: base de calculo, aliquota, '
                'diferenca de preco, quantidade, valor da operacao ou da prestacao; II - a correcao de '
                'dados cadastrais que implique mudanca do remetente ou do destinatario; III - a data de '
                'emissao ou de saida.'
            )

            NFE_NS = 'http://www.portalfiscal.inf.br/nfe'
            evento_xml = (
                '<envEvento xmlns="' + NFE_NS + '" versao="1.00">'
                + '<idLote>' + id_lote + '</idLote>'
                + '<evento versao="1.00">'
                + '<infEvento Id="' + id_evento + '">'
                + '<cOrgao>' + c_uf + '</cOrgao>'
                + '<tpAmb>' + tp_amb + '</tpAmb>'
                + '<CNPJ>' + cnpj_emitente + '</CNPJ>'
                + '<chNFe>' + chave_nfe + '</chNFe>'
                + '<dhEvento>' + dh_evento + '</dhEvento>'
                + '<tpEvento>110110</tpEvento>'
                + '<nSeqEvento>' + str(seq) + '</nSeqEvento>'
                + '<verEvento>1.00</verEvento>'
                + '<detEvento versao="1.00">'
                + '<descEvento>Carta de Correcao</descEvento>'
                + '<xCorrecao>' + x_correcao + '</xCorrecao>'
                + '<xCondUso>' + x_cond_uso + '</xCondUso>'
                + '</detEvento>'
                + '</infEvento>'
                + '</evento>'
                + '</envEvento>'
            )

            from pynfe.processamento.assinatura import AssinaturaA1
            from lxml import etree as _etree

            if not certificado_pfx:
                return {
                    'success': False,
                    'status': 'ERRO_CERTIFICADO',
                    'message': 'Certificado PFX é obrigatório para assinatura da CC-e'
                }

            pfx_bytes = certificado_pfx
            if isinstance(pfx_bytes, str):
                pfx_bytes = base64.b64decode(pfx_bytes)

            with tempfile.NamedTemporaryFile(suffix='.pfx', delete=False) as _pfx_f:
                _pfx_f.write(pfx_bytes)
                pfx_temp_path = _pfx_f.name

            assinador = AssinaturaA1(pfx_temp_path, senha_certificado)
            _xml_envelope = _etree.fromstring(evento_xml.encode('utf-8'))
            _evento_el = _xml_envelope.find(f'{{{NFE_NS}}}evento')
            _evento_assinado = assinador.assinar(_evento_el, retorna_string=False)
            _xml_envelope.remove(_xml_envelope.find(f'{{{NFE_NS}}}evento'))
            _xml_envelope.append(_evento_assinado)
            evento_xml_assinado = _etree.tostring(_xml_envelope, encoding='unicode')

            envelope = (
                '<?xml version="1.0" encoding="utf-8"?>'
                '<soap12:Envelope'
                ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
                ' xmlns:xsd="http://www.w3.org/2001/XMLSchema"'
                ' xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
                '<soap12:Header>'
                '<nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4">'
                + '<cUF>' + c_uf + '</cUF>'
                + '<versaoDados>1.00</versaoDados>'
                + '</nfeCabecMsg>'
                + '</soap12:Header>'
                + '<soap12:Body>'
                + '<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4">'
                + evento_xml_assinado
                + '</nfeDadosMsg>'
                + '</soap12:Body>'
                + '</soap12:Envelope>'
            )

            headers = {
                'Content-Type': (
                    'application/soap+xml; charset=utf-8;'
                    ' action="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4/nfeRecepcaoEventoNF"'
                ),
            }

            response = requests.post(
                endpoint,
                data=envelope.encode('utf-8'),
                headers=headers,
                timeout=30,
                verify=self.ca_bundle,
                cert=cert_request
            )

            if response.status_code != 200:
                return {
                    'success': False,
                    'status': 'ERRO_HTTP',
                    'codigo': response.status_code,
                    'message': f'Erro HTTP {response.status_code} na CC-e',
                    'resposta_completa': response.text
                }

            return self._processar_resposta_carta_correcao(response.text, seq)

        except Exception as e:
            print(f"[X] Erro ao enviar CC-e: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'status': 'ERRO_CCE',
                'message': f'Erro ao enviar CC-e: {e}'
            }
        finally:
            if cert_temp_path and os.path.exists(cert_temp_path):
                try:
                    os.unlink(cert_temp_path)
                except Exception:
                    pass
            if key_temp_path and os.path.exists(key_temp_path):
                try:
                    os.unlink(key_temp_path)
                except Exception:
                    pass
            if pfx_temp_path and os.path.exists(pfx_temp_path):
                try:
                    os.unlink(pfx_temp_path)
                except Exception:
                    pass

    def _processar_resposta_carta_correcao(self, resposta_xml, sequencia_evento):
        """Processa resposta da SEFAZ para evento de Carta de Correção."""
        try:
            root = ET.fromstring(resposta_xml)
            namespaces = {
                'nfe': 'http://www.portalfiscal.inf.br/nfe'
            }

            cstat_lote = root.find('.//nfe:retEnvEvento//nfe:cStat', namespaces)
            xmotivo_lote = root.find('.//nfe:retEnvEvento//nfe:xMotivo', namespaces)

            cstat_evento = root.find('.//nfe:retEvento//nfe:infEvento//nfe:cStat', namespaces)
            xmotivo_evento = root.find('.//nfe:retEvento//nfe:infEvento//nfe:xMotivo', namespaces)
            protocolo_evento = root.find('.//nfe:retEvento//nfe:infEvento//nfe:nProt', namespaces)

            codigo = cstat_evento.text if cstat_evento is not None else (
                cstat_lote.text if cstat_lote is not None else None
            )
            motivo = xmotivo_evento.text if xmotivo_evento is not None else (
                xmotivo_lote.text if xmotivo_lote is not None else 'Sem motivo retornado pela SEFAZ'
            )
            protocolo = protocolo_evento.text if protocolo_evento is not None else None

            sucesso = codigo in ['135', '136', '155']
            return {
                'success': sucesso,
                'status': 'AUTORIZADA' if sucesso else 'REJEITADA',
                'codigo': codigo,
                'message': motivo,
                'protocolo': protocolo,
                'sequencia_evento': int(sequencia_evento),
                'data_evento': datetime.now().isoformat(),
                'resposta_completa': resposta_xml
            }
        except Exception as e:
            return {
                'success': False,
                'status': 'ERRO_PROCESSAMENTO',
                'message': f'Erro ao processar resposta da CC-e: {e}',
                'resposta_completa': resposta_xml
            }

    def inutilizar_numeracao(self, cnpj_emitente, modelo, serie, numero_inicial,
                             numero_final, ano, justificativa,
                             certificado_pfx=None, senha_certificado=None):
        """
        Inutiliza numeração de NFe/NFCe na SEFAZ (NFeInutilizacao4).

        Args:
            cnpj_emitente: CNPJ do emitente (14 dígitos, sem pontuação)
            modelo: '55'=NFe, '65'=NFCe
            serie: Série da nota (int)
            numero_inicial: Primeiro número a inutilizar
            numero_final: Último número a inutilizar
            ano: Ano com 2 dígitos (ex: '26')
            justificativa: Texto (mín. 15 chars)
            certificado_pfx: Bytes do .pfx do cliente
            senha_certificado: Senha (str) do .pfx
        Returns:
            dict com success, status, codigo, mensagem, protocolo,
                 chave_inutilizacao, xml_pedido, xml_resposta
        """
        pfx_temp_path = None
        try:
            print(f"[INUTILIZAR] === INUTILIZANDO NUMERAÇÃO ===")
            print(f"[INUTILIZAR] Modelo: {modelo}, Série: {serie}, {numero_inicial}-{numero_final}, Ano: {ano}")

            # ---- Validações rápidas ----
            if numero_final < numero_inicial:
                return {'success': False, 'status': 'ERRO',
                        'mensagem': 'Número final deve ser maior ou igual ao número inicial'}
            if len(justificativa.strip()) < 15:
                return {'success': False, 'status': 'ERRO',
                        'mensagem': 'Justificativa deve ter no mínimo 15 caracteres'}

            # ---- Montar ID e XML ----
            cuf = '35'  # São Paulo
            cnpj_limpo = cnpj_emitente.replace('.', '').replace('/', '').replace('-', '').zfill(14)
            serie_fmt = str(serie).zfill(3)
            num_ini_fmt = str(numero_inicial).zfill(9)
            num_fin_fmt = str(numero_final).zfill(9)
            id_inut = f"ID{cuf}{ano}{cnpj_limpo}{modelo}{serie_fmt}{num_ini_fmt}{num_fin_fmt}"
            print(f"[INUTILIZAR] ID: {id_inut}")

            tp_amb = '1' if self.ambiente == 'producao' else '2'

            import re as _re
            just_limpa = _re.sub(r'[^\w\s\.\,\-]', '', justificativa.strip())
            just_limpa = ' '.join(just_limpa.split())

            xml_inut = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<inutNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
                f'<infInut Id="{id_inut}">'
                f'<tpAmb>{tp_amb}</tpAmb>'
                '<xServ>INUTILIZAR</xServ>'
                f'<cUF>{cuf}</cUF>'
                f'<ano>{ano}</ano>'
                f'<CNPJ>{cnpj_limpo}</CNPJ>'
                f'<mod>{modelo}</mod>'
                f'<serie>{serie}</serie>'
                f'<nNFIni>{numero_inicial}</nNFIni>'
                f'<nNFFin>{numero_final}</nNFFin>'
                f'<xJust>{just_limpa}</xJust>'
                '</infInut>'
                '</inutNFe>'
            )

            # ---- Assinar XML via PyNFe AssinaturaA1 ----
            if not certificado_pfx or not senha_certificado:
                return {'success': False, 'status': 'ERRO_CERTIFICADO',
                        'mensagem': 'Certificado PFX e senha são obrigatórios para inutilização'}

            pfx_bytes = certificado_pfx
            if isinstance(pfx_bytes, str):
                pfx_bytes = base64.b64decode(pfx_bytes)

            with tempfile.NamedTemporaryFile(suffix='.pfx', delete=False) as _f:
                _f.write(pfx_bytes)
                pfx_temp_path = _f.name

            from pynfe.processamento.assinatura import AssinaturaA1
            from lxml import etree as _etree

            assinador = AssinaturaA1(pfx_temp_path, senha_certificado)
            _xml_tree = _etree.fromstring(xml_inut.encode('utf-8'))
            _xml_assinado_tree = assinador.assinar(_xml_tree, retorna_string=False)
            xml_assinado = _etree.tostring(_xml_assinado_tree, encoding='unicode')

            # Limpar espaços desnecessários entre tags
            import re as _re2
            xml_assinado = _re2.sub(r'>\s+<', '><', xml_assinado.strip())
            print(f"[INUTILIZAR] XML assinado: {len(xml_assinado)} chars")

            # ---- Montar envelope SOAP ----
            envelope_soap = (
                '<?xml version="1.0" encoding="utf-8"?>'
                '<soap12:Envelope'
                ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
                ' xmlns:xsd="http://www.w3.org/2001/XMLSchema"'
                ' xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
                '<soap12:Header>'
                '<nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeInutilizacao4">'
                f'<cUF>{cuf}</cUF>'
                '<versaoDados>4.00</versaoDados>'
                '</nfeCabecMsg>'
                '</soap12:Header>'
                '<soap12:Body>'
                '<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeInutilizacao4">'
                + xml_assinado +
                '</nfeDadosMsg>'
                '</soap12:Body>'
                '</soap12:Envelope>'
            )

            url = self.urls.get('inutilizacao')
            if not url:
                return {'success': False, 'status': 'ERRO_CONFIG',
                        'mensagem': 'URL de inutilização não configurada'}

            headers = {
                'Content-Type': (
                    'application/soap+xml; charset=utf-8;'
                    ' action="http://www.portalfiscal.inf.br/nfe/wsdl/NFeInutilizacao4/nfeInutilizacaoNF"'
                )
            }

            cert_req = (self.cert_path, self.key_path) if self.cert_path and self.key_path else None

            print(f"[INUTILIZAR] Enviando para: {url}")
            response = requests.post(
                url,
                data=envelope_soap.encode('utf-8'),
                headers=headers,
                timeout=30,
                verify=self.ca_bundle,
                **(({'cert': cert_req}) if cert_req else {})
            )

            print(f"[INUTILIZAR] HTTP {response.status_code}")
            if response.status_code != 200:
                return {
                    'success': False,
                    'status': 'ERRO_HTTP',
                    'mensagem': f'Erro HTTP {response.status_code}',
                    'xml_pedido': xml_assinado,
                    'xml_resposta': response.text
                }

            return self._processar_resposta_inutilizacao(response.text, xml_assinado, id_inut)

        except Exception as e:
            print(f"[X] Erro ao inutilizar: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'status': 'ERRO',
                'mensagem': f'Erro ao processar inutilização: {str(e)}'
            }
        finally:
            if pfx_temp_path and os.path.exists(pfx_temp_path):
                try:
                    os.unlink(pfx_temp_path)
                except Exception:
                    pass

    def _processar_resposta_inutilizacao(self, resposta_xml, xml_pedido, id_inutilizacao):
        """Processa resposta da SEFAZ para inutilização (retInutNFe)."""
        try:
            print(f"[INUTILIZAR] Processando resposta (primeiros 500): {resposta_xml[:500]}")
            root = ET.fromstring(resposta_xml)
            ns = {
                'soap': 'http://www.w3.org/2003/05/soap-envelope',
                'nfe': 'http://www.portalfiscal.inf.br/nfe'
            }
            ret = root.find('.//nfe:retInutNFe', ns)
            if ret is None:
                return {
                    'success': False,
                    'status': 'ERRO',
                    'mensagem': 'Resposta da SEFAZ inválida (sem retInutNFe)',
                    'xml_pedido': xml_pedido,
                    'xml_resposta': resposta_xml
                }

            cstat_el = ret.find('nfe:infInut/nfe:cStat', ns)
            xmot_el = ret.find('nfe:infInut/nfe:xMotivo', ns)
            nprot_el = ret.find('nfe:infInut/nfe:nProt', ns)

            codigo = cstat_el.text if cstat_el is not None else None
            motivo = xmot_el.text if xmot_el is not None else 'Sem motivo'
            protocolo = nprot_el.text if nprot_el is not None else None

            print(f"[INUTILIZAR] cStat={codigo} - {motivo}")

            # 102 = Inutilização homologada
            sucesso = codigo == '102'
            return {
                'success': sucesso,
                'status': 'AUTORIZADA' if sucesso else 'REJEITADA',
                'codigo': codigo,
                'mensagem': motivo,
                'protocolo': protocolo,
                'chave_inutilizacao': id_inutilizacao,
                'xml_pedido': xml_pedido,
                'xml_resposta': resposta_xml
            }

        except Exception as e:
            print(f"[X] Erro ao processar resposta de inutilização: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'status': 'ERRO',
                'mensagem': f'Erro ao processar resposta: {str(e)}',
                'xml_pedido': xml_pedido,
                'xml_resposta': resposta_xml
            }