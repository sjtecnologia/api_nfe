#!/usr/bin/env python3
"""
Teste do Serviço de Cálculo IBS
Verifica funcionamento básico do módulo services/calculo_ibs.py
"""

import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from services.calculo_ibs_v2 import CalculoIBS

def test_calculo_basico():
    """Testa cálculo básico (stub)"""
    print("\n" + "="*60)
    print("[LOG] TESTE 1: Cálculo Básico")
    print("="*60)
    
    calc = CalculoIBS()
    
    resultado = calc.calcular(
        valor_base=1000.00,
        codigo_servico='01.01',
        municipio_origem='3550308',  # São Paulo
        dhEmi='2026-01-01'
    )
    
    print(f"Valor base: R$ {resultado['valor_base']:.2f}")
    print(f"Alíquota IBS: {resultado['aliquota_ibs']:.2f}%")
    print(f"Valor IBS: R$ {resultado['valor_ibs']:.2f}")
    print(f"Alíquota CBS: {resultado['aliquota_cbs']:.2f}%")
    print(f"Valor CBS: R$ {resultado['valor_cbs']:.2f}")
    print(f"Total tributos: R$ {resultado['total_tributos']:.2f}")
    print(f"Observação: {resultado['observacoes']}")
    
    assert resultado['total_tributos'] == 0.00, "Deve retornar 0 (stub)"
    print("[OK] Teste passou!")

def test_validacao_codigo():
    """Testa validação de código de serviço"""
    print("\n" + "="*60)
    print("[LOG] TESTE 2: Validação de Código de Serviço")
    print("="*60)
    
    calc = CalculoIBS()
    
    # Código válido
    valido = calc.validar_codigo_servico('01.01')
    print(f"Código 01.01: {'[OK] Válido' if valido else '[X] Inválido'}")
    assert valido == True, "01.01 deve ser válido"
    
    # Código inválido
    invalido = calc.validar_codigo_servico('99.99')
    print(f"Código 99.99: {'[OK] Válido' if invalido else '[X] Inválido'}")
    assert invalido == False, "99.99 deve ser inválido"
    
    print("[OK] Teste passou!")

def test_registro_historico():
    """Testa registro de cálculo no histórico"""
    print("\n" + "="*60)
    print("[LOG] TESTE 3: Registro no Histórico")
    print("="*60)
    
    calc = CalculoIBS()
    
    sucesso = calc.registrar_calculo(
        nfe_id=None,  # Teste sem NFe
        tipo_operacao='servico',
        codigo_servico='01.01',
        valor_base=1000.00,
        aliquota_ibs=0.00,
        valor_ibs=0.00,
        aliquota_cbs=0.00,
        valor_cbs=0.00,
        municipio_origem='3550308'
    )
    
    if sucesso:
        print("[OK] Registro inserido no histórico")
    else:
        print("[X] Falha ao registrar no histórico")
    
    assert sucesso == True, "Deve registrar com sucesso"
    print("[OK] Teste passou!")

def main():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("[?] TESTE DO SERVIÇO DE CÁLCULO IBS")
    print("="*60)
    
    try:
        test_calculo_basico()
        test_validacao_codigo()
        test_registro_historico()
        
        print("\n" + "="*60)
        print("[OK] TODOS OS TESTES PASSARAM!")
        print("="*60)
        print("\n[LOG] Próximos passos:")
        print("   1. Aguardar regulamentação das alíquotas IBS/CBS (2026)")
        print("   2. Implementar lógica real de cálculo no serviço")
        print("   3. Integrar com NFS-e quando disponível")
        print("="*60)
        
        return 0
    
    except Exception as e:
        print(f"\n[X] ERRO NOS TESTES: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
