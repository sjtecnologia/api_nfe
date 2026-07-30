"""
Serviço para gestão e sincronização de NCMs com a Receita Federal
"""
import requests
import json
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from sqlalchemy import text
from database.connection import get_db

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NCMService:
    """Serviço para gerenciamento de NCMs"""
    
    # URLs da Receita Federal para NCM (atualizadas para 2025)
    RECEITA_URLS = {
        # API oficial do Siscomex (requer captcha)
        'siscomex_api': 'https://portalunico.siscomex.gov.br/classif/api/publico/nomenclatura/pesquisar',
        # Download completo da nomenclatura (requer captcha)
        'siscomex_download': 'https://portalunico.siscomex.gov.br/classif/api/publico/nomenclatura/download',
        # API alternativa da Receita Federal
        'receita_api': 'https://www.gov.br/receitafederal/dados/nomenclatura-comum-mercosul-ncm',
        # Fallback para dados estáticos
        'github_backup': 'https://raw.githubusercontent.com/Brasil-API/brasil-api/main/api/ncm/v1/ncm.json',
        # APIs alternativas sem captcha
        'brasilapi': 'https://brasilapi.com.br/api/ncm/v1',
        'consulta_ncm': 'https://www.consultancm.com.br/api/ncm',
        'conecta_api': 'https://api.conecta.gov.br/nomenclatura/v1/ncm'
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; NCM-Sync/1.0)',
            'Accept': 'application/json, text/html',
            'Accept-Language': 'pt-BR,pt;q=0.9'
        })
    
    def get_local_ncm_count(self) -> int:
        """Retorna quantidade de NCMs no banco local"""
        try:
            db = next(get_db())
            result = db.execute(text("SELECT COUNT(*) as total FROM ncms")).fetchone()
            db.close()
            return result.total if result else 0
        except Exception as e:
            logger.error(f"Erro ao contar NCMs locais: {e}")
            return 0
    
    def get_last_sync_date(self) -> Optional[datetime]:
        """Retorna data da última sincronização"""
        try:
            db = next(get_db())
            result = db.execute(text("""
                SELECT MAX(data_atualizacao) as ultima_sync 
                FROM ncms 
                WHERE data_atualizacao IS NOT NULL
            """)).fetchone()
            db.close()
            return result.ultima_sync if result and result.ultima_sync else None
        except Exception as e:
            logger.error(f"Erro ao buscar última sincronização: {e}")
            return None
    
    def should_sync(self, force: bool = False) -> bool:
        """Verifica se deve sincronizar (a cada 30 dias)"""
        if force:
            return True
            
        last_sync = self.get_last_sync_date()
        if not last_sync:
            return True
            
        # Sincroniza a cada 30 dias
        return datetime.now() - last_sync > timedelta(days=30)
    
    def fetch_ncm_from_receita(self) -> List[Dict]:
        """Busca NCMs diretamente da Receita Federal com múltiplas fontes"""
        logger.info("[?] Buscando NCMs da Receita Federal...")
        
        ncms = []
        
        # Tenta diferentes fontes em ordem de prioridade
        for source_name, url in self.RECEITA_URLS.items():
            try:
                logger.info(f"Tentando fonte: {source_name}")
                
                response = self.session.get(url, timeout=45)
                response.raise_for_status()
                
                # Parse baseado na fonte
                if source_name == 'siscomex_api':
                    # Tenta buscar todos os NCMs paginadamente
                    data = response.json()
                    if 'nomenclaturas' in data:
                        for item in data['nomenclaturas']:
                            ncms.append({
                                'codigo': item.get('codigo', '').replace('.', ''),
                                'descricao': item.get('descricao', ''),
                                'unidade': item.get('unidade', ''),
                                'data_inicio': item.get('dataInicio'),
                                'data_fim': item.get('dataFim')
                            })
                        break
                        
                elif source_name == 'siscomex_download':
                    # Download completo em formato JSON ou CSV
                    content_type = response.headers.get('content-type', '')
                    if 'json' in content_type:
                        data = response.json()
                        if isinstance(data, list):
                            for item in data:
                                ncms.append({
                                    'codigo': str(item.get('codigo', '')).replace('.', ''),
                                    'descricao': item.get('descricao', ''),
                                    'unidade': item.get('unidade', ''),
                                    'data_inicio': item.get('dataInicio'),
                                    'data_fim': item.get('dataFim')
                                })
                            break
                    elif 'csv' in content_type:
                        # Parse CSV
                        lines = response.text.split('\n')
                        reader = csv.DictReader(lines)
                        for row in reader:
                            codigo = str(row.get('codigo', row.get('NCM', ''))).replace('.', '')
                            descricao = row.get('descricao', row.get('DESCRICAO', ''))
                            if codigo and descricao:
                                ncms.append({
                                    'codigo': codigo,
                                    'descricao': descricao,
                                    'unidade': row.get('unidade', ''),
                                    'data_inicio': row.get('dataInicio'),
                                    'data_fim': row.get('dataFim')
                                })
                        if ncms:
                            break
                            
                elif source_name == 'github_backup':
                    # Fonte de backup do GitHub
                    data = response.json()
                    if isinstance(data, list):
                        for item in data:
                            ncms.append({
                                'codigo': str(item.get('codigo', item.get('ncm', ''))).replace('.', ''),
                                'descricao': item.get('descricao', item.get('description', '')),
                                'unidade': item.get('unidade', ''),
                                'data_inicio': None,
                                'data_fim': None
                            })
                        break
                        
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout em {source_name} após 45s")
                continue
            except requests.exceptions.RequestException as e:
                logger.warning(f"Erro de rede em {source_name}: {e}")
                continue
            except json.JSONDecodeError as e:
                logger.warning(f"Erro ao fazer parse JSON de {source_name}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Falha inesperada em {source_name}: {e}")
                continue
        
        # Se conseguiu dados, valida e limpa
        if ncms:
            # Remove entradas inválidas
            valid_ncms = []
            for ncm in ncms:
                codigo = ncm.get('codigo', '').strip()
                descricao = ncm.get('descricao', '').strip()
                
                # Valida formato do código NCM (8 dígitos)
                if codigo and descricao and len(codigo) == 8 and codigo.isdigit():
                    valid_ncms.append(ncm)
            
            logger.info(f"[OK] Encontrados {len(valid_ncms)} NCMs válidos da Receita Federal")
            return valid_ncms
        
        # Se não conseguiu de nenhuma fonte oficial
        logger.warning("[!] Não foi possível buscar da Receita Federal")
        return []
    
    def sync_ncm_to_database(self, ncms: List[Dict], force: bool = False) -> Tuple[int, int]:
        """Sincroniza NCMs para o banco de dados"""
        if not ncms:
            return 0, 0
            
        logger.info(f"[SAVE] Sincronizando {len(ncms)} NCMs para o banco...")
        
        db = next(get_db())
        inserted = 0
        updated = 0
        
        try:
            for ncm in ncms:
                codigo = ncm.get('codigo', '').replace('.', '')
                descricao = ncm.get('descricao', '')
                tipo = ncm.get('tipo', 'analitico')  # Default para analítico
                
                if not codigo or not descricao:
                    continue
                
                # Verifica se já existe
                existing = db.execute(text("""
                    SELECT ncm_id FROM ncms WHERE codigo = :codigo
                """), {'codigo': codigo}).fetchone()
                
                if existing:
                    # Atualiza
                    db.execute(text("""
                        UPDATE ncms SET 
                            descricao = :descricao,
                            tipo = :tipo,
                            data_atualizacao = NOW(),
                            fonte_atualizacao = 'siscomex'
                        WHERE codigo = :codigo
                    """), {
                        'codigo': codigo,
                        'descricao': descricao,
                        'tipo': tipo
                    })
                    updated += 1
                else:
                    # Insere novo
                    db.execute(text("""
                        INSERT INTO ncms (codigo, descricao, tipo, data_atualizacao, fonte_atualizacao)
                        VALUES (:codigo, :descricao, :tipo, NOW(), 'siscomex')
                    """), {
                        'codigo': codigo,
                        'descricao': descricao,
                        'tipo': tipo
                    })
                    inserted += 1
            
            db.commit()
            logger.info(f"[OK] Sincronização concluída: {inserted} inseridos, {updated} atualizados")
            
        except Exception as e:
            db.rollback()
            logger.error(f"[X] Erro na sincronização: {e}")
            raise
        finally:
            db.close()
        
        return inserted, updated
    
    def search_ncm_local(self, query: str, limit: int = 50) -> List[Dict]:
        """Busca NCMs no banco local"""
        if not query or len(query) < 2:
            return []
        
        try:
            db = next(get_db())
            
            # Busca por código ou descrição
            results = db.execute(text("""
                SELECT ncm_id, codigo, descricao, data_atualizacao
                FROM ncms 
                WHERE codigo ILIKE :query 
                   OR descricao ILIKE :query
                ORDER BY 
                    CASE WHEN codigo ILIKE :exact_query THEN 1 ELSE 2 END,
                    codigo
                LIMIT :limit
            """), {
                'query': f'%{query}%',
                'exact_query': f'{query}%',
                'limit': limit
            }).fetchall()
            
            db.close()
            
            return [dict(row._mapping) for row in results]
            
        except Exception as e:
            logger.error(f"Erro na busca local de NCM: {e}")
            return []
    
    def search_ncm_online(self, query: str, limit: int = 10) -> List[Dict]:
        """Busca NCMs diretamente online (fallback)"""
        logger.info(f"[?] Buscando NCM online: {query}")
        
        # URLs para busca online
        search_apis = [
            {
                'name': 'siscomex',
                'url': 'https://portalunico.siscomex.gov.br/classif/api/publico/nomenclatura/pesquisar',
                'params': {'texto': query, 'limite': limit}
            },
            {
                'name': 'consulta_ncm',
                'url': 'https://www.consultancm.com.br/api/buscar',
                'params': {'q': query, 'limit': limit}
            }
        ]
        
        for api in search_apis:
            try:
                logger.info(f"Tentando busca online via {api['name']}")
                
                response = self.session.get(
                    api['url'],
                    params=api['params'],
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Parse baseado na API
                    results = []
                    if api['name'] == 'siscomex':
                        items = data.get('nomenclaturas', data.get('resultados', []))
                        for item in items:
                            codigo = str(item.get('codigo', '')).replace('.', '')
                            if len(codigo) == 8 and codigo.isdigit():
                                results.append({
                                    'codigo': codigo,
                                    'descricao': item.get('descricao', ''),
                                    'ncm_id': None,  # Marca como resultado online
                                    'data_atualizacao': None,
                                    'fonte': 'online'
                                })
                    
                    if results:
                        logger.info(f"[OK] {len(results)} NCMs encontrados online via {api['name']}")
                        return results[:limit]
                        
            except Exception as e:
                logger.warning(f"Falha na busca online via {api['name']}: {e}")
                continue
        
        logger.warning("[X] Nenhuma fonte online disponível")
        return []
    
    def search_ncm_hybrid(self, query: str, limit: int = 50) -> List[Dict]:
        """Busca híbrida: local primeiro, online se necessário"""
        
        # 1. Busca local primeiro
        results = self.search_ncm_local(query, limit)
        
        # 2. Se encontrou resultados suficientes, retorna
        if len(results) >= min(limit, 10):
            logger.info(f"[TRACE] {len(results)} NCMs encontrados localmente")
            return results
        
        # 3. Se poucos resultados, complementa com busca online
        if len(results) < 5:
            logger.info("[?] Complementando com busca online...")
            online_results = self.search_ncm_online(query, limit - len(results))
            
            # Mescla resultados evitando duplicatas
            existing_codes = {r.get('codigo') for r in results}
            for online_result in online_results:
                if online_result.get('codigo') not in existing_codes:
                    results.append(online_result)
        
        return results[:limit]
    
    def full_sync(self, force: bool = False) -> Dict:
        """Executa sincronização completa"""
        logger.info("[START] Iniciando sincronização completa de NCMs...")
        
        # Garante dados iniciais se banco estiver vazio
        # self.populate_initial_ncm_data()
        
        if not self.should_sync(force):
            logger.info("⏭️ Sincronização não necessária (última há menos de 30 dias)")
            return {
                'success': True,
                'message': 'Sincronização não necessária (dados atualizados há menos de 30 dias)',
                'local_count': self.get_local_ncm_count(),
                'skipped': True
            }
        
        try:
            # Busca dados da Receita Federal
            ncms = self.fetch_ncm_from_receita()
            
            if not ncms:
                # Se não conseguiu sincronizar mas já tem dados locais, considera sucesso parcial
                local_count = self.get_local_ncm_count()
                if local_count > 0:
                    logger.info(f"[?] Mantendo {local_count} NCMs locais (APIs externas indisponíveis)")
                    return {
                        'success': True,
                        'message': f'APIs da Receita Federal temporariamente indisponíveis. Mantendo {local_count} NCMs locais.',
                        'local_count': local_count,
                        'sync_failed': True,
                        'fallback_used': True
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Não foi possível obter dados da Receita Federal e banco local está vazio',
                        'local_count': 0,
                        'sync_failed': True
                    }
            
            # Sincroniza com banco
            inserted, updated = self.sync_ncm_to_database(ncms, force)
            
            logger.info(f"[?] Sincronização bem-sucedida!")
            return {
                'success': True,
                'message': f'Sincronização concluída com sucesso! {inserted} NCMs inseridos, {updated} atualizados',
                'inserted': inserted,
                'updated': updated,
                'total_synced': len(ncms),
                'local_count': self.get_local_ncm_count(),
                'sync_successful': True
            }
            
        except Exception as e:
            logger.error(f"[X] Erro na sincronização completa: {e}")
            
            # Verifica se ainda tem dados locais utilizáveis
            local_count = self.get_local_ncm_count()
            if local_count > 0:
                return {
                    'success': True,
                    'message': f'Erro na sincronização, mas mantendo {local_count} NCMs locais: {str(e)}',
                    'local_count': local_count,
                    'sync_failed': True,
                    'error': str(e)
                }
            else:
                return {
                    'success': False,
                    'message': f'Erro na sincronização e banco local vazio: {str(e)}',
                    'local_count': 0,
                    'sync_failed': True,
                    'error': str(e)
                }
    
    # def populate_initial_ncm_data(self) -> bool:
    #     """Popula dados iniciais de NCM se o banco estiver vazio"""
    #     if self.get_local_ncm_count() > 0:
    #         return True
        
    #     logger.info("[?] Populando dados iniciais de NCM...")
        
    #     # Dados básicos de NCM mais comuns organizados por categoria
    #     initial_ncms = [
    #         # Tecnologia e Informática
    #         {'codigo': '84714100', 'descricao': 'Máquinas automáticas para processamento de dados, portáteis'},
    #         {'codigo': '84713000', 'descricao': 'Máquinas automáticas para processamento de dados, portáteis'},
    #         {'codigo': '85171231', 'descricao': 'Telefones celulares'},
    #         {'codigo': '85176290', 'descricao': 'Aparelhos receptores para telefonia'},
    #         {'codigo': '85287200', 'descricao': 'Aparelhos receptores de televisão'},
    #         {'codigo': '85285290', 'descricao': 'Monitores de vídeo'},
    #         {'codigo': '84433210', 'descricao': 'Impressoras jato de tinta'},
    #         {'codigo': '84433290', 'descricao': 'Impressoras laser'},
            
    #         # Veículos e Peças
    #         {'codigo': '87032310', 'descricao': 'Automóveis com motor explosão até 1000cm³'},
    #         {'codigo': '87032390', 'descricao': 'Automóveis com motor explosão 1000-1500cm³'},
    #         {'codigo': '87089990', 'descricao': 'Outras partes e acessórios de veículos'},
    #         {'codigo': '40111000', 'descricao': 'Pneus novos de borracha'},
            
    #         # Roupas e Calçados
    #         {'codigo': '63029300', 'descricao': 'Roupas de cama de algodão'},
    #         {'codigo': '61051000', 'descricao': 'Camisas de malha de algodão, para homens'},
    #         {'codigo': '61091000', 'descricao': 'T-shirts de malha de algodão'},
    #         {'codigo': '64039900', 'descricao': 'Calçados de couro'},
    #         {'codigo': '64041900', 'descricao': 'Calçados de borracha ou plástico'},
            
    #         # Alimentos
    #         {'codigo': '25010010', 'descricao': 'Sal marinho'},
    #         {'codigo': '17019900', 'descricao': 'Açúcar refinado'},
    #         {'codigo': '10059010', 'descricao': 'Milho em grão'},
    #         {'codigo': '02071400', 'descricao': 'Pedaços e miudezas de galos/galinhas'},
    #         {'codigo': '04021000', 'descricao': 'Leite em pó desnatado'},
    #         {'codigo': '19059090', 'descricao': 'Outros produtos de padaria'},
            
    #         # Casa e Decoração
    #         {'codigo': '94036000', 'descricao': 'Móveis de madeira para escritório'},
    #         {'codigo': '94035000', 'descricao': 'Móveis de madeira para quarto'},
    #         {'codigo': '85131000', 'descricao': 'Lanternas elétricas portáteis'},
    #         {'codigo': '73239300', 'descricao': 'Panelas de ferro ou aço'},
            
    #         # Materiais de Construção
    #         {'codigo': '72142000', 'descricao': 'Barras de ferro com nervuras'},
    #         {'codigo': '76129090', 'descricao': 'Recipientes de alumínio'},
    #         {'codigo': '25232900', 'descricao': 'Cimento Portland'},
    #         {'codigo': '69091900', 'descricao': 'Aparelhos cerâmicos para uso doméstico'},
            
    #         # Produtos de Higiene e Limpeza
    #         {'codigo': '34011990', 'descricao': 'Outros sabões'},
    #         {'codigo': '34022000', 'descricao': 'Preparações tensoativas para lavagem'},
    #         {'codigo': '33049900', 'descricao': 'Outros produtos de beleza'},
    #         {'codigo': '96081000', 'descricao': 'Canetas esferográficas'},
            
    #         # Medicamentos e Saúde
    #         {'codigo': '30049099', 'descricao': 'Outros medicamentos'},
    #         {'codigo': '90183900', 'descricao': 'Outros instrumentos médicos'},
    #         {'codigo': '30051000', 'descricao': 'Curativos adesivos'},
            
    #         # Brinquedos e Esportes
    #         {'codigo': '95030099', 'descricao': 'Outros brinquedos'},
    #         {'codigo': '95069990', 'descricao': 'Outros artigos de esporte'},
    #         {'codigo': '49019900', 'descricao': 'Outros livros'}
    #     ]
        
    #     try:
    #         db = next(get_db())
            
    #         for ncm in initial_ncms:
    #             db.execute(text("""
    #                 INSERT INTO ncms (codigo, descricao, data_atualizacao, fonte_atualizacao)
    #                 VALUES (:codigo, :descricao, NOW(), 'dados_iniciais')
    #                 ON CONFLICT (codigo) DO NOTHING
    #             """), {
    #                 'codigo': ncm['codigo'],
    #                 'descricao': ncm['descricao']
    #             })
            
    #         db.commit()
    #         db.close()
            
    #         logger.info(f"[OK] {len(initial_ncms)} NCMs iniciais populados")
    #         return True
            
    #     except Exception as e:
    #         logger.error(f"[X] Erro ao popular dados iniciais: {e}")
    #         return False
    
    def process_siscomex_json(self, json_content: str) -> Dict:
        """
        Processa arquivo JSON baixado do Siscomex após resolver captcha
        
        Args:
            json_content: Conteúdo do arquivo JSON como string
        
        Returns:
            Dict com resultado do processamento
        """
        logger.info("[?] Processando arquivo JSON do Siscomex...")
        
        try:
            # Parse do JSON
            if isinstance(json_content, str):
                data = json.loads(json_content)
            else:
                data = json_content
            
            # Extrai NCMs do JSON do Siscomex
            ncms = []
            
            # Estrutura específica do JSON do Siscomex (formato oficial)
            if isinstance(data, dict) and 'Nomenclaturas' in data:
                logger.info(f"[LIST] Processando estrutura oficial do Siscomex com {len(data['Nomenclaturas'])} nomenclaturas")
                
                # Processa cada nomenclatura da lista oficial
                for item in data['Nomenclaturas']:
                    ncm = self._extract_ncm_from_siscomex_item(item)
                    if ncm:
                        ncms.append(ncm)
                        
            elif isinstance(data, list):
                # Array direto de NCMs (formato antigo/alternativo)
                logger.info(f"[LIST] Processando formato de array com {len(data)} itens")
                for item in data:
                    ncm = self._extract_ncm_from_siscomex_item(item)
                    if ncm:
                        ncms.append(ncm)
                        
            elif isinstance(data, dict):
                # Outros formatos possíveis
                possible_keys = [
                    'nomenclaturas', 'ncms', 'resultados', 'dados', 
                    'classificacoes', 'items', 'lista'
                ]
                
                ncm_list = None
                for key in possible_keys:
                    if key in data and isinstance(data[key], list):
                        ncm_list = data[key]
                        logger.info(f"[LIST] Encontrada chave '{key}' com {len(ncm_list)} itens")
                        break
                
                if ncm_list:
                    for item in ncm_list:
                        ncm = self._extract_ncm_from_siscomex_item(item)
                        if ncm:
                            ncms.append(ncm)
                else:
                    # Tenta processar como item único
                    ncm = self._extract_ncm_from_siscomex_item(data)
                    if ncm:
                        ncms.append(ncm)
            
            if not ncms:
                return {
                    'success': False,
                    'message': 'Não foi possível extrair NCMs válidos do arquivo JSON. Verifique o formato do arquivo.'
                }
            
            # Processa todos os níveis hierárquicos (2, 4, 6, 8 dígitos)
            valid_ncms = []
            stats = {'total': 0, 'sinteticos': 0, 'analiticos': 0, 'invalidos': 0}
            
            for ncm in ncms:
                codigo = str(ncm.get('codigo', '')).replace('.', '').strip()
                descricao = ncm.get('descricao', '').strip()
                
                # Remove caracteres especiais da descrição (---, etc.)
                descricao = descricao.replace('--', '').replace('-', '').strip()
                
                # Valida se é um código NCM válido (2, 4, 6 ou 8 dígitos)
                if codigo and descricao and codigo.isdigit() and len(codigo) in [2, 4, 6, 8]:
                    # Determina tipo baseado no tamanho do código
                    tipo = 'analitico' if len(codigo) == 8 else 'sintetico'
                    
                    valid_ncms.append({
                        'codigo': codigo,
                        'descricao': descricao,
                        'tipo': tipo,
                        'data_inicio': ncm.get('data_inicio'),
                        'data_fim': ncm.get('data_fim'),
                        'unidade': ncm.get('unidade', ''),
                        'tipo_ato': ncm.get('tipo_ato'),
                        'numero_ato': ncm.get('numero_ato'),
                        'ano_ato': ncm.get('ano_ato')
                    })
                    
                    stats['total'] += 1
                    if tipo == 'sintetico':
                        stats['sinteticos'] += 1
                    else:
                        stats['analiticos'] += 1
                else:
                    stats['invalidos'] += 1
            
            logger.info(f"[DATA] Processamento completo: {stats['total']} válidos ({stats['sinteticos']} sintéticos, {stats['analiticos']} analíticos), {stats['invalidos']} inválidos")
            
            if not valid_ncms:
                return {
                    'success': False,
                    'message': f'Nenhum NCM válido encontrado. Total processado: {len(ncms)}, Inválidos: {stats["invalidos"]}'
                }
            
            # Sincroniza com banco
            inserted, updated = self.sync_ncm_to_database(valid_ncms, force=True)
            
            logger.info(f"[OK] Processamento JSON concluído: {inserted} inseridos, {updated} atualizados")
            
            return {
                'success': True,
                'message': f'Arquivo JSON processado com sucesso! {inserted} NCMs inseridos, {updated} atualizados. Total processado: {len(valid_ncms)}',
                'inserted': inserted,
                'updated': updated,
                'total_processed': len(valid_ncms),
                'total_valid': len(valid_ncms)
            }
            
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'message': f'Erro ao fazer parse do JSON: {str(e)}. Verifique se o arquivo está em formato JSON válido.'
            }
        except Exception as e:
            logger.error(f"[X] Erro ao processar JSON do Siscomex: {e}")
            return {
                'success': False,
                'message': f'Erro no processamento: {str(e)}'
            }
    
    def _extract_ncm_from_siscomex_item(self, item: Dict) -> Optional[Dict]:
        """
        Extrai dados de NCM de um item do JSON do Siscomex
        
        Estrutura esperada do JSON do Siscomex:
        {
            "Codigo": "01.01",
            "Descricao": "Animais vivos da espécie equina.",
            "Data_Inicio": "01/04/2022",
            "Data_Fim": "31/12/9999",
            "Tipo_Ato_Ini": "Res Camex",
            "Numero_Ato_Ini": "272",
            "Ano_Ato_Ini": "2021"
        }
        
        Args:
            item: Item individual do JSON
            
        Returns:
            Dict com dados do NCM ou None se inválido
        """
        if not isinstance(item, dict):
            return None
        
        # Extrai código NCM (campo "Codigo" do Siscomex)
        codigo = item.get('Codigo', '').strip()
        if not codigo:
            return None
        
        # Remove pontos do código NCM e valida
        codigo_limpo = codigo.replace('.', '').strip()
        
        # Extrai descrição (campo "Descricao" do Siscomex)  
        descricao = item.get('Descricao', '').strip()
        if not descricao:
            return None
        
        # Processa datas do Siscomex (formato DD/MM/YYYY)
        data_inicio = self._parse_siscomex_date(item.get('Data_Inicio'))
        data_fim = self._parse_siscomex_date(item.get('Data_Fim'))
        
        # Extrai informações do ato normativo
        tipo_ato = item.get('Tipo_Ato_Ini', '').strip()
        numero_ato = item.get('Numero_Ato_Ini', '').strip()
        ano_ato = item.get('Ano_Ato_Ini', '').strip()
        
        return {
            'codigo': codigo_limpo,
            'descricao': descricao,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'unidade': '',  # Não disponível no JSON do Siscomex
            'tipo_ato': tipo_ato,
            'numero_ato': numero_ato,
            'ano_ato': ano_ato
        }
    
    def _parse_siscomex_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        Converte data do formato DD/MM/YYYY (Siscomex) para YYYY-MM-DD (banco)
        
        Args:
            date_str: Data no formato DD/MM/YYYY ou None
            
        Returns:
            Data no formato YYYY-MM-DD ou None se inválida
        """
        if not date_str or not isinstance(date_str, str):
            return None
        
        try:
            # Parse da data DD/MM/YYYY
            from datetime import datetime
            date_obj = datetime.strptime(date_str.strip(), '%d/%m/%Y')
            
            # Retorna no formato YYYY-MM-DD
            return date_obj.strftime('%Y-%m-%d')
            
        except (ValueError, AttributeError):
            logger.warning(f"Não foi possível processar data: {date_str}")
            return None

    def get_ncm_stats(self) -> Dict:
        """Retorna estatísticas dos NCMs"""
        # Garante que há dados iniciais
        # self.populate_initial_ncm_data()
        
        last_sync = self.get_last_sync_date()
        days_since_sync = None
        if last_sync:
            days_since_sync = (datetime.now() - last_sync).days
            
        return {
            'local_count': self.get_local_ncm_count(),
            'last_sync': last_sync,
            'should_sync': self.should_sync(),
            'days_since_sync': days_since_sync
        }

# Instância global do serviço
ncm_service = NCMService()