"""
Teste do relatório de faturamento com parsing de JSON
"""
from datetime import datetime, timedelta
from database.connection import get_db
from services.relatorio_service import RelatorioService

def test_faturamento():
    """Testa relatório de faturamento"""
    db = next(get_db())
    servico = RelatorioService(db)
    
    # Período: últimos 6 meses
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=180)
    
    # Cliente 11 (teste) ou 25 (que foi usado no erro)
    cliente_id = 11
    
    print(f"\n{'='*80}")
    print(f"TESTE RELATÓRIO DE FATURAMENTO")
    print(f"{'='*80}")
    print(f"Cliente ID: {cliente_id}")
    print(f"Período: {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}")
    print(f"{'='*80}\n")
    
    try:
        # Buscar relatório agrupado por mês
        resultado = servico.relatorio_faturamento(
            cliente_ids=[cliente_id],
            data_inicio=data_inicio,
            data_fim=data_fim,
            agrupar_por='mes'
        )
        
        print(f"✅ Relatório gerado com sucesso!\n")
        print(f"Totais Gerais:")
        print(f"  - Quantidade de Notas: {resultado['totais']['quantidade_notas']}")
        print(f"  - Valor Total: R$ {resultado['totais']['valor_total']:,.2f}")
        print(f"  - Ticket Médio: R$ {resultado['totais']['ticket_medio']:,.2f}")
        print(f"  - Total Impostos: R$ {resultado['totais']['total_impostos']:,.2f}")
        
        print(f"\n{'='*80}")
        print(f"Dados por Período:")
        print(f"{'='*80}")
        
        if len(resultado['dados']) == 0:
            print("⚠️  Nenhum dado encontrado no período!")
        else:
            for item in resultado['dados']:
                print(f"\nPeríodo: {item['periodo']}")
                print(f"  - Notas: {item['quantidade_notas']}")
                print(f"  - Valor Total: R$ {item['valor_total']:,.2f}")
                print(f"  - Valor Produtos: R$ {item['valor_produtos']:,.2f}")
                print(f"  - ICMS: R$ {item['total_icms']:,.2f}")
                print(f"  - IPI: R$ {item['total_ipi']:,.2f}")
                print(f"  - PIS: R$ {item['total_pis']:,.2f}")
                print(f"  - COFINS: R$ {item['total_cofins']:,.2f}")
                print(f"  - Ticket Médio: R$ {item['ticket_medio']:,.2f}")
        
    except Exception as e:
        print(f"❌ Erro ao gerar relatório: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    test_faturamento()
