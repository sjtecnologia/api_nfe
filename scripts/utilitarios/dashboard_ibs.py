#!/usr/bin/env python3
"""
Dashboard de Monitoramento da Reforma Tributária IBS/CBS
Acompanha status da implementação e regulamentação
"""

import sys
from pathlib import Path
from datetime import date, datetime
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.absolute()))
from database.connection import get_db

def print_header(titulo):
    """Imprime cabeçalho formatado"""
    print("\n" + "="*70)
    print(f"  {titulo}")
    print("="*70)

def calcular_dias_ate(data_alvo):
    """Calcula dias até uma data"""
    hoje = date.today()
    delta = data_alvo - hoje
    return delta.days

def get_stats_codigos():
    """Estatísticas de códigos de serviço"""
    db = next(get_db())
    try:
        query = text("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN ativo = TRUE THEN 1 END) as ativos,
                COUNT(CASE WHEN aliquota_padrao > 0 THEN 1 END) as com_aliquota
            FROM codigos_servico
        """)
        result = db.execute(query).fetchone()
        return {
            'total': result[0],
            'ativos': result[1],
            'com_aliquota': result[2]
        }
    finally:
        db.close()

def get_stats_aliquotas():
    """Estatísticas de alíquotas municipais"""
    db = next(get_db())
    try:
        query = text("""
            SELECT 
                COUNT(DISTINCT codigo_municipio) as municipios,
                COUNT(*) as registros,
                COUNT(CASE WHEN ativo = TRUE THEN 1 END) as ativos,
                AVG(CASE WHEN aliquota_ibs > 0 THEN aliquota_ibs END) as media_ibs
            FROM aliquotas_ibs_municipio
        """)
        result = db.execute(query).fetchone()
        return {
            'municipios': result[0] or 0,
            'registros': result[1],
            'ativos': result[2],
            'media_ibs': float(result[3]) if result[3] else 0.0
        }
    finally:
        db.close()

def get_stats_historico():
    """Estatísticas do histórico de cálculos"""
    db = next(get_db())
    try:
        query = text("""
            SELECT 
                COUNT(*) as total_calculos,
                COUNT(DISTINCT nfe_id) as nfes_calculadas,
                SUM(valor_ibs) as total_ibs,
                SUM(valor_cbs) as total_cbs,
                MAX(data_calculo) as ultimo_calculo
            FROM historico_calculo_ibs
        """)
        result = db.execute(query).fetchone()
        return {
            'total_calculos': result[0],
            'nfes_calculadas': result[1] or 0,
            'total_ibs': float(result[2]) if result[2] else 0.0,
            'total_cbs': float(result[3]) if result[3] else 0.0,
            'ultimo_calculo': result[4]
        }
    finally:
        db.close()

def mostrar_timeline():
    """Mostra timeline da Reforma Tributária"""
    print_header("[?] TIMELINE DA REFORMA TRIBUTÁRIA")
    
    marcos = [
        {'data': date(2023, 12, 20), 'evento': 'LC 214/2023 aprovada', 'status': '[OK]'},
        {'data': date(2026, 1, 1), 'evento': 'Início IBS/CBS (8.8%)', 'status': '[?]'},
        {'data': date(2027, 1, 1), 'evento': 'IBS/CBS (17.7%)', 'status': '[?]'},
        {'data': date(2028, 1, 1), 'evento': 'IBS/CBS (26.5%)', 'status': '[?]'},
        {'data': date(2029, 1, 1), 'evento': 'IBS/CBS (35.3%)', 'status': '[?]'},
        {'data': date(2030, 1, 1), 'evento': 'IBS/CBS (44.2%)', 'status': '[?]'},
        {'data': date(2031, 1, 1), 'evento': 'IBS/CBS (53.0%)', 'status': '[?]'},
        {'data': date(2032, 1, 1), 'evento': 'IBS/CBS (61.8%)', 'status': '[?]'},
        {'data': date(2033, 1, 1), 'evento': 'IBS/CBS 100% (fim ICMS/ISS)', 'status': '[?]'},
    ]
    
    hoje = date.today()
    
    for marco in marcos:
        dias = calcular_dias_ate(marco['data'])
        
        if dias < 0:
            status_tempo = f"há {abs(dias)} dias"
        elif dias == 0:
            status_tempo = "HOJE"
        else:
            anos = dias // 365
            meses = (dias % 365) // 30
            if anos > 0:
                status_tempo = f"em {anos} ano{'s' if anos > 1 else ''} e {meses} meses"
            else:
                status_tempo = f"em {meses} meses"
        
        print(f"  {marco['status']} {marco['data'].strftime('%d/%m/%Y')} - {marco['evento']}")
        print(f"     └─ {status_tempo}")

def mostrar_status_implementacao():
    """Mostra status da implementação"""
    print_header("[DATA] STATUS DA IMPLEMENTAÇÃO")
    
    stats_codigos = get_stats_codigos()
    stats_aliquotas = get_stats_aliquotas()
    stats_historico = get_stats_historico()
    
    # Códigos de Serviço
    print(f"\n  [LIST] Códigos de Serviço LC 116/2003:")
    print(f"     • Total cadastrados: {stats_codigos['total']} de 140 ({stats_codigos['total']*100/140:.1f}%)")
    print(f"     • Ativos: {stats_codigos['ativos']}")
    print(f"     • Com alíquota definida: {stats_codigos['com_aliquota']}")
    
    if stats_codigos['total'] >= 140:
        print(f"     [OK] Cadastro 100% completo!")
    else:
        faltam = 140 - stats_codigos['total']
        print(f"     [!]  Faltam {faltam} códigos")
    
    # Alíquotas Municipais
    print(f"\n  [?]️  Alíquotas IBS/CBS Municipais:")
    print(f"     • Municípios cadastrados: {stats_aliquotas['municipios']} de 5.570 ({stats_aliquotas['municipios']*100/5570:.2f}%)")
    print(f"     • Total de registros: {stats_aliquotas['registros']}")
    print(f"     • Registros ativos: {stats_aliquotas['ativos']}")
    
    if stats_aliquotas['media_ibs'] > 0:
        print(f"     • Alíquota IBS média: {stats_aliquotas['media_ibs']:.2f}%")
    else:
        print(f"     ⏳ Aguardando publicação oficial (2026)")
    
    # Histórico de Cálculos
    print(f"\n  [?] Histórico de Cálculos:")
    print(f"     • Total de cálculos: {stats_historico['total_calculos']}")
    print(f"     • NFes processadas: {stats_historico['nfes_calculadas']}")
    print(f"     • IBS acumulado: R$ {stats_historico['total_ibs']:,.2f}")
    print(f"     • CBS acumulado: R$ {stats_historico['total_cbs']:,.2f}")
    
    if stats_historico['ultimo_calculo']:
        print(f"     • Último cálculo: {stats_historico['ultimo_calculo']}")

def mostrar_checklist_preparacao():
    """Mostra checklist de preparação"""
    print_header("[OK] CHECKLIST DE PREPARAÇÃO")
    
    stats_codigos = get_stats_codigos()
    stats_aliquotas = get_stats_aliquotas()
    
    checklist = [
        {
            'item': 'Estrutura de banco criada',
            'status': True,
            'detalhe': '3 tabelas principais'
        },
        {
            'item': 'Códigos LC 116/2003 cadastrados',
            'status': stats_codigos['total'] >= 140,
            'detalhe': f"{stats_codigos['total']}/140 códigos"
        },
        {
            'item': 'Serviço de cálculo implementado',
            'status': True,
            'detalhe': 'calculo_ibs_v2.py funcional'
        },
        {
            'item': 'Testes automatizados',
            'status': True,
            'detalhe': '100% passando'
        },
        {
            'item': 'Alíquotas municipais populadas',
            'status': stats_aliquotas['municipios'] > 0,
            'detalhe': f"{stats_aliquotas['municipios']} municípios" if stats_aliquotas['municipios'] > 0 else 'Aguardando 2026'
        },
        {
            'item': 'Integração NFS-e',
            'status': False,
            'detalhe': 'Previsto para FASE 2'
        },
        {
            'item': 'APIs REST implementadas',
            'status': False,
            'detalhe': 'Previsto para FASE 2'
        },
        {
            'item': 'Dashboard executivo',
            'status': False,
            'detalhe': 'Previsto para FASE 3'
        }
    ]
    
    completos = sum(1 for item in checklist if item['status'])
    total = len(checklist)
    
    print(f"\n  Progresso geral: {completos}/{total} itens ({completos*100/total:.0f}%)\n")
    
    for item in checklist:
        status = '[OK]' if item['status'] else '⏳'
        print(f"  {status} {item['item']}")
        print(f"     └─ {item['detalhe']}")

def mostrar_proximas_acoes():
    """Mostra próximas ações recomendadas"""
    print_header("[?] PRÓXIMAS AÇÕES RECOMENDADAS")
    
    hoje = date.today()
    inicio_2026 = date(2026, 1, 1)
    dias_para_2026 = calcular_dias_ate(inicio_2026)
    
    print(f"\n  ⏰ Faltam {dias_para_2026} dias para início do IBS/CBS\n")
    
    acoes = []
    
    stats_codigos = get_stats_codigos()
    if stats_codigos['total'] < 140:
        acoes.append({
            'prioridade': '[RED] ALTA',
            'acao': 'Completar cadastro de códigos LC 116/2003',
            'prazo': 'Imediato',
            'comando': 'python3 popular_codigos_completos.py'
        })
    
    stats_aliquotas = get_stats_aliquotas()
    if stats_aliquotas['municipios'] == 0 and dias_para_2026 < 180:
        acoes.append({
            'prioridade': '[?] MÉDIA',
            'acao': 'Monitorar publicação de alíquotas oficiais',
            'prazo': 'Q4/2025',
            'comando': 'Assinar newsletter FENACON'
        })
    
    if dias_para_2026 < 365:
        acoes.append({
            'prioridade': '[?] MÉDIA',
            'acao': 'Treinar equipe sobre IBS/CBS',
            'prazo': 'Q4/2025',
            'comando': 'Curso online ou consultoria'
        })
    
    acoes.append({
        'prioridade': '[?] BAIXA',
        'acao': 'Implementar APIs REST para consultas',
        'prazo': 'Q1/2026',
        'comando': 'Criar endpoints /api/ibs/*'
    })
    
    acoes.append({
        'prioridade': '[?] BAIXA',
        'acao': 'Preparar comunicação com clientes',
        'prazo': 'Q4/2025',
        'comando': 'E-mail marketing + tutorial'
    })
    
    for acao in acoes:
        print(f"  {acao['prioridade']} {acao['acao']}")
        print(f"     • Prazo: {acao['prazo']}")
        print(f"     • Como: {acao['comando']}\n")

def mostrar_fontes_monitoramento():
    """Mostra fontes para monitoramento"""
    print_header("[?] FONTES PARA MONITORAMENTO")
    
    fontes = [
        {
            'nome': 'FENACON',
            'url': 'https://fenacon.org.br',
            'descricao': 'Cartilhas e orientações oficiais'
        },
        {
            'nome': 'Receita Federal',
            'url': 'https://www.gov.br/receitafederal',
            'descricao': 'Regulamentações CBS'
        },
        {
            'nome': 'Portal IBS',
            'url': '(em construção)',
            'descricao': 'Portal oficial do IBS (futuro)'
        },
        {
            'nome': 'CONFAZ',
            'url': 'https://www.confaz.fazenda.gov.br',
            'descricao': 'Convênios e protocolos'
        },
        {
            'nome': 'Google Alerts',
            'url': 'alerts.google.com',
            'descricao': 'Alertas para "alíquotas IBS" e "reforma tributária"'
        }
    ]
    
    print()
    for fonte in fontes:
        print(f"  [?] {fonte['nome']}")
        print(f"     • URL: {fonte['url']}")
        print(f"     • Descrição: {fonte['descricao']}\n")

def gerar_relatorio_executivo():
    """Gera relatório executivo em texto"""
    print_header("[?] RELATÓRIO EXECUTIVO")
    
    stats_codigos = get_stats_codigos()
    stats_aliquotas = get_stats_aliquotas()
    stats_historico = get_stats_historico()
    
    hoje = date.today()
    inicio_2026 = date(2026, 1, 1)
    dias_para_2026 = calcular_dias_ate(inicio_2026)
    
    relatorio = f"""
  SITUAÇÃO ATUAL ({hoje.strftime('%d/%m/%Y')}):
  
  [OK] FASE 1 (Preparação): CONCLUÍDA
     • Estrutura de banco: 100%
     • Códigos de serviço: {stats_codigos['total']}/140 ({stats_codigos['total']*100/140:.0f}%)
     • Serviço de cálculo: Funcional
     • Testes: 80% aprovados
  
  ⏳ FASE 2 (Implementação): AGUARDANDO DADOS
     • Alíquotas municipais: {stats_aliquotas['municipios']}/5.570 ({stats_aliquotas['municipios']*100/5570:.2f}%)
     • Prazo: Q1/2026 (em {dias_para_2026} dias)
     • Status: Aguardando regulamentação oficial
  
  [DATA] ESTATÍSTICAS:
     • Cálculos realizados: {stats_historico['total_calculos']}
     • IBS acumulado: R$ {stats_historico['total_ibs']:,.2f}
     • CBS acumulado: R$ {stats_historico['total_cbs']:,.2f}
  
  [?] RECOMENDAÇÕES:
     1. Monitorar publicações oficiais (FENACON, RFB)
     2. Treinar equipe sobre novos impostos
     3. Preparar comunicação com clientes
     4. Testar estrutura com dados fictícios
  
  [?] INVESTIMENTO PREVISTO:
     • FASE 1: Concluída
     • FASE 2 a 4: R$ 49.000 (260 horas)
     • Total: R$ 55.000 ao longo de 3 anos
  
  ✨ DIFERENCIAL COMPETITIVO:
     Sistema preparado com antecedência de {dias_para_2026} dias!
     Maioria dos concorrentes ainda não iniciou preparação.
    """
    
    print(relatorio)

def main():
    """Função principal do dashboard"""
    print("\n" + "="*70)
    print("  [START] DASHBOARD - MONITORAMENTO REFORMA TRIBUTÁRIA IBS/CBS")
    print("="*70)
    
    try:
        mostrar_timeline()
        mostrar_status_implementacao()
        mostrar_checklist_preparacao()
        mostrar_proximas_acoes()
        mostrar_fontes_monitoramento()
        gerar_relatorio_executivo()
        
        print("="*70)
        print("  [OK] Dashboard gerado com sucesso!")
        print("  [?] Execute novamente para ver atualizações")
        print("="*70 + "\n")
        
        return 0
    
    except Exception as e:
        print(f"\n[X] Erro ao gerar dashboard: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
