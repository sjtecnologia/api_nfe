"""
Service para NFS-e Nacional - São José do Rio Preto
Geração de XML, comunicação com webservice e processamento
"""

import os
import json
import re
import time
import requests
import hashlib
import uuid
import base64
import tempfile
import unicodedata
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from lxml import etree
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from services.certificate_service import _decrypt_password

# Importar models
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.nfse_model import (
    NFSeNacional, PrestadorNFSe, TomadoresNFSe, ServicoNFSe,
    CODIGOS_SERVICO_LC116, CODIGOS_MUNICIPIO_SP, ALIQUOTAS_ISS_SJRP,
    DEFAULT_CODIGO_NBS, normalizar_codigo_nbs
)


def _validar_periodo_certificado_x509(certificate):
    """Garante que o certificado X509 esteja vigente para o envio mTLS."""
    agora = datetime.now(certificate.not_valid_after_utc.tzinfo)
    if certificate.not_valid_before_utc and certificate.not_valid_before_utc > agora:
        raise ValueError(
            f"Certificado digital ainda não está válido para uso: {certificate.not_valid_before_utc:%d/%m/%Y}"
        )
    if certificate.not_valid_after_utc and certificate.not_valid_after_utc < agora:
        raise ValueError(
            f"Certificado digital expirado em {certificate.not_valid_after_utc:%d/%m/%Y}. "
            "Substitua o certificado ativo antes de emitir a NFS-e."
        )


class NFSeService:
    """
    Serviço para emissão de NFS-e Nacional
    Implementação para São José do Rio Preto - SP (GISS Online)
    """
    
    # Namespaces XML - GISS Online usa padrão próprio baseado em ABRASF modificado
    NS_ENVIO = "http://www.giss.com.br/enviar-lote-rps-envio-v2_04.xsd"
    NS_TIPOS = "http://www.giss.com.br/tipos-v2_04.xsd"
    NS_DSIG = "http://www.w3.org/2000/09/xmldsig#"
    MUNICIPIO_HOST_ALIASES = {
        "sao-jose-do-rio-preto": "sjrp",
        "sao-jose-rio-preto": "sjrp",
        "sjrp": "sjrp",
    }
    # Apenas hosts testados para SOAP/mTLS devem ser usados como fallback.
    # Obs.: ws-homologacao.giss.com.br serve portal HTML e retorna 405 no POST SOAP.
    FALLBACK_HOST_WHITELIST = {
        "homologacao": {
            "ws-homologacao-rtc.giss.com.br",
        },
        "producao": {
            "ws-rtc.giss.com.br",
            "ws-sjrp.giss.com.br",
        },
    }
    
    # URLs do webservice - GISS Online (Atualizado conforme documentação oficial)
    # NT007 v1.03.00 - Reforma Tributária (LC 214/2025)
    URLS_SJRP = {
        "homologacao": {
            "base": "https://ws-homologacao-rtc.giss.com.br/",
            "wsdl": "https://ws-homologacao-rtc.giss.com.br/service-ws/nf/nfse-ws?wsdl",
            "enviar_lote": "service-ws/nf/nfse-ws",
            "consultar_lote": "service-ws/nf/nfse-ws",
            "consultar_nfse": "service-ws/nf/nfse-ws",
            "cancelar": "service-ws/nf/nfse-ws",
            # Versões dos layouts (NT007)
            "versao_layout_rtc": "1.03.00",  # AnexoVI - Layout RN RTC IBS/CBS
            "versao_anexo_vii": "1.01.00"    # AnexoVII - IndOp_IBSCBS
        },
        "producao": {
            "base": "https://ws-rtc.giss.com.br/",
            "wsdl": "https://ws-rtc.giss.com.br/service-ws/nf/nfse-ws?wsdl",
            "enviar_lote": "service-ws/nf/nfse-ws",
            "consultar_lote": "service-ws/nf/nfse-ws",
            "consultar_nfse": "service-ws/nf/nfse-ws",
            "cancelar": "service-ws/nf/nfse-ws",
            # Versões dos layouts (NT007)
            "versao_layout_rtc": "1.03.00",  # AnexoVI - Layout RN RTC IBS/CBS
            "versao_anexo_vii": "1.01.00"    # AnexoVII - IndOp_IBSCBS
        }
    }
    
    def __init__(self, ambiente: str = "homologacao", municipio_slug: Optional[str] = None, ws_host: Optional[str] = None):
        """
        Inicializa o serviço NFS-e
        
        Args:
            ambiente: 'homologacao' ou 'producao'
        """
        self.ambiente = ambiente
        self.urls = self._resolver_urls(ambiente, municipio_slug=municipio_slug, ws_host=ws_host)
        
        # Configurações do certificado
        self.cert_path = os.getenv("CERT_PATH", "/home/ubuntu/api_nfe/certs/certificado.pfx")
        self.cert_password = os.getenv("CERT_PASSWORD", "")

    def _normalizar_municipio_slug(self, municipio_slug: str) -> str:
        """Normaliza slug do município para o padrão do host GISS."""
        texto = unicodedata.normalize("NFKD", municipio_slug).encode("ascii", "ignore").decode("ascii")
        texto = re.sub(r"[^a-zA-Z0-9]+", "-", texto.lower()).strip("-")
        return self.MUNICIPIO_HOST_ALIASES.get(texto, texto)

    def _montar_urls_municipio(self, host_suffix: str) -> Dict[str, str]:
        base = f"https://ws-{host_suffix}.giss.com.br/"
        endpoint = "service-ws/nf/nfse-ws"
        return {
            "base": base,
            "wsdl": f"{base}{endpoint}?wsdl",
            "enviar_lote": endpoint,
            "consultar_lote": endpoint,
            "consultar_nfse": endpoint,
            "cancelar": endpoint,
            "versao_layout_rtc": "1.03.00",
            "versao_anexo_vii": "1.01.00"
        }

    def _montar_urls_custom_host(self, host_value: str) -> Optional[Dict[str, str]]:
        """Monta URLs a partir de sufixo, hostname completo ou URL base."""
        valor = (host_value or "").strip()
        if not valor:
            return None

        if valor.startswith("https://") or valor.startswith("http://"):
            base = valor
        elif "." in valor:
            base = f"https://{valor}"
        else:
            base = f"https://ws-{valor}.giss.com.br"

        if not base.endswith("/"):
            base += "/"

        endpoint = "service-ws/nf/nfse-ws"
        return {
            "base": base,
            "wsdl": f"{base}{endpoint}?wsdl",
            "enviar_lote": endpoint,
            "consultar_lote": endpoint,
            "consultar_nfse": endpoint,
            "cancelar": endpoint,
            "versao_layout_rtc": "1.03.00",
            "versao_anexo_vii": "1.01.00"
        }

    def _extrair_hostname_base(self, base_url: str) -> str:
        """Extrai hostname de uma URL base para validações de segurança."""
        valor = (base_url or "").strip().lower()
        valor = re.sub(r"^https?://", "", valor)
        return valor.split('/')[0].strip()

    def _host_elegivel_para_fallback(self, base_url: str) -> bool:
        """Valida se host pertence à whitelist da operação."""
        host = self._extrair_hostname_base(base_url)
        permitidos = self.FALLBACK_HOST_WHITELIST.get(self.ambiente, set())
        if not permitidos:
            # Sem whitelist explícita para ambiente, manter apenas host atual.
            return host == self._extrair_hostname_base(self.urls.get("base", ""))
        return host in permitidos

    def _soap_action(self, operacao: str) -> str:
        """Resolve SOAPAction com suporte a override por variável de ambiente."""
        env_key = f"GISS_SOAP_ACTION_{operacao.upper()}"
        return os.getenv(env_key, f"http://nfse.abrasf.org.br/{operacao}")

    def _usar_schema_rtc(self) -> bool:
        """Define se o XML deve incluir blocos RTC (IBS/CBS e trib)."""
        valor = (
            os.getenv(f"GISS_SCHEMA_RTC_{self.ambiente.upper()}")
            or os.getenv("GISS_SCHEMA_RTC")
            or "false"
        )
        return str(valor).strip().lower() in {"1", "true", "yes", "on", "sim"}

    def _resolver_urls_envio_com_fallback(self) -> List[Dict[str, str]]:
        """Lista URLs de envio: principal + hosts alternativos configurados."""
        urls = [self.urls]
        bases_vistas = {self.urls.get("base")}

        fallback_raw = (
            os.getenv(f"GISS_WS_FALLBACK_HOSTS_{self.ambiente.upper()}")
            or os.getenv("GISS_WS_FALLBACK_HOSTS")
            or ""
        )

        if not fallback_raw:
            return urls

        for item in re.split(r"[;,]", fallback_raw):
            host = item.strip()
            if not host:
                continue

            url_custom = self._montar_urls_custom_host(host)
            if not url_custom:
                continue

            base = url_custom.get("base")
            if not self._host_elegivel_para_fallback(base):
                print(f"[NFSE] Ignorando host fallback fora da whitelist: {base}")
                continue

            if base in bases_vistas:
                continue

            bases_vistas.add(base)
            urls.append(url_custom)

        return urls

    def _resolver_urls(self, ambiente: str, municipio_slug: Optional[str] = None, ws_host: Optional[str] = None) -> Dict[str, str]:
        """Resolve URLs do webservice, priorizando host municipal e mantendo fallback legado."""
        ambiente_urls = self.URLS_SJRP.get(ambiente, self.URLS_SJRP["homologacao"])
        host_override = ws_host or os.getenv(f"GISS_WS_HOST_{ambiente.upper()}") or os.getenv("GISS_WS_HOST")
        slug_override = municipio_slug or os.getenv(f"GISS_MUNICIPIO_SLUG_{ambiente.upper()}") or os.getenv("GISS_MUNICIPIO_SLUG")

        if host_override:
            return self._montar_urls_municipio(host_override.strip())

        if slug_override:
            slug_normalizado = self._normalizar_municipio_slug(slug_override)
            if slug_normalizado:
                return self._montar_urls_municipio(slug_normalizado)

        return ambiente_urls

    def _validar_xml_rps_antes_envio(self, xml_rps: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Valida XML RPS contra XSD com modo configurável:
        - off: não valida
        - warn: valida e apenas registra aviso
        - strict: bloqueia envio quando inválido
        """
        mode = (os.getenv("NFSE_XSD_VALIDATION_MODE", "warn") or "warn").strip().lower()
        if mode not in {"off", "warn", "strict"}:
            mode = "warn"

        if mode == "off":
            return True, None

        from services.nfse_validation_service import NFSeValidationService

        xsd_path = os.getenv("NFSE_XSD_PATH")
        resultado = NFSeValidationService.validar_xml_contra_xsd(
            xml_content=xml_rps,
            xsd_path=xsd_path,
        )

        if resultado.get("valido"):
            return True, None

        if mode == "warn":
            print(
                "[NFSE] ⚠️ XML RPS inválido no XSD, mas envio continuará (modo warn). "
                f"Detalhes: {resultado.get('erros', [])[:3]}"
            )
            return True, {
                "tipo": "xsd_warning",
                "xsd_validation_mode": mode,
                "xsd_result": resultado,
            }

        return False, {
            "erro": "Validação XSD do XML RPS falhou",
            "mensagem": "XML inválido conforme schema XSD configurado (modo strict)",
            "xsd_validation_mode": mode,
            "xsd_result": resultado,
        }
        
    def gerar_id_lote(self) -> str:
        """Gera ID único para o lote de RPS (apenas números, máximo 15 dígitos)"""
        # Timestamp mais curto: YYMMDDHHMMSSmmm (milissegundos) = 15 dígitos
        timestamp = datetime.now().strftime("%y%m%d%H%M%S%f")[:15]
        return timestamp
    
    def gerar_numero_rps(self, ultimo_numero: int = 0) -> int:
        """Gera próximo número de RPS"""
        return ultimo_numero + 1
    
    def validar_cpf(self, cpf: str) -> bool:
        """Valida CPF"""
        cpf = ''.join(filter(str.isdigit, cpf))
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False
        
        # Cálculo dos dígitos verificadores
        for i in range(9, 11):
            soma = sum(int(cpf[j]) * ((i + 1) - j) for j in range(i))
            digito = (soma * 10) % 11
            if digito == 10:
                digito = 0
            if digito != int(cpf[i]):
                return False
        return True
    
    def validar_cnpj(self, cnpj: str) -> bool:
        """Valida CNPJ"""
        cnpj = ''.join(filter(str.isdigit, cnpj))
        if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
            return False
        
        # Cálculo dos dígitos verificadores
        multiplicadores1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        multiplicadores2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        
        soma = sum(int(cnpj[i]) * multiplicadores1[i] for i in range(12))
        digito1 = 11 - (soma % 11)
        if digito1 >= 10:
            digito1 = 0
        
        soma = sum(int(cnpj[i]) * multiplicadores2[i] for i in range(13))
        digito2 = 11 - (soma % 11)
        if digito2 >= 10:
            digito2 = 0
        
        return cnpj[-2:] == f"{digito1}{digito2}"
    
    def formatar_valor(self, valor: float) -> str:
        """Formata valor para o padrão do XML (2 casas decimais)"""
        return f"{valor:.2f}"
    
    def formatar_aliquota(self, aliquota: float) -> str:
        """Formata alíquota para o padrão GISS (decimal com 4 casas, ex: 5% = 0.0500)"""
        # Se alíquota estiver como percentual inteiro (ex: 5.00), dividir por 100
        if aliquota > 1:
            aliquota = aliquota / 100
        return f"{aliquota:.4f}"

    def formatar_percentual(self, valor: float) -> str:
        """Formata percentual com 2 casas conforme grupos RTC do GISS."""
        return f"{valor:.2f}"
    
    def limpar_texto(self, texto: str, max_len: int = 2000) -> str:
        """Remove caracteres especiais e limita tamanho"""
        if not texto:
            return ""
        # Remove caracteres problemáticos
        texto = texto.replace("&", "&amp;")
        texto = texto.replace("<", "&lt;")
        texto = texto.replace(">", "&gt;")
        texto = texto.replace('"', "&quot;")
        texto = texto.replace("'", "&apos;")
        return texto[:max_len]
    
    def gerar_xml_rps(self, nfse: NFSeNacional) -> str:
        """
        Gera o XML do RPS para envio ao webservice GISS Online
        Padrão GISS baseado em ABRASF 2.04 modificado
        
        Args:
            nfse: Objeto NFSeNacional com os dados
            
        Returns:
            XML do RPS como string
        """
        
        # Calcular valores
        nfse.calcular_valores()
        
        # Criar estrutura XML com namespaces GISS
        nsmap = {
            'p': self.NS_ENVIO,
            'p1': self.NS_TIPOS,
            'ds': self.NS_DSIG
        }
        
        # Root element - p:EnviarLoteRpsEnvio
        root = etree.Element("{%s}EnviarLoteRpsEnvio" % self.NS_ENVIO, nsmap=nsmap)
        
        # p:LoteRps
        lote_rps = etree.SubElement(root, "{%s}LoteRps" % self.NS_ENVIO)
        # Id alfanumérico evita falhas de resolução de URI (#Id) em alguns validadores XMLDSig.
        lote_rps.set("Id", "lote1")
        lote_rps.set("versao", "2.04")
        
        # p1:NumeroLote
        etree.SubElement(lote_rps, "{%s}NumeroLote" % self.NS_TIPOS).text = str(nfse.lote or self.gerar_id_lote())
        
        # p1:Prestador (dentro do lote)
        prestador_lote = etree.SubElement(lote_rps, "{%s}Prestador" % self.NS_TIPOS)
        cpf_cnpj_prest_lote = etree.SubElement(prestador_lote, "{%s}CpfCnpj" % self.NS_TIPOS)
        etree.SubElement(cpf_cnpj_prest_lote, "{%s}Cnpj" % self.NS_TIPOS).text = nfse.prestador.cnpj
        # InscricaoMunicipal é obrigatório no schema GISS
        inscricao = nfse.prestador.inscricao_municipal or "0"
        etree.SubElement(prestador_lote, "{%s}InscricaoMunicipal" % self.NS_TIPOS).text = inscricao
        
        # p1:QuantidadeRps
        etree.SubElement(lote_rps, "{%s}QuantidadeRps" % self.NS_TIPOS).text = "1"
        
        # p1:ListaRps
        lista_rps = etree.SubElement(lote_rps, "{%s}ListaRps" % self.NS_TIPOS)
        
        # p1:Rps
        rps = etree.SubElement(lista_rps, "{%s}Rps" % self.NS_TIPOS)
        
        # p1:InfDeclaracaoPrestacaoServico
        inf_rps = etree.SubElement(rps, "{%s}InfDeclaracaoPrestacaoServico" % self.NS_TIPOS)
        inf_rps.set("Id", "rps1")  # Id único para InfDeclaracaoPrestacaoServico
        
        # p1:Rps (identificação)
        rps_ident = etree.SubElement(inf_rps, "{%s}Rps" % self.NS_TIPOS)
        rps_ident.set("Id", "identificacao-rps1")  # Id único para elemento Rps
        ident_rps = etree.SubElement(rps_ident, "{%s}IdentificacaoRps" % self.NS_TIPOS)
        etree.SubElement(ident_rps, "{%s}Numero" % self.NS_TIPOS).text = str(nfse.numero_rps or 1)
        etree.SubElement(ident_rps, "{%s}Serie" % self.NS_TIPOS).text = nfse.serie_rps
        etree.SubElement(ident_rps, "{%s}Tipo" % self.NS_TIPOS).text = nfse.tipo_rps
        
        # Data de emissão (schema GISS v2.04 define xs:date)
        etree.SubElement(rps_ident, "{%s}DataEmissao" % self.NS_TIPOS).text = nfse.data_emissao.strftime("%Y-%m-%d")
        etree.SubElement(rps_ident, "{%s}Status" % self.NS_TIPOS).text = "1"  # Normal
        
        # p1:Competencia
        etree.SubElement(inf_rps, "{%s}Competencia" % self.NS_TIPOS).text = (nfse.data_competencia or nfse.data_emissao).strftime("%Y-%m-%d")
        
        # p1:Servico
        servico_el = etree.SubElement(inf_rps, "{%s}Servico" % self.NS_TIPOS)
        
        usar_schema_rtc = self._usar_schema_rtc()

        # p1:Valores do serviço - GISS exige valores zerados explícitos
        valores = etree.SubElement(servico_el, "{%s}Valores" % self.NS_TIPOS)
        etree.SubElement(valores, "{%s}ValorServicos" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_servicos)
        etree.SubElement(valores, "{%s}ValorDeducoes" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_deducoes)
        etree.SubElement(valores, "{%s}ValorPis" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_pis)
        etree.SubElement(valores, "{%s}ValorCofins" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_cofins)
        etree.SubElement(valores, "{%s}ValorInss" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_inss)
        etree.SubElement(valores, "{%s}ValorIr" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_ir)
        valor_csll_xml = nfse.servico.valor_csll if nfse.servico.csll_retida else 0.0
        etree.SubElement(valores, "{%s}ValorCsll" % self.NS_TIPOS).text = self.formatar_valor(valor_csll_xml)
        if nfse.servico.outras_retencoes > 0:
            etree.SubElement(valores, "{%s}OutrasRetencoes" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.outras_retencoes)
        
        percentual_total_tributos = (
            nfse.servico.percentual_total_tributos_federais +
            nfse.servico.percentual_total_tributos_estaduais +
            nfse.servico.percentual_total_tributos_municipais
        )
        valor_total_tributos = nfse.servico.base_calculo * (percentual_total_tributos / 100)
        if valor_total_tributos > 0:
            etree.SubElement(valores, "{%s}ValTotTributos" % self.NS_TIPOS).text = self.formatar_valor(valor_total_tributos)

        if nfse.servico.valor_iss > 0:
            etree.SubElement(valores, "{%s}ValorIss" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_iss)
        
        # Alíquota no formato decimal (ex: 5% = 0.0500)
        etree.SubElement(valores, "{%s}Aliquota" % self.NS_TIPOS).text = self.formatar_aliquota(nfse.servico.aliquota_iss)
        
        if nfse.servico.desconto_incondicionado > 0:
            etree.SubElement(valores, "{%s}DescontoIncondicionado" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.desconto_incondicionado)
        if nfse.servico.desconto_condicionado > 0:
            etree.SubElement(valores, "{%s}DescontoCondicionado" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.desconto_condicionado)
        
        # =============================================================================================
        # REFORMA TRIBUTÁRIA (LC 214/2025) - NT007 v1.03.00
        # Implementado: 09/02/2026
        # Referência: https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/rtc
        # =============================================================================================
        
        incluir_piscofins = any([
            nfse.servico.valor_pis_operacao > 0,
            nfse.servico.valor_cofins_operacao > 0,
            nfse.servico.base_calculo_pis_cofins > 0,
            nfse.servico.aliquota_pis > 0,
            nfse.servico.aliquota_cofins > 0,
            nfse.servico.cst_pis_cofins != "00",
            nfse.servico.tipo_retencao_pis_cofins == "1",
        ])
        incluir_totais = any([
            nfse.servico.percentual_total_tributos_federais > 0,
            nfse.servico.percentual_total_tributos_estaduais > 0,
            nfse.servico.percentual_total_tributos_municipais > 0,
        ])

        if usar_schema_rtc and (incluir_piscofins or incluir_totais):
            trib = etree.SubElement(valores, "{%s}trib" % self.NS_TIPOS)

            if incluir_piscofins:
                trib_fed = etree.SubElement(trib, "{%s}tribFed" % self.NS_TIPOS)
                piscofins = etree.SubElement(trib_fed, "{%s}piscofins" % self.NS_TIPOS)
                etree.SubElement(piscofins, "{%s}CST" % self.NS_TIPOS).text = nfse.servico.cst_pis_cofins

                if nfse.servico.base_calculo_pis_cofins > 0:
                    etree.SubElement(piscofins, "{%s}vBCPisCofins" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.base_calculo_pis_cofins)
                if nfse.servico.aliquota_pis > 0:
                    etree.SubElement(piscofins, "{%s}pAliqPis" % self.NS_TIPOS).text = self.formatar_percentual(nfse.servico.aliquota_pis)
                if nfse.servico.aliquota_cofins > 0:
                    etree.SubElement(piscofins, "{%s}pAliqCofins" % self.NS_TIPOS).text = self.formatar_percentual(nfse.servico.aliquota_cofins)
                if nfse.servico.valor_pis_operacao > 0:
                    etree.SubElement(piscofins, "{%s}vPis" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_pis_operacao)
                if nfse.servico.valor_cofins_operacao > 0:
                    etree.SubElement(piscofins, "{%s}vCofins" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_cofins_operacao)
                etree.SubElement(piscofins, "{%s}tpRetPisCofins" % self.NS_TIPOS).text = nfse.servico.tipo_retencao_pis_cofins

            if incluir_totais:
                tot_trib = etree.SubElement(trib, "{%s}totTrib" % self.NS_TIPOS)
                percentuais = etree.SubElement(tot_trib, "{%s}pTotTrib" % self.NS_TIPOS)
                etree.SubElement(percentuais, "{%s}pTotTribFed" % self.NS_TIPOS).text = self.formatar_percentual(nfse.servico.percentual_total_tributos_federais)
                etree.SubElement(percentuais, "{%s}pTotTribEst" % self.NS_TIPOS).text = self.formatar_percentual(nfse.servico.percentual_total_tributos_estaduais)
                etree.SubElement(percentuais, "{%s}pTotTribMun" % self.NS_TIPOS).text = self.formatar_percentual(nfse.servico.percentual_total_tributos_municipais)

        if usar_schema_rtc:
            ibscbs = etree.SubElement(valores, "{%s}IBSCBS" % self.NS_TIPOS)
            etree.SubElement(ibscbs, "{%s}finNFSe" % self.NS_TIPOS).text = nfse.servico.finalidade_nfse
            etree.SubElement(ibscbs, "{%s}indFinal" % self.NS_TIPOS).text = nfse.servico.indicador_consumidor_final
            etree.SubElement(ibscbs, "{%s}cIndOp" % self.NS_TIPOS).text = nfse.servico.codigo_indicador_operacao
            etree.SubElement(ibscbs, "{%s}indDest" % self.NS_TIPOS).text = nfse.servico.indicador_destinatario

            ibscbs_valores = etree.SubElement(ibscbs, "{%s}valores" % self.NS_TIPOS)
            ibscbs_trib = etree.SubElement(ibscbs_valores, "{%s}trib" % self.NS_TIPOS)
            grupo_ibscbs = etree.SubElement(ibscbs_trib, "{%s}gIBSCBS" % self.NS_TIPOS)
            etree.SubElement(grupo_ibscbs, "{%s}CST" % self.NS_TIPOS).text = nfse.servico.cst_ibs_cbs
            etree.SubElement(grupo_ibscbs, "{%s}cClassTrib" % self.NS_TIPOS).text = nfse.servico.codigo_classificacao_tributaria
            etree.SubElement(ibscbs_valores, "{%s}cLocalidadeIncid" % self.NS_TIPOS).text = nfse.servico.codigo_localidade_incidencia
            etree.SubElement(ibscbs_valores, "{%s}pRedutor" % self.NS_TIPOS).text = self.formatar_percentual(nfse.servico.percentual_redutor)
            etree.SubElement(ibscbs_valores, "{%s}vBC" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.base_calculo)
        
        # p1:IssRetido
        etree.SubElement(servico_el, "{%s}IssRetido" % self.NS_TIPOS).text = "1" if nfse.servico.iss_retido else "2"
        
        # p1:ItemListaServico (código LC 116) - ex: "11.02"
        # GISS exige formato NN.NN com zero à esquerda (01.02, não 1.02)
        codigo_lc116 = nfse.servico.codigo_tributacao_nacional
        if '.' in codigo_lc116:
            partes = codigo_lc116.split('.')
            codigo_lc116 = f"{partes[0].zfill(2)}.{partes[1].zfill(2)}"
        etree.SubElement(servico_el, "{%s}ItemListaServico" % self.NS_TIPOS).text = codigo_lc116
        
        # p1:CodigoTributacaoMunicipio - GISS exige após ItemListaServico
        # Derivar do código LC 116 ou usar padrão
        # Exemplo: "01.01" -> "8010001", "07.02" -> "8070002"
        codigo_sem_ponto = codigo_lc116.replace(".", "")
        codigo_trib_municipal = f"80{codigo_sem_ponto.zfill(5)}" if len(codigo_sem_ponto) <= 5 else "8020001"
        etree.SubElement(servico_el, "{%s}CodigoTributacaoMunicipio" % self.NS_TIPOS).text = codigo_trib_municipal
        etree.SubElement(servico_el, "{%s}CodigoNbs" % self.NS_TIPOS).text = nfse.servico.codigo_nbs
        
        # p1:Discriminacao do serviço
        etree.SubElement(servico_el, "{%s}Discriminacao" % self.NS_TIPOS).text = self.limpar_texto(nfse.servico.discriminacao)
        
        # p1:CodigoMunicipio de prestação
        codigo_municipio = nfse.servico.codigo_municipio_prestacao or "3549805"
        etree.SubElement(servico_el, "{%s}CodigoMunicipio" % self.NS_TIPOS).text = codigo_municipio
        
        # p1:CodigoPais - GISS exige (Brasil = 1058 IBGE ou 0076 BACEN)
        etree.SubElement(servico_el, "{%s}CodigoPais" % self.NS_TIPOS).text = "1058"
        
        # p1:ExigibilidadeISS
        etree.SubElement(servico_el, "{%s}ExigibilidadeISS" % self.NS_TIPOS).text = "1"  # Exigível
        
        # p1:MunicipioIncidencia - GISS exige (código IBGE do município)
        etree.SubElement(servico_el, "{%s}MunicipioIncidencia" % self.NS_TIPOS).text = codigo_municipio
        
        # p1:Prestador
        prestador_el = etree.SubElement(inf_rps, "{%s}Prestador" % self.NS_TIPOS)
        cpf_cnpj_prestador = etree.SubElement(prestador_el, "{%s}CpfCnpj" % self.NS_TIPOS)
        etree.SubElement(cpf_cnpj_prestador, "{%s}Cnpj" % self.NS_TIPOS).text = nfse.prestador.cnpj
        # InscricaoMunicipal é obrigatório no schema GISS
        inscricao = nfse.prestador.inscricao_municipal or "0"
        etree.SubElement(prestador_el, "{%s}InscricaoMunicipal" % self.NS_TIPOS).text = inscricao
        
        # Tomador: schema RTC usa plural; schema legado usa singular.
        if nfse.Tomadores:
            tag_tomador = "TomadoresServico" if usar_schema_rtc else "TomadorServico"
            tag_ident_tomador = "IdentificacaoTomadores" if usar_schema_rtc else "IdentificacaoTomador"

            tomador_el = etree.SubElement(inf_rps, "{%s}%s" % (self.NS_TIPOS, tag_tomador))
            ident_Tomadores = etree.SubElement(tomador_el, "{%s}%s" % (self.NS_TIPOS, tag_ident_tomador))
            cpf_cnpj_Tomadores = etree.SubElement(ident_Tomadores, "{%s}CpfCnpj" % self.NS_TIPOS)
            
            if nfse.Tomadores.tipo_documento == "CPF":
                etree.SubElement(cpf_cnpj_Tomadores, "{%s}Cpf" % self.NS_TIPOS).text = nfse.Tomadores.cpf_cnpj
            else:
                etree.SubElement(cpf_cnpj_Tomadores, "{%s}Cnpj" % self.NS_TIPOS).text = nfse.Tomadores.cpf_cnpj
            
            if nfse.Tomadores.inscricao_municipal:
                etree.SubElement(ident_Tomadores, "{%s}InscricaoMunicipal" % self.NS_TIPOS).text = nfse.Tomadores.inscricao_municipal
            
            # Razão social
            etree.SubElement(tomador_el, "{%s}RazaoSocial" % self.NS_TIPOS).text = self.limpar_texto(nfse.Tomadores.razao_social, 150)
            
            # Endereço do Tomadores
            if nfse.Tomadores.endereco_logradouro:
                endereco_Tomadores = etree.SubElement(tomador_el, "{%s}Endereco" % self.NS_TIPOS)
                etree.SubElement(endereco_Tomadores, "{%s}Endereco" % self.NS_TIPOS).text = self.limpar_texto(nfse.Tomadores.endereco_logradouro, 125)
                numero_endereco = (nfse.Tomadores.endereco_numero or "S/N")[:10]
                etree.SubElement(endereco_Tomadores, "{%s}Numero" % self.NS_TIPOS).text = numero_endereco
                if nfse.Tomadores.endereco_complemento:
                    etree.SubElement(endereco_Tomadores, "{%s}Complemento" % self.NS_TIPOS).text = nfse.Tomadores.endereco_complemento[:60]
                bairro = self.limpar_texto(nfse.Tomadores.endereco_bairro or "NAO INFORMADO", 60)
                etree.SubElement(endereco_Tomadores, "{%s}Bairro" % self.NS_TIPOS).text = bairro
                codigo_municipio_tomador = nfse.Tomadores.endereco_codigo_municipio or "3549805"
                etree.SubElement(endereco_Tomadores, "{%s}CodigoMunicipio" % self.NS_TIPOS).text = codigo_municipio_tomador
                uf_tomador = (nfse.Tomadores.endereco_uf or "SP")[:2]
                etree.SubElement(endereco_Tomadores, "{%s}Uf" % self.NS_TIPOS).text = uf_tomador
                cep_tomador = (nfse.Tomadores.endereco_cep or "00000000").replace("-", "")[:8]
                cep_tomador = cep_tomador.ljust(8, "0")
                etree.SubElement(endereco_Tomadores, "{%s}Cep" % self.NS_TIPOS).text = cep_tomador
            
            # Contato do Tomadores - GISS v2.04 suporta apenas Telefone
            if nfse.Tomadores.telefone:
                contato_Tomadores = etree.SubElement(tomador_el, "{%s}Contato" % self.NS_TIPOS)
                etree.SubElement(contato_Tomadores, "{%s}Telefone" % self.NS_TIPOS).text = nfse.Tomadores.telefone[:20]
        
        # p1:OptanteSimplesNacional
        etree.SubElement(inf_rps, "{%s}OptanteSimplesNacional" % self.NS_TIPOS).text = "1" if nfse.optante_simples_nacional else "2"
        
        # p1:IncentivoFiscal
        etree.SubElement(inf_rps, "{%s}IncentivoFiscal" % self.NS_TIPOS).text = "1" if nfse.incentivador_cultural else "2"
        
        # Converter para string
        xml_str = etree.tostring(root, encoding="unicode", pretty_print=True)
        
        # Adicionar declaração XML
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
        
        # DEBUG: Salvar XML gerado para análise
        try:
            with open('/tmp/last_generated_nfse.xml', 'w', encoding='utf-8') as f:
                f.write(xml_str)
            print(f"[NFSE] XML não assinado salvo em /tmp/last_generated_nfse.xml")
        except:
            pass
        
        return xml_str
    
    def assinar_xml(self, xml: str, db_session=None, cliente_id: Optional[int] = None) -> str:
        """
        ⚠️ EXCLUSIVO PARA NFS-e - NÃO AFETA NF-e ⚠️
        
        Assina o XML RPS da NFS-e com certificado digital A1.
        Esta função usa signxml para assinar especificamente o elemento LoteRps
        conforme exigido pelo webservice GISS.
        
        A assinatura de NF-e usa PyNFe e está em services/sefaz_service.py
        
        Args:
            xml: XML a ser assinado
            db_session: Sessão do banco de dados
            cliente_id: ID do cliente
            
        Returns:
            XML assinado
        """
        try:
            print("[NFSE] Iniciando assinatura de RPS...")
            
            if not db_session or not cliente_id:
                print("[NFSE] ⚠️ Sessão ou cliente não fornecidos, retornando XML sem assinatura")
                return xml
            
            # Importar serviços necessários
            from services.certificate_service import get_active_certificate_for_client
            import tempfile
            import base64
            import os
            
            # 1. Buscar certificado ativo do cliente
            certificado = get_active_certificate_for_client(db_session, cliente_id)
            if not certificado:
                print("[NFSE] ⚠️ Nenhum certificado ativo encontrado")
                return xml
            
            print(f"[NFSE] Certificado ID: {certificado.get('certificado_id')}")
            
            # Verificar modo simulado
            if certificado.get('modo_simulado'):
                print("[NFSE] ⚠️ Certificado em modo simulado, retornando XML sem assinatura")
                return xml
            
            # 2. Obter dados do certificado
            cert_data = certificado.get('cert_data') or certificado.get('arquivo_certificado')
            cert_senha = certificado.get('password') or certificado.get('senha_certificado')
            
            if not cert_data or not cert_senha:
                print(f"[NFSE] ⚠️ Dados do certificado incompletos")
                return xml
            
            # 3. Salvar certificado em arquivo temporário
            with tempfile.NamedTemporaryFile(suffix='.pfx', delete=False) as tmp_file:
                if isinstance(cert_data, bytes):
                    tmp_file.write(cert_data)
                else:
                    tmp_file.write(base64.b64decode(cert_data))
                cert_file_path = tmp_file.name
            
            print(f"[NFSE] Certificado salvo temporariamente")
            
            # 4. Converter PFX para formato utilizável pela assinatura
            from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
            from cryptography.hazmat.primitives import hashes as crypto_hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            
            # Carregar PFX
            with open(cert_file_path, 'rb') as f:
                pfx_data = f.read()
            
            private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                pfx_data, 
                cert_senha.encode('utf-8')
            )
            
            from cryptography.hazmat.primitives import serialization
            print(f"[NFSE] Certificado carregado")
            
            # 5. Parse do XML
            parser = etree.XMLParser(remove_blank_text=True)
            if isinstance(xml, str):
                xml_element = etree.fromstring(xml.encode('utf-8'), parser=parser)
            elif isinstance(xml, bytes):
                xml_element = etree.fromstring(xml, parser=parser)
            else:
                xml_element = xml
            
            # 6. Assinar RPS e LoteRps (perfil legado GISS)
            namespaces = {
                'p': 'http://www.giss.com.br/enviar-lote-rps-envio-v2_04.xsd',
                'p1': 'http://www.giss.com.br/tipos-v2_04.xsd',
                'ds': 'http://www.w3.org/2000/09/xmldsig#'
            }
            ds_ns = "http://www.w3.org/2000/09/xmldsig#"

            cert_der = certificate.public_bytes(serialization.Encoding.DER)
            cert_base64 = base64.b64encode(cert_der).decode('utf-8')

            def _montar_assinatura(target_id: str, digest_value: str):
                assinatura = etree.Element(f"{{{ds_ns}}}Signature", nsmap={None: ds_ns})
                signed_info = etree.SubElement(assinatura, f"{{{ds_ns}}}SignedInfo")

                canon_method = etree.SubElement(signed_info, f"{{{ds_ns}}}CanonicalizationMethod")
                canon_method.set("Algorithm", "http://www.w3.org/TR/2001/REC-xml-c14n-20010315")

                sig_method = etree.SubElement(signed_info, f"{{{ds_ns}}}SignatureMethod")
                sig_method.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#rsa-sha1")

                reference = etree.SubElement(signed_info, f"{{{ds_ns}}}Reference")
                reference.set("URI", f"#{target_id}")

                transforms = etree.SubElement(reference, f"{{{ds_ns}}}Transforms")
                transform_env = etree.SubElement(transforms, f"{{{ds_ns}}}Transform")
                transform_env.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#enveloped-signature")

                digest_method = etree.SubElement(reference, f"{{{ds_ns}}}DigestMethod")
                digest_method.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#sha1")

                digest_elem = etree.SubElement(reference, f"{{{ds_ns}}}DigestValue")
                digest_elem.text = digest_value

                return assinatura, signed_info

            assinaturas_rps_ok = 0
            lote_rps = xml_element.find('./p:LoteRps', namespaces)
            if lote_rps is not None:
                rps_nodes = lote_rps.findall('./p1:ListaRps/p1:Rps', namespaces)
                for idx, rps_node in enumerate(rps_nodes, start=1):
                    inf_rps = rps_node.find('./p1:InfDeclaracaoPrestacaoServico', namespaces)
                    if inf_rps is None:
                        print(f"[NFSE] ⚠️ Rps #{idx} sem InfDeclaracaoPrestacaoServico")
                        continue

                    inf_id = inf_rps.get('Id')
                    if not inf_id:
                        inf_id = f"rps{idx}"
                        inf_rps.set('Id', inf_id)

                    inf_c14n = etree.tostring(inf_rps, method='c14n', exclusive=False, with_comments=False)
                    inf_digest = base64.b64encode(hashlib.sha1(inf_c14n).digest()).decode('utf-8')

                    assinatura_rps, signed_info_rps = _montar_assinatura(inf_id, inf_digest)

                    for assinatura_existente in rps_node.findall('./ds:Signature', namespaces):
                        rps_node.remove(assinatura_existente)

                    rps_node.append(assinatura_rps)

                    signed_info_c14n = etree.tostring(signed_info_rps, method='c14n', exclusive=False, with_comments=False)
                    assinatura_bytes = private_key.sign(
                        signed_info_c14n,
                        padding.PKCS1v15(),
                        crypto_hashes.SHA1(),
                    )

                    sig_value = etree.SubElement(assinatura_rps, f"{{{ds_ns}}}SignatureValue")
                    sig_value.text = base64.b64encode(assinatura_bytes).decode('utf-8')

                    # Compatibilidade GISS: KeyInfo dispara E172 em homologação RTC.
                    # Mantemos assinatura com SignedInfo + SignatureValue apenas.

                    assinaturas_rps_ok += 1

                print(f"[NFSE] Assinaturas RPS inseridas: {assinaturas_rps_ok}/{len(rps_nodes)}")

            # Assinatura do lote é obrigatória para o GISS (E173 quando ausente).
            assinatura_lote_ok = False
            if lote_rps is not None:
                lote_id = lote_rps.get('Id')
                if not lote_id:
                    lote_id = 'lote1'
                    lote_rps.set('Id', lote_id)

                # Calcula digest do lote com C14N inclusivo (padrão ABRASF/GISS legado).
                lote_c14n = etree.tostring(lote_rps, method='c14n', exclusive=False, with_comments=False)
                digest_value = base64.b64encode(hashlib.sha1(lote_c14n).digest()).decode('utf-8')

                assinatura_lote, signed_info = _montar_assinatura(lote_id, digest_value)

                # Remove assinatura de lote anterior no root para evitar duplicidade.
                for assinatura_existente in xml_element.findall('./ds:Signature', namespaces):
                    xml_element.remove(assinatura_existente)

                # Anexa no documento antes de canonicalizar SignedInfo.
                # Com C14N inclusivo, namespaces ancestrais entram no cálculo.
                xml_element.append(assinatura_lote)

                signed_info_c14n = etree.tostring(signed_info, method='c14n', exclusive=False, with_comments=False)
                assinatura_bytes = private_key.sign(
                    signed_info_c14n,
                    padding.PKCS1v15(),
                    crypto_hashes.SHA1(),
                )

                sig_value = etree.SubElement(assinatura_lote, f"{{{ds_ns}}}SignatureValue")
                sig_value.text = base64.b64encode(assinatura_bytes).decode('utf-8')

                # Compatibilidade GISS: KeyInfo dispara E172 em homologação RTC.
                # Mantemos assinatura com SignedInfo + SignatureValue apenas.

                assinatura_lote_ok = True
                print(f"[NFSE] Assinatura do LoteRps inserida com Reference URI '#{lote_id}'")
            else:
                print("[NFSE] ⚠️ LoteRps não encontrado para assinatura do lote")

            if assinatura_lote_ok:
                # Não usar pretty_print após assinar: reformatar pode invalidar digest.
                xml_assinado = etree.tostring(xml_element, encoding='unicode', pretty_print=False)
                xml_assinado = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_assinado
            else:
                print("[NFSE] ⚠️ Nenhuma assinatura foi inserida; retornando XML original")
                xml_assinado = xml
            
            # 7. Limpar arquivo temporário
            os.unlink(cert_file_path)
            
            print(f"[NFSE] ✅ RPS assinado: {len(xml_assinado)} caracteres")
            
            # DEBUG: Salvar para análise
            try:
                with open('/tmp/last_signed_nfse.xml', 'w', encoding='utf-8') as f:
                    f.write(xml_assinado)
                print(f"[NFSE] XML salvo em /tmp/last_signed_nfse.xml")
            except:
                pass
            
            return xml_assinado
            
        except Exception as e:
            print(f"[NFSE] ❌ Erro ao assinar: {e}")
            import traceback
            traceback.print_exc()
            # Em caso de erro, retornar XML sem assinatura
            print("[NFSE] ⚠️ Retornando XML sem assinatura devido ao erro")
            return xml
    
    def enviar_lote_rps(self, nfse: NFSeNacional, db_session=None) -> Tuple[bool, Dict[str, Any]]:
        """
        Envia lote de RPS para processamento no GISS Online
        
        Args:
            nfse: Objeto NFSeNacional
            db_session: Sessão do banco de dados (para buscar certificado)
            
        Returns:
            Tuple (sucesso, dados_resposta)
        """
        cert_file_path = None
        key_file_path = None
        envio_lock_path = None
        
        try:
            print(f"[NFSE] === ENVIANDO RPS PARA GISS ONLINE ===")
            print(f"[NFSE] Ambiente: {self.ambiente}")
            print(f"[NFSE] Cliente ID: {nfse.cliente_id}")

            # Marca de envio em andamento para evitar restart/reload no meio da transação.
            envio_lock_path = f"/tmp/nfse_envio_{os.getpid()}_{uuid.uuid4().hex}.lock"
            try:
                with open(envio_lock_path, "w", encoding="utf-8") as lock_file:
                    lock_file.write(
                        f"cliente_id={nfse.cliente_id}\n"
                        f"ambiente={self.ambiente}\n"
                        f"inicio={datetime.now().isoformat()}\n"
                    )
                print(f"[NFSE] Lock de envio criado: {envio_lock_path}")
            except Exception as lock_error:
                envio_lock_path = None
                print(f"[NFSE] ⚠️ Não foi possível criar lock de envio: {lock_error}")
            
            # 1. Gerar XML RPS (ou reaproveitar XML já persistido)
            xml_rps_existente = (getattr(nfse, 'xml_rps', None) or '').strip()
            if xml_rps_existente:
                xml_rps = xml_rps_existente
                print(f"[NFSE] Reutilizando XML RPS existente: {len(xml_rps)} caracteres")
            else:
                xml_rps = self.gerar_xml_rps(nfse)
                nfse.xml_rps = xml_rps
                print(f"[NFSE] XML RPS gerado: {len(xml_rps)} caracteres")

            xsd_ok, xsd_detalhes = self._validar_xml_rps_antes_envio(xml_rps)
            if not xsd_ok:
                print("[NFSE] ❌ Envio bloqueado por validação XSD (modo strict)")
                return False, xsd_detalhes or {
                    "erro": "Validação XSD do XML RPS falhou",
                    "mensagem": "XML inválido conforme schema XSD configurado",
                }
            if xsd_detalhes and xsd_detalhes.get("tipo") == "xsd_warning":
                print("[NFSE] ⚠️ Validação XSD reportou avisos (modo warn), seguindo com envio")
            
            # 2. Obter certificado do banco para envio HTTPS
            certificado = None
            if db_session and nfse.cliente_id:
                from database.models import CertificadoDigital
                certificado = db_session.query(CertificadoDigital).filter(
                    CertificadoDigital.cliente_id == nfse.cliente_id,
                    CertificadoDigital.ativo == True
                ).first()
            
            if not certificado:
                print("[NFSE] ⚠️ Certificado não encontrado no banco")
                return False, {"erro": "Certificado digital não encontrado", "mensagem": "Configure um certificado digital válido para o cliente"}
            
            # 3. Preparar certificado para requisição HTTPS (mTLS)
            cert_data = certificado.conteudo_certificado
            cert_senha_encrypted = certificado.senha_certificado
            
            if not cert_data or not cert_senha_encrypted:
                return False, {"erro": "Dados do certificado incompletos", "mensagem": "Certificado ou senha não configurados"}
            
            # Descriptografar a senha do certificado
            try:
                cert_senha = _decrypt_password(cert_senha_encrypted)
                print(f"[NFSE] Senha descriptografada com sucesso")
            except Exception as e:
                print(f"[NFSE] ❌ Erro ao descriptografar senha: {e}")
                return False, {"erro": "Erro ao descriptografar senha do certificado", "mensagem": str(e)}
            
            # 4. Converter PFX para PEM (necessário para requests)
            import tempfile
            from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
            
            # Decodificar certificado
            if not isinstance(cert_data, bytes):
                cert_data = base64.b64decode(cert_data)
            
            # Extrair chave privada e certificado do PFX
            private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                cert_data,
                cert_senha.encode('utf-8') if isinstance(cert_senha, str) else cert_senha
            )

            if not private_key or not certificate:
                return False, {"erro": "Certificado digital inválido", "mensagem": "Não foi possível extrair chave e certificado do arquivo do cliente"}

            try:
                _validar_periodo_certificado_x509(certificate)
            except ValueError as e:
                return False, {"erro": "Certificado digital vencido ou inválido", "mensagem": str(e)}
            
            # Salvar em arquivos temporários
            # O GISS historicamente aceita o certificado folha separado da chave privada.
            # Mantemos apenas o certificado do cliente no PEM do mTLS para evitar
            # rejeição do handshake por variação na cadeia enviada.
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as cert_file:
                cert_file.write(certificate.public_bytes(Encoding.PEM))
                cert_file_path = cert_file.name
            
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.key', delete=False) as key_file:
                key_file.write(private_key.private_bytes(
                    encoding=Encoding.PEM,
                    format=PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=NoEncryption()
                ))
                key_file_path = key_file.name
            
            print(f"[NFSE] Certificado convertido para PEM")
            
            # 5. Assinar XML
            xml_assinado = self.assinar_xml(xml_rps, db_session=db_session, cliente_id=nfse.cliente_id)
            print(f"[NFSE] XML assinado: {len(xml_assinado)} caracteres")
            
            # 6. Criar envelope SOAP para o webservice GISS
            # IMPORTANTE: O conteúdo dentro de nfseCabecMsg e nfseDadosMsg deve estar escapado (entidades HTML)
            import html
            
            # Cabeçalho conforme documentação GISS (namespace correto: cabecalho-v2_04.xsd)
            cabecalho = '''<cabecalho versao="2.04" xmlns="http://www.giss.com.br/cabecalho-v2_04.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <versaoDados>2.04</versaoDados>
</cabecalho>'''
            
            # Escapar XML para incluir no SOAP
            cabecalho_escaped = html.escape(cabecalho)
            dados_escaped = html.escape(xml_assinado)
            
            soap_envelope = f'''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:nfse="http://nfse.abrasf.org.br">
    <soapenv:Header/>
    <soapenv:Body>
        <nfse:RecepcionarLoteRpsRequest>
            <nfseCabecMsg>{cabecalho_escaped}</nfseCabecMsg>
            <nfseDadosMsg>{dados_escaped}</nfseDadosMsg>
        </nfse:RecepcionarLoteRpsRequest>
    </soapenv:Body>
</soapenv:Envelope>'''
            
            # Headers HTTP para SOAP
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": self._soap_action("RecepcionarLoteRps"),
            }
            
            # 7. Envio com retentativa para indisponibilidade temporária do provedor
            # Configurável por ambiente para ajuste fino sem novo deploy.
            max_tentativas, esperas_segundos = self._config_retry_envio()

            urls_envio = self._resolver_urls_envio_com_fallback()
            total_hosts = len(urls_envio)
            ultima_indisponibilidade = None
            ultimo_diagnostico_endpoint: Optional[Dict[str, Any]] = None
            if total_hosts > 1:
                print(f"[NFSE] Fallback de host habilitado: {total_hosts} hosts candidatos")

            for idx_host, urls_ativas in enumerate(urls_envio, start=1):
                url = urls_ativas["base"] + urls_ativas["enviar_lote"]
                print(f"[NFSE] URL ({idx_host}/{total_hosts}): {url}")
                print(f"[NFSE] Usando certificado mTLS")
                print(f"[NFSE] Enviando com envelope SOAP GISS (XML escapado)")

                trocar_host = False

                for tentativa in range(1, max_tentativas + 1):
                    print(
                        f"[NFSE] Enviando requisição... tentativa {tentativa}/{max_tentativas} "
                        f"(host {idx_host}/{total_hosts})"
                    )

                    response = requests.post(
                        url,
                        data=soap_envelope.encode("utf-8"),
                        headers=headers,
                        cert=(cert_file_path, key_file_path),  # mTLS: certificado + chave privada
                        timeout=60,
                        verify=True  # Validar certificado SSL do servidor
                    )

                    print(f"[NFSE] Status HTTP: {response.status_code}")
                    print(f"[NFSE] Resposta: {len(response.text)} caracteres")

                    # DEBUG: Salvar última resposta
                    try:
                        with open('/tmp/last_nfse_response.xml', 'w', encoding='utf-8') as f:
                            f.write(response.text)
                        print(f"[NFSE] Resposta salva em /tmp/last_nfse_response.xml")
                    except:
                        pass

                    if response.status_code == 200:
                        sucesso, dados_resposta = self._processar_resposta_envio(response.text)
                        if sucesso:
                            dados_resposta["host_utilizado"] = urls_ativas.get("base")
                            return True, dados_resposta

                        if self._resposta_indisponivel_temporaria(dados_resposta):
                            ultima_indisponibilidade = dados_resposta
                            if not ultimo_diagnostico_endpoint:
                                ultimo_diagnostico_endpoint = self._diagnosticar_endpoint_ws(cert_file_path, key_file_path)

                            endpoint_online = bool((ultimo_diagnostico_endpoint or {}).get("endpoint_online"))
                            status_wsdl = (ultimo_diagnostico_endpoint or {}).get("status_http_wsdl")
                            diagnostico_endpoint = (
                                "Endpoint do provedor online; indisponibilidade operacional retornada no conteúdo"
                                if endpoint_online
                                else "Endpoint do provedor sem resposta estável"
                            )

                            if tentativa < max_tentativas:
                                espera = esperas_segundos[min(tentativa - 1, len(esperas_segundos) - 1)]
                                print(f"[NFSE] ⏳ Provedor indisponível temporariamente; nova tentativa em {espera}s")
                                time.sleep(espera)
                                continue

                            if idx_host < total_hosts:
                                print("[NFSE] ⚠️ Host atual indisponível após retentativas; alternando para host fallback")
                                trocar_host = True
                                break

                            return False, {
                                "erro": "Indisponibilidade operacional retornada pelo provedor",
                                "mensagem": (
                                    f"Provedor retornou indisponibilidade após {max_tentativas * total_hosts} tentativas "
                                    f"em {total_hosts} host(s). Tente novamente em alguns minutos."
                                ),
                                "retriavel": True,
                                "tentativas": max_tentativas * total_hosts,
                                "detalhe": dados_resposta.get("mensagem") or dados_resposta.get("erro"),
                                "hosts_testados": [u.get("base") for u in urls_envio],
                                "diagnostico_endpoint": diagnostico_endpoint,
                                "endpoint_online": endpoint_online,
                                "status_http_wsdl": status_wsdl,
                            }

                        return False, dados_resposta

                    if response.status_code in (502, 503, 504):
                        if tentativa < max_tentativas:
                            espera = esperas_segundos[min(tentativa - 1, len(esperas_segundos) - 1)]
                            print(f"[NFSE] ⏳ HTTP {response.status_code} temporário; nova tentativa em {espera}s")
                            time.sleep(espera)
                            continue

                        if idx_host < total_hosts:
                            print(
                                f"[NFSE] ⚠️ HTTP {response.status_code} persistente no host atual; "
                                "alternando para host fallback"
                            )
                            trocar_host = True
                            break

                    if response.status_code in (400, 404, 405) and idx_host < total_hosts:
                        print(
                            f"[NFSE] ⚠️ HTTP {response.status_code} no host atual; "
                            "alternando para próximo host fallback"
                        )
                        trocar_host = True
                        break

                    if response.status_code in (400, 404, 405) and ultima_indisponibilidade:
                        print(
                            f"[NFSE] ⚠️ Host fallback retornou HTTP {response.status_code}; "
                            "mantendo diagnóstico de indisponibilidade do provedor"
                        )
                        return False, {
                            "erro": "Indisponibilidade operacional retornada pelo provedor",
                            "mensagem": (
                                f"Provedor retornou indisponibilidade após {max_tentativas * total_hosts} tentativas "
                                f"em {total_hosts} host(s). Tente novamente em alguns minutos."
                            ),
                            "retriavel": True,
                            "tentativas": max_tentativas * total_hosts,
                            "detalhe": ultima_indisponibilidade.get("mensagem") or ultima_indisponibilidade.get("erro"),
                            "hosts_testados": [u.get("base") for u in urls_envio],
                            "ultimo_status_http": response.status_code,
                            "endpoint_online": bool((ultimo_diagnostico_endpoint or {}).get("endpoint_online")),
                            "status_http_wsdl": (ultimo_diagnostico_endpoint or {}).get("status_http_wsdl"),
                        }

                    print(f"[NFSE] ❌ Erro HTTP {response.status_code}")
                    return False, {
                        "erro": f"Erro HTTP {response.status_code}",
                        "mensagem": response.text[:500],
                        "status_code": response.status_code,
                        "host_utilizado": urls_ativas.get("base")
                    }

                if trocar_host:
                    continue

            if ultima_indisponibilidade:
                return False, {
                    "erro": "Indisponibilidade operacional retornada pelo provedor",
                    "mensagem": (
                        f"Provedor retornou indisponibilidade após {max_tentativas * total_hosts} tentativas "
                        f"em {total_hosts} host(s). Tente novamente em alguns minutos."
                    ),
                    "retriavel": True,
                    "tentativas": max_tentativas * total_hosts,
                    "detalhe": ultima_indisponibilidade.get("mensagem") or ultima_indisponibilidade.get("erro"),
                    "hosts_testados": [u.get("base") for u in urls_envio],
                    "endpoint_online": bool((ultimo_diagnostico_endpoint or {}).get("endpoint_online")),
                    "status_http_wsdl": (ultimo_diagnostico_endpoint or {}).get("status_http_wsdl"),
                }

            return False, {
                "erro": "Falha no envio após retentativas",
                "mensagem": "Não foi possível concluir o envio do lote após múltiplas tentativas"
            }
                
        except Exception as e:
            print(f"[NFSE] ❌ Erro ao enviar lote: {e}")
            import traceback
            traceback.print_exc()
            return False, {
                "erro": "Erro interno",
                "mensagem": str(e),
                "tipo": type(e).__name__
            }
        finally:
            if envio_lock_path and os.path.exists(envio_lock_path):
                try:
                    os.unlink(envio_lock_path)
                    print(f"[NFSE] Lock de envio removido: {envio_lock_path}")
                except Exception:
                    pass

            # Limpar arquivos temporários de certificado
            if cert_file_path and os.path.exists(cert_file_path):
                try:
                    os.unlink(cert_file_path)
                    print("[NFSE] Certificado temporário removido")
                except:
                    pass
            if key_file_path and os.path.exists(key_file_path):
                try:
                    os.unlink(key_file_path)
                    print("[NFSE] Chave privada temporária removida")
                except:
                    pass
    

    def _carregar_certificado_mtls(self, db_session, cliente_id: int):
        """
        Carrega o certificado digital ativo do cliente no banco e converte o
        PFX para um par PEM (cert, key) temporário, para uso em mTLS com
        `requests`. Espelha a lógica já usada em `enviar_lote_rps`.

        Returns:
            Tuple (cert_file_path, key_file_path) — o chamador é responsável
            por apagar os arquivos temporários após o uso.
        """
        from database.models import CertificadoDigital

        certificado = db_session.query(CertificadoDigital).filter(
            CertificadoDigital.cliente_id == cliente_id,
            CertificadoDigital.ativo == True
        ).first()

        if not certificado:
            raise ValueError("Certificado digital não encontrado ou inativo para este cliente")

        cert_data = certificado.conteudo_certificado
        cert_senha_encrypted = certificado.senha_certificado

        if not cert_data or not cert_senha_encrypted:
            raise ValueError("Dados do certificado incompletos (arquivo ou senha ausente)")

        cert_senha = _decrypt_password(cert_senha_encrypted)

        if not isinstance(cert_data, bytes):
            cert_data = base64.b64decode(cert_data)

        private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
            cert_data,
            cert_senha.encode('utf-8') if isinstance(cert_senha, str) else cert_senha
        )

        if not private_key or not certificate:
            raise ValueError("Não foi possível extrair chave e certificado do PFX do cliente")

        _validar_periodo_certificado_x509(certificate)

        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as cert_file:
            cert_file.write(certificate.public_bytes(Encoding.PEM))
            cert_file_path = cert_file.name

        with tempfile.NamedTemporaryFile(mode='wb', suffix='.key', delete=False) as key_file:
            key_file.write(private_key.private_bytes(
                encoding=Encoding.PEM,
                format=PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=NoEncryption()
            ))
            key_file_path = key_file.name

        return cert_file_path, key_file_path

    def consultar_lote(
        self,
        protocolo: str,
        prestador_cnpj: str,
        inscricao_municipal: str,
        db_session=None,
        cliente_id: Optional[int] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Consulta situação do lote de RPS no GISS Online.

        Args:
            protocolo: Número do protocolo retornado no envio
            prestador_cnpj: CNPJ do prestador
            inscricao_municipal: Inscrição municipal do prestador
            db_session: Sessão do banco (para carregar o certificado mTLS do cliente)
            cliente_id: ID do cliente (para carregar o certificado mTLS)

        Returns:
            Tuple (sucesso, dados_resposta) — quando sucesso, `dados_resposta`
            inclui `situacao_codigo`, `situacao`, e (se processado com
            sucesso) `numero_nfse`, `codigo_verificacao`,
            `chave_nota_nacional` e `xml_nfse` (o `CompNfse` completo).

        NOTA: a operação SOAP usada aqui (`ConsultarLoteRpsRequest`) segue o
        mesmo padrão de envelope já validado em `enviar_lote_rps`
        (`RecepcionarLoteRpsRequest`). Validar o nome exato da operação
        contra o WSDL do GISS em homologação antes de usar em produção.
        """
        cert_file_path = None
        key_file_path = None
        try:
            xml_consulta = f'''<?xml version="1.0" encoding="UTF-8"?>
<ConsultarLoteRpsEnvio xmlns="http://www.giss.com.br/tipos-v2_04.xsd">
    <Prestador>
        <CpfCnpj>
            <Cnpj>{prestador_cnpj}</Cnpj>
        </CpfCnpj>
        <InscricaoMunicipal>{inscricao_municipal}</InscricaoMunicipal>
    </Prestador>
    <Protocolo>{protocolo}</Protocolo>
</ConsultarLoteRpsEnvio>'''

            cabecalho = '''<cabecalho versao="2.04" xmlns="http://www.giss.com.br/cabecalho-v2_04.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <versaoDados>2.04</versaoDados>
</cabecalho>'''

            import html
            cabecalho_escaped = html.escape(cabecalho)
            dados_escaped = html.escape(xml_consulta)

            soap_envelope = f'''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:nfse="http://nfse.abrasf.org.br">
    <soapenv:Header/>
    <soapenv:Body>
        <nfse:ConsultarLoteRpsRequest>
            <nfseCabecMsg>{cabecalho_escaped}</nfseCabecMsg>
            <nfseDadosMsg>{dados_escaped}</nfseDadosMsg>
        </nfse:ConsultarLoteRpsRequest>
    </soapenv:Body>
</soapenv:Envelope>'''

            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": self._soap_action("ConsultarLoteRps"),
            }
            url = self.urls["base"] + self.urls["consultar_lote"]

            cert_param = None
            if db_session and cliente_id:
                cert_file_path, key_file_path = self._carregar_certificado_mtls(db_session, cliente_id)
                cert_param = (cert_file_path, key_file_path)
            elif self.cert_path:
                cert_param = (self.cert_path, self.cert_password)

            print(f"[NFSE] Consultando lote (protocolo={protocolo}) em {url}")
            response = requests.post(
                url,
                data=soap_envelope.encode("utf-8"),
                headers=headers,
                cert=cert_param,
                timeout=60
            )

            try:
                with open('/tmp/last_nfse_consulta_response.xml', 'w', encoding='utf-8') as f:
                    f.write(response.text)
            except Exception:
                pass

            if response.status_code == 200:
                return self._processar_resposta_consulta(response.text)
            else:
                return False, {"erro": f"Erro HTTP {response.status_code}", "mensagem": response.text[:500]}

        except Exception as e:
            print(f"[NFSE] ❌ Erro ao consultar lote: {e}")
            return False, {"erro": str(e)}
        finally:
            for path in (cert_file_path, key_file_path):
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    def cancelar_nfse(self, numero_nfse: str, codigo_cancelamento: str, prestador_cnpj: str, inscricao_municipal: str, codigo_municipio: str = "3549805") -> Tuple[bool, Dict[str, Any]]:
        """
        Cancela uma NFS-e
        
        Args:
            numero_nfse: Número da NFS-e a cancelar
            codigo_cancelamento: Código do motivo (1-Erro emissão, 2-Serviço não prestado, etc.)
            prestador_cnpj: CNPJ do prestador
            inscricao_municipal: Inscrição municipal
            codigo_municipio: Código IBGE do município
            
        Returns:
            Tuple (sucesso, dados_resposta)
        """
        try:
            xml_cancelamento = f'''<?xml version="1.0" encoding="UTF-8"?>
<CancelarNfseEnvio xmlns="http://www.abrasf.org.br/nfse.xsd">
    <Pedido>
        <InfPedidoCancelamento Id="cancel{numero_nfse}">
            <IdentificacaoNfse>
                <Numero>{numero_nfse}</Numero>
                <CpfCnpj>
                    <Cnpj>{prestador_cnpj}</Cnpj>
                </CpfCnpj>
                <InscricaoMunicipal>{inscricao_municipal}</InscricaoMunicipal>
                <CodigoMunicipio>{codigo_municipio}</CodigoMunicipio>
            </IdentificacaoNfse>
            <CodigoCancelamento>{codigo_cancelamento}</CodigoCancelamento>
        </InfPedidoCancelamento>
    </Pedido>
</CancelarNfseEnvio>'''
            
            # Assinar XML
            xml_assinado = self.assinar_xml(xml_cancelamento)
            
            soap_envelope = self._criar_envelope_soap("CancelarNfse", xml_assinado)
            
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "CancelarNfse"
            }
            
            url = self.urls["base"] + self.urls["cancelar"]
            
            response = requests.post(
                url,
                data=soap_envelope.encode("utf-8"),
                headers=headers,
                cert=(self.cert_path, self.cert_password) if self.cert_path else None,
                timeout=60
            )
            
            if response.status_code == 200:
                return self._processar_resposta_cancelamento(response.text)
            else:
                return False, {"erro": f"Erro HTTP {response.status_code}"}
                
        except Exception as e:
            return False, {"erro": str(e)}
    
    def _criar_envelope_soap(self, operacao: str, xml_conteudo: str) -> str:
        """Cria envelope SOAP para a operação"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
               xmlns:nfse="http://nfse.abrasf.org.br">
    <soap:Body>
        <nfse:{operacao}Envio>
            {xml_conteudo}
        </nfse:{operacao}Envio>
    </soap:Body>
</soap:Envelope>'''
    
    def _processar_resposta_envio(self, xml_resposta: str) -> Tuple[bool, Dict[str, Any]]:
        """Processa resposta do envio de lote GISS Online"""
        try:
            print("[NFSE] Processando resposta XML...")
            
            # Parse SOAP response
            root = etree.fromstring(xml_resposta.encode("utf-8"))
            
            # Buscar outputXML dentro do SOAP Body
            output_xml = root.find(".//{http://nfse.abrasf.org.br}outputXML")
            if output_xml is None:
                output_xml = root.find(".//outputXML")
            
            if output_xml is not None and output_xml.text:
                # Desescapar o XML interno
                import html
                xml_interno = html.unescape(output_xml.text)
                print(f"[NFSE] XML interno extraído: {len(xml_interno)} caracteres")
                
                # Parse o XML interno
                root_interno = etree.fromstring(xml_interno.encode("utf-8"))
                
                # Procurar por protocolo (sucesso)
                protocolo_elem = root_interno.find(".//{*}Protocolo")
                if protocolo_elem is None:
                    protocolo_elem = root_interno.find(".//{*}NumeroProtocolo")
                
                if protocolo_elem is not None and protocolo_elem.text:
                    protocolo = protocolo_elem.text.strip()
                    print(f"[NFSE] ✅ Protocolo recebido: {protocolo}")
                    
                    # Verificar se há NFS-e já autorizada (resposta síncrona)
                    numero_nfse_elem = root_interno.find(".//{*}NumeroNfse")
                    if numero_nfse_elem is None:
                        numero_nfse_elem = root_interno.find(".//{*}Numero")
                    
                    if numero_nfse_elem is not None and numero_nfse_elem.text:
                        numero_nfse = numero_nfse_elem.text.strip()
                        print(f"[NFSE] ✅ NFS-e autorizada: {numero_nfse}")
                        return True, {
                            "sucesso": True,
                            "protocolo": protocolo,
                            "numero_nfse": numero_nfse,
                            "mensagem": "NFS-e autorizada com sucesso"
                        }
                    
                    return True, {
                        "sucesso": True,
                        "protocolo": protocolo,
                        "mensagem": "Lote enviado. Aguardando processamento."
                    }
                
                # Procurar por mensagens de erro
                msg_retorno = root_interno.find(".//{*}MensagemRetorno")
                if msg_retorno is not None:
                    codigo = msg_retorno.find(".//{*}Codigo")
                    mensagem = msg_retorno.find(".//{*}Mensagem")
                    correcao = msg_retorno.find(".//{*}Correcao")
                    
                    erro_msg = ""
                    if codigo is not None and codigo.text:
                        erro_msg += f"Código {codigo.text}: "
                    if mensagem is not None and mensagem.text:
                        erro_msg += mensagem.text
                    if correcao is not None and correcao.text:
                        erro_msg += f" ({correcao.text})"
                    
                    print(f"[NFSE] ❌ Erro: {erro_msg}")
                    return False, {
                        "erro": erro_msg or "Erro no processamento",
                        "mensagem": erro_msg
                    }

            fault_string_elem = root.find(".//{*}faultstring")
            if fault_string_elem is not None and fault_string_elem.text:
                fault_text = fault_string_elem.text.strip()
                print(f"[NFSE] ❌ SOAP Fault: {fault_text}")
                return False, {
                    "sucesso": False,
                    "erro": "SOAP Fault",
                    "mensagem": fault_text
                }

            mensagem_erro_elem = (
                root.find(".//Mensagem")
                or root.find(".//MensagemErro")
                or root.find(".//{*}Mensagem")
                or root.find(".//{*}MensagemErro")
            )
            
            codigo_erro_elem = (
                root.find(".//Codigo") or 
                root.find(".//CodigoErro") or
                root.find(".//{*}Codigo") or
                root.find(".//{*}CodigoErro")
            )
            
            if mensagem_erro_elem is not None:
                codigo = codigo_erro_elem.text if codigo_erro_elem is not None else ""
                mensagem = mensagem_erro_elem.text or "Erro desconhecido"
                
                print(f"[NFSE] ❌ Erro retornado - Código: {codigo}, Mensagem: {mensagem}")
                
                return False, {
                    "sucesso": False,
                    "codigo_erro": codigo,
                    "mensagem": mensagem
                }
            
            # Se chegou aqui, não encontrou protocolo nem erro explícito
            # Pode ser uma resposta não padronizada
            print(f"[NFSE] ⚠️ Resposta sem protocolo ou erro claro")
            print(f"[NFSE] Primeiros 1000 caracteres: {xml_resposta[:1000]}")
            
            return False, {
                "sucesso": False,
                "mensagem": "Resposta não processada - formato inesperado",
                "xml_resposta_sample": xml_resposta[:1000]
            }
            
        except Exception as e:
            print(f"[NFSE] ❌ Erro ao processar resposta: {e}")
            import traceback
            traceback.print_exc()
            return False, {
                "sucesso": False,
                "erro": str(e),
                "tipo_erro": type(e).__name__,
                "xml_resposta_sample": xml_resposta[:500] if xml_resposta else ""
            }

    def _resposta_indisponivel_temporaria(self, dados_resposta: Optional[Dict[str, Any]]) -> bool:
        """Detecta mensagem transitória de indisponibilidade do provedor GISS."""
        if not dados_resposta:
            return False

        texto = " ".join([
            str(dados_resposta.get("mensagem", "")),
            str(dados_resposta.get("erro", "")),
        ]).strip()

        if not texto:
            return False

        texto_normalizado = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii").lower()
        return (
            "sistema esta indisponivel" in texto_normalizado
            and "tente novamente mais tarde" in texto_normalizado
        )

    def _diagnosticar_endpoint_ws(self, cert_file_path: str, key_file_path: str) -> Dict[str, Any]:
        """Sonda o WSDL com mTLS para separar indisponibilidade operacional de queda de endpoint."""
        wsdl_url = self.urls.get("wsdl")
        if not wsdl_url:
            return {"endpoint_online": False, "motivo": "wsdl_nao_configurado"}

        try:
            resp = requests.get(
                wsdl_url,
                cert=(cert_file_path, key_file_path),
                timeout=20,
                verify=True,
            )
            return {
                "endpoint_online": resp.status_code == 200,
                "status_http_wsdl": resp.status_code,
            }
        except Exception as e:
            return {
                "endpoint_online": False,
                "erro_wsdl": str(e),
            }

    def _config_retry_envio(self) -> Tuple[int, List[int]]:
        """Resolve retentativas por ambiente com defaults mais curtos em homologação."""
        max_tentativas = int(
            os.getenv(
                f"NFSE_RETRY_ATTEMPTS_{self.ambiente.upper()}",
                os.getenv("NFSE_RETRY_ATTEMPTS", "2" if self.ambiente == "homologacao" else "5")
            )
        )

        delays_env = os.getenv(
            f"NFSE_RETRY_DELAYS_{self.ambiente.upper()}",
            os.getenv("NFSE_RETRY_DELAYS", "1,2" if self.ambiente == "homologacao" else "2,5,10,20")
        )
        esperas_segundos: List[int] = []
        for item in delays_env.split(','):
            item = item.strip()
            if item.isdigit():
                esperas_segundos.append(int(item))

        if not esperas_segundos:
            esperas_segundos = [1, 2] if self.ambiente == "homologacao" else [2, 5, 10, 20]

        if max_tentativas < 1:
            max_tentativas = 1

        return max_tentativas, esperas_segundos
    
    def _processar_resposta_consulta(self, xml_resposta: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Processa resposta da consulta de lote.

        Além da situação do lote, extrai (quando disponível) o `CompNfse`
        completo retornado pelo GISS — incluindo `ChaveNotaNacional` (chave de
        acesso da NFS-e no Ambiente de Dados Nacional), `Numero` e
        `CodigoVerificacao` — necessários para persistir a NFS-e nacional e,
        posteriormente, gerar o DANFSe (NT008).
        """
        try:
            root = etree.fromstring(xml_resposta.encode("utf-8"))

            # Situação do lote
            # 1-Não Recebido, 2-Não Processado, 3-Processado com Erro, 4-Processado com Sucesso
            situacao = root.find(".//{*}Situacao")

            if situacao is None:
                return False, {"erro": "Situação não encontrada na resposta"}

            situacao_code = situacao.text
            situacoes = {
                "1": "Não Recebido",
                "2": "Não Processado",
                "3": "Processado com Erro",
                "4": "Processado com Sucesso"
            }
            resultado: Dict[str, Any] = {
                "situacao_codigo": situacao_code,
                "situacao": situacoes.get(situacao_code, "Desconhecida"),
            }

            comp_nfse = root.find(".//{*}CompNfse")
            if comp_nfse is not None:
                def texto(tag: str, contexto=comp_nfse) -> Optional[str]:
                    el = contexto.find(f".//{{*}}{tag}")
                    return el.text.strip() if el is not None and el.text else None

                inf_nfse = comp_nfse.find(".//{*}InfNfse")
                resultado["numero_nfse"] = texto("Numero", inf_nfse) if inf_nfse is not None else None
                resultado["codigo_verificacao"] = texto("CodigoVerificacao", inf_nfse) if inf_nfse is not None else None
                # Chave de acesso da NFS-e no Ambiente de Dados Nacional (ADN) —
                # exigida para consulta pública e para o DANFSe (NT008)
                resultado["chave_nota_nacional"] = texto("ChaveNotaNacional")
                resultado["nfse_cancelada"] = comp_nfse.find(".//{*}NfseCancelamento") is not None
                resultado["xml_nfse"] = etree.tostring(
                    comp_nfse, encoding="unicode", pretty_print=True
                )

            return True, resultado

        except Exception as e:
            return False, {"erro": str(e)}
    
    def _processar_resposta_cancelamento(self, xml_resposta: str) -> Tuple[bool, Dict[str, Any]]:
        """Processa resposta do cancelamento"""
        try:
            root = etree.fromstring(xml_resposta.encode("utf-8"))
            
            # Verificar confirmação de cancelamento
            data_hora = root.find(".//{*}DataHora") or root.find(".//{*}DataHoraCancelamento")
            
            if data_hora is not None:
                return True, {
                    "sucesso": True,
                    "data_cancelamento": data_hora.text,
                    "mensagem": "NFS-e cancelada com sucesso"
                }
            
            # Verificar erros
            mensagem = root.find(".//{*}Mensagem")
            if mensagem is not None:
                return False, {"erro": mensagem.text}
            
            return False, {"erro": "Resposta não processada"}
            
        except Exception as e:
            return False, {"erro": str(e)}
    
    def obter_aliquota_iss(self, codigo_servico: str) -> float:
        """
        Obtém alíquota ISS para o código de serviço
        
        Args:
            codigo_servico: Código do serviço LC 116/2003
            
        Returns:
            Alíquota ISS em percentual
        """
        return ALIQUOTAS_ISS_SJRP.get(codigo_servico, ALIQUOTAS_ISS_SJRP["default"])


# Função auxiliar para criar NFS-e a partir de dados do formulário
def criar_nfse_de_formulario(dados: Dict[str, Any], prestador_data: Dict[str, Any]) -> NFSeNacional:
    """
    Cria objeto NFSeNacional a partir dos dados do formulário
    
    Args:
        dados: Dados do formulário
        prestador_data: Dados do prestador (emitente)
        
    Returns:
        Objeto NFSeNacional preenchido
    """

    dados["codigo_nbs"] = normalizar_codigo_nbs(dados.get("codigo_nbs", DEFAULT_CODIGO_NBS))
    
    # Prestador
    prestador = PrestadorNFSe(
        cnpj=prestador_data.get("cnpj", ""),
        inscricao_municipal=prestador_data.get("inscricao_municipal", ""),
        razao_social=prestador_data.get("razao_social", ""),
        nome_fantasia=prestador_data.get("nome_fantasia"),
        endereco_logradouro=prestador_data.get("logradouro", ""),
        endereco_numero=prestador_data.get("numero", ""),
        endereco_complemento=prestador_data.get("complemento", ""),
        endereco_bairro=prestador_data.get("bairro", ""),
        endereco_codigo_municipio=prestador_data.get("codigo_municipio", "3549805"),
        endereco_uf=prestador_data.get("uf", "SP"),
        endereco_cep=prestador_data.get("cep", ""),
        telefone=prestador_data.get("telefone", ""),
        email=prestador_data.get("email", ""),
        optante_simples_nacional=prestador_data.get("optante_simples", True)
    )
    
    # Tomadores
    Tomadores = TomadoresNFSe(
        tipo_documento="CNPJ" if len(dados.get("tomador_cpf_cnpj", "").replace(".", "").replace("-", "").replace("/", "")) == 14 else "CPF",
        cpf_cnpj=dados.get("tomador_cpf_cnpj", "").replace(".", "").replace("-", "").replace("/", ""),
        razao_social=dados.get("tomador_razao_social", ""),
        inscricao_municipal=dados.get("tomador_inscricao_municipal"),
        endereco_logradouro=dados.get("tomador_logradouro", ""),
        endereco_numero=dados.get("tomador_numero", ""),
        endereco_complemento=dados.get("tomador_complemento", ""),
        endereco_bairro=dados.get("tomador_bairro", ""),
        endereco_codigo_municipio=dados.get("tomador_codigo_municipio", ""),
        endereco_uf=dados.get("tomador_uf", "SP"),
        endereco_cep=dados.get("tomador_cep", ""),
        telefone=dados.get("tomador_telefone", ""),
        email=dados.get("tomador_email", "")
    )
    
    # Serviço
    servico = ServicoNFSe(
        codigo_tributacao_nacional=dados.get("codigo_servico", "17.01"),
        codigo_cnae=dados.get("codigo_cnae"),
        discriminacao=dados.get("discriminacao", ""),
        valor_servicos=float(dados.get("valor_servico", 0)),
        valor_deducoes=float(dados.get("valor_deducoes", 0)),
        valor_pis=float(dados.get("valor_pis", 0)),
        valor_cofins=float(dados.get("valor_cofins", 0)),
        valor_inss=float(dados.get("valor_inss", 0)),
        valor_ir=float(dados.get("valor_ir", 0)),
        valor_csll=float(dados.get("valor_csll", 0)),
        valor_pis_operacao=float(dados.get("valor_pis_operacao", dados.get("valor_pis", 0))),
        valor_cofins_operacao=float(dados.get("valor_cofins_operacao", dados.get("valor_cofins", 0))),
        outras_retencoes=float(dados.get("outras_retencoes", 0)),
        desconto_incondicionado=float(dados.get("desconto_incondicionado", 0)),
        desconto_condicionado=float(dados.get("desconto_condicionado", 0)),
        aliquota_iss=float(dados.get("aliquota_iss", 0)),
        aliquota_pis=float(dados.get("aliquota_pis", 0)),
        aliquota_cofins=float(dados.get("aliquota_cofins", 0)),
        iss_retido=dados.get("iss_retido", False),
        csll_retida=dados.get("csll_retida", float(dados.get("valor_csll", 0)) > 0),
        cst_pis_cofins=dados.get("cst_pis_cofins", "00"),
        tipo_retencao_pis_cofins=dados.get(
            "tipo_retencao_pis_cofins",
            "1" if (float(dados.get("valor_pis", 0)) > 0 or float(dados.get("valor_cofins", 0)) > 0) else "2"
        ),
        codigo_municipio_prestacao=dados.get("codigo_municipio_prestacao", "3549805"),
        codigo_pais=dados.get("codigo_pais", "1058"),
        base_calculo_pis_cofins=float(dados.get("base_calculo_pis_cofins", 0)),
        
        # Campos Reforma Tributária (LC 214/2025) - Obrigatórios GISS Online
        codigo_nbs=dados.get("codigo_nbs", DEFAULT_CODIGO_NBS),
        percentual_total_tributos_federais=float(dados.get("percentual_total_tributos_federais", 0)),
        percentual_total_tributos_estaduais=float(dados.get("percentual_total_tributos_estaduais", 0)),
        percentual_total_tributos_municipais=float(dados.get("percentual_total_tributos_municipais", 5)),
        finalidade_nfse=dados.get("finalidade_nfse", "0"),
        indicador_consumidor_final=dados.get("indicador_consumidor_final", "0"),
        codigo_indicador_operacao=dados.get("codigo_indicador_operacao", "000001"),
        indicador_destinatario=dados.get("indicador_destinatario", "0"),
        cst_ibs_cbs=dados.get("cst_ibs_cbs", "001"),
        codigo_classificacao_tributaria=dados.get("codigo_classificacao_tributaria", "000001"),
        codigo_localidade_incidencia=dados.get("codigo_localidade_incidencia", "3549805"),
        percentual_redutor=float(dados.get("percentual_redutor", 0))
    )
    
    # NFS-e
    nfse = NFSeNacional(
        cliente_id=dados.get("cliente_id", 0),
        numero_rps=dados.get("numero_rps"),
        serie_rps=dados.get("serie_rps", "1"),
        tipo_rps=dados.get("tipo_rps", "1"),
        data_emissao=datetime.now(),
        data_competencia=datetime.strptime(dados["data_competencia"], "%Y-%m-%d") if dados.get("data_competencia") else None,
        natureza_operacao=dados.get("natureza_operacao", "1"),
        regime_especial_tributacao=dados.get("regime_especial_tributacao"),
        optante_simples_nacional=dados.get("optante_simples_nacional", prestador_data.get("optante_simples", True)),
        incentivador_cultural=dados.get("incentivador_cultural", False),
        ambiente=dados.get("ambiente", "homologacao"),
        prestador=prestador,
        Tomadores=Tomadores,
        servico=servico,
        informacoes_complementares=dados.get("informacoes_complementares", "")
    )
    
    return nfse
