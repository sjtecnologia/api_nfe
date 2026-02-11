"""
Script de teste para validar geração de XML NFS-e com tags IBS/CBS (NT007 v1.03.00)
Data: 09/02/2026
Referência: https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/rtc
"""

import sys
import os
from datetime import datetime
from lxml import etree

# Adicionar caminho do projeto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.nfse_model import NFSeNacional, PrestadorNFSe, TomadoresNFSe, ServicoNFSe
from services.nfse_service import NFSeService


def criar_nfse_teste():
    """Cria objeto NFS-e de teste com todos os campos da Reforma Tributária"""
    
    # Prestador
    prestador = PrestadorNFSe(
        cnpj="12345678000190",
        inscricao_municipal="12345",
        razao_social="EMPRESA TESTE LTDA",
        nome_fantasia="Empresa Teste",
        endereco_logradouro="Rua Teste",
        endereco_numero="123",
        endereco_bairro="Centro",
        endereco_codigo_municipio="3549805",  # São José do Rio Preto
        endereco_uf="SP",
        endereco_cep="15015000",
        telefone="1733221234",
        email="contato@empresateste.com.br",
        optante_simples_nacional=True,
        incentivo_fiscal=False
    )
    
    # Tomador
    tomador = TomadoresNFSe(
        tipo_documento="CNPJ",
        cpf_cnpj="98765432000199",
        razao_social="CLIENTE TESTE LTDA",
        endereco_logradouro="Av. Cliente",
        endereco_numero="456",
        endereco_bairro="Jardim Teste",
        endereco_codigo_municipio="3549805",
        endereco_uf="SP",
        endereco_cep="15025000",
        telefone="1733224567",
        email="cliente@teste.com.br"
    )
    
    # Serviço com campos da Reforma Tributária
    servico = ServicoNFSe(
        codigo_tributacao_nacional="01.01",  # Análise e desenvolvimento de sistemas
        codigo_nbs="101010000",  # NBS obrigatório
        discriminacao="Desenvolvimento de sistema web personalizado conforme especificação do cliente. "
                      "Projeto incluindo análise de requisitos, modelagem de dados, desenvolvimento backend "
                      "e frontend, testes integrados e documentação técnica completa.",
        
        # Valores
        valor_servicos=5000.00,
        valor_deducoes=0.00,
        aliquota_iss=2.0,  # 2% para serviços de TI em SJRP
        
        # Retenções
        valor_pis=0.00,
        valor_cofins=0.00,
        valor_inss=0.00,
        valor_ir=0.00,
        valor_csll=0.00,
        iss_retido=False,
        
        # =============================================================================================
        # CAMPOS DA REFORMA TRIBUTÁRIA (LC 214/2025) - NT007 v1.03.00
        # =============================================================================================
        
        # TRIBUTOS TOTAIS (percentuais sobre valor do serviço)
        percentual_total_tributos_federais=7.50,    # PIS + COFINS + IR + CSLL (Simples Nacional)
        percentual_total_tributos_estaduais=0.00,   # Não há tributos estaduais para serviços
        percentual_total_tributos_municipais=2.00,  # ISS
        
        # IBS/CBS - Indicadores
        finalidade_nfse="0",                         # 0=Normal
        indicador_consumidor_final="1",              # 1=Consumidor final
        indicador_destinatario="0",                  # 0=Operação interna no município
        
        # IBS/CBS - Códigos operacionais
        codigo_indicador_operacao="000001",          # Operação interna (AnexoVII v1.01.00)
        cst_ibs_cbs="001",                          # 001=Tributação normal
        codigo_classificacao_tributaria="000001",    # Classificação padrão
        codigo_localidade_incidencia="3549805",      # São José do Rio Preto
        percentual_redutor=0.00,                     # Sem redução de base
        
        # Local da prestação
        codigo_municipio_prestacao="3549805",
        codigo_pais="1058"
    )
    
    # NFS-e completa
    nfse = NFSeNacional(
        cliente_id=1,
        numero_rps=1,
        serie_rps="1",
        tipo_rps="1",
        data_emissao=datetime.now(),
        data_competencia=datetime.now(),
        natureza_operacao="1",  # Tributação no município
        regime_especial_tributacao="6",  # Simples Nacional
        optante_simples_nacional=True,
        incentivador_cultural=False,
        ambiente="homologacao",
        prestador=prestador,
        Tomadores=tomador,
        servico=servico,
        informacoes_complementares="Nota fiscal de teste para validação do layout NT007 v1.03.00",
        lote="202602090001"
    )
    
    return nfse


def validar_tags_ibscbs(xml_string: str):
    """Valida se as tags IBS/CBS estão presentes no XML gerado"""
    
    print("\n" + "="*80)
    print("VALIDAÇÃO DE TAGS IBS/CBS - NT007 v1.03.00")
    print("="*80)
    
    # Parse do XML
    try:
        root = etree.fromstring(xml_string.encode('utf-8'))
    except Exception as e:
        print(f"❌ ERRO ao parsear XML: {e}")
        return False
    
    # Definir namespaces
    namespaces = {
        'p': 'http://www.giss.com.br/enviar-lote-rps-envio-v2_04.xsd',
        'p1': 'http://www.giss.com.br/tipos-v2_04.xsd'
    }
    
    resultados = {}
    
    # 1. Validar tag <trib> com <tribTot>
    print("\n1️⃣ TRIBUTOS TOTAIS:")
    trib = root.find('.//p1:trib', namespaces)
    if trib is not None:
        print("   ✅ Tag <trib> encontrada")
        
        trib_tot = trib.find('.//p1:tribTot', namespaces)
        if trib_tot is not None:
            print("   ✅ Tag <tribTot> encontrada")
            
            # Validar sub-elementos
            p_tot_trib_fed = trib_tot.find('p1:pTotTribFed', namespaces)
            p_tot_trib_est = trib_tot.find('p1:pTotTribEst', namespaces)
            p_tot_trib_mun = trib_tot.find('p1:pTotTribMun', namespaces)
            
            if p_tot_trib_fed is not None:
                print(f"   ✅ pTotTribFed: {p_tot_trib_fed.text}%")
                resultados['pTotTribFed'] = p_tot_trib_fed.text
            else:
                print("   ❌ pTotTribFed NÃO encontrado")
                
            if p_tot_trib_est is not None:
                print(f"   ✅ pTotTribEst: {p_tot_trib_est.text}%")
                resultados['pTotTribEst'] = p_tot_trib_est.text
            else:
                print("   ❌ pTotTribEst NÃO encontrado")
                
            if p_tot_trib_mun is not None:
                print(f"   ✅ pTotTribMun: {p_tot_trib_mun.text}%")
                resultados['pTotTribMun'] = p_tot_trib_mun.text
            else:
                print("   ❌ pTotTribMun NÃO encontrado")
        else:
            print("   ❌ Tag <tribTot> NÃO encontrada")
    else:
        print("   ❌ Tag <trib> NÃO encontrada")
    
    # 2. Validar tag <IBSCBS>
    print("\n2️⃣ IBS/CBS - REFORMA TRIBUTÁRIA:")
    ibscbs = root.find('.//p1:IBSCBS', namespaces)
    if ibscbs is not None:
        print("   ✅ Tag <IBSCBS> encontrada")
        
        # Validar campos obrigatórios
        campos_obrigatorios = {
            'tpOp': 'Tipo de Operação',
            'indIni': 'Indicador Consumidor Final',
            'indFin': 'Indicador Destinatário',
            'cIndOp': 'Código Indicador Operação',
            'cst': 'CST IBS/CBS',
            'cClassTrib': 'Classificação Tributária',
            'cLocInc': 'Localidade de Incidência'
        }
        
        for campo, descricao in campos_obrigatorios.items():
            elemento = ibscbs.find(f'p1:{campo}', namespaces)
            if elemento is not None:
                print(f"   ✅ {campo} ({descricao}): {elemento.text}")
                resultados[campo] = elemento.text
            else:
                print(f"   ❌ {campo} ({descricao}) NÃO encontrado")
        
        # Validar campo opcional pRedBC
        p_red_bc = ibscbs.find('p1:pRedBC', namespaces)
        if p_red_bc is not None:
            print(f"   ✅ pRedBC (Percentual Redutor): {p_red_bc.text}%")
            resultados['pRedBC'] = p_red_bc.text
        else:
            print(f"   ℹ️  pRedBC (Percentual Redutor): Não informado (campo opcional)")
            
    else:
        print("   ❌ Tag <IBSCBS> NÃO encontrada")
    
    print("\n" + "="*80)
    
    # Verificar se todas as tags obrigatórias estão presentes
    tags_esperadas = [
        'pTotTribFed', 'pTotTribEst', 'pTotTribMun',
        'tpOp', 'indIni', 'indFin', 'cIndOp', 'cst', 'cClassTrib', 'cLocInc'
    ]
    
    tags_presentes = [tag for tag in tags_esperadas if tag in resultados]
    
    print(f"\n📊 RESUMO:")
    print(f"   Tags obrigatórias esperadas: {len(tags_esperadas)}")
    print(f"   Tags encontradas: {len(tags_presentes)}")
    
    if len(tags_presentes) == len(tags_esperadas):
        print(f"\n✅ SUCESSO! XML compatível com NT007 v1.03.00")
        return True
    else:
        print(f"\n⚠️  ATENÇÃO! XML incompleto - {len(tags_esperadas) - len(tags_presentes)} tags faltando")
        tags_faltando = [tag for tag in tags_esperadas if tag not in resultados]
        print(f"   Tags ausentes: {', '.join(tags_faltando)}")
        return False


def main():
    """Função principal de teste"""
    
    print("="*80)
    print("TESTE DE GERAÇÃO DE XML NFS-e - NT007 v1.03.00")
    print("Data: 09/02/2026")
    print("="*80)
    
    try:
        # 1. Criar NFS-e de teste
        print("\n1. Criando NFS-e de teste...")
        nfse = criar_nfse_teste()
        print("   ✅ NFS-e criada com sucesso")
        
        # 2. Gerar XML
        print("\n2. Gerando XML...")
        service = NFSeService(ambiente="homologacao")
        xml_gerado = service.gerar_xml_rps(nfse)
        print(f"   ✅ XML gerado ({len(xml_gerado)} caracteres)")
        
        # 3. Salvar XML em arquivo para inspeção
        output_file = "test_nfse_nt007_output.xml"
        with open(output_file, 'w', encoding='utf-8') as f:
            # Formatar XML para melhor legibilidade
            try:
                parser = etree.XMLParser(remove_blank_text=True)
                root = etree.fromstring(xml_gerado.encode('utf-8'), parser)
                xml_formatado = etree.tostring(root, pretty_print=True, encoding='unicode')
                f.write(xml_formatado)
            except:
                f.write(xml_gerado)
        
        print(f"   ✅ XML salvo em: {output_file}")
        
        # 4. Validar tags IBS/CBS
        print("\n3. Validando tags IBS/CBS no XML...")
        validacao_ok = validar_tags_ibscbs(xml_gerado)
        
        # 5. Resultado final
        print("\n" + "="*80)
        if validacao_ok:
            print("✅ TESTE CONCLUÍDO COM SUCESSO!")
            print("   O XML está compatível com a Nota Técnica 007 v1.03.00")
            print(f"   Arquivo gerado: {output_file}")
        else:
            print("⚠️  TESTE CONCLUÍDO COM RESSALVAS")
            print("   O XML foi gerado mas algumas tags podem estar faltando")
            print("   Revise o arquivo gerado e a validação acima")
        print("="*80)
        
        return validacao_ok
        
    except Exception as e:
        print(f"\n❌ ERRO durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
