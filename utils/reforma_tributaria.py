from datetime import date, datetime


_INICIO_VIGENCIA_2027 = date(2027, 1, 1)


def vigencia_reforma(data_emissao):
    if data_emissao is None:
        raise ValueError("dhEmi é obrigatório para determinar a vigência da reforma")
    if isinstance(data_emissao, datetime):
        data = data_emissao.date()
    elif isinstance(data_emissao, date):
        data = data_emissao
    else:
        valor = str(data_emissao).strip()
        if "T" in valor or " " in valor:
            data = datetime.fromisoformat(valor.replace("Z", "+00:00")).date()
        else:
            data = date.fromisoformat(valor)

    return 2026 if data < _INICIO_VIGENCIA_2027 else 2027
