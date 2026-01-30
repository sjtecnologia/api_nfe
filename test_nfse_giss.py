#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste de geração de XML NFS-e com novo padrão GISS Online
"""

from services.nfse_service import NFSeService
from models.nfse_model import NFSeNacional, PrestadorNFSe, TomadoresNFSe, ServicoNFSe
from datetime import datetime

def main():
    # Criar prestador
    prestador = PrestadorNFSe(
        cnpj='12345678000199',
        inscricao_municipal='12345',
        razao_social='Empresa Teste LTDA',
        endereco_logradouro='Rua Teste',
        endereco_numero='123',
        endereco_bairro='Centro',
        endereco_codigo_municipio='3549805',
        endereco_uf='SP',
        endereco_cep='15015000'
    )

    # Criar Tomadores
    Tomadores = TomadoresNFSe(
        tipo_documento='CPF',
        cpf_cnpj='12345678900',
        razao_social='Cliente Teste',
        endereco_logradouro='Av. Brasil',
        endereco_numero='456',
        endereco_bairro='Jardim',
        endereco_codigo_municipio='3549805',
        endereco_uf='SP',
        endereco_cep='15020000',
        telefone='1733333333',
        email='cliente@teste.com'
    )

    # Criar serviço
    servico = ServicoNFSe(
        codigo_tributacao_nacional='01.01',
        codigo_nbs='101010000',  # NBS sem pontos, máximo 9 dígitos
        discriminacao='Análise e desenvolvimento de sistemas',
        valor_servicos=1000.00,
        aliquota_iss=5.0,
        codigo_municipio_prestacao='3549805',
        # Valores IBS/CBS obrigatórios - tamanhos corretos
        percentual_total_tributos_federais=5.00,
        percentual_total_tributos_estaduais=0.00,
        percentual_total_tributos_municipais=5.00,
        finalidade_nfse='0',
        indicador_consumidor_final='0',
        codigo_indicador_operacao='000001',  # 6 dígitos
        indicador_destinatario='0',
        cst_ibs_cbs='001',  # 3 dígitos
        codigo_classificacao_tributaria='000001',  # 6 dígitos
        codigo_localidade_incidencia='3549805',
        percentual_redutor=0.00
    )

    # Criar NFS-e
    nfse = NFSeNacional(
        cliente_id=1,
        numero_rps=1,
        serie_rps='1',
        tipo_rps='1',
        prestador=prestador,
        Tomadores=Tomadores,
        servico=servico,
        optante_simples_nacional=True,
        incentivador_cultural=False
    )

    # Gerar XML
    service = NFSeService(ambiente='homologacao')
    xml = service.gerar_xml_rps(nfse)
    
    print('✅ XML gerado com sucesso!')
    print(f'📏 Tamanho: {len(xml)} caracteres')
    print('\n' + '='*80)
    print('XML COMPLETO:')
    print('='*80)
    print(xml)
    print('='*80)
    
    # Salvar em arquivo
    with open('/tmp/nfse_giss_test.xml', 'w', encoding='utf-8') as f:
        f.write(xml)
    print(f'\n💾 XML salvo em: /tmp/nfse_giss_test.xml')

if __name__ == '__main__':
    main()
