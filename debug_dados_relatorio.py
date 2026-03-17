"""
Debug: Verificar dados no banco
"""
from database.connection import get_db
from sqlalchemy import text

def debug_dados():
    """Verifica dados no banco"""
    db = next(get_db())
    
    print(f"\n{'='*80}")
    print(f"DEBUG: Verificando dados no banco")
    print(f"{'='*80}\n")
    
    # 1. Verificar quantas notas existem para cliente 11
    result = db.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN tipo_nfe = 'S' THEN 1 END) as saidas,
            COUNT(CASE WHEN tipo_nfe = 'E' THEN 1 END) as entradas,
            COUNT(CASE WHEN status IN ('autorizada', 'Autorizada') THEN 1 END) as autorizadas,
            MIN(data_emissao) as primeira_data,
            MAX(data_emissao) as ultima_data
        FROM nfe_emitidas
        WHERE cliente_id = 11
    """)).fetchone()
    
    print(f"📊 Cliente 11:")
    print(f"  - Total de notas: {result.total}")
    print(f"  - Saídas (S): {result.saidas}")
    print(f"  - Entradas (E): {result.entradas}")
    print(f"  - Autorizadas: {result.autorizadas}")
    print(f"  - Primeira data: {result.primeira_data}")
    print(f"  - Última data: {result.ultima_data}")
    
    # 2. Ver os diferentes status existentes
    result = db.execute(text("""
        SELECT status, COUNT(*) as qtd
        FROM nfe_emitidas
        WHERE cliente_id = 11
        GROUP BY status
        ORDER BY qtd DESC
    """)).fetchall()
    
    print(f"\n📋 Status das notas:")
    for row in result:
        print(f"  - {row.status}: {row.qtd}")
    
    # 3. Ver exemplos de notas de saída
    result = db.execute(text("""
        SELECT 
            numero,
            data_emissao,
            tipo_nfe,
            status,
            valor_total
        FROM nfe_emitidas
        WHERE cliente_id = 11
        ORDER BY data_emissao DESC
        LIMIT 5
    """)).fetchall()
    
    print(f"\n📝 Últimas 5 notas:")
    for row in result:
        print(f"  - NFe {row.numero}: {row.data_emissao} | Tipo: {row.tipo_nfe} | Status: {row.status} | Valor: R$ {row.valor_total}")
    
    # 4. Testar a query exata do relatório de faturamento
    from datetime import datetime, timedelta
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=180)
    
    print(f"\n🔍 Testando query do relatório:")
    print(f"  Período: {data_inicio.date()} até {data_fim.date()}")
    
    result = db.execute(text("""
        SELECT 
            COUNT(*) as quantidade_notas,
            SUM(valor_total) as valor_total
        FROM nfe_emitidas
        WHERE cliente_id IN (11)
            AND data_emissao BETWEEN :data_inicio AND :data_fim
            AND status IN ('autorizada', 'Autorizada')
            AND tipo_nfe = 'S'
    """), {
        'data_inicio': data_inicio,
        'data_fim': data_fim
    }).fetchone()
    
    print(f"  Resultado: {result.quantidade_notas} notas, R$ {result.valor_total or 0}")
    
    # 5. Sem filtro de tipo e status
    result = db.execute(text("""
        SELECT 
            COUNT(*) as quantidade_notas,
            SUM(valor_total) as valor_total
        FROM nfe_emitidas
        WHERE cliente_id IN (11)
            AND data_emissao BETWEEN :data_inicio AND :data_fim
    """), {
        'data_inicio': data_inicio,
        'data_fim': data_fim
    }).fetchone()
    
    print(f"  Sem filtros: {result.quantidade_notas} notas, R$ {result.valor_total or 0}")
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    debug_dados()
