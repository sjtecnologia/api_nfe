"""
Testes para NFS-e com campos da Reforma Tributária
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from services.nfse_service import NFSeService, criar_nfse_de_formulario
from models.nfse_model import NFSeNacional
from services.certificate_service import get_active_certificate_for_client


def test_criar_nfse_com_campos_reforma():
    """Testa criação de NFS-e com todos os campos da Reforma Tributária"""
    
    # Dados do prestador
    prestador_data = {
        'cnpj': '12345678000190',
        'inscricao_municipal': '12345',
        'razao_social': 'Empresa Teste Ltda',
        'nome_fantasia': 'Empresa Teste',
        'logradouro': 'Rua Teste',
        'numero': '123',
        'bairro': 'Centro',
        'codigo_municipio': '3549805',
        'uf': 'SP',
        'cep': '15015000',
        'optante_simples': True
    }
    
    # Dados do formulário com campos da Reforma Tributária
    dados = {
        'cliente_id': 1,
        'numero_rps': 1,
        'serie_rps': '1',
        'tipo_rps': '1',
        'data_competencia': '2026-01-30',
        'natureza_operacao': '1',
        'ambiente': 'homologacao',
        
        # Tomadores
        'Tomadores_cpf_cnpj': '12345678000190',
        'Tomadores_razao_social': 'Cliente Teste',
        'Tomadores_logradouro': 'Av Principal',
        'Tomadores_numero': '456',
        'Tomadores_bairro': 'Centro',
        'Tomadores_codigo_municipio': '3549805',
        'Tomadores_uf': 'SP',
        'Tomadores_cep': '15015000',
        
        # Serviço
        'codigo_servico': '01.01',
        'discriminacao': 'Serviço de teste de software',
        'valor_servico': 1000.00,
        'aliquota_iss': 5.0,
        'codigo_municipio_prestacao': '3549805',
        
        # Campos Reforma Tributária
        'codigo_nbs': '101010000',
        'finalidade_nfse': '0',
        'indicador_consumidor_final': '1',
        'codigo_indicador_operacao': '000001',
        'indicador_destinatario': '0',
        'cst_ibs_cbs': '001',
        'codigo_classificacao_tributaria': '000001',
        'codigo_localidade_incidencia': '3549805',
        'percentual_redutor': 0.0,
        'percentual_total_tributos_federais': 0.0,
        'percentual_total_tributos_estaduais': 0.0,
        'percentual_total_tributos_municipais': 5.0,
        'regime_especial_tributacao': '6',
        'optante_simples_nacional': True,
        'incentivador_cultural': False,
    }
    
    # Criar NFS-e
    nfse = criar_nfse_de_formulario(dados, prestador_data)
    
    # Validações básicas
    assert nfse is not None
    assert isinstance(nfse, NFSeNacional)
    assert nfse.cliente_id == 1
    assert nfse.numero_rps == 1
    
    # Validar campos da Reforma Tributária
    assert nfse.servico.codigo_nbs == '101010000'
    assert nfse.servico.finalidade_nfse == '0'
    assert nfse.servico.indicador_consumidor_final == '1'
    assert nfse.servico.codigo_indicador_operacao == '000001'
    assert nfse.servico.indicador_destinatario == '0'
    assert nfse.servico.cst_ibs_cbs == '001'
    assert nfse.servico.codigo_classificacao_tributaria == '000001'
    assert nfse.servico.codigo_localidade_incidencia == '3549805'
    assert nfse.servico.percentual_redutor == 0.0
    
    # Validar tributos totais
    assert nfse.servico.percentual_total_tributos_federais == 0.0
    assert nfse.servico.percentual_total_tributos_estaduais == 0.0
    assert nfse.servico.percentual_total_tributos_municipais == 5.0
    
    # Validar regime tributário
    assert nfse.regime_especial_tributacao == '6'
    assert nfse.optante_simples_nacional == True
    assert nfse.incentivador_cultural == False
    
    print("✅ Teste de criação de NFS-e com Reforma Tributária passou!")


def test_validacao_codigo_nbs():
    """Testa validação do código NBS"""
    
    prestador_data = {
        'cnpj': '12345678000190',
        'inscricao_municipal': '12345',
        'razao_social': 'Empresa Teste',
        'optante_simples': True
    }
    
    # Teste com código NBS inválido (deve usar o padrão)
    dados = {
        'cliente_id': 1,
        'numero_rps': 1,
        'data_competencia': '2026-01-30',
        'Tomadores_cpf_cnpj': '12345678000190',
        'Tomadores_razao_social': 'Cliente',
        'Tomadores_logradouro': 'Rua',
        'Tomadores_numero': '1',
        'Tomadores_bairro': 'Centro',
        'Tomadores_codigo_municipio': '3549805',
        'Tomadores_uf': 'SP',
        'Tomadores_cep': '15015000',
        'codigo_servico': '01.01',
        'discriminacao': 'Teste',
        'valor_servico': 100.00,
        'aliquota_iss': 5.0,
        # Não fornece codigo_nbs, deve usar padrão
    }
    
    nfse = criar_nfse_de_formulario(dados, prestador_data)
    
    # Deve ter o valor padrão
    assert nfse.servico.codigo_nbs == '101010000'
    
    print("✅ Teste de validação de código NBS passou!")


def test_normaliza_codigo_nbs_com_pontuacao():
    """Aceita formato documentado com pontos e normaliza para 9 dígitos."""

    prestador_data = {
        'cnpj': '12345678000190',
        'inscricao_municipal': '12345',
        'razao_social': 'Empresa Teste',
        'optante_simples': True
    }

    dados = {
        'cliente_id': 1,
        'numero_rps': 1,
        'data_competencia': '2026-01-30',
        'tomador_cpf_cnpj': '12345678000190',
        'tomador_razao_social': 'Cliente',
        'tomador_logradouro': 'Rua',
        'tomador_numero': '1',
        'tomador_bairro': 'Centro',
        'tomador_codigo_municipio': '3549805',
        'tomador_uf': 'SP',
        'tomador_cep': '15015000',
        'codigo_servico': '01.07',
        'codigo_nbs': '1.0107.10.00',
        'discriminacao': 'Teste NBS formatado',
        'valor_servico': 100.00,
        'aliquota_iss': 5.0,
    }

    nfse = criar_nfse_de_formulario(dados, prestador_data)

    assert nfse.servico.codigo_nbs == '101071000'
    assert dados['codigo_nbs'] == '101071000'


def test_get_active_certificate_prioriza_vigente(monkeypatch):
    """Garante que um certificado vencido não é escolhido quando há um vigente."""

    class FakeCertificate:
        def __init__(self, certificado_digital_id, ativo, validade_inicio, validade_fim, nome_arquivo_original):
            self.certificado_digital_id = certificado_digital_id
            self.cliente_id = 11
            self.common_name = None
            self.validade_inicio = validade_inicio
            self.validade_fim = validade_fim
            self.conteudo_certificado = 'Y2VydA=='
            self.senha_certificado = 'c2VuaGE='
            self.ativo = ativo
            self.tipo_certificado = 'A1'
            self.data_upload = datetime(2026, 1, 1)
            self.fingerprint = f'fp-{certificado_digital_id}'
            self.nome_arquivo_original = nome_arquivo_original

    class FakeQuery:
        def __init__(self, certificados):
            self._certificados = certificados

        def filter_by(self, **kwargs):
            return self

        def order_by(self, *args):
            return self

        def all(self):
            return self._certificados

    class FakeDB:
        def __init__(self, certificados):
            self._certificados = certificados

        def query(self, model):
            return FakeQuery(self._certificados)

    certificado_vencido = FakeCertificate(
        certificado_digital_id=27,
        ativo=True,
        validade_inicio=datetime(2025, 2, 5, tzinfo=timezone.utc),
        validade_fim=datetime(2026, 2, 5, tzinfo=timezone.utc),
        nome_arquivo_original='vencido.pfx',
    )
    certificado_vigente = FakeCertificate(
        certificado_digital_id=37,
        ativo=True,
        validade_inicio=datetime(2026, 2, 5, tzinfo=timezone.utc),
        validade_fim=datetime(2027, 2, 5, tzinfo=timezone.utc),
        nome_arquivo_original='vigente.pfx',
    )

    monkeypatch.setattr('services.certificate_service._decode_certificate_data', lambda data: b'cert')
    monkeypatch.setattr('services.certificate_service._decrypt_password', lambda senha: 'senha')
    monkeypatch.setattr('services.certificate_service._validate_pkcs12_simple', lambda cert_data, password: ('pk', 'cert', []))

    resultado = get_active_certificate_for_client(FakeDB([certificado_vencido, certificado_vigente]), 11)

    assert resultado is not None
    assert resultado['certificado_id'] == 37
    assert resultado['nome_arquivo_original'] == 'vigente.pfx'
    assert resultado['modo_simulado'] is False


def test_calcular_valores():
    """Testa cálculo automático de valores"""
    
    prestador_data = {
        'cnpj': '12345678000190',
        'inscricao_municipal': '12345',
        'razao_social': 'Empresa Teste',
        'optante_simples': True
    }
    
    dados = {
        'cliente_id': 1,
        'numero_rps': 1,
        'data_competencia': '2026-01-30',
        'Tomadores_cpf_cnpj': '12345678000190',
        'Tomadores_razao_social': 'Cliente',
        'Tomadores_logradouro': 'Rua',
        'Tomadores_numero': '1',
        'Tomadores_bairro': 'Centro',
        'Tomadores_codigo_municipio': '3549805',
        'Tomadores_uf': 'SP',
        'Tomadores_cep': '15015000',
        'codigo_servico': '01.01',
        'discriminacao': 'Serviço de TI',
        'valor_servico': 1000.00,
        'aliquota_iss': 5.0,
        'valor_deducoes': 100.00,
        'desconto_incondicionado': 50.00,
        'codigo_nbs': '101010000',
        'percentual_total_tributos_municipais': 5.0,
    }
    
    nfse = criar_nfse_de_formulario(dados, prestador_data)
    
    # Calcular valores
    nfse.calcular_valores()
    
    # Base de cálculo = valor_servicos - deduções - desconto
    # Base = 1000 - 100 - 50 = 850
    assert nfse.servico.base_calculo == 850.0
    
    # ISS = base * aliquota / 100
    # ISS = 850 * 5 / 100 = 42.50
    assert nfse.servico.valor_iss == 42.50
    
    # Valor líquido = valor_servicos - desconto - retencoes
    # Como ISS não está retido, não entra nas retenções
    # Valor líquido = 1000 - 50 - 0 = 950
    assert nfse.servico.valor_liquido == 950.0
    
    print("✅ Teste de cálculo de valores passou!")


def test_percentuais_default():
    """Testa valores padrão dos percentuais"""
    
    prestador_data = {
        'cnpj': '12345678000190',
        'inscricao_municipal': '12345',
        'razao_social': 'Empresa Teste',
        'optante_simples': True
    }
    
    # Dados mínimos (sem percentuais específicos)
    dados = {
        'cliente_id': 1,
        'numero_rps': 1,
        'data_competencia': '2026-01-30',
        'Tomadores_cpf_cnpj': '12345678000190',
        'Tomadores_razao_social': 'Cliente',
        'Tomadores_logradouro': 'Rua',
        'Tomadores_numero': '1',
        'Tomadores_bairro': 'Centro',
        'Tomadores_codigo_municipio': '3549805',
        'Tomadores_uf': 'SP',
        'Tomadores_cep': '15015000',
        'codigo_servico': '01.01',
        'discriminacao': 'Teste',
        'valor_servico': 100.00,
        'aliquota_iss': 5.0,
    }
    
    nfse = criar_nfse_de_formulario(dados, prestador_data)
    
    # Valores padrão
    assert nfse.servico.percentual_total_tributos_federais == 0.0
    assert nfse.servico.percentual_total_tributos_estaduais == 0.0
    assert nfse.servico.percentual_total_tributos_municipais == 5.0  # Padrão ISS
    assert nfse.servico.codigo_nbs == '101010000'
    assert nfse.servico.finalidade_nfse == '0'
    assert nfse.servico.indicador_consumidor_final == '0'
    assert nfse.optante_simples_nacional == True
    assert nfse.incentivador_cultural == False
    
    print("✅ Teste de valores padrão passou!")


def test_gerar_xml_com_tributos_federais_giss(monkeypatch):
    """Gera XML no formato GISS com blocos trib/totTrib/piscofins e IBSCBS."""

    prestador_data = {
        'cnpj': '12345678000190',
        'inscricao_municipal': '12345',
        'razao_social': 'Empresa Teste',
        'optante_simples': True
    }

    dados = {
        'cliente_id': 1,
        'numero_rps': 1,
        'data_competencia': '2026-01-30',
        'tomador_cpf_cnpj': '12345678000190',
        'tomador_razao_social': 'Cliente',
        'tomador_logradouro': 'Rua',
        'tomador_numero': '1',
        'tomador_bairro': 'Centro',
        'tomador_codigo_municipio': '3549805',
        'tomador_uf': 'SP',
        'tomador_cep': '15015000',
        'codigo_servico': '01.01',
        'discriminacao': 'Teste estrutura GISS',
        'valor_servico': 1000.00,
        'valor_pis': 15.25,
        'valor_cofins': 70.30,
        'valor_csll': 10.00,
        'csll_retida': True,
        'aliquota_iss': 5.0,
        'base_calculo_pis_cofins': 1000.00,
        'aliquota_pis': 1.65,
        'aliquota_cofins': 7.60,
        'valor_pis_operacao': 15.25,
        'valor_cofins_operacao': 70.30,
        'tipo_retencao_pis_cofins': '1',
        'cst_pis_cofins': '01',
        'codigo_nbs': '101010000',
        'percentual_total_tributos_federais': 9.25,
        'percentual_total_tributos_estaduais': 0.0,
        'percentual_total_tributos_municipais': 5.0,
        'finalidade_nfse': '0',
        'indicador_consumidor_final': '1',
        'codigo_indicador_operacao': '000001',
        'indicador_destinatario': '0',
        'cst_ibs_cbs': '001',
        'codigo_classificacao_tributaria': '000001',
        'codigo_localidade_incidencia': '3549805',
        'percentual_redutor': 0.0,
    }

    monkeypatch.setenv('GISS_SCHEMA_RTC_HOMOLOGACAO', 'true')
    nfse = criar_nfse_de_formulario(dados, prestador_data)
    service = NFSeService()
    xml = service.gerar_xml_rps(nfse)

    assert '<p1:tribFed>' in xml
    assert '<p1:piscofins>' in xml
    assert '<p1:tpRetPisCofins>1</p1:tpRetPisCofins>' in xml
    assert '<p1:totTrib>' in xml
    assert '<p1:pTotTribFed>9.25</p1:pTotTribFed>' in xml
    assert '<p1:IBSCBS>' in xml
    assert '<p1:finNFSe>0</p1:finNFSe>' in xml
    assert '<p1:cLocalidadeIncid>3549805</p1:cLocalidadeIncid>' in xml
    assert '<p1:CodigoNbs>101010000</p1:CodigoNbs>' in xml


def test_resolver_urls_giss_por_municipio():
    """Permite novo padrão ws-MUNICIPIO.giss.com.br sem perder fallback atual."""

    service = NFSeService(ambiente='homologacao', municipio_slug='Sao Jose do Rio Preto')

    assert service.urls['base'] == 'https://ws-sjrp.giss.com.br/'
    assert service.urls['wsdl'] == 'https://ws-sjrp.giss.com.br/service-ws/nf/nfse-ws?wsdl'


def test_url_producao_sjrp_default():
    """Produção usa o endpoint RTC atual; SJRP continua disponível por override."""

    service = NFSeService(ambiente='producao')

    assert service.urls['base'] == 'https://ws-rtc.giss.com.br/'
    assert service.urls['wsdl'] == 'https://ws-rtc.giss.com.br/service-ws/nf/nfse-ws?wsdl'

    sjrp = NFSeService(ambiente='producao', municipio_slug='Sao Jose do Rio Preto')
    assert sjrp.urls['base'] == 'https://ws-sjrp.giss.com.br/'


if __name__ == '__main__':
    print("\n" + "="*80)
    print("🧪 TESTES - NFS-e com Reforma Tributária (LC 214/2025)")
    print("="*80 + "\n")
    
    try:
        test_criar_nfse_com_campos_reforma()
        test_validacao_codigo_nbs()
        test_calcular_valores()
        test_percentuais_default()
        
        print("\n" + "="*80)
        print("✅ TODOS OS TESTES PASSARAM!")
        print("="*80 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ Teste falhou: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
