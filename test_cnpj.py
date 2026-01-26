import re

def calcular_cnpj_correto(cnpj_base):
    cnpj = re.sub(r'[^0-9]', '', str(cnpj_base))
    base = cnpj[:12]
    
    # Primeiro dígito
    soma = 0
    pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    for i in range(12):
        soma += int(base[i]) * pesos[i]
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    # Segundo dígito
    base_com_dv1 = base + str(digito1)
    soma = 0
    pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    for i in range(13):
        soma += int(base_com_dv1[i]) * pesos[i]
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    return base + str(digito1) + str(digito2)

cnpj_invalido = '46840224000102'
cnpj_correto = calcular_cnpj_correto(cnpj_invalido)

print(f'❌ CNPJ cadastrado (INVÁLIDO): {cnpj_invalido}')
print(f'✅ CNPJ correto seria:         {cnpj_correto}')
print(f'')
print(f'Formatado: {cnpj_correto[:2]}.{cnpj_correto[2:5]}.{cnpj_correto[5:8]}/{cnpj_correto[8:12]}-{cnpj_correto[12:14]}')
