"""
services/product_classification_service.py

Serviço de classificação fiscal de produtos via IA.
Extrai a lógica do endpoint api_sugestao_tributaria (admin_routes.py) para
uma classe reutilizável, separando a lógica de negócio da camada de rota.

Uso:
    from services.product_classification_service import ProductClassificationService

    svc = ProductClassificationService(db)
    result = svc.classify(descricao='Parafuso aço inox M6', cliente_id=42)
    # result = {'sucesso': True, 'classificacao': {...}, 'ids': {...}}
"""
import logging
import requests as req_lib
from sqlalchemy import text

logger = logging.getLogger(__name__)

IA_SERVICE_URL = 'http://localhost:8081'
IA_TIMEOUT_SECONDS = 150  # LLM pode ser lenta — 150 s + margem


class ProductClassificationService:
    """
    Orquestra a classificação fiscal de produtos através do serviço de IA
    e converte os códigos retornados (NCM, CFOP, CST, CSOSN) nos IDs
    correspondentes do banco de dados.
    """

    def __init__(self, db):
        self._db = db

    # ─────────────────────────────────────────────────────────────────────────
    # Ponto de entrada público
    # ─────────────────────────────────────────────────────────────────────────

    def classify(self, descricao: str, cliente_id=None,
                 tipo_item: str = 'Produto',
                 unidade_comercial: str = 'UN',
                 codigo_interno: str = '') -> dict:
        """
        Classifica um produto via IA e enriquece com IDs do banco.

        :param descricao:         Descrição do produto (obrigatória)
        :param cliente_id:        ID do cliente — usado para enriquecer contexto (UF, regime)
        :param tipo_item:         'Produto' ou 'Serviço'
        :param unidade_comercial: Unidade de medida (default 'UN')
        :param codigo_interno:    Código interno do produto (opcional)
        :returns: dict com chaves 'sucesso', 'classificacao', 'ids' e descrições opcionais.
        :raises ValueError: se descricao for vazia.
        :raises ProductClassificationUnavailable: se serviço de IA não responder.
        """
        if not descricao:
            raise ValueError('Descrição do produto é obrigatória')

        payload = {
            'descricao': descricao,
            'tipo_item': tipo_item,
            'unidade_comercial': unidade_comercial,
            'codigo_interno': codigo_interno,
            'cliente_id': cliente_id,
        }

        # Enriquecer com dados do cliente (UF, regime)
        if cliente_id:
            payload.update(self._enrich_from_client(cliente_id))

        classificacao = self._call_ia(payload)
        resultado = self._resolve_ids(classificacao)
        return resultado

    # ─────────────────────────────────────────────────────────────────────────
    # Privado — chamada ao serviço de IA
    # ─────────────────────────────────────────────────────────────────────────

    def _enrich_from_client(self, cliente_id) -> dict:
        """Busca UF e regime tributário do cliente para contextualizar a IA."""
        try:
            row = self._db.execute(text("""
                SELECT c.uf, rt.nome AS regime_nome
                FROM clientes c
                LEFT JOIN regimes_tributarios rt
                       ON c.regime_tributario_id = rt.regime_tributario_id
                WHERE c.cliente_id = :cid
            """), {'cid': cliente_id}).fetchone()

            if row:
                d = dict(row._mapping)
                logger.debug('[IA] Contexto cliente: UF=%s, Regime=%s',
                             d.get('uf'), d.get('regime_nome'))
                return {
                    'uf_origem': d.get('uf'),
                    'regime_tributario': d.get('regime_nome'),
                }
        except Exception as e:
            logger.warning('[IA] Não foi possível enriquecer contexto do cliente %s: %s', cliente_id, e)
        return {}

    def _call_ia(self, payload: dict) -> dict:
        """
        Chama o serviço de IA e retorna a classificação bruta.
        Levanta ProductClassificationUnavailable se a chamada falhar.
        """
        logger.debug('[IA] Chamando API IA: descricao=%s', payload.get('descricao'))
        try:
            resp = req_lib.post(
                f'{IA_SERVICE_URL}/sugestao',
                json=payload,
                timeout=IA_TIMEOUT_SECONDS,
            )
        except req_lib.exceptions.RequestException as e:
            logger.error('[IA] Falha de conexão com serviço IA: %s', e)
            raise ProductClassificationUnavailable(
                'Serviço de IA não está disponível (porta 8081).'
            ) from e

        if resp.status_code != 200:
            logger.error('[IA] API IA retornou status %s', resp.status_code)
            raise ProductClassificationError(
                f'Erro HTTP {resp.status_code} ao consultar API de IA'
            )

        result = resp.json()

        if result.get('erro'):
            raise ProductClassificationError(result['erro'])

        if not result.get('ncm'):
            raise ProductClassificationError(
                'Resposta da API de IA inválida — NCM ausente'
            )

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Privado — resolução de IDs no banco
    # ─────────────────────────────────────────────────────────────────────────

    def _resolve_ids(self, classificacao: dict) -> dict:
        """
        Converte os códigos retornados pela IA (NCM, CFOP, CST, CSOSN)
        nos IDs numéricos do banco de dados.
        """
        resultado: dict = {
            'sucesso': True,
            'classificacao': classificacao,
            'ids': {},
        }

        # NCM
        ncm_codigo = classificacao.get('ncm')
        if ncm_codigo:
            row = self._db.execute(text("""
                SELECT ncm_id, codigo, descricao
                FROM ncms
                WHERE REPLACE(codigo, '.', '') = :codigo
                LIMIT 1
            """), {'codigo': ncm_codigo.replace('.', '')}).fetchone()
            if row:
                d = dict(row._mapping)
                resultado['ids']['ncm_id'] = d['ncm_id']
                resultado['ncm_descricao'] = d['descricao']
                logger.debug('[IA] NCM %s → id=%s', d['codigo'], d['ncm_id'])
            else:
                logger.warning('[IA] NCM %s não encontrado no banco', ncm_codigo)

        # CFOP
        cfop_codigo = classificacao.get('cfop')
        if cfop_codigo:
            row = self._db.execute(text("""
                SELECT cfop_id, cfop, descricao
                FROM cfops
                WHERE REPLACE(cfop, '.', '') = :cfop OR cfop = :cfop
                LIMIT 1
            """), {'cfop': cfop_codigo}).fetchone()
            if row:
                d = dict(row._mapping)
                resultado['ids']['cfop_id'] = d['cfop_id']
                resultado['cfop_descricao'] = d['descricao']
                logger.debug('[IA] CFOP %s → id=%s', d['cfop'], d['cfop_id'])
            else:
                logger.warning('[IA] CFOP %s não encontrado no banco', cfop_codigo)

        # CST ICMS
        cst_codigo = classificacao.get('cst')
        if cst_codigo:
            row = self._db.execute(text("""
                SELECT cst_id, codigo, descricao
                FROM cst_icms
                WHERE codigo = :cst
                LIMIT 1
            """), {'cst': cst_codigo}).fetchone()
            if row:
                d = dict(row._mapping)
                resultado['ids']['cst_id'] = d['cst_id']
                resultado['cst_descricao'] = d['descricao']

        # CSOSN
        csosn_codigo = classificacao.get('csosn')
        if csosn_codigo:
            row = self._db.execute(text("""
                SELECT csosn_id, codigo, descricao
                FROM csosn_icms
                WHERE codigo = :csosn
                LIMIT 1
            """), {'csosn': csosn_codigo}).fetchone()
            if row:
                d = dict(row._mapping)
                resultado['ids']['csosn_id'] = d['csosn_id']
                resultado['csosn_descricao'] = d['descricao']

        # CEST (texto livre, sem tabela)
        cest = classificacao.get('cest')
        if cest:
            resultado['ids']['cest'] = cest

        return resultado


# ─────────────────────────────────────────────────────────────────────────────
# Exceções customizadas
# ─────────────────────────────────────────────────────────────────────────────

class ProductClassificationError(Exception):
    """Erro de negócio retornado pelo serviço de IA."""


class ProductClassificationUnavailable(Exception):
    """Serviço de IA inacessível (timeout ou conexão recusada)."""
