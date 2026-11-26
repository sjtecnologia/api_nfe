"""
Teste para verificar filtro por cliente ativo
"""
from database.connection import get_db
from sqlalchemy import text

def verificar_dados_por_cliente():
    """Verifica quantos dados existem por cliente"""
    db = next(get_db())
    
    result = db.execute(text("""
        SELECT 
            cliente_id,
            COUNT(*) as total_notas,
            SUM(valor_total) as valor_total
        FROM nfe_emitidas
        WHERE UPPER(status) = 'AUTORIZADA'
        GROUP BY cliente_id
        ORDER BY cliente_id
    """)).fetchall()
    
    print(f"\n{'='*80}")
    print(f"DADOS POR CLIENTE")
    print(f"{'='*80}\n")
    
    print(f"{'Cliente ID':<15} {'Total Notas':<15} {'Valor Total':<20}")
    print(f"{'-'*50}")
    
    for row in result:
        print(f"{row.cliente_id:<15} {row.total_notas:<15} R$ {float(row.valor_total or 0):>15,.2f}")
    
    print(f"\n{'='*80}")
    print(f"IMPORTANTE: Os relatórios agora exigem que um cliente esteja")
    print(f"selecionado na sessão. Apenas os dados do cliente ativo serão")
    print(f"mostrados.")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    verificar_dados_por_cliente()
