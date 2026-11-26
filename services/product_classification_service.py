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
import json
import re
from sqlalchemy import text

from services.ai_providers import AIProviderError, LegacyNcmClassificationProvider
from services.ai_service import AIResponseFormatError, AIService, AIServiceConfig, AIUsageLimitExceeded

logger = logging.getLogger(__name__)


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
                 codigo_interno: str = '',
                 user_id=None) -> dict:
        """
        Classifica um produto via IA e enriquece com IDs do banco.

        :param descricao:         Descrição do produto (obrigatória)
        :param cliente_id:        ID do cliente — usado para enriquecer contexto (UF, regime)
        :param tipo_item:         'Produto' ou 'Serviço'
        :param unidade_comercial: Unidade de medida (default 'UN')
        :param codigo_interno:    Código interno do produto (opcional)
        :param user_id:          Usuário autenticado (opcional, para log/limites)
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

        classificacao = self._call_ia(payload, cliente_id=cliente_id, user_id=user_id)
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

    def _call_ia(self, payload: dict, cliente_id=None, user_id=None) -> dict:
        """
        Chama o serviço de IA e retorna a classificação bruta.
        Levanta ProductClassificationUnavailable se a chamada falhar.
        """
        logger.debug('[IA] Chamando classificador legado via AIService: descricao=%s', payload.get('descricao'))
        ai_service = AIService(
            db=self._db,
            provider=LegacyNcmClassificationProvider(),
            config=AIServiceConfig(provider_url=''),
        )
        try:
            result = ai_service.generate_json(
                prompt_name='product_classification',
                user_message=json.dumps(payload, ensure_ascii=False),
                cliente_id=cliente_id,
                user_id=user_id,
                functionality='classificacao_produto',
                tools_scope='products',
                record=True,
            )
        except AIProviderError as e:
            logger.error('[IA] Falha de conexão com classificador legado: %s', e)
            raise ProductClassificationUnavailable(
                'Serviço de IA não está disponível (porta 8081).'
            ) from e
        except (AIResponseFormatError, AIUsageLimitExceeded) as e:
            logger.error('[IA] Erro ao processar classificação: %s', e)
            raise ProductClassificationError(str(e)) from e

        parsed = result.get('parsed') or {}
        result = self._normalize_classificacao(parsed)
        diagnostico = {
            'provider': result.get('_provider') or parsed.get('_provider') or (result and ai_service.provider.provider_name),
            'model': result.get('_model') or parsed.get('_model') or None,
        }

        if result.get('erro'):
            raise ProductClassificationError(result['erro'])

        if not result.get('ncm'):
            raise ProductClassificationError(
                'Resposta da API de IA inválida — NCM ausente'
            )

        if diagnostico['provider']:
            result['_diagnostico'] = diagnostico

        return result

    def _normalize_classificacao(self, raw: dict) -> dict:
        """Normaliza chaves e formatos retornados pela IA para reduzir variações."""
        normalized = dict(raw)

        if not normalized.get('cst') and normalized.get('cst_icms'):
            normalized['cst'] = str(normalized.get('cst_icms')).strip()
        if not normalized.get('csosn') and normalized.get('csosn_icms'):
            normalized['csosn'] = str(normalized.get('csosn_icms')).strip()

        normalized['ncm'] = self._digits_only(normalized.get('ncm'))
        normalized['cfop'] = self._digits_only(normalized.get('cfop'))
        normalized['cst'] = self._digits_only(normalized.get('cst'))
        normalized['csosn'] = self._digits_only(normalized.get('csosn'))
        normalized['cest'] = self._digits_only(normalized.get('cest'))

        return normalized

    @staticmethod
    def _digits_only(value):
        if value is None:
            return None
        cleaned = re.sub(r'\D+', '', str(value))
        return cleaned or None

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
            'avisos': [],
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
                # Fallback: tenta subitem aproximado por prefixo (6 dígitos)
                prefixo_ncm = ncm_codigo[:6]
                row_prefixo = None
                if len(prefixo_ncm) == 6:
                    row_prefixo = self._db.execute(text("""
                        SELECT ncm_id, codigo, descricao
                        FROM ncms
                        WHERE REPLACE(codigo, '.', '') LIKE :prefixo
                        ORDER BY codigo
                        LIMIT 1
                    """), {'prefixo': f'{prefixo_ncm}%'}).fetchone()

                if row_prefixo:
                    d = dict(row_prefixo._mapping)
                    resultado['ids']['ncm_id'] = d['ncm_id']
                    resultado['ncm_descricao'] = d['descricao']
                    resultado['avisos'].append(
                        f'NCM {ncm_codigo} não encontrado exatamente; aplicado aproximado {d.get("codigo")}.'
                    )
                    logger.warning('[IA] NCM %s não exato; usando aproximado %s', ncm_codigo, d.get('codigo'))
                else:
                    logger.warning('[IA] NCM %s não encontrado no banco', ncm_codigo)
                    resultado['avisos'].append(f'NCM {ncm_codigo} não encontrado no cadastro local')

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
                resultado['avisos'].append(f'CFOP {cfop_codigo} não encontrado no cadastro local')

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
            else:
                # Fallback: aceita variações como 00 vs 000
                rows = self._db.execute(text("""
                    SELECT cst_id, codigo, descricao
                    FROM cst_icms
                """)).fetchall()

                alvo = self._digits_only(cst_codigo) or ''
                alvo_norm = alvo.zfill(3)
                match = None
                for raw in rows:
                    d = dict(raw._mapping)
                    codigo_norm = self._digits_only(d.get('codigo')) or ''
                    if codigo_norm.zfill(3) == alvo_norm:
                        match = d
                        break

                if match:
                    resultado['ids']['cst_id'] = match['cst_id']
                    resultado['cst_descricao'] = match['descricao']
                    resultado['avisos'].append(
                        f'CST {cst_codigo} ajustado para formato local {match.get("codigo")}.'
                    )
                    logger.warning('[IA] CST %s não exato; usando %s', cst_codigo, match.get('codigo'))

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

        diagnostico = classificacao.get('_diagnostico')
        if diagnostico:
            resultado['diagnostico'] = diagnostico

        return resultado


# ─────────────────────────────────────────────────────────────────────────────
# Exceções customizadas
# ─────────────────────────────────────────────────────────────────────────────

class ProductClassificationError(Exception):
    """Erro de negócio retornado pelo serviço de IA."""


class ProductClassificationUnavailable(Exception):
    """Serviço de IA inacessível (timeout ou conexão recusada)."""
