"""
Testes para NFS-e com campos da Reforma Tributária
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from services.nfse_service import criar_nfse_de_formulario
from models.nfse_model import NFSeNacional


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
