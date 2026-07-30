"""
Gerador do DANFSe (Documento Auxiliar da NFS-e Nacional)
Baseado na Nota Técnica SE/CGNFS-e nº 008 - Versão 1.02 (14/07/2026)

Escopo e formato real do XML:
São José do Rio Preto/SP está no Ambiente de Dados Nacional (ADN) desde
janeiro/2026. A prefeitura usa o GISS Online como "sistema do município": ele
recebe o RPS, converte para NFS-e, registra no ADN e devolve um XML no formato
`CompNfse` (namespace `giss.com.br`, baseado em ABRASF 2.04 estendido pela
Reforma Tributária) — e NÃO no formato puro `NFSe/infNFSe/DPS/infDPS` descrito
"cru" na NT008. A chave de acesso oficial do ADN vem no campo
`CompNfse/ChaveNotaNacional` (ver `docs/nfse_sjrp_giss/schemas_modificados_gissv2/`).

Este módulo extrai os dados a partir desse `CompNfse` real (retornado por
`services/nfse_service.py::_processar_resposta_consulta`) e monta o DANFSe
seguindo o layout do Anexo I da NT008. Se o XML não tiver `ChaveNotaNacional`
(ex.: NFS-e antiga, pré-migração, ou XML de outro formato), a geração é
recusada (`XmlNaoENacionalError`) para não emitir um DANFSe sem chave de
acesso nacional válida.
"""

import io
import logging
from typing import Any, Dict, Optional, Union

from lxml import etree

logger = logging.getLogger(__name__)


class XmlNaoENacionalError(Exception):
    """Levantado quando o XML informado não tem chave de acesso do ADN (ChaveNotaNacional)."""


def _root(xml_content: Union[str, bytes]) -> Any:
    xml_bytes = xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content
    return etree.fromstring(xml_bytes)


def _txt(el: Optional[Any], tag: str) -> Optional[str]:
    """Busca o texto da primeira ocorrência de `tag` (qualquer namespace) dentro de `el`."""
    if el is None:
        return None
    found = el.find(f".//{{*}}{tag}")
    if found is None or not found.text:
        return None
    return found.text.strip()


def _attr_id(el: Optional[Any]) -> Optional[str]:
    if el is None:
        return None
    return el.get("Id") or el.get("id")


def extrair_dados_nfse_nacional(xml_content: Union[str, bytes]) -> Dict[str, Any]:
    """
    Extrai os campos exigidos pelo item 2.1 da NT008 a partir do XML `CompNfse`
    retornado pelo GISS Online (SJRP, Ambiente de Dados Nacional).
    Levanta `XmlNaoENacionalError` se não houver `ChaveNotaNacional`.
    """
    root = _root(xml_content)

    comp_nfse = root if root.tag.endswith("CompNfse") else root.find(".//{*}CompNfse")
    if comp_nfse is None:
        comp_nfse = root  # fallback: talvez o XML já seja o CompNfse "puro"

    chave_nacional = _txt(comp_nfse, "ChaveNotaNacional")
    if not chave_nacional:
        raise XmlNaoENacionalError(
            "O XML informado não possui ChaveNotaNacional (chave de acesso da "
            "NFS-e no Ambiente de Dados Nacional). Não é possível gerar o "
            "DANFSe sem essa chave — verifique se a NFS-e foi processada com "
            "sucesso pelo GISS/ADN."
        )

    inf_nfse = comp_nfse.find(".//{*}InfNfse")
    valores_nfse = inf_nfse.find(".//{*}ValoresNfse") if inf_nfse is not None else None
    prestador_servico = inf_nfse.find(".//{*}PrestadorServico") if inf_nfse is not None else None
    decl_prest = comp_nfse.find(".//{*}InfDeclaracaoPrestacaoServico")
    servico = decl_prest.find(".//{*}Servico") if decl_prest is not None else None
    valores_serv = servico.find(".//{*}Valores") if servico is not None else None
    ibscbs = valores_serv.find(".//{*}IBSCBS") if valores_serv is not None else None
    ibscbs_total = comp_nfse.find(".//{*}IBSCBSTotal")
    prestador = decl_prest.find(".//{*}Prestador") if decl_prest is not None else None
    tomador = decl_prest.find(".//{*}TomadoresServico") if decl_prest is not None else None
    rps = decl_prest.find(".//{*}Rps") if decl_prest is not None else None

    def cpf_cnpj(el: Optional[Any]) -> Optional[str]:
        if el is None:
            return None
        cpf_cnpj_el = el.find(".//{*}CpfCnpj")
        return _txt(cpf_cnpj_el, "Cnpj") or _txt(cpf_cnpj_el, "Cpf") if cpf_cnpj_el is not None else None

    dados: Dict[str, Any] = {
        "chave_acesso": chave_nacional,
        "numero_nfse": _txt(inf_nfse, "Numero"),
        "codigo_verificacao": _txt(inf_nfse, "CodigoVerificacao"),
        "dh_proc": _txt(inf_nfse, "DataEmissao"),
        "competencia": _txt(decl_prest, "Competencia"),
        "numero_dps": _txt(rps, "Numero"),
        "serie_dps": _txt(rps, "Serie"),
        "dh_emi_dps": _txt(rps, "DataEmissao"),
        "tp_emit": "Prestador",
        "c_stat": "2" if comp_nfse.find(".//{*}NfseCancelamento") is not None else "1",
        "fin_nfse": _txt(ibscbs, "finNFSe"),
        "tp_amb": None,  # não vem no CompNfse do GISS; informar via parâmetro se necessário
        "amb_ger": "GISS Online (ADN)",
        "x_loc_emi": "São José do Rio Preto/SP",
        # Prestador
        "prest_cnpj": cpf_cnpj(prestador),
        "prest_im": _txt(prestador, "InscricaoMunicipal"),
        "prest_fone": _txt(prestador_servico, "Telefone"),
        "prest_nome": _txt(prestador_servico, "RazaoSocial"),
        "prest_email": _txt(prestador_servico, "Email"),
        "prest_simples": _txt(decl_prest, "OptanteSimplesNacional"),
        # Tomador
        "toma_cnpj": cpf_cnpj(tomador),
        "toma_nome": _txt(tomador, "RazaoSocial"),
        "toma_fone": _txt(tomador, "Telefone"),
        "toma_email": _txt(tomador, "Email"),
        # Destinatário — GISS não tem bloco próprio de "Destinatário da Operação"
        # separado do Tomador (diferente do schema nacional puro NFSe/infNFSe).
        "dest_cnpj": None,
        "dest_nome": None,
        # Serviço
        "c_trib_nac": _txt(servico, "ItemListaServico") or _txt(servico, "CodigoTributacaoMunicipio"),
        "c_nbs": _txt(servico, "CodigoNbs"),
        "x_desc_serv": _txt(servico, "Discriminacao"),
        "x_trib_nac": None,
        # ISSQN (valores oficiais da NFS-e, em InfNfse/ValoresNfse)
        "trib_issqn": "1" if valores_nfse is not None and _txt(valores_nfse, "ValorIss") else None,
        "v_bc_issqn": _txt(valores_nfse, "BaseCalculo"),
        "aliq_issqn": _txt(valores_nfse, "Aliquota"),
        "v_issqn": _txt(valores_nfse, "ValorIss"),
        # IBS/CBS
        "cst_ibscbs": _txt(ibscbs, "CST"),
        "c_class_trib": _txt(ibscbs, "cClassTrib"),
        "v_ibs_tot": _txt(ibscbs_total, "vIBSTot"),
        "v_cbs_tot": _txt(ibscbs_total, "vCBS"),
        # Totais
        "v_serv": _txt(valores_serv, "ValorServicos"),
        "v_liq": _txt(valores_nfse, "ValorLiquidoNfse"),
        "v_tot_nf": _txt(ibscbs_total, "vTotNF"),
        # Complementares
        "x_inf_comp": _txt(decl_prest, "InformacoesComplementares"),
    }
    return dados



def _fmt_moeda(valor: Optional[str]) -> str:
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    except (TypeError, ValueError):
        return "-"


def gerar_danfse_pdf(
    xml_content: Union[str, bytes],
    output_pdf_path: str,
    ambiente: str = "producao",
) -> bool:
    """
    Gera o DANFSe em PDF (layout resumido, Anexo I da NT008) a partir do
    `CompNfse` retornado pelo GISS Online (SJRP/ADN). Retorna True em caso de
    sucesso.

    Args:
        xml_content: XML `CompNfse` (ou envelope que o contenha).
        output_pdf_path: caminho de saída do PDF.
        ambiente: "producao" ou "homologacao" — usado para exibir o aviso
            "NFS-e SEM VALIDADE JURÍDICA", já que o `CompNfse` do GISS não
            carrega essa informação.

    Levanta `XmlNaoENacionalError` se o XML não tiver `ChaveNotaNacional` —
    quem chamar deve tratar esse erro e explicar ao usuário que o documento
    não é elegível para DANFSe.
    """
    dados = extrair_dados_nfse_nacional(xml_content)
    dados["tp_amb"] = "2" if ambiente == "homologacao" else "1"
    return renderizar_danfse_pdf(dados, output_pdf_path)


def renderizar_danfse_pdf(dados: Dict[str, Any], output_pdf_path: str) -> bool:
    """
    Desenha o PDF do DANFSe (layout resumido, Anexo I da NT008) a partir de um
    dicionário de dados já extraído/montado — usado tanto pela NFS-e real
    (via `extrair_dados_nfse_nacional`) quanto por uma prévia/rascunho
    pré-emissão (montada diretamente do formulário, sem chave nacional).

    Campos esperados em `dados` (todos opcionais, exibem "-" se ausentes):
    ver `extrair_dados_nfse_nacional` para a lista completa de chaves. Chave
    extra opcional: `watermark_texto` — se definida, sobrepõe o texto padrão
    de marca d'água (que por padrão só aparece quando `c_stat == "2"`,
    indicando NFS-e cancelada).
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    try:
        import qrcode
        from reportlab.lib.utils import ImageReader

        qr_disponivel = True
    except ImportError:
        qr_disponivel = False

    largura, altura = A4
    margem = 8 * mm
    c = canvas.Canvas(output_pdf_path, pagesize=A4)


    y = altura - margem

    # --- Cabeçalho ---
    c.setFillColor(colors.Color(0.93, 0.93, 0.93))
    c.rect(margem, y - 16 * mm, largura - 2 * margem, 16 * mm, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(largura / 2, y - 6 * mm, "DANFSe v2.0")
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(largura / 2, y - 10 * mm, "Documento Auxiliar da NFS-e")

    if dados.get("tp_amb") == "2":
        c.setFillColor(colors.red)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(largura / 2, y - 13.5 * mm, "NFS-e SEM VALIDADE JURÍDICA")
        c.setFillColor(colors.black)

    c.setFont("Helvetica", 7)
    c.drawString(margem + 2 * mm, y - 4 * mm, f"Município: {dados.get('x_loc_emi') or '-'}")
    c.drawString(margem + 2 * mm, y - 8 * mm, f"Ambiente Gerador: {dados.get('amb_ger') or '-'}")
    c.drawString(margem + 2 * mm, y - 12 * mm, f"Tipo de Ambiente: {'Homologação' if dados.get('tp_amb') == '2' else 'Produção'}")

    if qr_disponivel and dados.get("chave_acesso"):
        qr_url = f"https://www.nfse.gov.br/ConsultaPublica/?tpc=1&chave={dados['chave_acesso']}"
        qr_img = qrcode.make(qr_url)
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        buf.seek(0)
        c.drawImage(ImageReader(buf), largura - margem - 18 * mm, y - 16 * mm, width=15 * mm, height=15 * mm)

    y -= 18 * mm

    def bloco_titulo(titulo: str, altura_bloco: float = 5 * mm) -> None:
        nonlocal y
        c.setFillColor(colors.Color(0.93, 0.93, 0.93))
        c.rect(margem, y - altura_bloco, largura - 2 * margem, altura_bloco, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(margem + 1.5 * mm, y - altura_bloco + 1.5 * mm, titulo.upper())
        y -= altura_bloco

    def linha(campos: list, altura_linha: float = 7 * mm) -> None:
        """campos: lista de (rótulo, valor); dividido em colunas iguais."""
        nonlocal y
        c.rect(margem, y - altura_linha, largura - 2 * margem, altura_linha, fill=0, stroke=1)
        n = len(campos)
        largura_col = (largura - 2 * margem) / n
        for i, (rotulo, valor) in enumerate(campos):
            x = margem + i * largura_col
            if i > 0:
                c.line(x, y, x, y - altura_linha)
            if rotulo:
                c.setFont("Helvetica-Bold", 6)
                c.drawString(x + 1.5 * mm, y - 2.3 * mm, rotulo)
            c.setFont("Helvetica", 7)
            c.drawString(x + 1.5 * mm, y - altura_linha + 2 * mm, (valor or "-")[:70])
        y -= altura_linha

    # --- Dados de Identificação da NFS-e ---
    bloco_titulo("Dados da NFS-e")
    linha([("Chave de Acesso da NFS-e", dados.get("chave_acesso"))], altura_linha=7 * mm)
    linha([
        ("Número da NFS-e", dados.get("numero_nfse")),
        ("Competência", dados.get("competencia")),
        ("Data/Hora Emissão NFS-e", dados.get("dh_proc")),
    ])
    linha([
        ("Número da DPS", dados.get("numero_dps")),
        ("Série da DPS", dados.get("serie_dps")),
        ("Data/Hora Emissão DPS", dados.get("dh_emi_dps")),
    ])
    linha([
        ("Emitente da NFS-e", dados.get("tp_emit")),
        ("Situação da NFS-e", "Cancelada" if dados.get("c_stat") == "2" else "Normal"),
        ("Finalidade", dados.get("fin_nfse")),
    ])

    # --- Prestador ---
    bloco_titulo("Prestador / Fornecedor")
    linha([
        ("CNPJ/CPF/NIF", dados.get("prest_cnpj")),
        ("Inscrição Municipal", dados.get("prest_im")),
        ("Telefone", dados.get("prest_fone")),
    ])
    linha([("Nome / Nome Empresarial", dados.get("prest_nome"))], altura_linha=7 * mm)
    linha([("E-mail", dados.get("prest_email"))], altura_linha=7 * mm)

    # --- Tomador ---
    if dados.get("toma_cnpj") or dados.get("toma_nome"):
        bloco_titulo("Tomador / Adquirente")
        linha([
            ("CNPJ/CPF/NIF", dados.get("toma_cnpj")),
            ("Telefone", dados.get("toma_fone")),
        ])
        linha([("Nome / Nome Empresarial", dados.get("toma_nome"))], altura_linha=7 * mm)
        if dados.get("toma_email"):
            linha([("E-mail", dados.get("toma_email"))], altura_linha=7 * mm)
    else:
        bloco_titulo("Tomador / Adquirente")
        linha([("", "TOMADOR/ADQUIRENTE DA OPERAÇÃO NÃO IDENTIFICADO NA NFS-e")], altura_linha=7 * mm)

    # --- Destinatário ---
    bloco_titulo("Destinatário da Operação")
    if dados.get("dest_cnpj") or dados.get("dest_nome"):
        linha([
            ("CNPJ/CPF/NIF", dados.get("dest_cnpj")),
            ("Nome / Nome Empresarial", dados.get("dest_nome")),
        ])
    else:
        linha([("", "DESTINATÁRIO DA OPERAÇÃO NÃO IDENTIFICADO NA NFS-e")], altura_linha=7 * mm)

    # --- Serviço Prestado ---
    bloco_titulo("Serviço Prestado")
    linha([
        ("Código de Tributação Nacional", dados.get("c_trib_nac")),
        ("Código da NBS", dados.get("c_nbs")),
    ])
    if dados.get("x_trib_nac"):
        c.setFont("Helvetica", 6)
        c.drawString(margem + 1.5 * mm, y - 3 * mm, (dados["x_trib_nac"] or "")[:180])
        y -= 4 * mm

    y -= 3 * mm
    c.setFont("Helvetica-Bold", 6)
    c.drawString(margem + 1.5 * mm, y, "Descrição do Serviço")
    y -= 4 * mm
    c.setFont("Helvetica", 7)
    desc = (dados.get("x_desc_serv") or "-")[:600]
    linhas_desc = [desc[i:i + 110] for i in range(0, len(desc), 110)] or ["-"]
    for l in linhas_desc[:6]:
        c.drawString(margem + 1.5 * mm, y, l)
        y -= 3.6 * mm
    y -= 2 * mm

    # --- Tributação Municipal (ISSQN) ---
    bloco_titulo("Tributação Municipal (ISSQN)")
    if dados.get("trib_issqn"):
        linha([
            ("BC ISSQN", _fmt_moeda(dados.get("v_bc_issqn"))),
            ("Alíquota Aplicada", dados.get("aliq_issqn") or "-"),
            ("ISSQN Apurado", _fmt_moeda(dados.get("v_issqn"))),
        ])
    else:
        linha([("", "TRIBUTAÇÃO MUNICIPAL (ISSQN) - OPERAÇÃO NÃO SUJEITA AO ISSQN")], altura_linha=7 * mm)

    # --- Tributação IBS/CBS ---
    bloco_titulo("Tributação IBS / CBS")
    linha([
        ("CST / cClassTrib", f"{dados.get('cst_ibscbs') or '-'} / {dados.get('c_class_trib') or '-'}"),
        ("Valor Total Apurado - IBS", _fmt_moeda(dados.get("v_ibs_tot"))),
        ("Valor Total Apurado - CBS", _fmt_moeda(dados.get("v_cbs_tot"))),
    ])

    # --- Valor Total da NFS-e ---
    c.setFillColor(colors.Color(0.93, 0.93, 0.93))
    c.rect(margem, y - 6 * mm, largura - 2 * margem, 6 * mm, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(margem + 1.5 * mm, y - 4 * mm, "VALOR TOTAL DA NFS-e")
    y -= 6 * mm
    linha([
        ("Valor da Operação/Serviço", _fmt_moeda(dados.get("v_serv"))),
        ("Valor Líquido da NFS-e", _fmt_moeda(dados.get("v_liq"))),
        ("Valor Líquido da NFS-e + IBS/CBS", _fmt_moeda(dados.get("v_tot_nf"))),
    ])

    # --- Informações Complementares ---
    bloco_titulo("Informações Complementares")
    y -= 3 * mm
    info = dados.get("x_inf_comp") or ""
    c.setFont("Helvetica", 6.5)
    linhas_info = [info[i:i + 150] for i in range(0, len(info), 150)][:4] or ["-"]
    for l in linhas_info:
        c.drawString(margem + 1.5 * mm, y, l)
        y -= 3.2 * mm

    # --- Marca d'água (cancelada/substituída/rascunho) ---
    texto_marca = dados.get("watermark_texto") or ("CANCELADA" if dados.get("c_stat") == "2" else None)
    if texto_marca:
        c.saveState()
        tamanho_fonte = 60 if len(texto_marca) <= 12 else 36
        c.setFont("Helvetica-Bold", tamanho_fonte)
        c.setFillColor(colors.Color(0.6, 0.6, 0.6, alpha=0.35))
        c.translate(largura / 2, altura / 2)
        c.rotate(45)
        c.drawCentredString(0, 0, texto_marca)
        c.restoreState()

    c.showPage()
    c.save()
    logger.info(f"DANFSe gerado com sucesso: {output_pdf_path}")
    return True
