import pytest

from utils.reforma_tributaria import vigencia_reforma


@pytest.mark.parametrize(
    ("data_emissao", "vigencia_esperada"),
    [("2026-12-31", 2026), ("2027-01-01", 2027)],
)
def test_vigencia_reforma_muda_em_2027(data_emissao, vigencia_esperada):
    assert vigencia_reforma(data_emissao) == vigencia_esperada
