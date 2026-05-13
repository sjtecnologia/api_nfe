"""
database/repositories/product_repository.py

Repositório de produtos — centraliza todas as queries de produtos,
eliminando SQL bruto espalhado pelas rotas.

Uso:
    from database.repositories.product_repository import ProductRepository

    repo = ProductRepository(db)
    result = repo.search_for_select2(
        cliente_id=42, term='parafuso', page=1
    )
    # result = {'results': [...], 'pagination': {'more': False}}
"""
from sqlalchemy import text


class ProductRepository:
    """Acesso a dados de produtos com suporte a busca paginada para Select2."""

    PER_PAGE = 30

    def __init__(self, db):
        self._db = db

    # ─────────────────────────────────────────────────────────────────────────
    # Busca para Select2
    # ─────────────────────────────────────────────────────────────────────────

    def search_for_select2(self, cliente_id, term: str = '', page: int = 1) -> dict:
        """
        Retorna produtos paginados no formato esperado pelo Select2.

        :param cliente_id: ID do cliente/emitente
        :param term:       Termo de busca (descrição ou código interno)
        :param page:       Número da página (1-based)
        :returns: {'results': [...], 'pagination': {'more': bool}}
        """
        offset = (page - 1) * self.PER_PAGE
        params: dict = {
            'cliente_id': cliente_id,
            'limit': self.PER_PAGE + 1,
            'offset': offset,
        }
        where_extra = ''
        if term:
            where_extra = " AND (p.descricao ILIKE :q OR p.codigo_interno ILIKE :q)"
            params['q'] = f'%{term}%'

        rows = self._db.execute(text(f"""
            SELECT
                p.produto_id,
                p.codigo_interno,
                p.descricao,
                p.preco_unitario_padrao,
                p.unidade_comercial,
                p.origem_mercadoria,
                n.codigo            AS ncm_codigo,
                cf.cfop             AS cfop_codigo,
                cst.codigo          AS cst_codigo,
                cs.codigo           AS csosn_codigo,
                p.classificacao_ibs_cbs_id
            FROM produtos p
            LEFT JOIN ncms         n   ON p.ncm_id    = n.ncm_id
            LEFT JOIN cfops        cf  ON p.cfop_id   = cf.cfop_id
            LEFT JOIN cst_icms     cst ON p.cst_id    = cst.cst_id
            LEFT JOIN csosn_icms   cs  ON p.csosn_id  = cs.csosn_id
            WHERE p.cliente_id = :cliente_id
              AND p.ativo = true{where_extra}
            ORDER BY p.descricao
            LIMIT :limit OFFSET :offset
        """), params).fetchall()

        has_more = len(rows) > self.PER_PAGE
        rows = rows[: self.PER_PAGE]

        return {
            'results': [self._row_to_select2(r) for r in rows],
            'pagination': {'more': has_more},
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Busca por ID
    # ─────────────────────────────────────────────────────────────────────────

    def get_by_id(self, produto_id: int, cliente_id: int) -> dict | None:
        """
        Retorna dicionário completo de um produto ou None se não encontrado.
        Valida que o produto pertence ao cliente informado.
        """
        row = self._db.execute(text("""
            SELECT
                p.produto_id, p.codigo_interno, p.descricao,
                p.preco_unitario_padrao, p.unidade_comercial, p.origem_mercadoria,
                n.codigo AS ncm_codigo, cf.cfop AS cfop_codigo,
                cst.codigo AS cst_codigo, cs.codigo AS csosn_codigo,
                p.classificacao_ibs_cbs_id, p.ativo
            FROM produtos p
            LEFT JOIN ncms        n   ON p.ncm_id   = n.ncm_id
            LEFT JOIN cfops       cf  ON p.cfop_id  = cf.cfop_id
            LEFT JOIN cst_icms    cst ON p.cst_id   = cst.cst_id
            LEFT JOIN csosn_icms  cs  ON p.csosn_id = cs.csosn_id
            WHERE p.produto_id = :produto_id
              AND p.cliente_id = :cliente_id
        """), {'produto_id': produto_id, 'cliente_id': cliente_id}).fetchone()

        if not row:
            return None
        return self._row_to_dict(row)

    # ─────────────────────────────────────────────────────────────────────────
    # Privado — mapeamento de linhas
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _to_dict(row) -> dict:
        """Converte RowProxy de SQLAlchemy para dicionário Python."""
        if hasattr(row, '_mapping'):
            return dict(row._mapping)
        if hasattr(row, '_asdict'):
            return row._asdict()
        # Fallback posicional (não recomendado mas tolerado)
        keys = [
            'produto_id', 'codigo_interno', 'descricao', 'preco_unitario_padrao',
            'unidade_comercial', 'origem_mercadoria', 'ncm_codigo', 'cfop_codigo',
            'cst_codigo', 'csosn_codigo', 'classificacao_ibs_cbs_id',
        ]
        return {k: v for k, v in zip(keys, row)}

    def _row_to_select2(self, row) -> dict:
        d = self._to_dict(row)
        codigo = d.get('codigo_interno') or ''
        descricao = d.get('descricao') or ''
        text_label = f"{codigo} - {descricao}".strip(' -') if codigo else descricao
        return {
            'id':                       d.get('produto_id'),
            'text':                     text_label,
            'codigo':                   codigo,
            'preco':                    float(d.get('preco_unitario_padrao') or 0),
            'unidade':                  d.get('unidade_comercial') or 'UN',
            'ncm':                      d.get('ncm_codigo') or '',
            'cfop':                     d.get('cfop_codigo') or '',
            'cst':                      d.get('cst_codigo') or '',
            'csosn':                    d.get('csosn_codigo') or '',
            'origem':                   d.get('origem_mercadoria') if d.get('origem_mercadoria') is not None else 0,
            'classificacao_ibs_cbs_id': d.get('classificacao_ibs_cbs_id') or '',
        }

    def _row_to_dict(self, row) -> dict:
        return self._row_to_select2(row)
