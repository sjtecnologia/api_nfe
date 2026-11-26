"""
Utilitários de paginação.
Elimina o cálculo manual de page/per_page/offset/total_pages repetido em 4 lugares.
"""
from dataclasses import dataclass
from flask import request


@dataclass
class Page:
    """Encapsula os parâmetros de paginação de uma requisição."""
    page: int
    per_page: int
    offset: int
    total: int = 0

    @property
    def total_pages(self) -> int:
        if not self.per_page:
            return 0
        return (self.total + self.per_page - 1) // self.per_page

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    def as_dict(self) -> dict:
        return {
            'page': self.page,
            'per_page': self.per_page,
            'total': self.total,
            'total_pages': self.total_pages,
            'has_next': self.has_next,
            'has_prev': self.has_prev,
        }


def get_page(default_per_page: int = 20, max_per_page: int = 200) -> Page:
    """
    Extrai e valida os parâmetros de paginação da request atual.

    Uso:
        from utils.pagination import get_page

        pag = get_page(default_per_page=50)
        rows = db.execute(text("SELECT ... LIMIT :lim OFFSET :off"),
                          {'lim': pag.per_page, 'off': pag.offset}).fetchall()
        total = db.execute(text("SELECT COUNT(*) FROM ...")).scalar()
        pag.total = total
        return render_template('lista.html', rows=rows, pag=pag)
    """
    page = max(1, request.args.get('page', 1, type=int))
    per_page = min(
        max(1, request.args.get('per_page', default_per_page, type=int)),
        max_per_page
    )
    return Page(page=page, per_page=per_page, offset=(page - 1) * per_page)
