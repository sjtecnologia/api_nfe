"""
Serviço de Validação NFS-e - Reforma Tributária NT007 v1.03.00
Data: 09/02/2026
Referência: AnexoVII - IndOp_IBSCBS v1.01.00
"""

from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from lxml import etree


class NFSeValidationService:
    """
    Serviço de validação de dados NFS-e conforme NT007 v1.03.00
    """
    
    @staticmethod
    def validar_codigo_indicador_operacao(codigo: str, db: Session) -> Tuple[bool, str, Optional[Dict]]:
        """
        Valida se código de indicador de operação existe no AnexoVII
        
        Args:
            codigo: Código do indicador (6 dígitos)
            db: Sessão do banco de dados
            
        Returns:
            (valido: bool, mensagem: str, dados: dict ou None)
        """
        from database.models import IndicadorOperacaoIBSCBS
        
        # Validar formato
        if not codigo or len(codigo) != 6 or not codigo.isdigit():
            return False, f"Código do indicador de operação inválido: '{codigo}' (deve ter 6 dígitos)", None
        
        # Buscar no banco
        indicador = db.query(IndicadorOperacaoIBSCBS).filter_by(
            codigo_indicador=codigo,
            ativo=True
        ).first()
        
        if not indicador:
            return False, f"Código de operação '{codigo}' não encontrado no AnexoVII v1.01.00", None
        
        dados = {
            'codigo': indicador.codigo_indicador,
            'descricao': indicador.descricao,
            'tipo_operacao': indicador.tipo_operacao,
            'categoria': indicador.categoria
        }
        
        return True, f"Código válido: {indicador.descricao}", dados
    
    @staticmethod
    def validar_classificacao_tributaria(codigo: str, db: Session) -> Tuple[bool, str, Optional[Dict]]:
        """
        Valida se código de classificação tributária é válido
        
        Args:
            codigo: Código de classificação (6 dígitos)
            db: Sessão do banco de dados
            
        Returns:
            (valido: bool, mensagem: str, dados: dict ou None)
        """
        from database.models import ClassificacaoTributariaNFSe
        
        # Validar formato
        if not codigo or len(codigo) != 6 or not codigo.isdigit():
            return False, f"Código de classificação tributária inválido: '{codigo}' (deve ter 6 dígitos)", None
        
        # Buscar no banco
        classificacao = db.query(ClassificacaoTributariaNFSe).filter_by(
            codigo_classificacao=codigo,
            ativo=True
        ).first()
        
        if not classificacao:
            return False, f"Classificação tributária '{codigo}' não encontrada", None
        
        dados = {
            'codigo': classificacao.codigo_classificacao,
            'descricao': classificacao.descricao,
            'categoria': classificacao.categoria,
            'aliquota_sugerida_ibs': float(classificacao.aliquota_sugerida_ibs) if classificacao.aliquota_sugerida_ibs else None,
            'aliquota_sugerida_cbs': float(classificacao.aliquota_sugerida_cbs) if classificacao.aliquota_sugerida_cbs else None
        }
        
        return True, f"Classificação válida: {classificacao.descricao}", dados
    
    @staticmethod
    def validar_cst_ibs_cbs(codigo: str, db: Session) -> Tuple[bool, str, Optional[Dict]]:
        """
        Valida se CST IBS/CBS é válido
        
        Args:
            codigo: Código CST (3 dígitos)
            db: Sessão do banco de dados
            
        Returns:
            (valido: bool, mensagem: str, dados: dict ou None)
        """
        from database.models import CSTIBSCBS
        
        # Validar formato
        if not codigo or len(codigo) != 3 or not codigo.isdigit():
            return False, f"CST IBS/CBS inválido: '{codigo}' (deve ter 3 dígitos)", None
        
        # Buscar no banco
        cst = db.query(CSTIBSCBS).filter_by(
            codigo_cst=codigo,
            ativo=True
        ).first()
        
        if not cst:
            return False, f"CST IBS/CBS '{codigo}' não encontrado", None
        
        dados = {
            'codigo': cst.codigo_cst,
            'descricao': cst.descricao,
            'categoria': cst.categoria,
            'permite_credito': cst.permite_credito,
            'calcula_ibs': cst.calcula_ibs,
            'calcula_cbs': cst.calcula_cbs
        }
        
        return True, f"CST válido: {cst.descricao}", dados
    
    @staticmethod
    def validar_codigo_nbs(codigo: str, db: Session) -> Tuple[bool, str, Optional[Dict]]:
        """
        Valida se código NBS é válido
        
        Args:
            codigo: Código NBS (9 dígitos sem pontos)
            db: Sessão do banco de dados
            
        Returns:
            (valido: bool, mensagem: str, dados: dict ou None)
        """
        from database.models import NomenclaturaBrasileiraServicos
        
        # Remover pontos se houver
        codigo = codigo.replace('.', '').replace('-', '')
        
        # Validar formato
        if not codigo or len(codigo) != 9 or not codigo.isdigit():
            return False, f"Código NBS inválido: '{codigo}' (deve ter 9 dígitos sem pontos)", None
        
        # Buscar no banco
        nbs = db.query(NomenclaturaBrasileiraServicos).filter_by(
            codigo_nbs=codigo,
            ativo=True
        ).first()
        
        if not nbs:
            return False, f"Código NBS '{codigo}' não encontrado", None
        
        dados = {
            'codigo_nbs': nbs.codigo_nbs,
            'descricao': nbs.descricao,
            'codigo_lc116': nbs.codigo_lc116,
            'categoria': nbs.categoria,
            'subcategoria': nbs.subcategoria
        }
        
        return True, f"NBS válido: {nbs.descricao}", dados
    
    @staticmethod
    def validar_codigo_municipio_ibge(codigo: str) -> Tuple[bool, str]:
        """
        Valida formato do código de município IBGE
        
        Args:
            codigo: Código IBGE (7 dígitos)
            
        Returns:
            (valido: bool, mensagem: str)
        """
        if not codigo or len(codigo) != 7 or not codigo.isdigit():
            return False, f"Código de município IBGE inválido: '{codigo}' (deve ter 7 dígitos)"
        
        return True, "Código de município válido"
    
    @staticmethod
    def validar_percentual_redutor(percentual: float) -> Tuple[bool, str]:
        """
        Valida percentual redutor de base de cálculo
        
        Args:
            percentual: Percentual (0 a 100)
            
        Returns:
            (valido: bool, mensagem: str)
        """
        if percentual < 0 or percentual > 100:
            return False, f"Percentual redutor inválido: {percentual} (deve estar entre 0 e 100)"
        
        return True, "Percentual redutor válido"
    
    @staticmethod
    def validar_nfse_completa(dados: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """
        Valida todos os campos obrigatórios da Reforma Tributária em uma NFS-e
        
        Args:
            dados: Dicionário com dados da NFS-e
            db: Sessão do banco de dados
            
        Returns:
            Dicionário com resultado da validação:
            {
                'valido': bool,
                'erros': list,
                'avisos': list,
                'dados_validados': dict
            }
        """
        resultado = {
            'valido': True,
            'erros': [],
            'avisos': [],
            'dados_validados': {}
        }
        
        # 1. Validar Código NBS
        codigo_nbs = dados.get('codigo_nbs', '').strip()
        if codigo_nbs:
            valido, msg, dados_nbs = NFSeValidationService.validar_codigo_nbs(codigo_nbs, db)
            if not valido:
                resultado['erros'].append(f"NBS: {msg}")
                resultado['valido'] = False
            else:
                resultado['dados_validados']['nbs'] = dados_nbs
        else:
            resultado['erros'].append("NBS: Código NBS é obrigatório")
            resultado['valido'] = False
        
        # 2. Validar Código Indicador de Operação
        codigo_indop = dados.get('codigo_indicador_operacao', '').strip()
        if codigo_indop:
            valido, msg, dados_indop = NFSeValidationService.validar_codigo_indicador_operacao(codigo_indop, db)
            if not valido:
                resultado['erros'].append(f"Indicador Operação: {msg}")
                resultado['valido'] = False
            else:
                resultado['dados_validados']['indicador_operacao'] = dados_indop
        else:
            resultado['avisos'].append("Indicador de Operação não informado (usando padrão 000001)")
        
        # 3. Validar CST IBS/CBS
        cst = dados.get('cst_ibs_cbs', '').strip()
        if cst:
            valido, msg, dados_cst = NFSeValidationService.validar_cst_ibs_cbs(cst, db)
            if not valido:
                resultado['erros'].append(f"CST IBS/CBS: {msg}")
                resultado['valido'] = False
            else:
                resultado['dados_validados']['cst'] = dados_cst
        else:
            resultado['avisos'].append("CST IBS/CBS não informado (usando padrão 001)")
        
        # 4. Validar Classificação Tributária
        classificacao = dados.get('codigo_classificacao_tributaria', '').strip()
        if classificacao:
            valido, msg, dados_class = NFSeValidationService.validar_classificacao_tributaria(classificacao, db)
            if not valido:
                resultado['erros'].append(f"Classificação Tributária: {msg}")
                resultado['valido'] = False
            else:
                resultado['dados_validados']['classificacao'] = dados_class
        else:
            resultado['avisos'].append("Classificação Tributária não informada (usando padrão 000001)")
        
        # 5. Validar Código de Município
        codigo_municipio = dados.get('codigo_localidade_incidencia', '').strip()
        if codigo_municipio:
            valido, msg = NFSeValidationService.validar_codigo_municipio_ibge(codigo_municipio)
            if not valido:
                resultado['erros'].append(f"Município: {msg}")
                resultado['valido'] = False
        
        # 6. Validar Percentual Redutor (se informado)
        percentual_redutor = dados.get('percentual_redutor', 0)
        if percentual_redutor > 0:
            valido, msg = NFSeValidationService.validar_percentual_redutor(percentual_redutor)
            if not valido:
                resultado['erros'].append(f"Percentual Redutor: {msg}")
                resultado['valido'] = False
        
        # 7. Validar Tributos Totais (avisos apenas)
        trib_fed = dados.get('percentual_total_tributos_federais', 0)
        trib_est = dados.get('percentual_total_tributos_estaduais', 0)
        trib_mun = dados.get('percentual_total_tributos_municipais', 0)
        
        if trib_fed == 0 and trib_est == 0 and trib_mun == 0:
            resultado['avisos'].append("Nenhum tributo total informado - verifique se está correto")
        
        return resultado

    @staticmethod
    def _default_xsd_path() -> Path:
        """Retorna o XSD do documento de envio de lote RPS v2.04.

        O XML gerado por ``NFSeService.gerar_xml_rps`` tem como raiz
        ``EnviarLoteRpsEnvio``. O schema ``nfse_v2-04.xsd`` descreve a NFS-e
        retornada pelo provedor e, portanto, rejeita corretamente (mas de
        forma enganosa) o documento de envio. Usar o schema de envio como
        padrão permite que o modo ``strict`` bloqueie apenas XMLs RPS de fato
        inválidos.
        """
        project_root = Path(__file__).resolve().parents[1]
        return project_root / "Documentacao" / "Documentacao giss" / "schemas_modificados_gissv2" / "Schemas_XSD_Servicos_Prestados" / "v2_04" / "enviar-lote-rps-envio-v2_04.xsd"

    @staticmethod
    def validar_xml_contra_xsd(xml_content: str, xsd_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Valida um XML NFS-e contra um schema XSD.

        Args:
            xml_content: Conteúdo XML em string
            xsd_path: Caminho absoluto/relativo para XSD. Se omitido, usa XSD padrão do projeto.

        Returns:
            {
                'valido': bool,
                'xsd_path': str,
                'erros': list[str],
                'mensagem': str
            }
        """
        if not xml_content or not xml_content.strip():
            return {
                'valido': False,
                'xsd_path': '',
                'erros': ['Conteúdo XML não fornecido'],
                'mensagem': 'XML vazio'
            }

        resolved_xsd = Path(xsd_path).expanduser() if xsd_path else NFSeValidationService._default_xsd_path()
        if not resolved_xsd.is_absolute():
            resolved_xsd = Path.cwd() / resolved_xsd
        resolved_xsd = resolved_xsd.resolve()

        if not resolved_xsd.exists():
            return {
                'valido': False,
                'xsd_path': str(resolved_xsd),
                'erros': [f'Arquivo XSD não encontrado: {resolved_xsd}'],
                'mensagem': 'XSD não encontrado'
            }

        try:
            xml_doc = etree.fromstring(xml_content.encode('utf-8'))
        except etree.XMLSyntaxError as exc:
            return {
                'valido': False,
                'xsd_path': str(resolved_xsd),
                'erros': [f'XML malformado: {exc}'],
                'mensagem': 'XML inválido'
            }

        try:
            xsd_doc = etree.parse(str(resolved_xsd))
            schema = etree.XMLSchema(xsd_doc)
        except (etree.XMLSchemaParseError, etree.XMLSyntaxError, OSError) as exc:
            return {
                'valido': False,
                'xsd_path': str(resolved_xsd),
                'erros': [f'Falha ao carregar schema XSD: {exc}'],
                'mensagem': 'XSD inválido'
            }

        is_valid = schema.validate(xml_doc)
        if is_valid:
            return {
                'valido': True,
                'xsd_path': str(resolved_xsd),
                'erros': [],
                'mensagem': 'XML válido conforme XSD'
            }

        errors = []
        for error in schema.error_log:
            errors.append(f'Linha {error.line}: {error.message}')

        return {
            'valido': False,
            'xsd_path': str(resolved_xsd),
            'erros': errors,
            'mensagem': 'XML inválido conforme XSD'
        }


# =============================================================================
# FUNÇÕES AUXILIARES PARA USO EM ROTAS
# =============================================================================

def validar_e_obter_dados_nbs(codigo_nbs: str, db: Session) -> Dict[str, Any]:
    """
    Função auxiliar para validar NBS e retornar dados formatados
    
    Returns:
        {'sucesso': bool, 'mensagem': str, 'dados': dict ou None}
    """
    valido, mensagem, dados = NFSeValidationService.validar_codigo_nbs(codigo_nbs, db)
    
    return {
        'sucesso': valido,
        'mensagem': mensagem,
        'dados': dados
    }


def buscar_nbs_por_termo(termo: str, db: Session, limite: int = 20) -> list:
    """
    Busca códigos NBS por termo de busca
    
    Args:
        termo: Termo para buscar (código, descrição, palavras-chave)
        db: Sessão do banco de dados
        limite: Número máximo de resultados
        
    Returns:
        Lista de dicionários com resultados
    """
    from database.models import NomenclaturaBrasileiraServicos
    from sqlalchemy import or_, func
    
    # Buscar por código, descrição ou palavras-chave
    query = db.query(NomenclaturaBrasileiraServicos).filter(
        NomenclaturaBrasileiraServicos.ativo == True,
        or_(
            NomenclaturaBrasileiraServicos.codigo_nbs.ilike(f'%{termo}%'),
            NomenclaturaBrasileiraServicos.descricao.ilike(f'%{termo}%'),
            NomenclaturaBrasileiraServicos.codigo_lc116.ilike(f'%{termo}%'),
            NomenclaturaBrasileiraServicos.palavras_chave.ilike(f'%{termo}%'),
            NomenclaturaBrasileiraServicos.categoria.ilike(f'%{termo}%')
        )
    ).order_by(
        NomenclaturaBrasileiraServicos.categoria,
        NomenclaturaBrasileiraServicos.codigo_nbs
    ).limit(limite)
    
    resultados = []
    for nbs in query.all():
        resultados.append({
            'codigo_nbs': nbs.codigo_nbs,
            'descricao': nbs.descricao,
            'codigo_lc116': nbs.codigo_lc116,
            'categoria': nbs.categoria,
            'subcategoria': nbs.subcategoria,
            'descricao_completa': f"{nbs.codigo_nbs} - {nbs.descricao}"
        })
    
    return resultados
