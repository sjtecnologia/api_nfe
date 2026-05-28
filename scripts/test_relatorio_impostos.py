"""
Teste do relatório de impostos
"""
from datetime import datetime, timedelta
from database.connection import get_db
from services.relatorio_service import RelatorioService

def test_impostos():
    """Testa relatório de impostos"""
    db = next(get_db())
    servico = RelatorioService(db)
    
    # Período: últimos 6 meses
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=180)
    
    cliente_id = 11
    
    print(f"\n{'='*80}")
    print(f"TESTE RELATÓRIO DE IMPOSTOS")
    print(f"{'='*80}")
    print(f"Cliente ID: {cliente_id}")
    print(f"Período: {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}")
    print(f"{'='*80}\n")
    
    try:
        # Buscar relatório
        resultado = servico.relatorio_impostos(
            cliente_ids=[cliente_id],
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        print(f"✅ Relatório gerado com sucesso!\n")
        print(f"Resumo:")
        print(f"  - Total de Notas: {resultado['resumo']['total_notas']}")
        print(f"  - Base de Cálculo: R$ {resultado['resumo']['base_calculo']:,.2f}")
        print(f"  - Total de Impostos: R$ {resultado['resumo']['total_impostos']:,.2f}")
        print(f"  - Carga Tributária: {resultado['resumo']['carga_tributaria_percentual']}%")
        
        print(f"\n{'='*80}")
        print(f"DETALHAMENTO POR IMPOSTO:")
        print(f"{'='*80}\n")
        
        impostos = resultado['impostos']
        print(f"{'Imposto':<15} {'Valor':<20} {'Alíq. Efetiva':<15} {'% Total':<10}")
        print(f"{'-'*60}")
        
        for nome, dados in impostos.items():
            nome_upper = nome.upper()
            valor = dados['valor']
            aliquota = dados.get('aliquota_efetiva', 'N/A')
            percentual = dados['percentual_total']
            print(f"{nome_upper:<15} R$ {valor:>15,.2f} {str(aliquota):>13}% {percentual:>8.2f}%")
        
        # Detalhamento por CFOP
        if resultado['detalhamento_cfop']:
            print(f"\n{'='*80}")
            print(f"DETALHAMENTO POR CFOP:")
            print(f"{'='*80}\n")
            
            print(f"{'CFOP':<10} {'Qtd Notas':<12} {'Valor Total':<18} {'ICMS':<15} {'IPI':<15}")
            print(f"{'-'*70}")
            
            for cfop in resultado['detalhamento_cfop']:
                print(f"{cfop['cfop']:<10} {cfop['quantidade_notas']:<12} R$ {cfop['valor_total']:>13,.2f} R$ {cfop['icms']:>10,.2f} R$ {cfop['ipi']:>10,.2f}")
        else:
            print(f"\n⚠️  Nenhum CFOP encontrado")
        
    except Exception as e:
        print(f"❌ Erro ao gerar relatório: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    test_impostos()
