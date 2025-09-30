from lxml import etree
from datetime import datetime, timezone
import uuid
from utils.helpers import get_uf_ibge_code, limpar_cnpj_cpf
from decimal import Decimal

def generate_nfe_xml(form_data, emitente_data, destinatario_data, items_data, tp_amb=2, operation='emitir'):
    """
    Gera o XML da NFe baseado nos dados fornecidos
    """
    try:
        print("🔧 Iniciando geração do XML da NFe...")
        
        # ✅ CONVERTER TODOS OS VALORES PARA STRING
        def to_str(value, default=""):
            """Converte qualquer valor para string"""
            if value is None:
                return default
            return str(value)
        
        # Criar elemento raiz
        nfe_proc = etree.Element("nfeProc", 
                               xmlns="http://www.portalfiscal.inf.br/nfe",
                               versao="4.00")
        
        nfe = etree.SubElement(nfe_proc, "NFe")
        inf_nfe = etree.SubElement(nfe, "infNFe", versao="4.00")
        
        # Gerar chave da NFe (simplificada para teste)
        chave_acesso = gerar_chave_nfe(emitente_data, form_data)
        inf_nfe.set("Id", f"NFe{chave_acesso}")
        
        print(f"🔑 Chave de acesso gerada: {chave_acesso}")
        
        # ===== IDE - IDENTIFICAÇÃO =====
        ide = etree.SubElement(inf_nfe, "ide")
        
        # Código da UF - CONVERTER PARA STRING
        uf_codigo = get_uf_ibge_code(emitente_data.get('uf', 'SP'))
        print(f"🌍 UF: {emitente_data.get('uf')} -> Código: {uf_codigo} (tipo: {type(uf_codigo)})")
        
        etree.SubElement(ide, "cUF").text = to_str(uf_codigo)
        etree.SubElement(ide, "cNF").text = chave_acesso[-8:]  # Código numérico
        etree.SubElement(ide, "natOp").text = form_data.get('natOp', 'Venda')
        etree.SubElement(ide, "mod").text = "55"  # NFe
        etree.SubElement(ide, "serie").text = to_str(form_data.get('serie', '1'))
        etree.SubElement(ide, "nNF").text = "1"  # Número sequencial (simplificado)
        
        # Data/hora de emissão
        data_emissao = form_data.get('dataEmissao')
        if data_emissao:
            # Converter para formato ISO
            try:
                dt = datetime.fromisoformat(data_emissao.replace('T', ' '))
                data_iso = dt.strftime('%Y-%m-%dT%H:%M:%S-03:00')
            except:
                data_iso = datetime.now().strftime('%Y-%m-%dT%H:%M:%S-03:00')
        else:
            data_iso = datetime.now().strftime('%Y-%m-%dT%H:%M:%S-03:00')
        
        etree.SubElement(ide, "dhEmi").text = data_iso
        etree.SubElement(ide, "tpNF").text = to_str(form_data.get('tpNF', '1'))
        etree.SubElement(ide, "idDest").text = "1"  # Operação interna
        
        # Código do município - CONVERTER PARA STRING
        cod_municipio = emitente_data.get('codigo_municipio', '3549805')
        etree.SubElement(ide, "cMunFG").text = to_str(cod_municipio)
        
        etree.SubElement(ide, "tpImp").text = "1"  # DANFE normal
        etree.SubElement(ide, "tpEmis").text = "1"  # Emissão normal
        etree.SubElement(ide, "cDV").text = chave_acesso[-1]  # Dígito verificador
        etree.SubElement(ide, "tpAmb").text = to_str(tp_amb)
        etree.SubElement(ide, "finNFe").text = to_str(form_data.get('finNFe', '1'))
        etree.SubElement(ide, "indFinal").text = "1"  # Consumidor final
        etree.SubElement(ide, "indPres").text = "1"  # Operação presencial
        
        print("✅ IDE criado")
        
        # ===== EMIT - EMITENTE =====
        emit = etree.SubElement(inf_nfe, "emit")
        
        # CNPJ do emitente - limpar formatação
        cnpj_emitente = limpar_cnpj_cpf(emitente_data.get('cnpj', ''))
        etree.SubElement(emit, "CNPJ").text = cnpj_emitente
        etree.SubElement(emit, "xNome").text = emitente_data.get('razao_social', '')
        
        if emitente_data.get('nome_fantasia'):
            etree.SubElement(emit, "xFant").text = emitente_data.get('nome_fantasia')
        
        # Endereço do emitente
        ender_emit = etree.SubElement(emit, "enderEmit")
        etree.SubElement(ender_emit, "xLgr").text = emitente_data.get('logradouro', '')
        etree.SubElement(ender_emit, "nro").text = to_str(emitente_data.get('numero', 'SN'))
        etree.SubElement(ender_emit, "xBairro").text = emitente_data.get('bairro', '')
        etree.SubElement(ender_emit, "cMun").text = to_str(emitente_data.get('codigo_municipio', '3549805'))
        etree.SubElement(ender_emit, "xMun").text = emitente_data.get('nome_municipio', '')
        etree.SubElement(ender_emit, "UF").text = emitente_data.get('uf', 'SP')
        
        # CEP - limpar formatação
        cep_emitente = limpar_cnpj_cpf(emitente_data.get('cep', ''))
        if cep_emitente:
            etree.SubElement(ender_emit, "CEP").text = cep_emitente
        
        etree.SubElement(ender_emit, "cPais").text = "1058"  # Brasil
        etree.SubElement(ender_emit, "xPais").text = "Brasil"
        
        # Inscrição estadual
        ie_emitente = emitente_data.get('inscricao_estadual', '').replace('.', '').replace('-', '')
        etree.SubElement(emit, "IE").text = ie_emitente
        
        print("✅ EMIT criado")
        
        # ===== DEST - DESTINATÁRIO =====
        dest = etree.SubElement(inf_nfe, "dest")
        
        # CPF/CNPJ do destinatário
        doc_dest = limpar_cnpj_cpf(destinatario_data.get('cpf_cnpj', ''))
        if len(doc_dest) == 11:
            etree.SubElement(dest, "CPF").text = doc_dest
        else:
            etree.SubElement(dest, "CNPJ").text = doc_dest
        
        etree.SubElement(dest, "xNome").text = destinatario_data.get('nome_razao_social', '')
        
        # Endereço do destinatário
        ender_dest = etree.SubElement(dest, "enderDest")
        etree.SubElement(ender_dest, "xLgr").text = destinatario_data.get('logradouro', '')
        etree.SubElement(ender_dest, "nro").text = to_str(destinatario_data.get('numero', 'SN'))
        etree.SubElement(ender_dest, "xBairro").text = destinatario_data.get('bairro', '')
        etree.SubElement(ender_dest, "cMun").text = to_str(destinatario_data.get('codigo_municipio', ''))
        etree.SubElement(ender_dest, "xMun").text = destinatario_data.get('nome_municipio', '')
        etree.SubElement(ender_dest, "UF").text = destinatario_data.get('uf', '')
        
        # CEP destinatário
        cep_dest = limpar_cnpj_cpf(destinatario_data.get('cep', ''))
        if cep_dest:
            etree.SubElement(ender_dest, "CEP").text = cep_dest
        
        etree.SubElement(ender_dest, "cPais").text = "1058"  # Brasil
        etree.SubElement(ender_dest, "xPais").text = "Brasil"
        
        print("✅ DEST criado")
        
        # ===== DET - DETALHES DOS ITENS =====
        print(f"📦 === CRIANDO {len(items_data)} ITENS ===")
        
        for i, item in enumerate(items_data, 1):
            print(f"📦 Processando item {i}: {item.get('descricao', 'Sem descrição')}")
            
            det = etree.SubElement(inf_nfe, "det", nItem=to_str(i))
            print(f"✅ Tag <det nItem='{i}'> criada")
            
            # Produto
            prod = etree.SubElement(det, "prod")
            etree.SubElement(prod, "cProd").text = item.get('codigo_produto', f'PROD{i:03d}')
            etree.SubElement(prod, "cEAN").text = ""  # Código de barras (vazio)
            etree.SubElement(prod, "xProd").text = item.get('descricao', '')
            
            # NCM - limpar formatação
            ncm = limpar_cnpj_cpf(item.get('ncm', ''))
            etree.SubElement(prod, "NCM").text = ncm
            
            etree.SubElement(prod, "uCom").text = item.get('unidade', 'UN')
            etree.SubElement(prod, "qCom").text = to_str(item.get('quantidade', '1'))
            etree.SubElement(prod, "vUnCom").text = to_str(item.get('valor_unitario', '0'))
            etree.SubElement(prod, "vProd").text = to_str(item.get('valor_total', '0'))
            etree.SubElement(prod, "cEANTrib").text = ""
            etree.SubElement(prod, "uTrib").text = item.get('unidade', 'UN')
            etree.SubElement(prod, "qTrib").text = to_str(item.get('quantidade', '1'))
            etree.SubElement(prod, "vUnTrib").text = to_str(item.get('valor_unitario', '0'))
            
            print(f"✅ Produto do item {i} criado")
            
            # Impostos
            imposto = etree.SubElement(det, "imposto")
            
            # ICMS
            icms = etree.SubElement(imposto, "ICMS")
            
            # Usar CST informado ou padrão
            cst_icms = item.get('cst_icms', '00')
            icms_group = etree.SubElement(icms, f"ICMS{cst_icms}")
            
            etree.SubElement(icms_group, "orig").text = to_str(item.get('origem', '0'))
            etree.SubElement(icms_group, "CST").text = cst_icms
            etree.SubElement(icms_group, "modBC").text = "3"  # Valor da operação
            
            bc_icms = item.get('bc_icms', item.get('valor_total', '0'))
            etree.SubElement(icms_group, "vBC").text = to_str(bc_icms)
            
            aliq_icms = item.get('aliquota_icms', '18.00')
            etree.SubElement(icms_group, "pICMS").text = to_str(aliq_icms)
            
            valor_icms = item.get('valor_icms', '0')
            etree.SubElement(icms_group, "vICMS").text = to_str(valor_icms)
            
            print(f"✅ Item {i} completo: {item.get('descricao', 'Sem descrição')}")
        
        print(f"✅ TODOS OS {len(items_data)} ITENS CRIADOS")
        
        # ===== TOTAL =====
        total = etree.SubElement(inf_nfe, "total")
        icms_tot = etree.SubElement(total, "ICMSTot")
        
        # Calcular totais
        valor_total_produtos = sum(float(item.get('valor_total', 0)) for item in items_data)
        valor_total_icms = sum(float(item.get('valor_icms', 0)) for item in items_data)
        
        etree.SubElement(icms_tot, "vBC").text = to_str(valor_total_produtos)
        etree.SubElement(icms_tot, "vICMS").text = to_str(valor_total_icms)
        etree.SubElement(icms_tot, "vICMSDeson").text = "0.00"
        etree.SubElement(icms_tot, "vBCST").text = "0.00"
        etree.SubElement(icms_tot, "vST").text = "0.00"
        etree.SubElement(icms_tot, "vProd").text = to_str(valor_total_produtos)
        etree.SubElement(icms_tot, "vFrete").text = "0.00"
        etree.SubElement(icms_tot, "vSeg").text = "0.00"
        etree.SubElement(icms_tot, "vDesc").text = "0.00"
        etree.SubElement(icms_tot, "vII").text = "0.00"
        etree.SubElement(icms_tot, "vIPI").text = "0.00"
        etree.SubElement(icms_tot, "vPIS").text = "0.00"
        etree.SubElement(icms_tot, "vCOFINS").text = "0.00"
        etree.SubElement(icms_tot, "vOutro").text = "0.00"
        etree.SubElement(icms_tot, "vNF").text = to_str(valor_total_produtos)
        
        print("✅ TOTAL criado")
        
        # ===== TRANSPORTE =====
        transp = etree.SubElement(inf_nfe, "transp")
        etree.SubElement(transp, "modFrete").text = to_str(form_data.get('modFrete', '9'))
        
        print("✅ TRANSP criado")
        
        # ===== PAGAMENTO =====
        pag = etree.SubElement(inf_nfe, "pag")
        det_pag = etree.SubElement(pag, "detPag")
        etree.SubElement(det_pag, "tPag").text = to_str(form_data.get('formaPagamento', '01'))
        etree.SubElement(det_pag, "vPag").text = to_str(form_data.get('valorPagamento', '0'))
        
        print("✅ PAG criado")
        
        # ===== INFORMAÇÕES ADICIONAIS =====
        if form_data.get('infCpl'):
            inf_adic = etree.SubElement(inf_nfe, "infAdic")
            etree.SubElement(inf_adic, "infCpl").text = form_data.get('infCpl')
        
        # ✅ GERAR XML COMO STRING - CORRIGIDO
        try:
            # Primeiro, gerar sem declaração XML
            xml_bytes = etree.tostring(nfe_proc, 
                                     encoding='utf-8', 
                                     pretty_print=True,
                                     xml_declaration=True)
            
            # Converter bytes para string
            xml_str = xml_bytes.decode('utf-8')
            
            print(f"✅ XML serializado com sucesso: {len(xml_str)} caracteres")
            print(f"🔍 XML Preview (primeiros 300 chars):")
            print(xml_str[:300])
            
            return xml_str
            
        except Exception as e:
            print(f"❌ Erro na serialização XML: {e}")
            # Fallback: gerar sem declaração XML
            try:
                xml_str = etree.tostring(nfe_proc, 
                                       encoding='unicode', 
                                       pretty_print=True)
                
                # Adicionar declaração XML manualmente
                xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
                
                print(f"✅ XML gerado com fallback: {len(xml_str)} caracteres")
                return xml_str
                
            except Exception as e2:
                print(f"❌ Erro no fallback: {e2}")
                raise
        
    except Exception as e:
        print(f"❌ Erro na geração do XML: {e}")
        import traceback
        traceback.print_exc()
        raise

def gerar_chave_nfe(emitente_data, form_data):
    """
    Gera chave de acesso da NFe (simplificada)
    """
    try:
        print("🔑 Gerando chave de acesso...")
        
        uf_codigo = get_uf_ibge_code(emitente_data.get('uf', 'SP'))
        aamm = datetime.now().strftime('%y%m')
        cnpj = limpar_cnpj_cpf(emitente_data.get('cnpj', ''))[:14]
        modelo = "55"
        serie = str(form_data.get('serie', '1')).zfill(3)
        numero = "000000001"  # Simplificado
        codigo_numerico = str(uuid.uuid4().int)[:8]
        
        # Montar chave sem DV
        chave_sem_dv = f"{uf_codigo:02d}{aamm}{cnpj}{modelo}{serie}{numero}{codigo_numerico}"
        
        print(f"🔧 Chave sem DV: {chave_sem_dv} (tamanho: {len(chave_sem_dv)})")
        
        # ✅ CORRIGIR CÁLCULO DO DV
        # Calcular DV usando operação módulo correta
        soma_digitos = sum(int(d) for d in chave_sem_dv)
        dv = soma_digitos % 10  # ✅ OPERAÇÃO MÓDULO CORRIGIDA
        
        chave_completa = chave_sem_dv + str(dv)
        
        print(f"🔑 Chave completa: {chave_completa}")
        print(f"✅ DV calculado: {dv}")
        
        return chave_completa
        
    except Exception as e:
        print(f"❌ Erro ao gerar chave: {e}")
        import traceback
        traceback.print_exc()
        # Chave de fallback para testes
        return "35" + datetime.now().strftime('%y%m') + "12345678000100" + "55" + "001" + "000000001" + "12345678" + "1"

def sign_xml(xml_content, certificado_data):
    """
    Assina o XML da NFe (simulado para testes)
    """
    print("✍️ Simulando assinatura do XML...")
    
    # Para testes, apenas adicionar uma tag de assinatura simulada
    assinatura_simulada = """
    <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
        <SignedInfo>
            <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
            <SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
        </SignedInfo>
        <SignatureValue>ASSINATURA_SIMULADA_PARA_TESTES</SignatureValue>
    </Signature>
    """
    
    # Inserir assinatura antes do fechamento da tag NFe
    xml_assinado = xml_content.replace('</NFe>', f'{assinatura_simulada}</NFe>')
    
    print("✅ XML assinado (simulado)")
    return xml_assinado

def send_to_sefaz(xml_assinado, certificado_data, cnpj_emitente, tp_amb=2):
    """
    Envia XML para SEFAZ (simulado para testes)
    """
    print("📤 Simulando envio para SEFAZ...")
    
    # Simular resposta da SEFAZ
    resultado = {
        'status': '100',
        'mensagem': 'Autorizado o uso da NF-e',
        'chave_acesso': gerar_chave_nfe({'uf': 'SP', 'cnpj': cnpj_emitente}, {'serie': '1'}),
        'protocolo': f'135{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'data_autorizacao': datetime.now().isoformat(),
        'xml_protocolo': xml_assinado
    }
    
    print(f"✅ Resposta SEFAZ simulada: {resultado['status']} - {resultado['mensagem']}")
    return resultado