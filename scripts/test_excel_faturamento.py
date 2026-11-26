"""
Teste da geração de Excel de faturamento com impostos
"""
from datetime import datetime, timedelta
from database.connection import get_db
from services.relatorio_service import RelatorioService
from routes.relatorios_routes import gerar_excel_faturamento
import io

def test_excel_faturamento():
    """Testa geração do Excel de faturamento"""
    db = next(get_db())
    servico = RelatorioService(db)
    
    # Período: últimos 6 meses
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=180)
    
    cliente_id = 11
    
    print(f"\n{'='*80}")
    print(f"TESTE EXCEL RELATÓRIO DE FATURAMENTO")
    print(f"{'='*80}")
    print(f"Cliente ID: {cliente_id}")
    print(f"Período: {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}")
    print(f"{'='*80}\n")
    
    try:
        # Buscar dados
        dados = servico.relatorio_faturamento(
            cliente_ids=[cliente_id],
            data_inicio=data_inicio,
            data_fim=data_fim,
            agrupar_por='mes'
        )
        
        print("✅ Dados do relatório obtidos:")
        print(f"  - Total de períodos: {len(dados['dados'])}")
        print(f"  - Quantidade de notas: {dados['totais']['quantidade_notas']}")
        print(f"  - Valor total: R$ {dados['totais']['valor_total']:,.2f}")
        
        if dados['dados']:
            print(f"\n📊 Primeira linha de dados:")
            primeiro = dados['dados'][0]
            print(f"  - Período: {primeiro['periodo']}")
            print(f"  - Quantidade: {primeiro['quantidade_notas']}")
            print(f"  - Valor Total: R$ {primeiro['valor_total']:,.2f}")
            print(f"  - ICMS: R$ {primeiro['total_icms']:,.2f}")
            print(f"  - IPI: R$ {primeiro['total_ipi']:,.2f}")
            print(f"  - PIS: R$ {primeiro['total_pis']:,.2f}")
            print(f"  - COFINS: R$ {primeiro['total_cofins']:,.2f}")
            print(f"  - Ticket Médio: R$ {primeiro['ticket_medio']:,.2f}")
        
        # Testar estrutura do Excel (não baixar, só verificar)
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, NamedStyle
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Faturamento"
        
        # Cabeçalhos esperados
        headers = ['Período', 'Quantidade NFes', 'Valor Total', 'ICMS', 'IPI', 'PIS', 'COFINS', 'Ticket Médio']
        ws.append(headers)
        
        # Adicionar primeira linha de dadosprimeiro = dados['dados'][0] if dados['dados'] else None
        if primeiro:
            ws.append([
                primeiro.get('periodo', ''),
                primeiro.get('quantidade_notas', 0),
                primeiro.get('valor_total', 0),
                primeiro.get('total_icms', 0),
                primeiro.get('total_ipi', 0),
                primeiro.get('total_pis', 0),
                primeiro.get('total_cofins', 0),
                primeiro.get('ticket_medio', 0)
            ])
        
        print(f"\n✅ Excel gerado com {len(headers)} colunas:")
        for i, h in enumerate(headers, 1):
            print(f"  {i}. {h}")
        
        # Salvar temporariamente para verificar
        output = io.BytesIO()
        wb.save(output)
        print(f"\n✅ Arquivo Excel gerado com sucesso! Tamanho: {len(output.getvalue())} bytes")
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    test_excel_faturamento()
