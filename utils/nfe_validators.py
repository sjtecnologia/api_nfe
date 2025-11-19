import re
from datetime import datetime
from decimal import Decimal

def validar_cnpj(cnpj):
    """
    Valida CNPJ brasileiro
    """
    if not cnpj:
        return False
    
    # Remove caracteres não numéricos
    cnpj = re.sub(r'[^0-9]', '', str(cnpj))
    
    # Verifica se tem 14 dígitos
    if len(cnpj) != 14:
        return False
    
    # Verifica se não são todos os dígitos iguais
    if cnpj == cnpj[0] * 14:
        return False
    
    # Calcula o primeiro dígito verificador
    soma = 0
    peso = 5
    for i in range(12):
        soma += int(cnpj[i]) * peso
        peso -= 1
        if peso < 2:
            peso = 9
    
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    # Calcula o segundo dígito verificador
    soma = 0
    peso = 6
    for i in range(13):
        soma += int(cnpj[i]) * peso
        peso -= 1
        if peso < 2:
            peso = 9
    
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    # Verifica se os dígitos calculados conferem
    return cnpj[-2:] == f"{digito1}{digito2}"

def validar_cpf(cpf):
    """
    Valida CPF brasileiro
    """
    if not cpf:
        return False
    
    # Remove caracteres não numéricos
    cpf = re.sub(r'[^0-9]', '', str(cpf))
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        return False
    
    # Verifica se não são todos os dígitos iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Calcula o primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    # Calcula o segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    # Verifica se os dígitos calculados conferem
    return cpf[-2:] == f"{digito1}{digito2}"

def validar_dados_nfe(form_data, emitente_data, destinatario_data, nfe_items):
    """
    Valida todos os dados necessários para emissão da NFe
    """
    erros = []
    
    print(f"🔍 VALIDAÇÃO - CNPJ Emitente recebido: '{emitente_data.get('cnpj')}'")
    print(f"🔍 VALIDAÇÃO - Tipo do CNPJ: {type(emitente_data.get('cnpj'))}")
    
    # ✅ VALIDAÇÕES DO EMITENTE
    cnpj_emitente = emitente_data.get('cnpj', '').strip()
    print(f"🔍 VALIDAÇÃO - CNPJ após strip: '{cnpj_emitente}'")
    
    if not cnpj_emitente:
        erros.append("CNPJ do emitente é obrigatório")
    elif not validar_cnpj(cnpj_emitente):
        erros.append(f"CNPJ do emitente é inválido: {cnpj_emitente}")
    else:
        print(f"✅ CNPJ do emitente válido: {cnpj_emitente}")
    
    if not emitente_data.get('razao_social'):
        erros.append("Razão social do emitente é obrigatória")
    
    if not emitente_data.get('inscricao_estadual'):
        erros.append("Inscrição estadual do emitente é obrigatória")
    
    if not emitente_data.get('logradouro'):
        erros.append("Endereço do emitente é obrigatório")
    
    if not emitente_data.get('uf'):
        erros.append("UF do emitente é obrigatória")
    
    # ✅ VALIDAÇÕES DO DESTINATÁRIO
    if not destinatario_data:
        erros.append("Destinatário é obrigatório")
    else:
        cpf_cnpj_dest = destinatario_data.get('cpf_cnpj', '').strip()
        print(f"🔍 VALIDAÇÃO - CPF/CNPJ Destinatário: '{cpf_cnpj_dest}'")
        
        if not cpf_cnpj_dest:
            erros.append("CPF/CNPJ do destinatário é obrigatório")
        else:
            # Verifica se é CPF (11 dígitos) ou CNPJ (14 dígitos)
            cpf_cnpj_limpo = re.sub(r'[^0-9]', '', cpf_cnpj_dest)
            if len(cpf_cnpj_limpo) == 11:
                if not validar_cpf(cpf_cnpj_dest):
                    erros.append(f"CPF do destinatário é inválido: {cpf_cnpj_dest}")
                else:
                    print(f"✅ CPF do destinatário válido: {cpf_cnpj_dest}")
            elif len(cpf_cnpj_limpo) == 14:
                if not validar_cnpj(cpf_cnpj_dest):
                    erros.append(f"CNPJ do destinatário é inválido: {cpf_cnpj_dest}")
                else:
                    print(f"✅ CNPJ do destinatário válido: {cpf_cnpj_dest}")
            else:
                erros.append(f"CPF/CNPJ do destinatário deve ter 11 ou 14 dígitos: {cpf_cnpj_dest}")
        
        if not destinatario_data.get('nome_razao_social'):
            erros.append("Nome/Razão social do destinatário é obrigatório")
        
        if not destinatario_data.get('logradouro'):
            erros.append("Endereço do destinatário é obrigatório")
        
        if not destinatario_data.get('uf'):
            erros.append("UF do destinatário é obrigatória")
    
    # ✅ VALIDAÇÕES DOS DADOS GERAIS
    if not form_data.get('natOp'):
        erros.append("Natureza da operação é obrigatória")
    
    if not form_data.get('serie'):
        erros.append("Série da NFe é obrigatória")
    else:
        try:
            serie = int(form_data.get('serie'))
            if serie < 1 or serie > 999:
                erros.append("Série deve estar entre 1 e 999")
        except ValueError:
            erros.append("Série deve ser um número válido")
    
    # ✅ VALIDAÇÕES DOS ITENS
    if not nfe_items:
        erros.append("Pelo menos um item deve ser informado")
    else:
        for i, item in enumerate(nfe_items, 1):
            item_prefix = f"Item {i}: "
            
            if not item.get('descricao'):
                erros.append(f"{item_prefix}Descrição é obrigatória")
            
            if not item.get('quantidade'):
                erros.append(f"{item_prefix}Quantidade é obrigatória")
            else:
                try:
                    qtd = float(item.get('quantidade'))
                    if qtd <= 0:
                        erros.append(f"{item_prefix}Quantidade deve ser maior que zero")
                except ValueError:
                    erros.append(f"{item_prefix}Quantidade deve ser um número válido")
            
            if not item.get('valor_unitario'):
                erros.append(f"{item_prefix}Valor unitário é obrigatório")
            else:
                try:
                    valor = float(item.get('valor_unitario'))
                    if valor <= 0:
                        erros.append(f"{item_prefix}Valor unitário deve ser maior que zero")
                except ValueError:
                    erros.append(f"{item_prefix}Valor unitário deve ser um número válido")
            
            if not item.get('ncm'):
                erros.append(f"{item_prefix}NCM é obrigatório")
            elif len(re.sub(r'[^0-9]', '', item.get('ncm', ''))) != 8:
                erros.append(f"{item_prefix}NCM deve ter 8 dígitos")
            
            if not item.get('cfop'):
                erros.append(f"{item_prefix}CFOP é obrigatório")
            elif len(re.sub(r'[^0-9]', '', item.get('cfop', ''))) != 4:
                erros.append(f"{item_prefix}CFOP deve ter 4 dígitos")
            
            # Validar CST ICMS ou CSOSN (um dos dois é obrigatório)
            if not item.get('cst_icms') and not item.get('csosn'):
                erros.append(f"{item_prefix}CST ICMS ou CSOSN é obrigatório")
            
            if item.get('origem') is None or item.get('origem') == '':
                erros.append(f"{item_prefix}Origem da mercadoria é obrigatória")
    
    # ✅ VALIDAÇÃO DO PAGAMENTO
    if not form_data.get('formaPagamento'):
        erros.append("Forma de pagamento é obrigatória")
    
    if not form_data.get('valorPagamento'):
        erros.append("Valor do pagamento é obrigatório")
    else:
        try:
            valor_pag = float(form_data.get('valorPagamento'))
            if valor_pag <= 0:
                erros.append("Valor do pagamento deve ser maior que zero")
        except ValueError:
            erros.append("Valor do pagamento deve ser um número válido")
    
    print(f"🔍 VALIDAÇÃO FINAL - {len(erros)} erros encontrados")
    if erros:
        for erro in erros:
            print(f"❌ {erro}")
    
    return erros

def validar_xml_nfe(xml_content):
    """
    Valida o XML da NFe gerado
    """
    erros = []
    
    if not xml_content:
        erros.append("XML não foi gerado")
        return False, erros
    
    print(f"🔍 VALIDAÇÃO XML - Tamanho: {len(xml_content)} caracteres")
    
    # Converter para minúsculas para validação case-insensitive
    xml_lower = xml_content.lower()
    
    # ✅ VALIDAÇÕES BÁSICAS DO XML - CORRIGIDAS
    if '<nfe>' not in xml_lower and '<nfe ' not in xml_lower:
        erros.append("XML não contém tag NFe")
    else:
        print("✅ Tag NFe encontrada")
    
    if '<emit>' not in xml_lower:
        erros.append("XML não contém dados do emitente")
    else:
        print("✅ Dados do emitente encontrados")
    
    if '<dest>' not in xml_lower:
        erros.append("XML não contém dados do destinatário")
    else:
        print("✅ Dados do destinatário encontrados")
    
    # ✅ VALIDAÇÃO DE ITENS - CORRIGIDA
    if '<det ' not in xml_lower and '<det>' not in xml_lower:
        erros.append("XML não contém itens da NFe")
        print(f"❌ Tag <det> não encontrada no XML")
        print(f"🔍 Buscando por 'det' no XML...")
        # Debug: mostrar onde deveria estar
        if 'det' in xml_lower:
            print("✅ Palavra 'det' encontrada em algum lugar")
        else:
            print("❌ Palavra 'det' não encontrada em lugar nenhum")
    else:
        print("✅ Itens da NFe encontrados")
    
    # ✅ VALIDAÇÕES ADICIONAIS
    if '<infnfe' not in xml_lower:
        erros.append("XML não contém informações da NFe (infNFe)")
    else:
        print("✅ infNFe encontrado")
    
    if '<ide>' not in xml_lower:
        erros.append("XML não contém identificação da NFe")
    else:
        print("✅ IDE encontrado")
    
    # Verificar se tem assinatura (se já foi assinado)
    has_signature = '<signature>' in xml_lower or '<ds:signature>' in xml_lower
    if has_signature:
        print("✅ Assinatura encontrada no XML")
    else:
        print("ℹ️ XML ainda não foi assinado")
    
    # ✅ DEBUG: Mostrar estrutura do XML
    print("🔍 ESTRUTURA XML DEBUG:")
    linhas = xml_content.split('\n')[:20]  # Primeiras 20 linhas
    for i, linha in enumerate(linhas, 1):
        if 'det' in linha.lower():
            print(f"  {i:2d}: {linha.strip()} ⭐")  # Marcar linhas com 'det'
        elif any(tag in linha.lower() for tag in ['nfe', 'emit', 'dest', 'ide']):
            print(f"  {i:2d}: {linha.strip()} ✅")
        else:
            print(f"  {i:2d}: {linha.strip()}")
    
    if erros:
        print(f"❌ VALIDAÇÃO XML - {len(erros)} erros encontrados:")
        for erro in erros:
            print(f"   - {erro}")
        return False, erros
    
    print(f"✅ VALIDAÇÃO XML - XML válido!")
    return True, []

def limpar_cnpj_cpf(documento):
    """
    Remove caracteres não numéricos de CPF/CNPJ
    """
    if not documento:
        return ''
    return re.sub(r'[^0-9]', '', str(documento))

def formatar_cnpj(cnpj):
    """
    Formata CNPJ no padrão XX.XXX.XXX/XXXX-XX
    """
    cnpj = limpar_cnpj_cpf(cnpj)
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
    return cnpj

def formatar_cpf(cpf):
    """
    Formata CPF no padrão XXX.XXX.XXX-XX
    """
    cpf = limpar_cnpj_cpf(cpf)
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:11]}"
    return cpf