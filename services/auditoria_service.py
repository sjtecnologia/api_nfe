"""
Serviço de Auditoria - Registra e consulta ações no sistema
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import text, and_, or_
from flask import request
from database.connection import get_db
import json
import traceback


class AuditoriaService:
    """Serviço para gerenciar logs de auditoria"""
    
    @staticmethod
    def registrar_acao(
        user_id: Optional[int],
        acao: str,
        tabela_afetada: Optional[str] = None,
        registro_id: Optional[int] = None,
        dados_antes: Optional[Dict] = None,
        dados_depois: Optional[Dict] = None,
        descricao: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Registra uma ação no log de auditoria
        
        Args:
            user_id: ID do usuário que realizou a ação (None para ações do sistema)
            acao: Tipo de ação (CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc.)
            tabela_afetada: Nome da tabela afetada
            registro_id: ID do registro afetado
            dados_antes: Estado anterior do registro
            dados_depois: Estado posterior do registro
            descricao: Descrição adicional
            ip_address: IP do cliente (capturado automaticamente se None)
            user_agent: User agent (capturado automaticamente se None)
        
        Returns:
            bool: True se registrado com sucesso, False caso contrário
        """
        db = None
        try:
            # Captura IP e User Agent do request atual se não fornecidos
            if ip_address is None and request:
                ip_address = request.remote_addr
            
            if user_agent is None and request:
                user_agent = request.headers.get('User-Agent', '')
            
            # Converte dicionários para JSON
            dados_antes_json = json.dumps(dados_antes) if dados_antes else None
            dados_depois_json = json.dumps(dados_depois) if dados_depois else None
            
            db = next(get_db())
            
            query = text("""
                INSERT INTO auditoria (
                    user_id, acao, tabela_afetada, registro_id,
                    dados_antes, dados_depois, descricao,
                    ip_address, user_agent, timestamp
                ) VALUES (
                    :user_id, :acao, :tabela_afetada, :registro_id,
                    :dados_antes, :dados_depois, :descricao,
                    :ip_address, :user_agent, CURRENT_TIMESTAMP
                )
            """)
            
            db.execute(query, {
                'user_id': user_id,
                'acao': acao,
                'tabela_afetada': tabela_afetada,
                'registro_id': registro_id,
                'dados_antes': dados_antes_json,
                'dados_depois': dados_depois_json,
                'descricao': descricao,
                'ip_address': ip_address,
                'user_agent': user_agent
            })
            
            db.commit()
            print(f"[OK] Auditoria registrada: {acao} em {tabela_afetada} por user {user_id}")
            return True
            
        except Exception as e:
            print(f"[X] Erro ao registrar auditoria: {e}")
            traceback.print_exc()
            if db:
                db.rollback()
            return False
        finally:
            if db:
                db.close()
    
    @staticmethod
    def obter_logs(
        user_id: Optional[int] = None,
        acao: Optional[str] = None,
        tabela_afetada: Optional[str] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Dict], int]:
        """
        Obtém logs de auditoria com filtros
        
        Args:
            user_id: Filtrar por usuário
            acao: Filtrar por tipo de ação
            tabela_afetada: Filtrar por tabela
            data_inicio: Data inicial
            data_fim: Data final
            limit: Limite de registros
            offset: Offset para paginação
        
        Returns:
            tuple: (lista de logs, total de registros)
        """
        db = None
        try:
            db = next(get_db())
            
            # Construir query com filtros
            where_clauses = []
            params = {}
            
            if user_id is not None:
                where_clauses.append("a.user_id = :user_id")
                params['user_id'] = user_id
            
            if acao:
                where_clauses.append("a.acao = :acao")
                params['acao'] = acao
            
            if tabela_afetada:
                where_clauses.append("a.tabela_afetada = :tabela_afetada")
                params['tabela_afetada'] = tabela_afetada
            
            if data_inicio:
                where_clauses.append("a.timestamp >= :data_inicio")
                params['data_inicio'] = data_inicio
            
            if data_fim:
                where_clauses.append("a.timestamp <= :data_fim")
                params['data_fim'] = data_fim
            
            where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            
            # Query para contar total
            count_query = text(f"""
                SELECT COUNT(*) as total
                FROM auditoria a
                {where_sql}
            """)
            
            total_result = db.execute(count_query, params).fetchone()
            total = total_result[0] if total_result else 0
            
            # Query principal com JOIN para pegar username
            params['limit'] = limit
            params['offset'] = offset
            
            query = text(f"""
                SELECT 
                    a.auditoria_id,
                    a.user_id,
                    u.username,
                    a.acao,
                    a.tabela_afetada,
                    a.registro_id,
                    a.timestamp,
                    a.dados_antes,
                    a.dados_depois,
                    a.ip_address,
                    a.user_agent,
                    a.descricao
                FROM auditoria a
                LEFT JOIN users u ON a.user_id = u.id
                {where_sql}
                ORDER BY a.timestamp DESC
                LIMIT :limit OFFSET :offset
            """)
            
            result = db.execute(query, params)
            
            logs = []
            for row in result:
                logs.append({
                    'auditoria_id': row[0],
                    'user_id': row[1],
                    'username': row[2] or 'Sistema',
                    'acao': row[3],
                    'tabela_afetada': row[4],
                    'registro_id': row[5],
                    'timestamp': row[6],
                    'dados_antes': row[7],
                    'dados_depois': row[8],
                    'ip_address': row[9],
                    'user_agent': row[10],
                    'descricao': row[11]
                })
            
            return logs, total
            
        except Exception as e:
            print(f"[X] Erro ao obter logs de auditoria: {e}")
            traceback.print_exc()
            return [], 0
        finally:
            if db:
                db.close()
    
    @staticmethod
    def obter_estatisticas_auditoria(dias: int = 30) -> Dict[str, Any]:
        """
        Obtém estatísticas de auditoria dos últimos N dias
        
        Args:
            dias: Número de dias para análise
        
        Returns:
            dict: Estatísticas de auditoria
        """
        db = None
        try:
            db = next(get_db())
            data_inicio = datetime.now() - timedelta(days=dias)
            
            # Total de ações
            query_total = text("""
                SELECT COUNT(*) as total
                FROM auditoria
                WHERE timestamp >= :data_inicio
            """)
            total_result = db.execute(query_total, {'data_inicio': data_inicio}).fetchone()
            total_acoes = total_result[0] if total_result else 0
            
            # Ações por tipo
            query_por_tipo = text("""
                SELECT acao, COUNT(*) as quantidade
                FROM auditoria
                WHERE timestamp >= :data_inicio
                GROUP BY acao
                ORDER BY quantidade DESC
            """)
            acoes_por_tipo = []
            for row in db.execute(query_por_tipo, {'data_inicio': data_inicio}):
                acoes_por_tipo.append({'acao': row[0], 'quantidade': row[1]})
            
            # Usuários mais ativos
            query_usuarios = text("""
                SELECT u.username, COUNT(*) as quantidade
                FROM auditoria a
                JOIN users u ON a.user_id = u.id
                WHERE a.timestamp >= :data_inicio
                GROUP BY u.username
                ORDER BY quantidade DESC
                LIMIT 10
            """)
            usuarios_ativos = []
            for row in db.execute(query_usuarios, {'data_inicio': data_inicio}):
                usuarios_ativos.append({'username': row[0], 'quantidade': row[1]})
            
            # Tabelas mais alteradas
            query_tabelas = text("""
                SELECT tabela_afetada, COUNT(*) as quantidade
                FROM auditoria
                WHERE timestamp >= :data_inicio AND tabela_afetada IS NOT NULL
                GROUP BY tabela_afetada
                ORDER BY quantidade DESC
                LIMIT 10
            """)
            tabelas_alteradas = []
            for row in db.execute(query_tabelas, {'data_inicio': data_inicio}):
                tabelas_alteradas.append({'tabela': row[0], 'quantidade': row[1]})
            
            return {
                'total_acoes': total_acoes,
                'periodo_dias': dias,
                'acoes_por_tipo': acoes_por_tipo,
                'usuarios_ativos': usuarios_ativos,
                'tabelas_alteradas': tabelas_alteradas
            }
            
        except Exception as e:
            print(f"[X] Erro ao obter estatísticas: {e}")
            traceback.print_exc()
            return {
                'total_acoes': 0,
                'periodo_dias': dias,
                'acoes_por_tipo': [],
                'usuarios_ativos': [],
                'tabelas_alteradas': []
            }
        finally:
            if db:
                db.close()
    
    @staticmethod
    def limpar_logs_antigos(dias: int = 365) -> int:
        """
        Remove logs de auditoria mais antigos que N dias
        
        Args:
            dias: Número de dias para manter logs
        
        Returns:
            int: Número de registros removidos
        """
        db = None
        try:
            db = next(get_db())
            data_limite = datetime.now() - timedelta(days=dias)
            
            query = text("""
                DELETE FROM auditoria
                WHERE timestamp < :data_limite
            """)
            
            result = db.execute(query, {'data_limite': data_limite})
            db.commit()
            
            # Type-safe rowcount access
            deletados = getattr(result, 'rowcount', 0)
            print(f"[OK] {deletados} registros de auditoria removidos (mais de {dias} dias)")
            return deletados
            
        except Exception as e:
            print(f"[X] Erro ao limpar logs antigos: {e}")
            traceback.print_exc()
            if db:
                db.rollback()
            return 0
        finally:
            if db:
                db.close()


# Atalhos para ações comuns
def registrar_login(user_id: int, sucesso: bool = True):
    """Registra tentativa de login"""
    acao = 'LOGIN_SUCCESS' if sucesso else 'LOGIN_FAILED'
    AuditoriaService.registrar_acao(
        user_id=user_id,
        acao=acao,
        descricao=f"Usuário {'entrou' if sucesso else 'tentou entrar'} no sistema"
    )


def registrar_logout(user_id: int):
    """Registra logout"""
    AuditoriaService.registrar_acao(
        user_id=user_id,
        acao='LOGOUT',
        descricao="Usuário saiu do sistema"
    )


def registrar_criacao(user_id: int, tabela: str, registro_id: int, dados: Dict):
    """Registra criação de registro"""
    AuditoriaService.registrar_acao(
        user_id=user_id,
        acao='CREATE',
        tabela_afetada=tabela,
        registro_id=registro_id,
        dados_depois=dados,
        descricao=f"Registro criado em {tabela}"
    )


def registrar_atualizacao(user_id: int, tabela: str, registro_id: int, dados_antes: Dict, dados_depois: Dict):
    """Registra atualização de registro"""
    AuditoriaService.registrar_acao(
        user_id=user_id,
        acao='UPDATE',
        tabela_afetada=tabela,
        registro_id=registro_id,
        dados_antes=dados_antes,
        dados_depois=dados_depois,
        descricao=f"Registro atualizado em {tabela}"
    )


def registrar_exclusao(user_id: int, tabela: str, registro_id: int, dados: Dict):
    """Registra exclusão de registro"""
    AuditoriaService.registrar_acao(
        user_id=user_id,
        acao='DELETE',
        tabela_afetada=tabela,
        registro_id=registro_id,
        dados_antes=dados,
        descricao=f"Registro excluído de {tabela}"
    )
