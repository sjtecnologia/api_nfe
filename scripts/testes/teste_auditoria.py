"""
Script de Teste do Sistema de Auditoria
Testa todas as funcionalidades do serviço de auditoria
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.auditoria_service import (
    AuditoriaService,
    registrar_login,
    registrar_logout,
    registrar_criacao,
    registrar_atualizacao,
    registrar_exclusao
)
from datetime import datetime

def teste_basico():
    """Testa registro básico de auditoria"""
    print("\n" + "="*60)
    print("TESTE 1: Registro Básico de Auditoria")
    print("="*60)
    
    # Teste 1: Login bem-sucedido
    print("\n1. Testando registro de login...")
    registrar_login(user_id=1, sucesso=True)
    print("[OK] Login registrado")
    
    # Teste 2: Login falhado
    print("\n2. Testando registro de login falhado...")
    AuditoriaService.registrar_acao(
        user_id=None,
        acao='LOGIN_FAILED',
        descricao="Tentativa de login com usuário 'admin' falhou"
    )
    print("[OK] Login falhado registrado")
    
    # Teste 3: Criação de produto
    print("\n3. Testando registro de criação...")
    registrar_criacao(
        user_id=1,
        tabela='produtos',
        registro_id=999,
        dados={'nome': 'Produto Teste', 'preco': 100.50, 'estoque': 50}
    )
    print("[OK] Criação registrada")
    
    # Teste 4: Atualização de produto
    print("\n4. Testando registro de atualização...")
    registrar_atualizacao(
        user_id=1,
        tabela='produtos',
        registro_id=999,
        dados_antes={'nome': 'Produto Teste', 'preco': 100.50, 'estoque': 50},
        dados_depois={'nome': 'Produto Teste Atualizado', 'preco': 120.00, 'estoque': 45}
    )
    print("[OK] Atualização registrada")
    
    # Teste 5: Exclusão de produto
    print("\n5. Testando registro de exclusão...")
    registrar_exclusao(
        user_id=1,
        tabela='produtos',
        registro_id=999,
        dados={'nome': 'Produto Teste Atualizado', 'preco': 120.00, 'estoque': 45}
    )
    print("[OK] Exclusão registrada")
    
    # Teste 6: Logout
    print("\n6. Testando registro de logout...")
    registrar_logout(user_id=1)
    print("[OK] Logout registrado")


def teste_consulta():
    """Testa consulta de logs"""
    print("\n" + "="*60)
    print("TESTE 2: Consulta de Logs")
    print("="*60)
    
    # Teste 1: Buscar todos os logs
    print("\n1. Buscando todos os logs (últimos 10)...")
    logs, total = AuditoriaService.obter_logs(limit=10)
    print(f"[OK] Encontrados {total} logs no total, mostrando {len(logs)}")
    
    if logs:
        print("\nÚltimos 3 logs:")
        for i, log in enumerate(logs[:3], 1):
            print(f"  {i}. [{log['acao']}] {log['username']} - {log['descricao'] or '-'}")
    
    # Teste 2: Filtrar por usuário
    print("\n2. Buscando logs do usuário ID 1...")
    logs_user, total_user = AuditoriaService.obter_logs(user_id=1, limit=10)
    print(f"[OK] Encontrados {total_user} logs do usuário 1")
    
    # Teste 3: Filtrar por ação
    print("\n3. Buscando logs de LOGIN...")
    logs_login, total_login = AuditoriaService.obter_logs(acao='LOGIN_SUCCESS', limit=10)
    print(f"[OK] Encontrados {total_login} logs de LOGIN_SUCCESS")
    
    # Teste 4: Filtrar por tabela
    print("\n4. Buscando logs da tabela 'produtos'...")
    logs_produtos, total_produtos = AuditoriaService.obter_logs(tabela_afetada='produtos', limit=10)
    print(f"[OK] Encontrados {total_produtos} logs de alterações em produtos")


def teste_estatisticas():
    """Testa estatísticas de auditoria"""
    print("\n" + "="*60)
    print("TESTE 3: Estatísticas de Auditoria")
    print("="*60)
    
    print("\n1. Obtendo estatísticas dos últimos 30 dias...")
    stats = AuditoriaService.obter_estatisticas_auditoria(dias=30)
    
    print(f"\n[DATA] ESTATÍSTICAS:")
    print(f"   Total de ações: {stats['total_acoes']}")
    print(f"   Período: {stats['periodo_dias']} dias")
    
    if stats['acoes_por_tipo']:
        print(f"\n   Ações por tipo:")
        for acao in stats['acoes_por_tipo'][:5]:
            print(f"      - {acao['acao']}: {acao['quantidade']}")
    
    if stats['usuarios_ativos']:
        print(f"\n   Usuários mais ativos:")
        for usuario in stats['usuarios_ativos'][:5]:
            print(f"      - {usuario['username']}: {usuario['quantidade']} ações")
    
    if stats['tabelas_alteradas']:
        print(f"\n   Tabelas mais alteradas:")
        for tabela in stats['tabelas_alteradas'][:5]:
            print(f"      - {tabela['tabela']}: {tabela['quantidade']} alterações")
    
    print("[OK] Estatísticas obtidas com sucesso")


def teste_acao_complexa():
    """Testa registro de ação complexa com JSON"""
    print("\n" + "="*60)
    print("TESTE 4: Registro de Ação Complexa")
    print("="*60)
    
    print("\n1. Registrando emissão de NFe...")
    AuditoriaService.registrar_acao(
        user_id=1,
        acao='CREATE',
        tabela_afetada='nfe_emitidas',
        registro_id=12345,
        dados_depois={
            'numero_nfe': '000012345',
            'serie': '1',
            'valor_total': 1500.00,
            'destinatario': {
                'razao_social': 'Empresa Teste LTDA',
                'cnpj': '12.345.678/0001-90'
            },
            'itens': [
                {'produto': 'Produto A', 'quantidade': 2, 'valor': 500.00},
                {'produto': 'Produto B', 'quantidade': 1, 'valor': 500.00}
            ]
        },
        descricao='NFe emitida com sucesso - 3 itens',
        ip_address='192.168.1.100',
        user_agent='Mozilla/5.0 (Test Script)'
    )
    print("[OK] NFe registrada na auditoria")
    
    print("\n2. Registrando cancelamento de NFe...")
    AuditoriaService.registrar_acao(
        user_id=1,
        acao='DELETE',
        tabela_afetada='nfe_emitidas',
        registro_id=12345,
        dados_antes={
            'numero_nfe': '000012345',
            'status': 'AUTORIZADA'
        },
        dados_depois={
            'numero_nfe': '000012345',
            'status': 'CANCELADA'
        },
        descricao='NFe cancelada pelo usuário',
        ip_address='192.168.1.100'
    )
    print("[OK] Cancelamento registrado na auditoria")


def main():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("INICIANDO TESTES DO SISTEMA DE AUDITORIA")
    print("="*60)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    try:
        teste_basico()
        teste_consulta()
        teste_estatisticas()
        teste_acao_complexa()
        
        print("\n" + "="*60)
        print("[OK] TODOS OS TESTES CONCLUÍDOS COM SUCESSO!")
        print("="*60)
        print("\nAcesse http://127.0.0.1:8080/admin/auditoria para ver os logs")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n[X] ERRO NOS TESTES: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
