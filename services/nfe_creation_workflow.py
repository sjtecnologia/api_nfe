"""
services/nfe_creation_workflow.py

Extrai a lógica de construção de contexto do formulário de emissão de NFe
(GET handler da rota emitir_nfe).

Mantém toda a lógica de negócio aqui, deixando a rota responsável apenas
por receber a requisição, chamar o workflow e renderizar o template.

Uso:
    from services.nfe_creation_workflow import NFeCreationWorkflow

    wf = NFeCreationWorkflow(db)
    ctx = wf.prepare_emitter_context(emitente_cliente_id)
    return render_template('admin/nfes/emitir.html', **ctx)
"""
import logging
from sqlalchemy.orm import Session
from database.models import (
    DestinatarioNFe, Csticms, Csosnicms,
)

logger = logging.getLogger(__name__)


class NFeCreationWorkflow:
    """
    Monta o contexto necessário para renderizar o formulário de emissão de NFe.
    Responsabilidades:
      - Buscar destinatários do cliente
      - Buscar CSTs e CSOSNs
      - Buscar classificações IBS/CBS ativas
    Não responsabilidade:
      - Determinar o cliente (feito pela rota, que passa o ID já validado)
      - Construir dados do emitente (feito pela rota antes de chamar o workflow)
      - Processar o POST de emissão (mantido na rota)
    """

    def __init__(self, db: Session):
        self._db = db

    # ─────────────────────────────────────────────────────────────────────────
    # Ponto de entrada público
    # ─────────────────────────────────────────────────────────────────────────

    def prepare_emitter_context(self, emitente_cliente_id: int) -> dict:
        """
        Retorna dicionário pronto para ser desempacotado como kwargs do
        render_template('admin/nfes/emitir.html', ...).

        :param emitente_cliente_id: ID do cliente/emitente (já validado pela rota)
        :returns: dict com as seguintes chaves:
          - destinatarios: list[dict]
          - produtos: list (vazio — carregado via AJAX)
          - all_cfops: list (vazio — carregado via AJAX)
          - all_ncms: list (vazio — carregado via AJAX)
          - all_csts: list[dict]
          - all_csosns: list[dict]
          - classificacoes_ibs_cbs: list[dict]
          - initial_nfe_items: list (vazio)
        """
        destinatarios = self._load_destinatarios(emitente_cliente_id)
        csts          = self._load_csts()
        csosns        = self._load_csosns()
        classificacoes = self._load_classificacoes_ibs_cbs()

        logger.debug(
            'NFeCreationWorkflow: cliente=%s destinatarios=%d csts=%d csosns=%d ibs_cbs=%d',
            emitente_cliente_id, len(destinatarios), len(csts), len(csosns), len(classificacoes)
        )

        return {
            'destinatarios':         destinatarios,
            'produtos':              [],   # carregados via AJAX
            'all_cfops':             [],   # carregados via AJAX
            'all_ncms':              [],   # carregados via AJAX
            'all_csts':              csts,
            'all_csosns':            csosns,
            'classificacoes_ibs_cbs': classificacoes,
            'initial_nfe_items':     [],
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Privado — loaders de dados
    # ─────────────────────────────────────────────────────────────────────────

    def _load_destinatarios(self, cliente_id: int) -> list:
        try:
            rows = self._db.query(DestinatarioNFe).filter_by(
                cliente_id=cliente_id
            ).all()
            return [
                {
                    'destinatario_id':  d.destinatario_id,
                    'nome_razao_social': d.nome_razao_social,
                    'cpf_cnpj':          d.cpf_cnpj,
                    'logradouro':        d.logradouro,
                    'numero':            d.numero,
                    'bairro':            d.bairro,
                    'cep':               d.cep,
                    'codigo_municipio':  d.codigo_municipio,
                    'nome_municipio':    d.nome_municipio,
                    'uf':                d.uf,
                }
                for d in rows
            ]
        except Exception as e:
            logger.error('Erro ao carregar destinatários do cliente %s: %s', cliente_id, e)
            return []

    def _load_csts(self) -> list:
        try:
            rows = self._db.query(Csticms).all()
            return [
                {'cst_id': c.cst_id, 'codigo': c.codigo, 'descricao': c.descricao}
                for c in rows
            ]
        except Exception as e:
            logger.warning('Erro ao carregar CSTs: %s', e)
            return []

    def _load_csosns(self) -> list:
        try:
            rows = self._db.query(Csosnicms).all()
            return [
                {'csosn_id': c.csosn_id, 'codigo': c.codigo, 'descricao': c.descricao}
                for c in rows
            ]
        except Exception as e:
            logger.warning('Erro ao carregar CSOSNs: %s', e)
            return []

    def _load_classificacoes_ibs_cbs(self) -> list:
        try:
            from database.models import ClassificacaoIBSCBS
            rows = self._db.query(ClassificacaoIBSCBS).filter_by(ativo=True).all()
            return [
                {
                    'classificacao_id':  c.classificacao_id,
                    'codigo':             c.codigo,
                    'descricao':          c.descricao,
                    'aliquota_ibs_uf':    float(c.aliquota_ibs_uf),
                    'aliquota_ibs_mun':   float(c.aliquota_ibs_mun),
                    'aliquota_cbs':       float(c.aliquota_cbs),
                }
                for c in rows
            ]
        except Exception as e:
            logger.warning('Erro ao carregar classificações IBS/CBS: %s', e)
            return []
