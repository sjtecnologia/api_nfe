import base64
import io
import logging
import os
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape
from lxml import etree

logger = logging.getLogger(__name__)


NFE_NS = "http://www.portalfiscal.inf.br/nfe"
BRASILIA = ZoneInfo("America/Sao_Paulo")


def _local_text(node: Any, path: str, default: str = "") -> str:
    if node is None:
        return default
    found = node.xpath(path)
    if not found:
        return default
    value = found[0]
    if isinstance(value, str):
        return value.strip()
    return (value.text or "").strip()


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0").replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _money(value: Any) -> str:
    return f"{_decimal(value):.2f}"


def _money_br(valor: Any) -> str:
    try:
        arredondado = _decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{arredondado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (InvalidOperation, ValueError):
        return "0,00"


def _format_documento(value: str) -> str:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if len(digits) == 14:
        return f"{digits[:2]}.***.***/****-{digits[-2:]}"
    if len(digits) == 11:
        return f"{digits[:3]}.***.***-{digits[-2:]}"
    return "***"


def _to_brasilia(value: str) -> str:
    if not value:
        return ""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BRASILIA)
    return parsed.astimezone(BRASILIA).strftime("%d/%m/%Y %H:%M:%S")


def _private_key(certificado: Any) -> Any:
    if certificado is None:
        return None
    if hasattr(certificado, "sign"):
        return certificado
    if not isinstance(certificado, dict):
        return None
    key = certificado.get("private_key")
    if key is not None:
        return key
    cert_data = certificado.get("cert_data") or certificado.get("arquivo_certificado")
    password = certificado.get("password") or certificado.get("senha_certificado")
    if not cert_data:
        return None
    if isinstance(cert_data, str):
        cert_data = base64.b64decode(cert_data)
    if isinstance(password, str):
        password = password.encode("utf-8")
    from cryptography.hazmat.primitives.serialization import pkcs12

    private_key, _, _ = pkcs12.load_key_and_certificates(cert_data, password)
    return private_key


def gerar_qrcode_tipo2(
    chave,
    tp_amb,
    ambiente,
    contingencia=False,
    vnf=None,
    tipo_dest=None,
    id_dest=None,
    data_emissao=None,
    certificado=None,
):
    """Monta a URL de consulta v3 e assina seus parâmetros em contingência."""
    base_url = str(ambiente or "").strip()
    if not urlsplit(base_url).scheme:
        base_url = os.environ.get("NFE_QRCODE_TIPO2_URL", "").strip()
    if not base_url:
        raise ValueError("URL de consulta QR Code não informada")

    parameters = [str(chave), "3", str(tp_amb)]
    if contingencia:
        if isinstance(data_emissao, datetime):
            emission_date = data_emissao
        else:
            emission_date = datetime.fromisoformat(str(data_emissao).replace("Z", "+00:00"))
        day = str(emission_date.day).zfill(2)
        value = f"{abs(_decimal(vnf)):.2f}"
        if len(value) > 15:
            raise ValueError("vNF excede o limite de 15 caracteres do QR Code offline")
        value = value.zfill(15)
        destination_types = {"CNPJ": "1", "CPF": "2", "IDESTRANGEIRO": "3"}
        destination_type = destination_types.get(str(tipo_dest or "").upper(), str(tipo_dest or ""))
        if destination_type not in {"1", "2", "3"}:
            raise ValueError("Tipo de destinatário inválido para QR Code offline")
        destination_id = "" if destination_type == "3" else str(id_dest or "")
        parameters.extend([day, value, destination_type, destination_id])
        private_key = _private_key(certificado)
        if private_key is None:
            raise ValueError("Certificado/chave privada indisponível para QR Code em contingência")
        from services.xml_signature_service_old import XMLSignatureService

        signature = XMLSignatureService()._sign_data("|".join(parameters).encode("utf-8"), private_key)
        parameters.append(signature)

    parts = urlsplit(base_url)
    query = parts.query + ("&" if parts.query else "") + "p=" + "|".join(parameters)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


class DanfeSimplificadoTipo2Service:
    def __init__(self, output_dir: Optional[str] = None):
        self.project_root = Path(__file__).resolve().parent.parent
        self.template_dir = self.project_root / "templates"
        self.output_dir = Path(output_dir or self.project_root / "static" / "danfe")

    def _preparar_dados_tipo2(self, dados_nfe, protocolo=None):
        xml_content = dados_nfe if isinstance(dados_nfe, (str, bytes)) else (
            dados_nfe.get("xml") or dados_nfe.get("xml_content") or dados_nfe.get("xml_autorizado")
        )
        if not xml_content:
            raise ValueError("XML da NF-e não informado para gerar o DANFE Tipo 2")
        if isinstance(xml_content, str):
            xml_content = xml_content.encode("utf-8")
        root = etree.fromstring(xml_content)
        inf_nfe = root.xpath("//*[local-name()='infNFe']")[0]
        emit = inf_nfe.xpath("./*[local-name()='emit']")[0]
        ide = inf_nfe.xpath("./*[local-name()='ide']")[0]
        total = inf_nfe.xpath("./*[local-name()='total']")[0]
        emit_address = emit.xpath("./*[local-name()='enderEmit']")
        emit_address = emit_address[0] if emit_address else None
        issuer_id = _local_text(emit, "./*[local-name()='CNPJ']/text()") or _local_text(
            emit, "./*[local-name()='CPF']/text()"
        )

        products = []
        product_total = Decimal("0")
        for detail in inf_nfe.xpath("./*[local-name()='det']"):
            product = detail.xpath("./*[local-name()='prod']")
            if not product:
                continue
            product = product[0]
            product_total += _decimal(_local_text(product, "./*[local-name()='vProd']/text()"))
            products.append({
                "codigo": _local_text(product, "./*[local-name()='cProd']/text()"),
                "descricao": _local_text(product, "./*[local-name()='xProd']/text()"),
                "quantidade": _local_text(product, "./*[local-name()='qCom']/text()"),
                "unidade": _local_text(product, "./*[local-name()='uCom']/text()"),
                "valor_unitario": _money_br(_local_text(product, "./*[local-name()='vUnCom']/text()")),
                "valor_total": _money_br(_local_text(product, "./*[local-name()='vProd']/text()")),
            })
        distinct_items = len({item["codigo"] for item in products})
        total_node = total.xpath("./*[local-name()='ICMSTot']")
        total_node = total_node[0] if total_node else total
        freight = _decimal(_local_text(total_node, "./*[local-name()='vFrete']/text()"))
        insurance = _decimal(_local_text(total_node, "./*[local-name()='vSeg']/text()"))
        other = _decimal(_local_text(total_node, "./*[local-name()='vOutro']/text()"))
        discount = _decimal(_local_text(total_node, "./*[local-name()='vDesc']/text()"))
        additions = freight + insurance + other
        invoice_total = _decimal(_local_text(total_node, "./*[local-name()='vNF']/text()"))

        payment_rows = []
        for payment in inf_nfe.xpath(".//*[local-name()='pag']/*[local-name()='detPag']"):
            payment_rows.append({
                "forma": _local_text(payment, "./*[local-name()='tPag']/text()"),
                "valor": _money_br(_local_text(payment, "./*[local-name()='vPag']/text()")),
            })
        change = _money_br(_local_text(inf_nfe, ".//*[local-name()='pag']/*[local-name()='vTroco']/text()"))

        tax_values = []
        for tag, label in (("vCBS", "CBS"), ("vIBS", "IBS"), ("vIS", "IS")):
            for tax_node in inf_nfe.xpath(f".//*[local-name()='{tag}']"):
                value = (tax_node.text or "").strip()
                if value:
                    tax_values.append({"nome": label, "valor": _money_br(value)})

        access_key = _local_text(root, ".//*[local-name()='chNFe']/text()")
        if not access_key:
            access_key = _local_text(inf_nfe, "@Id").removeprefix("NFe")
        key_url = " ".join(access_key[index:index + 4] for index in range(0, len(access_key), 4))
        qr_base_url = _local_text(root, ".//*[local-name()='urlChave']/text()")
        tp_amb = _local_text(ide, "./*[local-name()='tpAmb']/text()")
        tp_emis = _local_text(ide, "./*[local-name()='tpEmis']/text()", "1")
        contingency = tp_emis != "1"
        destination_nodes = inf_nfe.xpath("./*[local-name()='dest']")
        destination = destination_nodes[0] if destination_nodes else None
        destination_cnpj = _local_text(destination, "./*[local-name()='CNPJ']/text()")
        destination_cpf = _local_text(destination, "./*[local-name()='CPF']/text()")
        destination_id = destination_cnpj or destination_cpf
        destination_type = "1" if destination_cnpj else "2" if destination_cpf else "3"
        certificate_data = dados_nfe.get("certificado") if isinstance(dados_nfe, dict) else None
        private_key = certificate_data.get("private_key") if isinstance(certificate_data, dict) else certificate_data
        emission_raw = _local_text(ide, "./*[local-name()='dhEmi']/text()") or _local_text(
            ide, "./*[local-name()='dEmi']/text()"
        )
        qr_data = gerar_qrcode_tipo2(
            access_key,
            tp_amb,
            qr_base_url,
            contingencia=contingency,
            vnf=invoice_total,
            tipo_dest=destination_type,
            id_dest=destination_id,
            data_emissao=emission_raw,
            certificado=private_key,
        )
        qr_image = ""
        try:
            import qrcode

            image = qrcode.make(qr_data)
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            qr_image = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
        except ImportError:
            logger.warning("Biblioteca qrcode indisponível; DANFE Tipo 2 será salvo com URL de consulta")

        presence = _local_text(ide, "./*[local-name()='indPres']/text()", "1")
        delivery_nodes = inf_nfe.xpath(".//*[local-name()='entrega' or local-name()='enderEntrega']")
        delivery = delivery_nodes[0] if delivery_nodes else None
        destination_name = _local_text(destination, "./*[local-name()='xNome']/text()")
        delivery_address = " ".join(filter(None, [
            _local_text(delivery, "./*[local-name()='xLgr']/text()"),
            _local_text(delivery, "./*[local-name()='nro']/text()"),
            _local_text(delivery, "./*[local-name()='xCpl']/text()"),
            _local_text(delivery, "./*[local-name()='xBairro']/text()"),
            _local_text(delivery, "./*[local-name()='xMun']/text()"),
            _local_text(delivery, "./*[local-name()='UF']/text()"),
            _local_text(delivery, "./*[local-name()='CEP']/text()"),
        ]))
        if presence != "1" and (not destination_name or not delivery_address):
            raise ValueError("Nome do consumidor e endereço de entrega são obrigatórios em operação não presencial")

        protocol_node = root.xpath(".//*[local-name()='protNFe']/*[local-name()='infProt']")
        protocol_node = protocol_node[0] if protocol_node else None
        protocol_data = protocolo if isinstance(protocolo, dict) else {}
        protocol_number = protocol_data.get("nProt") or _local_text(protocol_node, "./*[local-name()='nProt']/text()")
        protocol_date = protocol_data.get("dhRecbto") or _local_text(protocol_node, "./*[local-name()='dhRecbto']/text()")
        additional = inf_nfe.xpath("./*[local-name()='infAdic']")
        additional = additional[0] if additional else None
        tp_amb = tp_amb or (dados_nfe.get("tp_amb", "") if isinstance(dados_nfe, dict) else "")

        data = {
            "emitente_documento": _format_documento(issuer_id),
            "emitente_nome": _local_text(emit, "./*[local-name()='xNome']/text()"),
            "emitente_endereco": " ".join(filter(None, [
                _local_text(emit_address, "./*[local-name()='xLgr']/text()"),
                _local_text(emit_address, "./*[local-name()='nro']/text()"),
                _local_text(emit_address, "./*[local-name()='xCpl']/text()"),
                _local_text(emit_address, "./*[local-name()='xBairro']/text()"),
                _local_text(emit_address, "./*[local-name()='xMun']/text()"),
                _local_text(emit_address, "./*[local-name()='UF']/text()"),
                _local_text(emit_address, "./*[local-name()='CEP']/text()"),
            ])),
            "itens": products,
            "quantidade_itens_distintos": distinct_items,
            "soma_produtos": _money_br(product_total),
            "acrescimos": _money_br(additions),
            "descontos": _money_br(discount),
            "mostrar_acrescimos": additions > 0,
            "mostrar_descontos": discount > 0,
            "valor_nota": _money_br(invoice_total),
            "mostrar_valor_nota": additions > 0 or discount > 0,
            "pagamentos": payment_rows,
            "troco": change,
            "tributos": tax_values,
            "url_chave": qr_base_url,
            "chave_url": key_url,
            "qrcode_url": qr_data,
            "qrcode_imagem": qr_image,
            "consumidor_documento": _format_documento(
                _local_text(destination, "./*[local-name()='CNPJ']/text()") or _local_text(
                    destination, "./*[local-name()='CPF']/text()"
                )
            ),
            "consumidor_nome": destination_name,
            "endereco_entrega": delivery_address,
            "presencial": presence == "1",
            "numero": _local_text(ide, "./*[local-name()='nNF']/text()"),
            "serie": _local_text(ide, "./*[local-name()='serie']/text()"),
            "chave_acesso": access_key,
            "emissao": _to_brasilia(emission_raw),
            "protocolo": "" if contingency else protocol_number,
            "data_protocolo": "" if contingency else _to_brasilia(protocol_date),
            "contingencia": contingency,
            "homologacao": tp_amb == "2",
            "inf_ad_fisco": _local_text(additional, "./*[local-name()='infAdFisco']/text()"),
            "inf_cpl": _local_text(additional, "./*[local-name()='infCpl']/text()"),
        }

        return data

    def gerar_danfe_tipo2_html(self, dados_nfe, protocolo=None):
        data = self._preparar_dados_tipo2(dados_nfe, protocolo)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        environment = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        template = environment.get_template("danfe_tipo2.html")
        html = template.render(**data)
        file_name = f"danfe_tipo2_{data['chave_acesso'] or 'sem_chave'}.html"
        output_path = self.output_dir / file_name
        output_path.write_text(html, encoding="utf-8")
        return str(output_path)

    def gerar_danfe_tipo2(self, dados_nfe, protocolo=None, caminho_pdf=None):
        try:
            return gerar_danfe_tipo2_pdf(dados_nfe, protocolo, caminho_pdf)
        except Exception as exc:
            logger.error("ERRO_DANFE_TIPO2: %s", exc)
            raise


def gerar_danfe_tipo2_pdf(dados_nfe, protocolo=None, caminho_pdf=None):
    service = DanfeSimplificadoTipo2Service()
    data = service._preparar_dados_tipo2(dados_nfe, protocolo)

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Image as ReportLabImage
    from reportlab.platypus import HRFlowable, Paragraph, Table, TableStyle
    from xml.sax.saxutils import escape

    page_width = 56 * mm
    side_margin = 2 * mm
    content_width = page_width - 2 * side_margin
    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "Tipo2Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=8.5,
        spaceAfter=1.5,
        wordWrap="CJK",
    )
    centered_style = ParagraphStyle(
        "Tipo2Centered",
        parent=body_style,
        alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        "Tipo2Heading",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=9,
        alignment=TA_CENTER,
        spaceBefore=2,
        spaceAfter=2,
    )
    bold_style = ParagraphStyle("Tipo2Bold", parent=body_style, fontName="Helvetica-Bold")
    right_style = ParagraphStyle("Tipo2Right", parent=body_style, alignment=TA_RIGHT)

    def paragraph(text, style=body_style):
        return Paragraph(escape(str(text or "")), style)

    story = []

    def add_line(text, style=body_style):
        story.append(paragraph(text, style))

    def add_section(title):
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceBefore=2, spaceAfter=2))
        story.append(paragraph(title, heading_style))

    def add_pair(label, value, emphasize=False):
        left_style = bold_style if emphasize else body_style
        row = Table(
            [[paragraph(label, left_style), paragraph(value, right_style)]],
            colWidths=[content_width * 0.66, content_width * 0.34],
        )
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        story.append(row)

    if data["contingencia"]:
        add_line("EMITIDA EM CONTINGÊNCIA Pendente de autorização", bold_style)
    add_line(data["emitente_documento"], centered_style)
    add_line(data["emitente_nome"], bold_style)
    add_line(data["emitente_endereco"], centered_style)
    add_line("DANFE Simplificado Tipo 2", heading_style)
    if data["homologacao"]:
        add_line("EMITIDA EM AMBIENTE DE HOMOLOGAÇÃO - SEM VALOR FISCAL", bold_style)
    add_line("Via do Estabelecimento", centered_style)

    add_section("ITENS")
    for item in data["itens"]:
        add_line(f"{item['codigo']} - {item['descricao']}", bold_style)
        add_line(
            f"{item['quantidade']} {item['unidade']} x {item['valor_unitario']} = {item['valor_total']}"
        )

    add_section("TOTAIS")
    add_line(f"Itens distintos: {data['quantidade_itens_distintos']}")
    add_pair("Produtos", data["soma_produtos"])
    if data["mostrar_acrescimos"]:
        add_pair("Acréscimos", data["acrescimos"])
    if data["mostrar_descontos"]:
        add_pair("Descontos", data["descontos"])
    if data["mostrar_valor_nota"]:
        add_pair("Valor da NF", data["valor_nota"], emphasize=True)
    for payment in data["pagamentos"]:
        add_pair(f"Pagamento {payment['forma']}", payment["valor"])
    if data["troco"] != "0,00":
        add_pair("Troco", data["troco"])

    add_section("III-A - TRIBUTOS")
    for tax in data["tributos"]:
        add_pair(tax["nome"], tax["valor"])

    add_section("CHAVE DE ACESSO")
    if data["url_chave"]:
        add_line(data["url_chave"])
    add_line(data["chave_url"], centered_style)

    add_section("Consulte pela Chave")
    import qrcode

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=0,
    )
    qr.add_data(data["qrcode_url"])
    qr.make(fit=True)
    qr_buffer = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_image = ReportLabImage(qr_buffer, width=25 * mm, height=25 * mm)
    qr_with_quiet_zone = Table(
        [[qr_image]],
        colWidths=[31 * mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
        ]),
    )
    story.append(qr_with_quiet_zone)
    add_line(data["qrcode_url"])
    if data["contingencia"]:
        add_line("EMITIDA EM CONTINGÊNCIA Pendente de autorização", bold_style)

    add_section(f"CONSUMIDOR CNPJ: {data['consumidor_documento']}")
    if data["consumidor_nome"]:
        add_line(data["consumidor_nome"])
    if data["endereco_entrega"]:
        add_line(f"Entrega: {data['endereco_entrega']}")

    add_section("DADOS DA NF-e")
    add_pair("NF-e", data["numero"])
    add_pair("Série", data["serie"])
    add_line(f"Emissão: {data['emissao']}")
    if data["protocolo"]:
        add_line(f"Protocolo de autorização: {data['protocolo']}")
    if data["data_protocolo"]:
        add_line(f"Recebimento: {data['data_protocolo']}")

    add_section("INFORMAÇÕES ADICIONAIS")
    if data["inf_ad_fisco"]:
        add_line(data["inf_ad_fisco"])
    if data["inf_cpl"]:
        add_line(data["inf_cpl"])

    content_height = sum(
        flowable.wrap(content_width, 100000)[1]
        + flowable.getSpaceBefore()
        + flowable.getSpaceAfter()
        for flowable in story
    )
    page_height = max(40 * mm, content_height + 4 * mm)

    output_path = Path(caminho_pdf) if caminho_pdf else (
        service.output_dir / f"danfe_tipo2_{data['chave_acesso'] or data['numero']}.pdf"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output_path), pagesize=(page_width, page_height))
    y = page_height - 2 * mm
    for flowable in story:
        y -= flowable.getSpaceBefore()
        _, flow_height = flowable.wrap(content_width, y)
        y -= flow_height
        flowable.drawOn(pdf, side_margin, y)
        y -= flowable.getSpaceAfter()
    pdf.showPage()
    pdf.save()
    return str(output_path)
