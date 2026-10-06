"""Gera o PDF assinavel do Contrato de Licenca EmiteMax a partir do docx fonte.

Uso:
    python3 scripts/gerar_contrato_pdf.py [saida1.pdf] [saida2.pdf]      # modo generico (placeholders em branco)
    python3 scripts/gerar_contrato_pdf.py --cliente NOME_CHAVE saida.pdf # preenche com dados de um cliente cadastrado abaixo

Le o arquivo "Documentacao/CONTRATO DE LICENÇA E TERMOS DE USO - EMITEMAX.docx",
padroniza a referencia ao cliente para "LICENCIADA" (o docx original mistura
"LICENCIADO"/"LICENCIADA") e gera o PDF final pronto para assinatura (fisica
ou por plataforma de assinatura eletronica, ex.: D4Sign).
"""
import re
import sys
from pathlib import Path

import docx
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

BASE_DIR = Path(__file__).resolve().parent.parent
DOCX_PATH = BASE_DIR / "Documentacao" / "CONTRATO DE LICENÇA E TERMOS DE USO - EMITEMAX.docx"

HEADING_PREFIXES = ("Cláusula",)
HEADING_EXACT = {
    "CONTRATANTE",
    "CONTRATADA",
    "ASSINATURAS",
    "DECLARAÇÃO FINAL",
    "INFORMAÇÕES ADICIONAIS PARA PREENCHIMENTO",
}

# Dados de clientes conhecidos para preenchimento automatico do contrato.
CLIENTES = {
    "restaurante_brasilidade": {
        "nome_empresa": "RESTAURANTE BRASILIDADE LTDA",
        "cnpj": "56.126.037/0001-15",
        "endereco": "Avenida Alfredo Antonio de Oliveira, Loja F-07",
        "numero": "2077",
        "bairro": "Jardim Marajó",
        "cep": "15.046-355",
        "cidade": "São José do Rio Preto",
        "uf": "SP",
        "rep_nome": "Maressa de Oliveira Spricido dos Santos",
        "rep_cpf": "431.133.148-79",
        "rep_cargo": "Sócia-Administradora",
        "plano": "Básico",
        "valor_mensalidade": "60,00",
    },
    "paulo_roberto_homsi_filho": {
        "nome_empresa": "PAULO ROBERTO HOMSI FILHO",
        "cnpj": "68.842.523/0001-19",
        "endereco": "R Antonio Evaristo Cabrera",
        "numero": "390",
        "bairro": "Jardim Tarraf II",
        "cep": "15.092-460",
        "cidade": "São José do Rio Preto",
        "uf": "SP",
        "rep_nome": "Paulo Roberto Homsi Filho",
        "rep_cpf": "",
        "rep_cargo": "Empresário Individual",
        "plano": "Básico",
        "valor_mensalidade": "60,00",
    },
}

STYLE_TITLE = ParagraphStyle(
    "ContratoTitulo", fontName="Helvetica-Bold", fontSize=15, leading=18,
    alignment=TA_CENTER, spaceAfter=16,
)
STYLE_HEADING = ParagraphStyle(
    "ContratoSecao", fontName="Helvetica-Bold", fontSize=11, leading=14,
    spaceBefore=12, spaceAfter=6,
)
STYLE_BODY = ParagraphStyle(
    "ContratoCorpo", fontName="Helvetica", fontSize=9.5, leading=13,
    alignment=TA_JUSTIFY, spaceAfter=6,
)


def normalizar_texto(texto: str) -> str:
    texto = re.sub(r"\bLICENCIADO\b", "LICENCIADA", texto)
    texto = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return texto


def preencher_preambulo(texto: str, cliente: dict) -> str:
    """Substitui os placeholders [CAMPO] do preambulo pelos dados do cliente."""
    substituicoes = {
        "[NOME DA EMPRESA]": cliente["nome_empresa"],
        "[CNPJ]": cliente["cnpj"],
        "[ENDEREÇO COMPLETO]": cliente["endereco"],
        "[NÚMERO]": cliente["numero"],
        "[BAIRRO]": cliente["bairro"],
        "[CEP]": cliente["cep"],
        "[CIDADE]": cliente["cidade"],
        "[UF]": cliente["uf"],
    }
    for placeholder, valor in substituicoes.items():
        texto = texto.replace(placeholder, valor)
    return texto


def preencher_assinatura_licenciada(texto: str, cliente: dict) -> str:
    """Preenche os campos em branco do bloco de assinatura da LICENCIADA."""
    texto = re.sub(r"^RAZÃO SOCIAL:\s*_+$", f"RAZÃO SOCIAL: {cliente['nome_empresa']}", texto)
    texto = re.sub(r"^CNPJ:\s*_+$", f"CNPJ: {cliente['cnpj']}", texto)
    texto = re.sub(r"^Nome do Representante Legal:\s*_+$", f"Nome do Representante Legal: {cliente['rep_nome']}", texto)
    texto = re.sub(r"^CPF:\s*_+$", f"CPF: {cliente['rep_cpf']}", texto)
    texto = re.sub(r"^Cargo:\s*_+$", f"Cargo: {cliente['rep_cargo']}", texto)
    return texto


def preencher_informacoes_adicionais(texto: str, cliente: dict) -> str:
    if texto.startswith("Plano Contratado:"):
        texto = texto.replace(f"( ) {cliente['plano']}", f"(X) {cliente['plano']}")
    elif texto.startswith("Valor da Mensalidade:"):
        texto = re.sub(r"R\$\s*_+", f"R$ {cliente['valor_mensalidade']}", texto)
    return texto


def eh_titulo(texto: str, indice: int) -> bool:
    return indice == 1


def eh_secao(texto: str) -> bool:
    return texto.startswith(HEADING_PREFIXES) or texto in HEADING_EXACT


def gerar_pdf(caminho_saida: Path, cliente: dict | None = None) -> None:
    doc_origem = docx.Document(str(DOCX_PATH))
    story = []
    dentro_bloco_licenciada = False
    for indice, paragrafo in enumerate(doc_origem.paragraphs):
        texto_bruto = paragrafo.text.strip()
        if texto_bruto == "LICENCIADO:":
            dentro_bloco_licenciada = True
        elif texto_bruto.startswith("Testemunhas"):
            dentro_bloco_licenciada = False

        if not texto_bruto:
            story.append(Spacer(1, 0.25 * cm))
            continue
        texto = normalizar_texto(texto_bruto)
        if cliente:
            texto = preencher_preambulo(texto, cliente)
            if dentro_bloco_licenciada:
                texto = preencher_assinatura_licenciada(texto, cliente)
            texto = preencher_informacoes_adicionais(texto, cliente)
        if eh_titulo(texto, indice):
            story.append(Paragraph(texto, STYLE_TITLE))
        elif eh_secao(texto):
            story.append(Paragraph(texto, STYLE_HEADING))
        else:
            story.append(Paragraph(texto, STYLE_BODY))

    documento = SimpleDocTemplate(
        str(caminho_saida), pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
        title="Contrato de Licenca e Termos de Uso - EmiteMax",
    )
    documento.build(story)


def main() -> None:
    argumentos = sys.argv[1:]
    cliente = None
    if argumentos and argumentos[0] == "--cliente":
        chave_cliente = argumentos[1]
        cliente = CLIENTES[chave_cliente]
        destinos = argumentos[2:] or [
            str(BASE_DIR / "Documentacao" / f"Contrato_EmiteMax_{chave_cliente}_assinavel.pdf")
        ]
    else:
        destinos = argumentos or [
            str(BASE_DIR / "Documentacao" / "Contrato_EmiteMax_Cliente_1_assinavel.pdf"),
            str(BASE_DIR / "Documentacao" / "Contrato_EmiteMax_Cliente_2_assinavel.pdf"),
        ]
    for destino in destinos:
        caminho = Path(destino)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        gerar_pdf(caminho, cliente)
        print(f"Gerado: {caminho}")


if __name__ == "__main__":
    main()
