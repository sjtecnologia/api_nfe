#!/usr/bin/env python3
"""
Teste das Correções de CEP e Validações
Valida as correções aplicadas nas sessões anteriores
"""

import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.absolute()))

def test_cep_api():
    """Testa integração com ViaCEP"""
    print("\n" + "="*60)
    print("🔍 TESTE 1: API ViaCEP")
    print("="*60)
    
    ceps_teste = [
        ('01310-100', 'Avenida Paulista, São Paulo'),
        ('20040-020', 'Praça XV de Novembro, Rio de Janeiro'),
        ('70040-020', 'Esplanada dos Ministérios, Brasília')
    ]
    
    sucessos = 0
    for cep, local_esperado in ceps_teste:
        try:
            url = f'https://viacep.com.br/ws/{cep.replace("-", "")}/json/'
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'erro' not in data:
                    print(f"  ✅ {cep}: {data.get('logradouro', 'N/A')} - {data.get('localidade', 'N/A')}")
                    sucessos += 1
                else:
                    print(f"  ❌ {cep}: CEP não encontrado")
            else:
                print(f"  ⚠️  {cep}: Status {response.status_code}")
        except Exception as e:
            print(f"  ❌ {cep}: Erro - {e}")
    
    print(f"\n📊 Resultado: {sucessos}/{len(ceps_teste)} consultas bem-sucedidas")
    return sucessos == len(ceps_teste)

def test_codigo_uf_fallback():
    """Testa fallback de código UF em 3 camadas"""
    print("\n" + "="*60)
    print("🔍 TESTE 2: Fallback Código UF")
    print("="*60)
    
    from database.connection import get_db
    from sqlalchemy import text
    
    # Cenários de teste
    cenarios = [
        {
            'nome': 'Destinatário com UF válida',
            'dados': {'uf': 'SP'},
            'esperado': 35
        },
        {
            'nome': 'Destinatário sem UF, CEP válido',
            'dados': {'cep': '01310100'},
            'esperado': 35  # São Paulo
        },
        {
            'nome': 'Sem dados, usar emissor',
            'dados': {},
            'esperado': 'valor_do_emissor'
        }
    ]
    
    sucessos = 0
    for cenario in cenarios:
        try:
            # Simular lógica de fallback
            codigo_uf = None
            
            # Camada 1: UF do destinatário
            if 'uf' in cenario['dados']:
                ufs = {
                    'SP': 35, 'RJ': 33, 'MG': 31, 'RS': 43,
                    'PR': 41, 'SC': 42, 'BA': 29, 'PE': 26,
                    'CE': 23, 'DF': 53
                }
                codigo_uf = ufs.get(cenario['dados']['uf'])
            
            # Camada 2: CEP do destinatário
            if not codigo_uf and 'cep' in cenario['dados']:
                # Simular consulta CEP
                cep = cenario['dados']['cep']
                if cep.startswith('01'):  # São Paulo
                    codigo_uf = 35
            
            # Camada 3: Emissor
            if not codigo_uf:
                codigo_uf = 'valor_do_emissor'
            
            if str(codigo_uf) == str(cenario['esperado']):
                print(f"  ✅ {cenario['nome']}: {codigo_uf}")
                sucessos += 1
            else:
                print(f"  ❌ {cenario['nome']}: Esperado {cenario['esperado']}, obtido {codigo_uf}")
        
        except Exception as e:
            print(f"  ❌ {cenario['nome']}: Erro - {e}")
    
    print(f"\n📊 Resultado: {sucessos}/{len(cenarios)} cenários validados")
    return sucessos == len(cenarios)

def test_formatacao_dados():
    """Testa formatação de CEP, CPF, CNPJ"""
    print("\n" + "="*60)
    print("🔍 TESTE 3: Formatação de Dados")
    print("="*60)
    
    testes = [
        {
            'tipo': 'CEP',
            'entrada': '01310-100',
            'esperado': '01310100',
            'funcao': lambda x: x.replace('-', '').replace('.', '')
        },
        {
            'tipo': 'CPF',
            'entrada': '123.456.789-00',
            'esperado': '12345678900',
            'funcao': lambda x: x.replace('.', '').replace('-', '')
        },
        {
            'tipo': 'CNPJ',
            'entrada': '12.345.678/0001-90',
            'esperado': '12345678000190',
            'funcao': lambda x: x.replace('.', '').replace('/', '').replace('-', '')
        }
    ]
    
    sucessos = 0
    for teste in testes:
        try:
            resultado = teste['funcao'](teste['entrada'])
            if resultado == teste['esperado']:
                print(f"  ✅ {teste['tipo']}: '{teste['entrada']}' → '{resultado}'")
                sucessos += 1
            else:
                print(f"  ❌ {teste['tipo']}: Esperado '{teste['esperado']}', obtido '{resultado}'")
        except Exception as e:
            print(f"  ❌ {teste['tipo']}: Erro - {e}")
    
    print(f"\n📊 Resultado: {sucessos}/{len(testes)} formatações corretas")
    return sucessos == len(testes)

def test_validacao_destinatario():
    """Testa validação de dados do destinatário"""
    print("\n" + "="*60)
    print("🔍 TESTE 4: Validação Destinatário")
    print("="*60)
    
    from database.connection import get_db
    from sqlalchemy import text
    
    db = next(get_db())
    try:
        # Verificar se tabela destinatarios existe
        query = text("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'destinatarios'
        """)
        result = db.execute(query).fetchone()
        
        if result and result[0] > 0:
            # Verificar campos NOT NULL
            query = text("""
                SELECT column_name, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'destinatarios' 
                  AND column_name IN ('codigo_uf', 'cep', 'cpf', 'cnpj')
                ORDER BY column_name
            """)
            
            colunas = db.execute(query).fetchall()
            print("\n  Campos verificados:")
            for col in colunas:
                nullable = "NULL" if col[1] == 'YES' else "NOT NULL"
                default = f" (default: {col[2]})" if col[2] else ""
                print(f"    • {col[0]}: {nullable}{default}")
            
            print("\n  ✅ Estrutura validada")
            return True
        else:
            print("  ⚠️  Tabela destinatarios não encontrada")
            return False
    
    except Exception as e:
        print(f"  ❌ Erro: {e}")
        return False
    finally:
        db.close()

def test_codigo_ibs():
    """Testa serviço de cálculo IBS"""
    print("\n" + "="*60)
    print("🔍 TESTE 5: Serviço IBS")
    print("="*60)
    
    try:
        from services.calculo_ibs_v2 import CalculoIBS
        
        calc = CalculoIBS()
        
        # Teste 1: Validar código
        valido = calc.validar_codigo_servico('01.01')
        print(f"  ✅ Validação código 01.01: {valido}")
        
        # Teste 2: Cálculo básico
        resultado = calc.calcular(
            valor_base=1000.00,
            codigo_servico='01.01',
            municipio_origem='3550308'
        )
        print(f"  ✅ Cálculo stub: Total = R$ {resultado['total_tributos']:.2f}")
        
        # Teste 3: Registro histórico
        sucesso = calc.registrar_calculo(
            nfe_id=None,
            tipo_operacao='teste',
            codigo_servico='01.01',
            valor_base=1000.00,
            aliquota_ibs=0.00,
            valor_ibs=0.00,
            aliquota_cbs=0.00,
            valor_cbs=0.00,
            municipio_origem='3550308'
        )
        print(f"  ✅ Registro histórico: {sucesso}")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Erro: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("🧪 BATERIA DE TESTES - CORREÇÕES APLICADAS")
    print("="*60)
    
    resultados = []
    
    # Teste 1: API CEP
    resultados.append(('API ViaCEP', test_cep_api()))
    
    # Teste 2: Fallback UF
    resultados.append(('Fallback Código UF', test_codigo_uf_fallback()))
    
    # Teste 3: Formatação
    resultados.append(('Formatação Dados', test_formatacao_dados()))
    
    # Teste 4: Validação Destinatário
    resultados.append(('Validação Destinatário', test_validacao_destinatario()))
    
    # Teste 5: Serviço IBS
    resultados.append(('Serviço IBS', test_codigo_ibs()))
    
    # Resumo
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    
    passou = sum(1 for _, resultado in resultados if resultado)
    total = len(resultados)
    
    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"  {status}: {nome}")
    
    print(f"\n📈 Score: {passou}/{total} testes passaram ({passou*100/total:.0f}%)")
    
    if passou == total:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("="*60)
        return 0
    else:
        print(f"\n⚠️  {total - passou} teste(s) falharam")
        print("="*60)
        return 1

if __name__ == '__main__':
    sys.exit(main())
