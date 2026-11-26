"""
Teste do relatório de produtos/serviços
"""
from datetime import datetime, timedelta
from database.connection import get_db
from services.relatorio_service import RelatorioService

def test_produtos():
    """Testa relatório de produtos"""
    db = next(get_db())
    servico = RelatorioService(db)
    
    # Período: últimos 6 meses
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=180)
    
    cliente_id = 11
    
    print(f"\n{'='*80}")
    print(f"TESTE RELATÓRIO DE PRODUTOS/SERVIÇOS")
    print(f"{'='*80}")
    print(f"Cliente ID: {cliente_id}")
    print(f"Período: {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}")
    print(f"{'='*80}\n")
    
    try:
        # Buscar relatório
        resultado = servico.relatorio_produtos(
            cliente_ids=[cliente_id],
            data_inicio=data_inicio,
            data_fim=data_fim,
            limite=20
        )
        
        print(f"✅ Relatório gerado com sucesso!\n")
        print(f"Resumo:")
        print(f"  - Total de Notas: {resultado['resumo']['total_notas']}")
        print(f"  - Total de Produtos: {resultado['resumo']['total_produtos']}")
        print(f"  - Valor Total Vendas: R$ {resultado['resumo']['valor_total_vendas']:,.2f}")
        print(f"  - Ticket Médio: R$ {resultado['resumo']['ticket_medio']:,.2f}")
        
        print(f"\n{'='*80}")
        print(f"TOP PRODUTOS:")
        print(f"{'='*80}")
        
        if len(resultado['produtos']) == 0:
            print("⚠️  Nenhum produto encontrado no período!")
        else:
            print(f"\n{'Código':<15} {'Descrição':<40} {'Qtd':<10} {'Valor Total':<15} {'% Vendas':<10}")
            print(f"{'-'*95}")
            for i, produto in enumerate(resultado['produtos'][:10], 1):
                print(f"{produto['codigo']:<15} {produto['descricao'][:40]:<40} {produto['quantidade_total']:<10.0f} R$ {produto['valor_total_vendas']:>10,.2f} {produto['percentual_vendas']:>8.1f}%")
        
    except Exception as e:
        print(f"❌ Erro ao gerar relatório: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    test_produtos()
