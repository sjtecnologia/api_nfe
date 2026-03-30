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
        'cancelamento': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx'
    }
    
    # URLs SEFAZ-SP Produção 
    URLS_PRODUCAO = {
        'autorizacao': 'https://nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx',
        'consulta': 'https://nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx',
        'status_servico': 'https://nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx',
        'cancelamento': 'https://nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx'
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
        
        # Configuração SSL
        # Em homologação, servidores SEFAZ podem ter certificados auto-assinados/expirados
        # Em produção, verificar SSL normalmente
        if ambiente == 'homologacao':
            # Desabilitar verificação SSL estrita para ambiente de testes
            self.ca_bundle = False
            print(f"[SSL] Homologação: Verificação SSL desabilitada (ambiente de testes)")
        else:
            # Em produção, usar bundle de certificados com fallback
            custom_bundle = '/home/ubuntu/api_nfe/ca-bundle-icpbrasil.pem'
            if os.path.exists(custom_bundle):
                self.ca_bundle = custom_bundle
                print(f"[SSL] Produção: Usando bundle customizado: {custom_bundle}")
            else:
                # Preferir certificados do sistema (inclui ICP-Brasil no Linux)
                linux_system_certs = '/etc/ssl/certs/ca-certificates.crt'
                if os.path.exists(linux_system_certs):
                    self.ca_bundle = linux_system_certs
                    print(f"[SSL] Produção: Usando certificados do sistema Linux: {linux_system_certs}")
                else:
                    try:
                        import certifi
                        self.ca_bundle = certifi.where()
                        print(f"[SSL] Produção: Usando certifi: {self.ca_bundle}")
                    except ImportError:
                        self.ca_bundle = True
                        print(f"[SSL] Produção: Usando verificação SSL padrão")
            
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
    
    def cancelar_nfe(self, chave_nfe, protocolo, justificativa, cnpj_emitente, certificado_pfx=None, senha_certificado=None):
        """
        Cancela uma NFe autorizada na SEFAZ
        
        Args:
            chave_nfe: Chave de acesso da NFe (44 dígitos)
            protocolo: Número do protocolo de autorização
            justificativa: Justificativa do cancelamento (mínimo 15 caracteres)
            cnpj_emitente: CNPJ do emitente
            certificado_pfx: Bytes ou path do certificado .pfx
            senha_certificado: Senha do certificado
        
        Returns:
            dict com success, protocolo, data_cancelamento, mensagem
        """
        try:
            print(f"[CANCEL] Iniciando cancelamento de NFe")
            print(f"[CANCEL] Chave: {chave_nfe}")
            print(f"[CANCEL] Protocolo: {protocolo}")
            print(f"[CANCEL] Justificativa: {justificativa[:50]}...")
            
            # Validações
            if not chave_nfe or len(chave_nfe) != 44:
                return {'success': False, 'message': 'Chave de acesso inválida'}
            
            if not justificativa or len(justificativa) < 15:
                return {'success': False, 'message': 'Justificativa deve ter no mínimo 15 caracteres'}
            
            # Criar XML do evento de cancelamento
            xml_evento = self._criar_xml_cancelamento(chave_nfe, protocolo, justificativa, cnpj_emitente)
            
            # Assinar o XML do evento
            print(f"[CANCEL] Assinando evento de cancelamento...")
            xml_evento_assinado = self._assinar_evento(xml_evento, certificado_pfx, senha_certificado)
            
            # Criar envelope SOAP
            envelope = self._criar_envelope_evento(xml_evento_assinado)
            
            # Headers
            headers = {
                'Content-Type': 'application/soap+xml; charset=utf-8',
            }
            
            print(f"[CANCEL] Enviando para: {self.urls.get('cancelamento')}")
            
            # Fazer requisição
            request_kwargs = {
                'data': envelope.encode('utf-8'),
                'headers': headers,
                'timeout': 30,
                'verify': self.ca_bundle
            }
            
            # Adicionar certificado digital para autenticação mútua TLS
            # Usar os arquivos PEM temporários criados na assinatura
            if hasattr(self, '_temp_cert_path') and hasattr(self, '_temp_key_path'):
                request_kwargs['cert'] = (self._temp_cert_path, self._temp_key_path)
                print(f"[CANCEL] Usando certificado TLS: {self._temp_cert_path}")
            elif self.cert_path and self.key_path:
                request_kwargs['cert'] = (self.cert_path, self.key_path)
                print(f"[CANCEL] Usando certificado TLS (classe): {self.cert_path}")
            else:
                print(f"[CANCEL] ⚠️ ATENÇÃO: Nenhum certificado TLS configurado!")
            
            response = requests.post(self.urls.get('cancelamento'), **request_kwargs)
            
            # Limpar arquivos temporários após a requisição
            if hasattr(self, '_temp_cert_path'):
                try:
                    import os
                    os.unlink(self._temp_cert_path)
                    os.unlink(self._temp_key_path)
                    if self._temp_pfx_path:
                        os.unlink(self._temp_pfx_path)
                    print(f"[CANCEL] Arquivos temporários removidos")
                except:
                    pass
            
            print(f"[CANCEL] Status HTTP: {response.status_code}")
            
            if response.status_code == 200:
                return self._processar_resposta_cancelamento(response.text)
            else:
                print(f"[CANCEL] Erro HTTP: {response.status_code}")
                print(f"[CANCEL] Resposta: {response.text[:500]}")
                return {
                    'success': False,
                    'message': f'Erro HTTP {response.status_code}'
                }
                
        except Exception as e:
            print(f"[CANCEL] Erro ao cancelar NFe: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Erro ao cancelar: {str(e)}'
            }
    
    def _criar_xml_cancelamento(self, chave_nfe, protocolo, justificativa, cnpj_emitente):
        """Cria XML do evento de cancelamento SEM formatação (compacto)"""
        from datetime import datetime
        
        # tpAmb: 1=Produção, 2=Homologação
        tp_amb = '1' if self.ambiente == 'producao' else '2'
        
        # Número sequencial do evento (sempre 1 para cancelamento)
        n_seq_evento = '1'
        
        # Tipo de evento: 110111 = Cancelamento
        tp_evento = '110111'
        
        # Data/hora do evento no formato AAAA-MM-DDTHH:MM:SS-03:00
        dh_evento = datetime.now().strftime('%Y-%m-%dT%H:%M:%S-03:00')
        
        # Gerar ID do evento: ID + tpEvento + chave + nSeqEvento (formato: ID + 52 dígitos)
        id_evento = f"ID{tp_evento}{chave_nfe}{n_seq_evento.zfill(2)}"
        
        # Criar XML compacto (SEM quebras de linha, SEM indentação)
        xml = f'<evento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">'
        xml += f'<infEvento Id="{id_evento}">'
        xml += f'<cOrgao>35</cOrgao>'
        xml += f'<tpAmb>{tp_amb}</tpAmb>'
        xml += f'<CNPJ>{cnpj_emitente}</CNPJ>'
        xml += f'<chNFe>{chave_nfe}</chNFe>'
        xml += f'<dhEvento>{dh_evento}</dhEvento>'
        xml += f'<tpEvento>{tp_evento}</tpEvento>'
        xml += f'<nSeqEvento>{n_seq_evento}</nSeqEvento>'
        xml += f'<verEvento>1.00</verEvento>'
        xml += f'<detEvento versao="1.00">'
        xml += f'<descEvento>Cancelamento</descEvento>'
        xml += f'<nProt>{protocolo}</nProt>'
        xml += f'<xJust>{justificativa}</xJust>'
        xml += f'</detEvento>'
        xml += f'</infEvento>'
        xml += f'</evento>'
        
        print(f"[CANCEL] XML evento (100 chars): {xml[:100]}")
        return xml
    
    def _assinar_evento(self, xml_evento, certificado_pfx=None, senha_certificado=None):
        """Assina o XML do evento de cancelamento usando PyNFe"""
        try:
            from pynfe.processamento.assinatura import AssinaturaA1
            from lxml import etree
            import tempfile
            import os
            
            print(f"[CANCEL] Preparando certificado para assinatura...")
            
            # Se não foi passado certificado, usar o configurado na classe
            if not certificado_pfx and self.cert_path:
                # Ler arquivo PEM e tentar converter (ou usar dados já salvos)
                print(f"[CANCEL] Usando certificado da classe: {self.cert_path}")
                # Por enquanto, vamos precisar que seja passado o PFX
                raise Exception("Certificado PFX não fornecido")
            
            # Salvar certificado em arquivo temporário se for bytes
            if isinstance(certificado_pfx, bytes):
                with tempfile.NamedTemporaryFile(suffix='.pfx', delete=False) as tmp_file:
                    tmp_file.write(certificado_pfx)
                    cert_file_path = tmp_file.name
                    temp_file_created = True
            else:
                # É um caminho
                cert_file_path = certificado_pfx
                temp_file_created = False
            
            print(f"[CANCEL] Certificado PFX: {cert_file_path}")
            
            # Extrair certificado e chave para uso na requisição HTTPS
            print(f"[CANCEL] Extraindo certificado e chave para autenticação TLS...")
            with open(cert_file_path, 'rb') as f:
                pfx_data = f.read()
            
            # Carregar PFX usando a API mais recente do pyOpenSSL
            from cryptography.hazmat.primitives.serialization import pkcs12
            from cryptography.hazmat.primitives import serialization
            
            senha_bytes = senha_certificado.encode() if isinstance(senha_certificado, str) else senha_certificado
            
            # Carregar PKCS12
            private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                pfx_data, senha_bytes
            )
            
            # Criar arquivos temporários para cert e key
            cert_pem_file = tempfile.NamedTemporaryFile(suffix='.pem', delete=False)
            key_pem_file = tempfile.NamedTemporaryFile(suffix='.key', delete=False)
            
            # Exportar certificado
            cert_pem_file.write(certificate.public_bytes(serialization.Encoding.PEM))
            cert_pem_file.close()
            
            # Exportar chave privada
            key_pem_file.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
            key_pem_file.close()
            
            # Guardar paths dos arquivos PEM para uso posterior
            self._temp_cert_path = cert_pem_file.name
            self._temp_key_path = key_pem_file.name
            self._temp_pfx_path = cert_file_path if temp_file_created else None
            
            print(f"[CANCEL] Cert PEM: {self._temp_cert_path}")
            print(f"[CANCEL] Key PEM: {self._temp_key_path}")
            
            # Criar assinador
            assinador = AssinaturaA1(cert_file_path, senha_certificado)
            
            # Parsear XML
            xml_element = etree.fromstring(xml_evento.encode('utf-8'))
            
            # Assinar
            print(f"[CANCEL] Assinando com PyNFe AssinaturaA1...")
            xml_assinado = assinador.assinar(xml_element, retorna_string=True)
            
            # Remover espaços antes/depois do XML assinado (sem alterar o conteúdo interno)
            xml_assinado_clean = xml_assinado.strip()
            
            print(f"[CANCEL] ✅ Evento assinado com sucesso")
            print(f"[CANCEL] XML assinado (100 chars): {xml_assinado_clean[:100]}")
            return xml_assinado_clean
            
        except Exception as e:
            print(f"[CANCEL] ❌ Erro ao assinar evento: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Erro ao assinar evento: {str(e)}")
    
    def _criar_envelope_evento(self, xml_evento):
        """Cria envelope SOAP para envio de evento"""
        from datetime import datetime
        from lxml import etree
        
        # Gerar número do lote (timestamp)
        numero_lote = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Garantir que o XML está limpo e sem declaração
        if isinstance(xml_evento, str) and xml_evento.startswith('<?xml'):
            xml_evento = xml_evento.split('?>', 1)[1]
        
        # Remover qualquer espaço antes/depois
        xml_evento = xml_evento.strip()
        
        # Criar estrutura completa
        envelope_str = '<?xml version="1.0" encoding="utf-8"?>'
        envelope_str += '<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
        envelope_str += '<soap12:Body>'
        envelope_str += '<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4">'
        envelope_str += '<envEvento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">'
        envelope_str += f'<idLote>{numero_lote}</idLote>'
        envelope_str += xml_evento
        envelope_str += '</envEvento>'
        envelope_str += '</nfeDadosMsg>'
        envelope_str += '</soap12:Body>'
        envelope_str += '</soap12:Envelope>'
        
        print(f"[CANCEL] Envelope criado (200 chars): {envelope_str[:200]}")
        
        return envelope_str
    
    def _processar_resposta_cancelamento(self, resposta_xml):
        """Processa resposta do cancelamento"""
        try:
            print(f"[CANCEL] Processando resposta...")
            print(f"[CANCEL] Resposta XML (primeiros 1000 chars): {resposta_xml[:1000]}")
            
            # Parse do XML
            root = ET.fromstring(resposta_xml)
            
            # Namespace
            namespaces = {
                'soap': 'http://www.w3.org/2003/05/soap-envelope',
                'nfe': 'http://www.portalfiscal.inf.br/nfe'
            }
            
            # Primeiro verificar erro no lote (retEnvEvento)
            cstat_lote = root.find('.//nfe:retEnvEvento//nfe:cStat', namespaces)
            if cstat_lote is not None:
                codigo_lote = cstat_lote.text
                print(f"[CANCEL] Status do Lote: {codigo_lote}")
                
                # Se lote foi rejeitado (erro 5xx), retornar erro
                if codigo_lote.startswith('5'):
                    xmotivo_lote = root.find('.//nfe:retEnvEvento//nfe:xMotivo', namespaces)
                    motivo_lote = xmotivo_lote.text if xmotivo_lote is not None else 'Erro desconhecido'
                    print(f"[CANCEL] Erro no lote: {codigo_lote} - {motivo_lote}")
                    return {
                        'success': False,
                        'message': f'Erro {codigo_lote}: {motivo_lote}'
                    }
            
            # Buscar código de status do evento individual
            cstat = root.find('.//nfe:retEvento//nfe:infEvento//nfe:cStat', namespaces)
            xmotivo = root.find('.//nfe:retEvento//nfe:infEvento//nfe:xMotivo', namespaces)
            nprot = root.find('.//nfe:retEvento//nfe:infEvento//nfe:nProt', namespaces)
            dh_reg_evento = root.find('.//nfe:retEvento//nfe:infEvento//nfe:dhRegEvento', namespaces)
            
            if cstat is not None:
                codigo = cstat.text
                motivo = xmotivo.text if xmotivo is not None else 'Sem motivo'
                protocolo = nprot.text if nprot is not None else None
                data_evento = dh_reg_evento.text if dh_reg_evento is not None else None
                
                print(f"[CANCEL] Status do Evento: {codigo} - {motivo}")
                
                # Códigos de sucesso: 135 = Evento registrado e vinculado à NF-e
                if codigo in ['135', '136']:  # 136 = Cancelamento já registrado
                    return {
                        'success': True,
                        'protocolo': protocolo,
                        'data_cancelamento': data_evento,
                        'message': motivo
                    }
                else:
                    return {
                        'success': False,
                        'message': f'Erro {codigo}: {motivo}'
                    }
            else:
                print(f"[CANCEL] Não foi possível extrair status do evento")
                return {
                    'success': False,
                    'message': 'Resposta inválida da SEFAZ'
                }
                
        except Exception as e:
            print(f"[CANCEL] Erro ao processar resposta: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Erro ao processar resposta: {str(e)}'
            }
            return {'status': 'ERRO', 'mensagem': str(e)}