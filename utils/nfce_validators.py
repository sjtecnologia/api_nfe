"""
Validadores específicos para NFC-e (Nota Fiscal de Consumidor Eletrônica)
"""

from typing import Dict, List, Any
import re


def validar_dados_nfce(dados: Dict[str, Any]) -> List[str]:
    """
    Valida dados de uma NFC-e antes da emissão
    
    Args:
        dados: Dicionário com dados da NFC-e
        
    Returns:
        Lista de erros encontrados (vazia se válido)
    """
    erros = []
    
    # 1. Validar Emitente
    if not dados.get('emitente_id'):
        erros.append('ID do emitente é obrigatório')
    
    # 2. Validar Produtos
    produtos = dados.get('produtos', [])
    if not produtos:
        erros.append('NFC-e deve ter pelo menos um produto')
    elif len(produtos) > 500:  # Limite SEFAZ
        erros.append('NFC-e não pode ter mais de 500 produtos')
    
    valor_total = 0
    for idx, produto in enumerate(produtos, 1):
        # Validar estrutura do produto
        if not produto.get('produto'):
            erros.append(f'Produto {idx}: Objeto produto não encontrado')
            continue
            
        if not produto.get('quantidade') or produto['quantidade'] <= 0:
            erros.append(f'Produto {idx}: Quantidade inválida')
        
        if not produto.get('valor_unitario') or produto['valor_unitario'] <= 0:
            erros.append(f'Produto {idx}: Valor unitário inválido')
        
        # Validar NCM
        ncm_obj = produto['produto'].ncm if hasattr(produto['produto'], 'ncm') and produto['produto'].ncm else None
        ncm = ncm_obj.codigo if ncm_obj and hasattr(ncm_obj, 'codigo') else None
        if not ncm or len(ncm.replace('.', '')) != 8:
            erros.append(f'Produto {idx}: NCM inválido ou não informado')
        
        # Validar CFOP
        cfop_obj = produto['produto'].cfop if hasattr(produto['produto'], 'cfop') and produto['produto'].cfop else None
        cfop = cfop_obj.cfop if cfop_obj and hasattr(cfop_obj, 'cfop') else None
        if not cfop:
            erros.append(f'Produto {idx}: CFOP não informado')
        
        # Calcular valor
        quantidade = float(produto.get('quantidade', 0))
        valor_unitario = float(produto.get('valor_unitario', 0))
        desconto = float(produto.get('desconto', 0))
        valor_produto = (quantidade * valor_unitario) - desconto
        
        if valor_produto < 0:
            erros.append(f'Produto {idx}: Desconto não pode ser maior que o valor total')
        
        valor_total += valor_produto
    
    # 3. Validar Valor Total (limite NFC-e pode variar por estado)
    # Padrão: verificar se não é negativo
    if valor_total < 0:
        erros.append('Valor total da NFC-e não pode ser negativo')
    
    # Limite exemplo: R$ 10.000,00 (varia por UF)
    LIMITE_VALOR_NFCE = 10000.00
    if valor_total > LIMITE_VALOR_NFCE:
        erros.append(f'Valor total excede o limite de R$ {LIMITE_VALOR_NFCE:.2f} para NFC-e. Use NF-e.')
    
    # 4. Validar Destinatário (opcional, mas se informado deve ser válido)
    destinatario = dados.get('destinatario', {})
    if destinatario:
        cpf_cnpj = destinatario.get('cpf_cnpj', '').strip()
        
        if cpf_cnpj:
            # Remove formatação
            cpf_cnpj_limpo = re.sub(r'[^\d]', '', cpf_cnpj)
            
            if len(cpf_cnpj_limpo) == 11:
                # Validar CPF
                if not validar_cpf(cpf_cnpj_limpo):
                    erros.append('CPF do destinatário inválido')
            elif len(cpf_cnpj_limpo) == 14:
                # Validar CNPJ
                if not validar_cnpj(cpf_cnpj_limpo):
                    erros.append('CNPJ do destinatário inválido')
            else:
                erros.append('CPF/CNPJ do destinatário com tamanho inválido')
        
        # Email opcional
        email = destinatario.get('email', '').strip()
        if email and not validar_email(email):
            erros.append('E-mail do destinatário inválido')
    
    # 5. Validar Forma de Pagamento
    forma_pagamento = dados.get('forma_pagamento')
    if not forma_pagamento:
        erros.append('Forma de pagamento é obrigatória')
    else:
        formas_validas = [
            '01',  # Dinheiro
            '02',  # Cheque
            '03',  # Cartão de Crédito
            '04',  # Cartão de Débito
            '05',  # Crédito Loja
            '10',  # Vale Alimentação
            '11',  # Vale Refeição
            '12',  # Vale Presente
            '13',  # Vale Combustível
            '15',  # Boleto Bancário
            '16',  # PIX
            '17',  # Transferência Bancária
            '18',  # Programa de fidelidade
            '19',  # Sem pagamento
            '90',  # Sem pagamento
            '99'   # Outros
        ]
        if forma_pagamento not in formas_validas:
            erros.append(f'Forma de pagamento inválida: {forma_pagamento}')
    
    # 6. Validar Valor Pago e Troco (para dinheiro)
    if forma_pagamento == '01':  # Dinheiro
        valor_pago = dados.get('valor_pago', 0)
        if valor_pago < valor_total:
            erros.append('Valor pago deve ser maior ou igual ao total da venda')
        
        troco = dados.get('troco', 0)
        troco_calculado = valor_pago - valor_total
        
        if abs(troco - troco_calculado) > 0.01:  # Tolerância de 1 centavo
            erros.append(f'Troco incorreto. Esperado: R$ {troco_calculado:.2f}')
    
    # 7. Validar Informações Adicionais (tamanho)
    info_adicionais = dados.get('informacoes_adicionais', '')
    if len(info_adicionais) > 5000:
        erros.append('Informações adicionais excedem 5000 caracteres')
    
    return erros


def validar_nfce_para_cancelamento(nfce, horas_limite: int = 24) -> List[str]:
    """
    Valida se uma NFC-e pode ser cancelada
    
    Args:
        nfce: Objeto NFeEmitidas (NFC-e)
        horas_limite: Limite de horas para cancelamento (padrão 24h)
        
    Returns:
        Lista de erros (vazia se pode cancelar)
    """
    from datetime import datetime, timedelta
    
    erros = []
    
    # 1. Verificar se já está cancelada
    if nfce.status == 'Cancelada':
        erros.append('NFC-e já está cancelada')
        return erros
    
    # 2. Verificar se está autorizada
    if nfce.status != 'Autorizada':
        erros.append(f'Apenas NFC-e autorizadas podem ser canceladas. Status atual: {nfce.status}')
        return erros
    
    # 3. Verificar prazo
    if nfce.data_autorizacao:
        prazo_limite = nfce.data_autorizacao + timedelta(hours=horas_limite)
        if datetime.now() > prazo_limite:
            tempo_decorrido = datetime.now() - nfce.data_autorizacao
            horas_decorridas = tempo_decorrido.total_seconds() / 3600
            erros.append(f'Prazo de cancelamento expirado ({horas_decorridas:.1f}h). Limite: {horas_limite}h')
    
    # 4. Verificar se é NFC-e (modelo 65)
    if nfce.modelo != '65':
        erros.append(f'Este não é um documento NFC-e. Modelo: {nfce.modelo}')
    
    return erros


def validar_cpf(cpf: str) -> bool:
    """
    Valida CPF (apenas dígitos)
    
    Args:
        cpf: CPF com 11 dígitos
        
    Returns:
        True se válido
    """
    if not cpf or len(cpf) != 11:
        return False
    
    # CPFs inválidos conhecidos
    if cpf in ['00000000000', '11111111111', '22222222222', '33333333333',
               '44444444444', '55555555555', '66666666666', '77777777777',
               '88888888888', '99999999999']:
        return False
    
    # Validar primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = 11 - (soma % 11)
    if digito1 >= 10:
        digito1 = 0
    
    if int(cpf[9]) != digito1:
        return False
    
    # Validar segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = 11 - (soma % 11)
    if digito2 >= 10:
        digito2 = 0
    
    if int(cpf[10]) != digito2:
        return False
    
    return True


def validar_cnpj(cnpj: str) -> bool:
    """
    Valida CNPJ (apenas dígitos)
    
    Args:
        cnpj: CNPJ com 14 dígitos
        
    Returns:
        True se válido
    """
    if not cnpj or len(cnpj) != 14:
        return False
    
    # CNPJs inválidos conhecidos
    if cnpj in ['00000000000000', '11111111111111', '22222222222222', '33333333333333',
                '44444444444444', '55555555555555', '66666666666666', '77777777777777',
                '88888888888888', '99999999999999']:
        return False
    
    # Validar primeiro dígito verificador
    multiplicadores1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores1[i] for i in range(12))
    digito1 = 11 - (soma % 11)
    if digito1 >= 10:
        digito1 = 0
    
    if int(cnpj[12]) != digito1:
        return False
    
    # Validar segundo dígito verificador
    multiplicadores2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores2[i] for i in range(13))
    digito2 = 11 - (soma % 11)
    if digito2 >= 10:
        digito2 = 0
    
    if int(cnpj[13]) != digito2:
        return False
    
    return True


def validar_email(email: str) -> bool:
    """
    Valida formato de e-mail
    
    Args:
        email: Endereço de e-mail
        
    Returns:
        True se válido
    """
    if not email:
        return False
    
    # Regex simples para validação de e-mail
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validar_valor_nfce_por_uf(valor: float, uf: str) -> tuple[bool, str]:
    """
    Valida valor da NFC-e conforme limite do estado
    
    Limites por UF (valores podem variar - verificar legislação atual):
    - Padrão: R$ 10.000,00
    - Alguns estados: até R$ 50.000,00
    
    Args:
        valor: Valor total da NFC-e
        uf: Sigla do estado (ex: 'SP', 'RJ')
        
    Returns:
        (válido, mensagem)
    """
    # Limites por UF (exemplo - verificar legislação atual de cada estado)
    limites_uf = {
        'SP': 10000.00,
        'RJ': 10000.00,
        'MG': 10000.00,
        'ES': 10000.00,
        'BA': 10000.00,
        'PR': 10000.00,
        'SC': 10000.00,
        'RS': 10000.00,
        'GO': 10000.00,
        'MT': 10000.00,
        'MS': 10000.00,
        'DF': 10000.00,
    }
    
    limite = limites_uf.get(uf, 10000.00)
    
    if valor > limite:
        return False, f'Valor R$ {valor:.2f} excede limite de R$ {limite:.2f} para NFC-e em {uf}'
    
    return True, 'Valor válido'


def validar_quantidade_itens_nfce(num_itens: int) -> tuple[bool, str]:
    """
    Valida quantidade de itens na NFC-e
    
    Args:
        num_itens: Número de itens
        
    Returns:
        (válido, mensagem)
    """
    if num_itens < 1:
        return False, 'NFC-e deve ter pelo menos 1 item'
    
    if num_itens > 500:
        return False, 'NFC-e não pode ter mais de 500 itens (limite SEFAZ)'
    
    return True, 'Quantidade de itens válida'


def validar_justificativa_cancelamento(justificativa: str) -> tuple[bool, str]:
    """
    Valida justificativa de cancelamento
    
    Args:
        justificativa: Texto da justificativa
        
    Returns:
        (válido, mensagem)
    """
    if not justificativa or not justificativa.strip():
        return False, 'Justificativa é obrigatória'
    
    justificativa = justificativa.strip()
    
    if len(justificativa) < 15:
        return False, 'Justificativa deve ter pelo menos 15 caracteres'
    
    if len(justificativa) > 255:
        return False, 'Justificativa não pode exceder 255 caracteres'
    
    # Validar caracteres especiais problemáticos
    caracteres_invalidos = ['<', '>', '&', '"', "'"]
    for char in caracteres_invalidos:
        if char in justificativa:
            return False, f'Justificativa contém caractere inválido: {char}'
    
    return True, 'Justificativa válida'


def formatar_cpf_cnpj(valor: str) -> str:
    """
    Formata CPF ou CNPJ
    
    Args:
        valor: CPF/CNPJ sem formatação
        
    Returns:
        CPF/CNPJ formatado
    """
    # Remove caracteres não numéricos
    numeros = re.sub(r'[^\d]', '', valor)
    
    if len(numeros) == 11:
        # Formatar CPF: 000.000.000-00
        return f'{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}'
    elif len(numeros) == 14:
        # Formatar CNPJ: 00.000.000/0000-00
        return f'{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}'
    else:
        return valor


# Exemplo de uso
if __name__ == '__main__':
    # Teste de validação
    dados_teste = {
        'emitente_id': 1,
        'produtos': [
            {
                'produto': type('obj', (object,), {
                    'ncm_codigo': '9401.30.00',
                    'cfop_padrao': '5102'
                })(),
                'quantidade': 2,
                'valor_unitario': 150.00,
                'desconto': 10.00
            }
        ],
        'forma_pagamento': '01',
        'valor_pago': 300.00,
        'troco': 10.00,
        'destinatario': {
            'cpf_cnpj': '12345678901',
            'email': 'teste@teste.com'
        }
    }
    
    erros = validar_dados_nfce(dados_teste)
    
    if erros:
        print('❌ Erros encontrados:')
        for erro in erros:
            print(f'  - {erro}')
    else:
        print('✅ Dados válidos!')
    
    # Teste de validadores individuais
    print(f'\nCPF 12345678901: {validar_cpf("12345678901")}')
    print(f'Email teste@teste.com: {validar_email("teste@teste.com")}')
    print(f'Formatado: {formatar_cpf_cnpj("12345678901")}')
