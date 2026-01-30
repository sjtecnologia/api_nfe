"""
Service para NFS-e Nacional - São José do Rio Preto
Geração de XML, comunicação com webservice e processamento
"""

import os
import json
import requests
import hashlib
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from lxml import etree

# Importar models
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.nfse_model import (
    NFSeNacional, PrestadorNFSe, TomadoresNFSe, ServicoNFSe,
    CODIGOS_SERVICO_LC116, CODIGOS_MUNICIPIO_SP, ALIQUOTAS_ISS_SJRP
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
    
    # URLs do webservice - São José do Rio Preto usa GISS Online
    URLS_SJRP = {
        "homologacao": {
            "base": "https://homologacao.giss.com.br/SaoJoseDoRioPreto/servlet/",
            "wsdl": "https://homologacao.giss.com.br/SaoJoseDoRioPreto/servlet/aws_nfse?wsdl",
            "enviar_lote": "aws_nfse",
            "consultar_lote": "aws_nfse",
            "consultar_nfse": "aws_nfse",
            "cancelar": "aws_nfse"
        },
        "producao": {
            "base": "https://www.giss.com.br/SaoJoseDoRioPreto/servlet/",
            "wsdl": "https://www.giss.com.br/SaoJoseDoRioPreto/servlet/aws_nfse?wsdl",
            "enviar_lote": "aws_nfse",
            "consultar_lote": "aws_nfse",
            "consultar_nfse": "aws_nfse",
            "cancelar": "aws_nfse"
        }
    }
    
    def __init__(self, ambiente: str = "homologacao"):
        """
        Inicializa o serviço NFS-e
        
        Args:
            ambiente: 'homologacao' ou 'producao'
        """
        self.ambiente = ambiente
        self.urls = self.URLS_SJRP.get(ambiente, self.URLS_SJRP["homologacao"])
        
        # Configurações do certificado
        self.cert_path = os.getenv("CERT_PATH", "/home/ubuntu/api_nfe/certs/certificado.pfx")
        self.cert_password = os.getenv("CERT_PASSWORD", "")
        
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
        lote_rps.set("versao", "2.04")
        
        # p1:NumeroLote
        etree.SubElement(lote_rps, "{%s}NumeroLote" % self.NS_TIPOS).text = str(nfse.lote or self.gerar_id_lote())
        
        # p1:Prestador (dentro do lote)
        prestador_lote = etree.SubElement(lote_rps, "{%s}Prestador" % self.NS_TIPOS)
        cpf_cnpj_prest_lote = etree.SubElement(prestador_lote, "{%s}CpfCnpj" % self.NS_TIPOS)
        etree.SubElement(cpf_cnpj_prest_lote, "{%s}Cnpj" % self.NS_TIPOS).text = nfse.prestador.cnpj
        if nfse.prestador.inscricao_municipal:
            etree.SubElement(prestador_lote, "{%s}InscricaoMunicipal" % self.NS_TIPOS).text = nfse.prestador.inscricao_municipal
        
        # p1:QuantidadeRps
        etree.SubElement(lote_rps, "{%s}QuantidadeRps" % self.NS_TIPOS).text = "1"
        
        # p1:ListaRps
        lista_rps = etree.SubElement(lote_rps, "{%s}ListaRps" % self.NS_TIPOS)
        
        # p1:Rps
        rps = etree.SubElement(lista_rps, "{%s}Rps" % self.NS_TIPOS)
        
        # p1:InfDeclaracaoPrestacaoServico
        inf_rps = etree.SubElement(rps, "{%s}InfDeclaracaoPrestacaoServico" % self.NS_TIPOS)
        inf_rps.set("Id", f"rps{nfse.numero_rps or 1}")
        
        # p1:Rps (identificação)
        rps_ident = etree.SubElement(inf_rps, "{%s}Rps" % self.NS_TIPOS)
        ident_rps = etree.SubElement(rps_ident, "{%s}IdentificacaoRps" % self.NS_TIPOS)
        etree.SubElement(ident_rps, "{%s}Numero" % self.NS_TIPOS).text = str(nfse.numero_rps or 1)
        etree.SubElement(ident_rps, "{%s}Serie" % self.NS_TIPOS).text = nfse.serie_rps
        etree.SubElement(ident_rps, "{%s}Tipo" % self.NS_TIPOS).text = nfse.tipo_rps
        
        # Data de emissão
        etree.SubElement(rps_ident, "{%s}DataEmissao" % self.NS_TIPOS).text = nfse.data_emissao.strftime("%Y-%m-%d")
        etree.SubElement(rps_ident, "{%s}Status" % self.NS_TIPOS).text = "1"  # Normal
        
        # p1:Competencia
        etree.SubElement(inf_rps, "{%s}Competencia" % self.NS_TIPOS).text = (nfse.data_competencia or nfse.data_emissao).strftime("%Y-%m-%d")
        
        # p1:Servico
        servico_el = etree.SubElement(inf_rps, "{%s}Servico" % self.NS_TIPOS)
        
        # p1:Valores do serviço
        valores = etree.SubElement(servico_el, "{%s}Valores" % self.NS_TIPOS)
        etree.SubElement(valores, "{%s}ValorServicos" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_servicos)
        
        if nfse.servico.valor_deducoes > 0:
            etree.SubElement(valores, "{%s}ValorDeducoes" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_deducoes)
        if nfse.servico.valor_pis > 0:
            etree.SubElement(valores, "{%s}ValorPis" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_pis)
        if nfse.servico.valor_cofins > 0:
            etree.SubElement(valores, "{%s}ValorCofins" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_cofins)
        if nfse.servico.valor_inss > 0:
            etree.SubElement(valores, "{%s}ValorInss" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_inss)
        if nfse.servico.valor_ir > 0:
            etree.SubElement(valores, "{%s}ValorIr" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_ir)
        if nfse.servico.valor_csll > 0:
            etree.SubElement(valores, "{%s}ValorCsll" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_csll)
        if nfse.servico.outras_retencoes > 0:
            etree.SubElement(valores, "{%s}OutrasRetencoes" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.outras_retencoes)
        
        if nfse.servico.valor_iss > 0:
            etree.SubElement(valores, "{%s}ValorIss" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.valor_iss)
        
        etree.SubElement(valores, "{%s}Aliquota" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.aliquota_iss)
        
        if nfse.servico.desconto_incondicionado > 0:
            etree.SubElement(valores, "{%s}DescontoIncondicionado" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.desconto_incondicionado)
        if nfse.servico.desconto_condicionado > 0:
            etree.SubElement(valores, "{%s}DescontoCondicionado" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.desconto_condicionado)
        
        # p1:trib - Tributos totais (obrigatório GISS)
        trib = etree.SubElement(valores, "{%s}trib" % self.NS_TIPOS)
        tot_trib = etree.SubElement(trib, "{%s}totTrib" % self.NS_TIPOS)
        p_tot_trib = etree.SubElement(tot_trib, "{%s}pTotTrib" % self.NS_TIPOS)
        etree.SubElement(p_tot_trib, "{%s}pTotTribFed" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.percentual_total_tributos_federais)
        etree.SubElement(p_tot_trib, "{%s}pTotTribEst" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.percentual_total_tributos_estaduais)
        etree.SubElement(p_tot_trib, "{%s}pTotTribMun" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.percentual_total_tributos_municipais)
        
        # p1:IBSCBS - Reforma Tributária (obrigatório GISS)
        ibs_cbs = etree.SubElement(valores, "{%s}IBSCBS" % self.NS_TIPOS)
        etree.SubElement(ibs_cbs, "{%s}finNFSe" % self.NS_TIPOS).text = nfse.servico.finalidade_nfse
        etree.SubElement(ibs_cbs, "{%s}indFinal" % self.NS_TIPOS).text = nfse.servico.indicador_consumidor_final
        etree.SubElement(ibs_cbs, "{%s}cIndOp" % self.NS_TIPOS).text = nfse.servico.codigo_indicador_operacao
        etree.SubElement(ibs_cbs, "{%s}indDest" % self.NS_TIPOS).text = nfse.servico.indicador_destinatario
        
        # p1:valores (dentro de IBSCBS)
        valores_ibs = etree.SubElement(ibs_cbs, "{%s}valores" % self.NS_TIPOS)
        trib_ibs = etree.SubElement(valores_ibs, "{%s}trib" % self.NS_TIPOS)
        g_ibs_cbs = etree.SubElement(trib_ibs, "{%s}gIBSCBS" % self.NS_TIPOS)
        etree.SubElement(g_ibs_cbs, "{%s}CST" % self.NS_TIPOS).text = nfse.servico.cst_ibs_cbs
        etree.SubElement(g_ibs_cbs, "{%s}cClassTrib" % self.NS_TIPOS).text = nfse.servico.codigo_classificacao_tributaria
        
        etree.SubElement(valores_ibs, "{%s}cLocalidadeIncid" % self.NS_TIPOS).text = nfse.servico.codigo_localidade_incidencia
        etree.SubElement(valores_ibs, "{%s}pRedutor" % self.NS_TIPOS).text = self.formatar_valor(nfse.servico.percentual_redutor)
        
        # p1:IssRetido
        etree.SubElement(servico_el, "{%s}IssRetido" % self.NS_TIPOS).text = "1" if nfse.servico.iss_retido else "2"
        
        # p1:ItemListaServico (código LC 116)
        etree.SubElement(servico_el, "{%s}ItemListaServico" % self.NS_TIPOS).text = nfse.servico.codigo_tributacao_nacional
        
        # p1:CodigoCnae (opcional)
        if nfse.servico.codigo_cnae:
            etree.SubElement(servico_el, "{%s}CodigoCnae" % self.NS_TIPOS).text = nfse.servico.codigo_cnae
        
        # p1:CodigoNbs (obrigatório GISS)
        etree.SubElement(servico_el, "{%s}CodigoNbs" % self.NS_TIPOS).text = nfse.servico.codigo_nbs
        
        # p1:Discriminacao do serviço
        etree.SubElement(servico_el, "{%s}Discriminacao" % self.NS_TIPOS).text = self.limpar_texto(nfse.servico.discriminacao)
        
        # p1:CodigoMunicipio de prestação
        etree.SubElement(servico_el, "{%s}CodigoMunicipio" % self.NS_TIPOS).text = nfse.servico.codigo_municipio_prestacao or "3549805"
        
        # p1:ExigibilidadeISS
        etree.SubElement(servico_el, "{%s}ExigibilidadeISS" % self.NS_TIPOS).text = "1"  # Exigível
        
        # p1:Prestador
        prestador_el = etree.SubElement(inf_rps, "{%s}Prestador" % self.NS_TIPOS)
        cpf_cnpj_prestador = etree.SubElement(prestador_el, "{%s}CpfCnpj" % self.NS_TIPOS)
        etree.SubElement(cpf_cnpj_prestador, "{%s}Cnpj" % self.NS_TIPOS).text = nfse.prestador.cnpj
        if nfse.prestador.inscricao_municipal:
            etree.SubElement(prestador_el, "{%s}InscricaoMunicipal" % self.NS_TIPOS).text = nfse.prestador.inscricao_municipal
        
        # p1:TomadoresServico
        if nfse.Tomadores:
            tomador_el = etree.SubElement(inf_rps, "{%s}TomadoresServico" % self.NS_TIPOS)
            ident_Tomadores = etree.SubElement(tomador_el, "{%s}IdentificacaoTomadores" % self.NS_TIPOS)
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
                if nfse.Tomadores.endereco_numero:
                    etree.SubElement(endereco_Tomadores, "{%s}Numero" % self.NS_TIPOS).text = nfse.Tomadores.endereco_numero[:10]
                if nfse.Tomadores.endereco_complemento:
                    etree.SubElement(endereco_Tomadores, "{%s}Complemento" % self.NS_TIPOS).text = nfse.Tomadores.endereco_complemento[:60]
                if nfse.Tomadores.endereco_bairro:
                    etree.SubElement(endereco_Tomadores, "{%s}Bairro" % self.NS_TIPOS).text = nfse.Tomadores.endereco_bairro[:60]
                if nfse.Tomadores.endereco_codigo_municipio:
                    etree.SubElement(endereco_Tomadores, "{%s}CodigoMunicipio" % self.NS_TIPOS).text = nfse.Tomadores.endereco_codigo_municipio
                if nfse.Tomadores.endereco_uf:
                    etree.SubElement(endereco_Tomadores, "{%s}Uf" % self.NS_TIPOS).text = nfse.Tomadores.endereco_uf
                if nfse.Tomadores.endereco_cep:
                    etree.SubElement(endereco_Tomadores, "{%s}Cep" % self.NS_TIPOS).text = nfse.Tomadores.endereco_cep.replace("-", "")[:8]
            
            # Contato do Tomadores
            if nfse.Tomadores.telefone or nfse.Tomadores.email:
                contato_Tomadores = etree.SubElement(tomador_el, "{%s}Contato" % self.NS_TIPOS)
                if nfse.Tomadores.telefone:
                    etree.SubElement(contato_Tomadores, "{%s}Telefone" % self.NS_TIPOS).text = nfse.Tomadores.telefone[:20]
                if nfse.Tomadores.email:
                    etree.SubElement(contato_Tomadores, "{%s}Email" % self.NS_TIPOS).text = nfse.Tomadores.email[:80]
        
        # p1:OptanteSimplesNacional
        etree.SubElement(inf_rps, "{%s}OptanteSimplesNacional" % self.NS_TIPOS).text = "1" if nfse.optante_simples_nacional else "2"
        
        # p1:IncentivoFiscal
        etree.SubElement(inf_rps, "{%s}IncentivoFiscal" % self.NS_TIPOS).text = "1" if nfse.incentivador_cultural else "2"
        
        # Converter para string
        xml_str = etree.tostring(root, encoding="unicode", pretty_print=True)
        
        # Adicionar declaração XML
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
        
        return xml_str
    
    def assinar_xml(self, xml: str, db_session=None, cliente_id: Optional[int] = None) -> str:
        """
        Assina o XML RPS da NFS-e com certificado digital A1
        
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
            from pynfe.processamento.assinatura import AssinaturaA1
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
            
            # 4. Criar assinador PyNFe
            assinador = AssinaturaA1(cert_file_path, cert_senha)
            
            # 5. Parse do XML
            if isinstance(xml, str):
                xml_element = etree.fromstring(xml.encode('utf-8'))
            elif isinstance(xml, bytes):
                xml_element = etree.fromstring(xml)
            else:
                xml_element = xml
            
            # 6. Assinar (PyNFe assina automaticamente a tag com atributo Id)
            print("[NFSE] Assinando com PyNFe...")
            xml_assinado = assinador.assinar(xml_element, retorna_string=True)
            
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
        try:
            print(f"[NFSE] === ENVIANDO RPS PARA GISS ONLINE ===")
            print(f"[NFSE] Ambiente: {self.ambiente}")
            print(f"[NFSE] Cliente ID: {nfse.cliente_id}")
            
            # 1. Gerar XML RPS
            xml_rps = self.gerar_xml_rps(nfse)
            nfse.xml_rps = xml_rps
            print(f"[NFSE] XML RPS gerado: {len(xml_rps)} caracteres")
            
            # 2. Assinar XML
            xml_assinado = self.assinar_xml(xml_rps, db_session=db_session, cliente_id=nfse.cliente_id)
            print(f"[NFSE] XML assinado: {len(xml_assinado)} caracteres")
            
            # 3. Criar envelope SOAP para RecepcionarLoteRps
            # GISS Online usa estrutura específica
            soap_envelope = f'''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
               xmlns:ws="http://nfse.abrasf.org.br">
    <soap:Body>
        <ws:RecepcionarLoteRpsRequest>
            <nfseCabecMsg>
                <![CDATA[<?xml version="1.0" encoding="UTF-8"?>
<cabecalho xmlns="http://www.abrasf.org.br/nfse.xsd" versao="2.04">
    <versaoDados>2.04</versaoDados>
</cabecalho>]]>
            </nfseCabecMsg>
            <nfseDadosMsg>
                <![CDATA[{xml_assinado}]]>
            </nfseDadosMsg>
        </ws:RecepcionarLoteRpsRequest>
    </soap:Body>
</soap:Envelope>'''
            
            # 4. Headers HTTP
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "RecepcionarLoteRps"
            }
            
            # 5. URL do webservice
            url = self.urls["base"] + self.urls["enviar_lote"]
            print(f"[NFSE] URL: {url}")
            
            # 6. Fazer requisição HTTP POST
            print(f"[NFSE] Enviando requisição SOAP...")
            
            response = requests.post(
                url,
                data=soap_envelope.encode("utf-8"),
                headers=headers,
                timeout=60,
                verify=True  # Validar certificado SSL
            )
            
            print(f"[NFSE] Status HTTP: {response.status_code}")
            print(f"[NFSE] Resposta: {len(response.text)} caracteres")
            
            # DEBUG: Salvar resposta
            try:
                with open('/tmp/last_nfse_response.xml', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"[NFSE] Resposta salva em /tmp/last_nfse_response.xml")
            except:
                pass
            
            # 7. Processar resposta
            if response.status_code == 200:
                return self._processar_resposta_envio(response.text)
            else:
                print(f"[NFSE] ❌ Erro HTTP {response.status_code}")
                return False, {
                    "erro": f"Erro HTTP {response.status_code}",
                    "mensagem": response.text[:500],
                    "status_code": response.status_code
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
    
    def consultar_lote(self, protocolo: str, prestador_cnpj: str, inscricao_municipal: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Consulta situação do lote de RPS
        
        Args:
            protocolo: Número do protocolo retornado no envio
            prestador_cnpj: CNPJ do prestador
            inscricao_municipal: Inscrição municipal do prestador
            
        Returns:
            Tuple (sucesso, dados_resposta)
        """
        try:
            # Montar XML de consulta
            xml_consulta = f'''<?xml version="1.0" encoding="UTF-8"?>
<ConsultarSituacaoLoteRpsEnvio xmlns="http://www.abrasf.org.br/nfse.xsd">
    <Prestador>
        <CpfCnpj>
            <Cnpj>{prestador_cnpj}</Cnpj>
        </CpfCnpj>
        <InscricaoMunicipal>{inscricao_municipal}</InscricaoMunicipal>
    </Prestador>
    <Protocolo>{protocolo}</Protocolo>
</ConsultarSituacaoLoteRpsEnvio>'''
            
            # Montar envelope SOAP
            soap_envelope = self._criar_envelope_soap("ConsultarSituacaoLoteRps", xml_consulta)
            
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "ConsultarSituacaoLoteRps"
            }
            
            url = self.urls["base"] + self.urls["consultar_lote"]
            
            response = requests.post(
                url,
                data=soap_envelope.encode("utf-8"),
                headers=headers,
                cert=(self.cert_path, self.cert_password) if self.cert_path else None,
                timeout=60
            )
            
            if response.status_code == 200:
                return self._processar_resposta_consulta(response.text)
            else:
                return False, {"erro": f"Erro HTTP {response.status_code}"}
                
        except Exception as e:
            return False, {"erro": str(e)}
    
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
            
            # Parse XML
            # Remove namespace prefixes para facilitar busca
            xml_limpo = xml_resposta
            for ns_prefix in ['soap:', 'ns1:', 'ns2:', 'ws:', 'nfse:']:
                xml_limpo = xml_limpo.replace(ns_prefix, '')
            
            root = etree.fromstring(xml_limpo.encode("utf-8"))
            
            # Procurar por protocolo (sucesso)
            # GISS pode retornar em diferentes estruturas
            protocolo_elem = (
                root.find(".//Protocolo") or 
                root.find(".//NumeroProtocolo") or
                root.find(".//{*}Protocolo") or
                root.find(".//{*}NumeroProtocolo")
            )
            
            if protocolo_elem is not None and protocolo_elem.text:
                protocolo = protocolo_elem.text.strip()
                print(f"[NFSE] ✅ Protocolo recebido: {protocolo}")
                
                # Verificar se há NFS-e já autorizada (resposta síncrona)
                numero_nfse_elem = (
                    root.find(".//NumeroNfse") or
                    root.find(".//Numero") or
                    root.find(".//{*}NumeroNfse")
                )
                
                if numero_nfse_elem is not None and numero_nfse_elem.text:
                    numero_nfse = numero_nfse_elem.text.strip()
                    print(f"[NFSE] ✅ NFS-e autorizada imediatamente: {numero_nfse}")
                    return True, {
                        "sucesso": True,
                        "protocolo": protocolo,
                        "numero_nfse": numero_nfse,
                        "mensagem": "NFS-e autorizada com sucesso",
                        "sincrono": True
                    }
                
                return True, {
                    "sucesso": True,
                    "protocolo": protocolo,
                    "mensagem": "Lote enviado com sucesso. Aguardando processamento.",
                    "sincrono": False
                }
            
            # Procurar por erros
            mensagem_erro_elem = (
                root.find(".//Mensagem") or 
                root.find(".//MensagemRetorno") or
                root.find(".//DescricaoErro") or
                root.find(".//{*}Mensagem") or
                root.find(".//{*}MensagemRetorno")
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
    
    def _processar_resposta_consulta(self, xml_resposta: str) -> Tuple[bool, Dict[str, Any]]:
        """Processa resposta da consulta de lote"""
        try:
            root = etree.fromstring(xml_resposta.encode("utf-8"))
            
            # Situação do lote
            # 1-Não Recebido, 2-Não Processado, 3-Processado com Erro, 4-Processado com Sucesso
            situacao = root.find(".//{*}Situacao")
            
            if situacao is not None:
                situacao_code = situacao.text
                situacoes = {
                    "1": "Não Recebido",
                    "2": "Não Processado",
                    "3": "Processado com Erro",
                    "4": "Processado com Sucesso"
                }
                return True, {
                    "situacao_codigo": situacao_code,
                    "situacao": situacoes.get(situacao_code, "Desconhecida")
                }
            
            return False, {"erro": "Situação não encontrada na resposta"}
            
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
        outras_retencoes=float(dados.get("outras_retencoes", 0)),
        desconto_incondicionado=float(dados.get("desconto_incondicionado", 0)),
        desconto_condicionado=float(dados.get("desconto_condicionado", 0)),
        aliquota_iss=float(dados.get("aliquota_iss", 0)),
        iss_retido=dados.get("iss_retido", False),
        codigo_municipio_prestacao=dados.get("codigo_municipio_prestacao", "3549805"),
        codigo_pais=dados.get("codigo_pais", "1058"),
        
        # Campos Reforma Tributária (LC 214/2025) - Obrigatórios GISS Online
        codigo_nbs=dados.get("codigo_nbs", "101010000"),
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
