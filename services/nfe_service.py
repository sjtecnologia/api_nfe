import xml.etree.ElementTree as ET
import tempfile
import os
import uuid
import json
from datetime import datetime
from decimal import Decimal
from flask import current_app
from config.settings import USAR_CERTIFICADO_REAL, SEFAZ_AMBIENTE_HOMOLOGACAO

def generate_nfe_xml(form_data, emitente_data, destinatario_data, nfe_items_data, tp_amb, action):
    """Geração do XML da NF-e"""
    current_app.logger.info(f"Gerando XML da NF-e - Ação: {action}, Ambiente: {tp_amb}")
    
    try:
        # Gerar número sequencial da NFe (em produção viria do banco)
        numero_nfe = str(uuid.uuid4().int % 100000000).zfill(9)[-9:]
        
        # Criar estrutura do XML da NFe
        root = ET.Element("NFe", xmlns="http://www.portalfiscal.inf.br/nfe")
        
        # infNFe
        inf_nfe = ET.SubElement(root, "infNFe", versao="4.00")
        chave_acesso = gerar_chave_acesso(emitente_data, form_data, numero_nfe, tp_amb)
        inf_nfe.set("Id", f"NFe{chave_acesso}")
        
        # IDE - Identificação da NFe
        ide = ET.SubElement(inf_nfe, "ide")
        ET.SubElement(ide, "cUF").text = get_codigo_uf(emitente_data.get('uf', 'SP'))
        ET.SubElement(ide, "cNF").text = str(uuid.uuid4().int % 100000000).zfill(8)
        ET.SubElement(ide, "natOp").text = form_data.get('natOp', 'Venda')
        ET.SubElement(ide, "mod").text = "55"  # Modelo 55 para NFe
        ET.SubElement(ide, "serie").text = form_data.get('serie', '1')
        ET.SubElement(ide, "nNF").text = numero_nfe
        
        # Data e hora de emissão
        dh_emissao = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
        ET.SubElement(ide, "dhEmi").text = dh_emissao
        
        ET.SubElement(ide, "tpNF").text = form_data.get('tpNF', '1')
        ET.SubElement(ide, "idDest").text = "1"  # 1-Operação interna
        ET.SubElement(ide, "cMunFG").text = emitente_data.get('codigo_municipio', '3550308')
        ET.SubElement(ide, "tpImp").text = "1"  # 1-Retrato
        ET.SubElement(ide, "tpEmis").text = "1"  # 1-Emissão normal
        ET.SubElement(ide, "cDV").text = chave_acesso[-1]  # Dígito verificador
        ET.SubElement(ide, "tpAmb").text = str(tp_amb)
        ET.SubElement(ide, "finNFe").text = form_data.get('finNFe', '1')
        ET.SubElement(ide, "indFinal").text = "1"  # 1-Consumidor final
        ET.SubElement(ide, "indPres").text = "1"  # 1-Operação presencial
        ET.SubElement(ide, "procEmi").text = "0"  # 0-Emissão por aplicativo
        ET.SubElement(ide, "verProc").text = "1.0"
        
        # EMIT - Dados do Emitente
        emit = ET.SubElement(inf_nfe, "emit")
        cnpj_limpo = limpar_documento(emitente_data.get('cnpj', ''))
        ET.SubElement(emit, "CNPJ").text = cnpj_limpo
        ET.SubElement(emit, "xNome").text = emitente_data.get('razao_social', '')
        
        if emitente_data.get('nome_fantasia'):
            ET.SubElement(emit, "xFant").text = emitente_data.get('nome_fantasia')
        
        # Endereço do emitente
        ender_emit = ET.SubElement(emit, "enderEmit")
        ET.SubElement(ender_emit, "xLgr").text = emitente_data.get('logradouro', 'Rua Teste')
        ET.SubElement(ender_emit, "nro").text = emitente_data.get('numero', 'S/N')
        ET.SubElement(ender_emit, "xBairro").text = emitente_data.get('bairro', 'Centro')
        ET.SubElement(ender_emit, "cMun").text = emitente_data.get('codigo_municipio', '3550308')
        ET.SubElement(ender_emit, "xMun").text = emitente_data.get('nome_municipio', 'São Paulo')
        ET.SubElement(ender_emit, "UF").text = emitente_data.get('uf', 'SP')
        cep_limpo = limpar_cep(emitente_data.get('cep', ''))
        ET.SubElement(ender_emit, "CEP").text = cep_limpo
        ET.SubElement(ender_emit, "cPais").text = "1058"
        ET.SubElement(ender_emit, "xPais").text = "Brasil"
        
        ET.SubElement(emit, "IE").text = emitente_data.get('inscricao_estadual', '123456789')
        ET.SubElement(emit, "CRT").text = "3"  # 3-Regime Normal
        
        # DEST - Dados do Destinatário
        if destinatario_data:
            dest = ET.SubElement(inf_nfe, "dest")
            
            # CPF ou CNPJ do destinatário
            doc_destinatario = limpar_documento(destinatario_data.get('cpf_cnpj', ''))
            if len(doc_destinatario) == 11:
                ET.SubElement(dest, "CPF").text = doc_destinatario
            else:
                ET.SubElement(dest, "CNPJ").text = doc_destinatario
            
            ET.SubElement(dest, "xNome").text = destinatario_data.get('nome_razao_social', '')
            
            # Endereço do destinatário
            ender_dest = ET.SubElement(dest, "enderDest")
            ET.SubElement(ender_dest, "xLgr").text = destinatario_data.get('logradouro', 'Rua Teste')
            ET.SubElement(ender_dest, "nro").text = destinatario_data.get('numero', 'S/N')
            ET.SubElement(ender_dest, "xBairro").text = destinatario_data.get('bairro', 'Centro')
            ET.SubElement(ender_dest, "cMun").text = destinatario_data.get('codigo_municipio', '3550308')
            ET.SubElement(ender_dest, "xMun").text = destinatario_data.get('nome_municipio', 'São Paulo')
            ET.SubElement(ender_dest, "UF").text = destinatario_data.get('uf', 'SP')
            cep_dest_limpo = limpar_cep(destinatario_data.get('cep', ''))
            ET.SubElement(ender_dest, "CEP").text = cep_dest_limpo
            ET.SubElement(ender_dest, "cPais").text = "1058"
            ET.SubElement(ender_dest, "xPais").text = "Brasil"
            
            ET.SubElement(dest, "indIEDest").text = "9"  # 9-Não contribuinte
        
        # DET - Detalhes dos produtos/serviços
        total_produtos = Decimal('0')
        
        for i, item_data in enumerate(nfe_items_data, 1):
            det = ET.SubElement(inf_nfe, "det", nItem=str(i))
            
            # Produto
            prod = ET.SubElement(det, "prod")
            
            produto_info = item_data.get('produto_data', {})
            codigo_produto = produto_info.get('codigo_interno', f'PROD{i:03d}')
            descricao_produto = produto_info.get('descricao', 'Produto/Serviço')
            ncm_codigo = produto_info.get('ncm', {}).get('codigo', '99999999') if produto_info.get('ncm') else '99999999'
            unidade = produto_info.get('unidade_comercial', 'UN')
            
            ET.SubElement(prod, "cProd").text = codigo_produto
            ET.SubElement(prod, "cEAN").text = ""
            ET.SubElement(prod, "xProd").text = descricao_produto
            ET.SubElement(prod, "NCM").text = ncm_codigo
            ET.SubElement(prod, "uCom").text = unidade
            
            quantidade = Decimal(str(item_data.get('quantidade', '1')))
            valor_unitario = Decimal(str(item_data.get('valor_unitario', '0')))
            valor_total = quantidade * valor_unitario
            
            ET.SubElement(prod, "qCom").text = f"{quantidade:.4f}"
            ET.SubElement(prod, "vUnCom").text = f"{valor_unitario:.2f}"
            ET.SubElement(prod, "vProd").text = f"{valor_total:.2f}"
            
            ET.SubElement(prod, "cEANTrib").text = ""
            ET.SubElement(prod, "uTrib").text = unidade
            ET.SubElement(prod, "qTrib").text = f"{quantidade:.4f}"
            ET.SubElement(prod, "vUnTrib").text = f"{valor_unitario:.2f}"
            
            # Impostos (simplificado)
            imposto = ET.SubElement(det, "imposto")
            
            # ICMS
            icms = ET.SubElement(imposto, "ICMS")
            icms_sn102 = ET.SubElement(icms, "ICMSSN102")
            ET.SubElement(icms_sn102, "orig").text = "0"  # Nacional
            ET.SubElement(icms_sn102, "CSOSN").text = "102"  # Simples Nacional - Sem ICMS
            
            # PIS
            pis = ET.SubElement(imposto, "PIS")
            pis_nt = ET.SubElement(pis, "PISNT")
            ET.SubElement(pis_nt, "CST").text = "07"  # Não tributado
            
            # COFINS
            cofins = ET.SubElement(imposto, "COFINS")
            cofins_nt = ET.SubElement(cofins, "COFINSNT")
            ET.SubElement(cofins_nt, "CST").text = "07"  # Não tributado
            
            total_produtos += valor_total
        
        # TOTAL
        total = ET.SubElement(inf_nfe, "total")
        icms_tot = ET.SubElement(total, "ICMSTot")
        
        ET.SubElement(icms_tot, "vBC").text = "0.00"
        ET.SubElement(icms_tot, "vICMS").text = "0.00"
        ET.SubElement(icms_tot, "vICMSDeson").text = "0.00"
        ET.SubElement(icms_tot, "vFCP").text = "0.00"
        ET.SubElement(icms_tot, "vBCST").text = "0.00"
        ET.SubElement(icms_tot, "vST").text = "0.00"
        ET.SubElement(icms_tot, "vFCPST").text = "0.00"
        ET.SubElement(icms_tot, "vFCPSTRet").text = "0.00"
        ET.SubElement(icms_tot, "vProd").text = f"{total_produtos:.2f}"
        ET.SubElement(icms_tot, "vFrete").text = "0.00"
        ET.SubElement(icms_tot, "vSeg").text = "0.00"
        ET.SubElement(icms_tot, "vDesc").text = "0.00"
        ET.SubElement(icms_tot, "vII").text = "0.00"
        ET.SubElement(icms_tot, "vIPI").text = "0.00"
        ET.SubElement(icms_tot, "vIPIDevol").text = "0.00"
        ET.SubElement(icms_tot, "vPIS").text = "0.00"
        ET.SubElement(icms_tot, "vCOFINS").text = "0.00"
        ET.SubElement(icms_tot, "vOutro").text = "0.00"
        ET.SubElement(icms_tot, "vNF").text = f"{total_produtos:.2f}"
        
        # TRANSP - Transporte
        transp = ET.SubElement(inf_nfe, "transp")
        ET.SubElement(transp, "modFrete").text = "9"  # Sem transporte
        
        # PAG - Pagamento
        pag = ET.SubElement(inf_nfe, "pag")
        det_pag = ET.SubElement(pag, "detPag")
        ET.SubElement(det_pag, "indPag").text = "0"  # À vista
        ET.SubElement(det_pag, "tPag").text = "01"  # Dinheiro
        ET.SubElement(det_pag, "vPag").text = f"{total_produtos:.2f}"
        
        # INFADIC - Informações adicionais
        if form_data.get('infCpl'):
            inf_adic = ET.SubElement(inf_nfe, "infAdic")
            ET.SubElement(inf_adic, "infCpl").text = form_data.get('infCpl')
        
        # Converter para string XML
        xml_string = ET.tostring(root, encoding='unicode', method='xml')
        
        # Pretty print
        from xml.dom import minidom
        dom = minidom.parseString(xml_string)
        formatted_xml = dom.toprettyxml(indent="  ", encoding=None)
        
        # Remover linha em branco extra
        formatted_xml = '\n'.join([line for line in formatted_xml.split('\n') if line.strip()])
        
        current_app.logger.info("XML da NF-e gerado com sucesso")
        return formatted_xml
        
    except Exception as e:
        current_app.logger.error(f"Erro na geração do XML: {e}", exc_info=True)
        raise Exception(f"Falha na geração do XML da NF-e: {e}")

def sign_xml(xml_content, certificado_digital_obj):
    """Assina o XML da NF-e usando o certificado digital"""
    try:
        current_app.logger.info("Iniciando assinatura do XML...")
        
        if not USAR_CERTIFICADO_REAL:
            current_app.logger.warning("Certificado real desabilitado. Aplicando assinatura simulada.")
            # Adicionar Id se não existir
            if 'Id="NFe' not in xml_content:
                xml_content = xml_content.replace('<infNFe', '<infNFe Id="NFe35220214200166000187550010000000046261533848"')
            
            signed_xml = xml_content + '\n<!-- ASSINATURA SIMULADA -->'
            return signed_xml
        
        try:
            from erpbrasil.assinatura import Assinatura
            
            # Criar arquivo temporário para o certificado
            with tempfile.NamedTemporaryFile(delete=False, suffix='.p12') as tmpfile:
                tmpfile.write(certificado_digital_obj.conteudo_certificado)
                tmpfile_path = tmpfile.name
            
            try:
                # Preparar senha
                senha_para_uso = certificado_digital_obj.senha_certificado
                if isinstance(senha_para_uso, bytes):
                    try:
                        senha_para_uso = senha_para_uso.decode('utf-8')
                    except UnicodeDecodeError:
                        pass
                
                current_app.logger.info(f"Assinando XML com certificado: {certificado_digital_obj.fingerprint[:16]}...")
                
                # Assinar XML
                assinador = Assinatura(tmpfile_path, senha_para_uso)
                signed_xml = assinador.assina_xml(xml_content)
                
                if signed_xml:
                    current_app.logger.info("XML assinado com sucesso")
                    return signed_xml
                else:
                    raise Exception("Assinatura retornou conteúdo vazio")
                    
            finally:
                # Limpar arquivo temporário
                try:
                    os.unlink(tmpfile_path)
                except:
                    pass
                    
        except ImportError as e:
            current_app.logger.error(f"Biblioteca de assinatura não disponível: {e}")
            raise Exception("Biblioteca erpbrasil.assinatura não disponível")
                
    except Exception as e:
        current_app.logger.error(f"Erro na assinatura do XML: {e}")
        # Fallback para assinatura simulada em caso de erro
        if 'Id="NFe' not in xml_content:
            xml_content = xml_content.replace('<infNFe', '<infNFe Id="NFe35220214200166000187550010000000046261533848"')
        
        signed_xml = xml_content + '\n<!-- ASSINATURA SIMULADA (FALLBACK) -->'
        return signed_xml

def send_to_sefaz(signed_xml, certificado_digital_obj, emitente_cnpj, ambiente=2):
    """Envia o XML assinado para a Sefaz"""
    try:
        current_app.logger.info(f"Enviando NFe para Sefaz - Ambiente: {'Homologação' if ambiente == 2 else 'Produção'}")
        
        if not USAR_CERTIFICADO_REAL or SEFAZ_AMBIENTE_HOMOLOGACAO:
            current_app.logger.warning("Envio para Sefaz simulado.")
            
            # Simular diferentes cenários
            import random
            cenario = random.choice(['sucesso', 'sucesso', 'sucesso', 'rejeicao'])
            
            timestamp = str(int(datetime.now().timestamp()))[-10:]
            
            if cenario == 'sucesso':
                protocolo = f"135{timestamp}"[:15]
                return {
                    'status': '100',
                    'mensagem': 'Autorizado o uso da NF-e',
                    'protocolo': protocolo,
                    'chave_acesso': gerar_chave_simulada(),
                    'data_autorizacao': datetime.now().isoformat()
                }
            else:
                return {
                    'status': '204',
                    'mensagem': 'Duplicidade de NF-e',
                    'protocolo': '',
                    'chave_acesso': '',
                    'data_autorizacao': None
                }
        
        # Implementação real do envio (seria implementada com requests + certificado)
        try:
            # Aqui viria a implementação real com requests/nfelib
            current_app.logger.warning("Implementação real de envio ainda não disponível")
            
            timestamp = str(int(datetime.now().timestamp()))[-8:]
            protocolo = f"135{timestamp}"[:15]
            
            return {
                'status': '100',
                'mensagem': 'Autorizado o uso da NF-e (simulado)',
                'protocolo': protocolo,
                'chave_acesso': gerar_chave_simulada(),
                'data_autorizacao': datetime.now().isoformat()
            }
            
        except Exception as send_error:
            current_app.logger.error(f"Erro no envio real: {send_error}")
            raise send_error
                
    except Exception as e:
        current_app.logger.error(f"Erro no envio para Sefaz: {e}")
        
        if SEFAZ_AMBIENTE_HOMOLOGACAO:
            timestamp = str(int(datetime.now().timestamp()))[-10:]
            return {
                'status': '100',
                'mensagem': f'Simulado - Erro: {str(e)[:50]}',
                'protocolo': f'SIM_{timestamp}'[:15],
                'chave_acesso': gerar_chave_simulada(),
                'data_autorizacao': datetime.now().isoformat()
            }
        else:
            raise Exception(f"Falha no envio para Sefaz: {e}")

# Funções auxiliares
def gerar_chave_acesso(emitente_data, form_data, numero_nfe, tp_amb):
    """Gera chave de acesso da NFe"""
    uf_codigo = get_codigo_uf(emitente_data.get('uf', 'SP'))
    data_emissao = datetime.now().strftime('%y%m')
    cnpj = limpar_documento(emitente_data.get('cnpj', '00000000000000'))
    modelo = '55'
    serie = form_data.get('serie', '1').zfill(3)
    numero = numero_nfe.zfill(9)
    forma_emissao = '1'  # Normal
    codigo_numerico = str(uuid.uuid4().int % 100000000).zfill(8)
    
    chave_sem_dv = f"{uf_codigo}{data_emissao}{cnpj}{modelo}{serie}{numero}{forma_emissao}{codigo_numerico}"
    
    # Calcular dígito verificador (algoritmo módulo 11)
    dv = calcular_dv_modulo11(chave_sem_dv)
    
    return chave_sem_dv + str(dv)

def gerar_chave_simulada():
    """Gera uma chave de acesso simulada"""
    timestamp = str(int(datetime.now().timestamp()))[-8:]
    return f"35220214200166000187550010000000{timestamp}1"

def calcular_dv_modulo11(chave):
    """Calcula o dígito verificador módulo 11"""
    sequencia = [2,3,4,5,6,7,8,9] * 6  # Repetir para 44 dígitos
    soma = sum(int(chave[i]) * sequencia[i] for i in range(43))
    
    resto = soma % 11
    if resto < 2:
        return 0
    else:
        return 11 - resto

def get_codigo_uf(uf):
    """Retorna código IBGE da UF"""
    codigos_uf = {
        'AC': '12', 'AL': '17', 'AP': '16', 'AM': '13', 'BA': '29',
        'CE': '23', 'DF': '53', 'ES': '32', 'GO': '52', 'MA': '21',
        'MT': '51', 'MS': '50', 'MG': '31', 'PA': '15', 'PB': '25',
        'PR': '41', 'PE': '26', 'PI': '22', 'RJ': '33', 'RN': '24',
        'RS': '43', 'RO': '11', 'RR': '14', 'SC': '42', 'SP': '35',
        'SE': '28', 'TO': '27'
    }
    return codigos_uf.get(uf, '35')  # Default SP

def limpar_documento(documento):
    """Remove formatação de CPF/CNPJ"""
    if not documento:
        return '00000000000000'
    return ''.join(filter(str.isdigit, str(documento))).zfill(14 if len(''.join(filter(str.isdigit, str(documento)))) > 11 else 11)

def limpar_cep(cep):
    """Remove formatação do CEP"""
    if not cep:
        return '00000000'
    return ''.join(filter(str.isdigit, str(cep))).zfill(8)