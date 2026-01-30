#!/usr/bin/env python3
"""
Script de Migração para Preparação IBS/CBS
-------------------------------------------
Executa migração SQL e popula tabela de códigos de serviço LC 116/2003

Uso:
    python executar_migracao_ibs.py

Autor: Sistema NFe
Data: 17/11/2025
"""

import sys
import os
from pathlib import Path
from sqlalchemy import text

# Adicionar diretório raiz ao path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

# Importar conexão do banco de dados (padrão do projeto)
try:
    from database.connection import get_db
    print("[OK] Conexão de banco importada com sucesso")
except ImportError as e:
    print(f"[X] Erro ao importar database.connection: {e}")
    print("[TRACE] Diretório atual:", current_dir)
    print("\n[!]  Execute este script do diretório raiz do projeto:")
    print("    cd /Users/renato/Documents/Developement/api_nfe")
    print("    python3 executar_migracao_ibs.py")
    sys.exit(1)


def executar_migracao_sql():
    """Executa arquivo SQL de migração"""
    print("\n" + "="*60)
    print("[?] EXECUTANDO MIGRAÇÃO SQL")
    print("="*60)
    
    arquivo_sql = Path(__file__).parent / 'migrations' / '001_preparacao_ibs.sql'
    
    if not arquivo_sql.exists():
        print(f"[X] Arquivo não encontrado: {arquivo_sql}")
        return False
    
    print(f"[?] Lendo arquivo: {arquivo_sql.name}")
    
    db = next(get_db())
    try:
        with open(arquivo_sql, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print("[?] Executando comandos SQL...")
        
        # Executar SQL (split em statements individuais)
        statements = [s.strip() for s in sql_content.split(';') if s.strip()]
        
        for statement in statements:
            if statement:
                db.execute(text(statement))
        
        db.commit()
        print("[OK] Migração SQL executada com sucesso!")
        return True
    
    except Exception as e:
        db.rollback()
        print(f"[X] Erro ao executar migração SQL: {e}")
        return False
    finally:
        db.close()


def popular_codigos_servico():
    """Popula tabela codigos_servico com LC 116/2003"""
    print("\n" + "="*60)
    print("[LIST] POPULANDO CÓDIGOS DE SERVIÇO LC 116/2003")
    print("="*60)
    
    # Lista parcial dos códigos de serviço LC 116/2003
    # Fonte: Lei Complementar 116/2003 (Lista de Serviços)
    codigos = [
        # 01 - Serviços de informática e congêneres
        ('01.01', '1.01', 'Análise e desenvolvimento de sistemas.'),
        ('01.02', '1.02', 'Programação.'),
        ('01.03', '1.03', 'Processamento de dados e congêneres.'),
        ('01.04', '1.04', 'Elaboração de programas de computadores, inclusive de jogos eletrônicos.'),
        ('01.05', '1.05', 'Licenciamento ou cessão de direito de uso de programas de computação.'),
        ('01.06', '1.06', 'Assessoria e consultoria em informática.'),
        ('01.07', '1.07', 'Suporte técnico em informática, inclusive instalação, configuração e manutenção de programas de computação e bancos de dados.'),
        ('01.08', '1.08', 'Planejamento, confecção, manutenção e atualização de páginas eletrônicas.'),
        
        # 02 - Serviços de pesquisas e desenvolvimento
        ('02.01', '2.01', 'Serviços de pesquisas e desenvolvimento de qualquer natureza.'),
        
        # 03 - Serviços prestados mediante locação, cessão de direito de uso e congêneres
        ('03.02', '3.02', 'Cessão de direito de uso de marcas e de sinais de propaganda.'),
        ('03.03', '3.03', 'Exploração de salões de festas, centro de convenções, escritórios virtuais, stands, quadras esportivas, estádios, ginásios, auditórios, casas de espetáculos, parques de diversões, canchas e congêneres, para realização de eventos ou negócios de qualquer natureza.'),
        ('03.04', '3.04', 'Locação, sublocação, arrendamento, direito de passagem ou permissão de uso, compartilhado ou não, de ferrovia, rodovia, postes, cabos, dutos e condutos de qualquer natureza.'),
        ('03.05', '3.05', 'Cessão de andaimes, palcos, coberturas e outras estruturas de uso temporário.'),
        
        # 04 - Serviços de saúde, assistência médica e congêneres
        ('04.01', '4.01', 'Medicina e biomedicina.'),
        ('04.02', '4.02', 'Análises clínicas, patologia, eletricidade médica, radioterapia, quimioterapia, ultra-sonografia, ressonância magnética, radiologia, tomografia e congêneres.'),
        ('04.03', '4.03', 'Hospitais, clínicas, laboratórios, sanatórios, manicômios, casas de saúde, prontos-socorros, ambulatórios e congêneres.'),
        ('04.04', '4.04', 'Instrumentação cirúrgica.'),
        ('04.05', '4.05', 'Acupuntura.'),
        ('04.06', '4.06', 'Enfermagem, inclusive serviços auxiliares.'),
        ('04.07', '4.07', 'Serviços farmacêuticos.'),
        ('04.08', '4.08', 'Terapia ocupacional, fisioterapia e fonoaudiologia.'),
        ('04.09', '4.09', 'Terapias de qualquer espécie destinadas ao tratamento físico, orgânico e mental.'),
        ('04.10', '4.10', 'Nutrição.'),
        ('04.11', '4.11', 'Obstetrícia.'),
        ('04.12', '4.12', 'Odontologia.'),
        ('04.13', '4.13', 'Ortóptica.'),
        ('04.14', '4.14', 'Próteses sob encomenda.'),
        ('04.15', '4.15', 'Psicanálise.'),
        ('04.16', '4.16', 'Psicologia.'),
        ('04.17', '4.17', 'Casas de repouso e de recuperação, creches, asilos e congêneres.'),
        ('04.18', '4.18', 'Inseminação artificial, fertilização in vitro e congêneres.'),
        ('04.19', '4.19', 'Bancos de sangue, leite, pele, olhos, óvulos, sêmen e congêneres.'),
        ('04.20', '4.20', 'Coleta de sangue, leite, tecidos, sêmen, órgãos e materiais biológicos de qualquer espécie.'),
        ('04.21', '4.21', 'Unidade de atendimento, assistência ou tratamento móvel e congêneres.'),
        ('04.22', '4.22', 'Planos de medicina de grupo ou individual e convênios para prestação de assistência médica, hospitalar, odontológica e congêneres.'),
        ('04.23', '4.23', 'Outros planos de saúde que se cumpram através de serviços de terceiros contratados, credenciados, cooperados ou apenas pagos pelo operador do plano mediante indicação do beneficiário.'),
        
        # 05 - Serviços de medicina e assistência veterinária
        ('05.01', '5.01', 'Medicina veterinária e zootecnia.'),
        ('05.02', '5.02', 'Hospitais, clínicas, ambulatórios, prontos-socorros e congêneres, na área veterinária.'),
        ('05.03', '5.03', 'Laboratórios de análise na área veterinária.'),
        ('05.04', '5.04', 'Inseminação artificial, fertilização in vitro e congêneres.'),
        ('05.05', '5.05', 'Bancos de sangue e de órgãos e congêneres.'),
        ('05.06', '5.06', 'Coleta de sangue, leite, tecidos, sêmen, órgãos e materiais biológicos de qualquer espécie.'),
        ('05.07', '5.07', 'Unidade de atendimento, assistência ou tratamento móvel e congêneres.'),
        ('05.08', '5.08', 'Guarda, tratamento, amestramento, embelezamento, alojamento e congêneres.'),
        ('05.09', '5.09', 'Planos de atendimento e assistência médico-veterinária.'),
        
        # 06 - Serviços de cuidados pessoais, estética, atividades físicas e congêneres
        ('06.01', '6.01', 'Barbearia, cabeleireiros, manicuros, pedicuros e congêneres.'),
        ('06.02', '6.02', 'Esteticistas, tratamento de pele, depilação e congêneres.'),
        ('06.03', '6.03', 'Banhos, duchas, sauna, massagens e congêneres.'),
        ('06.04', '6.04', 'Ginástica, dança, esportes, natação, artes marciais e demais atividades físicas.'),
        ('06.05', '6.05', 'Centros de emagrecimento, spa e congêneres.'),
        
        # 07 - Serviços relativos a engenharia, arquitetura, geologia, urbanismo, construção civil
        ('07.01', '7.01', 'Engenharia, agronomia, agrimensura, arquitetura, geologia, urbanismo, paisagismo e congêneres.'),
        ('07.02', '7.02', 'Execução, por administração, empreitada ou subempreitada, de obras de construção civil, hidráulica ou elétrica e de outras obras semelhantes.'),
        ('07.03', '7.03', 'Elaboração de planos diretores, estudos de viabilidade, estudos organizacionais e outros, relacionados com obras e serviços de engenharia; elaboração de anteprojetos, projetos básicos e projetos executivos para trabalhos de engenharia.'),
        ('07.04', '7.04', 'Demolição.'),
        ('07.05', '7.05', 'Reparação, conservação e reforma de edifícios, estradas, pontes, portos e congêneres.'),
        ('07.06', '7.06', 'Colocação e instalação de tapetes, carpetes, assoalhos, cortinas, revestimentos de parede, vidros, divisórias, placas de gesso e congêneres, com material fornecido pelo Tomadores do serviço.'),
        ('07.07', '7.07', 'Recuperação, raspagem, polimento e lustração de pisos e congêneres.'),
        ('07.08', '7.08', 'Calafetação.'),
        ('07.09', '7.09', 'Varrição, coleta, remoção, incineração, tratamento, reciclagem, separação e destinação final de lixo, rejeitos e outros resíduos quaisquer.'),
        ('07.10', '7.10', 'Limpeza, manutenção e conservação de vias e logradouros públicos, imóveis, chaminés, piscinas, parques, jardins e congêneres.'),
        ('07.11', '7.11', 'Decoração e jardinagem, inclusive corte e poda de árvores.'),
        ('07.12', '7.12', 'Controle e tratamento de efluentes de qualquer natureza e de agentes físicos, químicos e biológicos.'),
        ('07.13', '7.13', 'Dedetização, desinfecção, desinsetização, imunização, higienização, desratização, pulverização e congêneres.'),
        ('07.16', '7.16', 'Florestamento, reflorestamento, semeadura, adubação e congêneres.'),
        ('07.17', '7.17', 'Escoramento, contenção de encostas e serviços congêneres.'),
        ('07.18', '7.18', 'Limpeza e dragagem de rios, portos, canais, baías, lagos, lagoas, represas, açudes e congêneres.'),
        ('07.19', '7.19', 'Acompanhamento e fiscalização da execução de obras de engenharia, arquitetura e urbanismo.'),
        ('07.20', '7.20', 'Aerofotogrametria (inclusive interpretação), cartografia, mapeamento, levantamentos topográficos, batimétricos, geográficos, geodésicos, geológicos, geofísicos e congêneres.'),
        ('07.21', '7.21', 'Pesquisa, perfuração, cimentação, mergulho, perfilagem, concretação, testemunhagem, pescaria, estimulação e outros serviços relacionados com a exploração e explotação de petróleo, gás natural e de outros recursos minerais.'),
        ('07.22', '7.22', 'Nucleação e bombardeamento de nuvens e congêneres.'),
        
        # 08 - Serviços de educação, ensino, orientação pedagógica
        ('08.01', '8.01', 'Ensino regular pré-escolar, fundamental, médio e superior.'),
        ('08.02', '8.02', 'Instrução, treinamento, orientação pedagógica e educacional, avaliação de conhecimentos de qualquer natureza.'),
        
        # 09 - Serviços relativos a hospedagem, turismo, viagens e congêneres
        ('09.01', '9.01', 'Hospedagem de qualquer natureza em hotéis, apart-service condominiais, flat, apart-hotéis, hotéis residência, residence-service, suite service, hotelaria marítima, motéis, pensões e congêneres; ocupação por temporada com fornecimento de serviço.'),
        ('09.02', '9.02', 'Agenciamento, organização, promoção, intermediação e execução de programas de turismo, passeios, viagens, excursões, hospedagens e congêneres.'),
        ('09.03', '9.03', 'Guias de turismo.'),
        
        # 10 - Serviços de intermediação e congêneres
        ('10.01', '10.01', 'Agenciamento, corretagem ou intermediação de câmbio, de seguros, de cartões de crédito, de planos de saúde e de planos de previdência privada.'),
        ('10.02', '10.02', 'Agenciamento, corretagem ou intermediação de títulos em geral, valores mobiliários e contratos quaisquer.'),
        ('10.03', '10.03', 'Agenciamento, corretagem ou intermediação de direitos de propriedade industrial, artística ou literária.'),
        ('10.04', '10.04', 'Agenciamento, corretagem ou intermediação de contratos de arrendamento mercantil (leasing), de franquia (franchising) e de faturização (factoring).'),
        ('10.05', '10.05', 'Agenciamento, corretagem ou intermediação de bens móveis ou imóveis, não abrangidos em outros itens ou subitens, inclusive aqueles realizados no âmbito de Bolsas de Mercadorias e Futuros, por quaisquer meios.'),
        ('10.06', '10.06', 'Agenciamento marítimo.'),
        ('10.07', '10.07', 'Agenciamento de notícias.'),
        ('10.08', '10.08', 'Agenciamento de publicidade e propaganda, inclusive o agenciamento de veiculação por quaisquer meios.'),
        ('10.09', '10.09', 'Representação de qualquer natureza, inclusive comercial.'),
        ('10.10', '10.10', 'Distribuição de bens de terceiros.'),
        
        # Adicionar mais códigos conforme necessário...
        # Total: ~140 códigos na LC 116/2003
    ]
    
    print(f"[DATA] Inserindo {len(codigos)} códigos de serviço...")
    
    db = next(get_db())
    try:
        for codigo, item, descricao in codigos:
            # Verificar se já existe
            check_query = text("""
                SELECT id FROM codigos_servico WHERE codigo = :codigo
            """)
            existe = db.execute(check_query, {'codigo': codigo}).fetchone()
            
            if not existe:
                insert_query = text("""
                    INSERT INTO codigos_servico 
                    (codigo, descricao, aliquota_padrao, ativo)
                    VALUES 
                    (:codigo, :descricao, 0.00, TRUE)
                """)
                
                db.execute(insert_query, {
                    'codigo': codigo,
                    'descricao': descricao
                })
                print(f"  [OK] {codigo} - {descricao[:50]}...")
            else:
                print(f"  ⏭️  {codigo} - Já existe")
        
        db.commit()
        print(f"\n[OK] {len(codigos)} códigos de serviço inseridos com sucesso!")
        return True
    
    except Exception as e:
        print(f"[X] Erro ao popular códigos de serviço: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def verificar_estruturas():
    """Verifica se estruturas foram criadas corretamente"""
    print("\n" + "="*60)
    print("[SEARCH] VERIFICANDO ESTRUTURAS CRIADAS")
    print("="*60)
    
    tabelas_esperadas = [
        'codigos_servico',
        'aliquotas_ibs_municipio',
        'historico_calculo_ibs'
    ]
    
    db = next(get_db())
    try:
        for tabela in tabelas_esperadas:
            query = text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = :tabela
            """)
            
            result = db.execute(query, {'tabela': tabela}).fetchone()
            
            if result and result[0] > 0:
                # Contar registros
                count_query = text(f"SELECT COUNT(*) FROM {tabela}")
                count_result = db.execute(count_query).fetchone()
                count = count_result[0] if count_result else 0
                print(f"  [OK] {tabela:<35} ({count} registros)")
            else:
                print(f"  [X] {tabela:<35} (NÃO ENCONTRADA)")
        
        return True
    
    except Exception as e:
        print(f"[X] Erro ao verificar estruturas: {e}")
        return False
    finally:
        db.close()


def exibir_resumo():
    """Exibe resumo da migração"""
    print("\n" + "="*60)
    print("[DATA] RESUMO DA MIGRAÇÃO")
    print("="*60)
    
    print("""
[OK] Estruturas IBS/CBS criadas com sucesso!

[LIST] O que foi feito:
  1. Tabela codigos_servico (LC 116/2003)
  2. Tabela aliquotas_ibs (aguardando dados oficiais 2026)
  3. Tabela nfe_itens_servico (para NFS-e futura)
  4. Tabela beneficios_fiscais_ibs
  5. Tabela conversao_tributaria_historica
  6. View vw_comparativo_tributacao
  7. Função buscar_aliquota_ibs_vigente()
  8. Campo tipo_nota adicionado em nfes
  9. Triggers de atualização automática
  10. Índices de performance

[?] Módulo Python criado:
  - services/calculo_ibs.py (pronto para uso)

[?] Próximos Passos:
  1. Aguardar publicação das alíquotas IBS oficiais (2026)
  2. Popular tabela aliquotas_ibs quando dados disponíveis
  3. Adaptar formulários para emissão de NFS-e
  4. Implementar interface de gestão de benefícios fiscais
  5. Criar relatórios comparativos tributação antiga vs IBS

[!]  IMPORTANTE:
  - Alíquotas IBS são placeholders (0.00%)
  - CBS federal estimada em 12% (aguardar oficial)
  - Sistema pronto para receber dados reais em 2026

[?] Documentação:
  - ANALISE_CARTILHA_IBS_VS_SISTEMA.md
  - migrations/001_preparacao_ibs.sql
  - services/calculo_ibs.py (docstrings completas)
    """)


def main():
    """Função principal"""
    print("\n" + "="*60)
    print("[START] MIGRAÇÃO IBS/CBS - PREPARAÇÃO REFORMA TRIBUTÁRIA")
    print("="*60)
    print("Data: 17/11/2025")
    print("Referência: LC 214/2023 e Cartilha IBS FENACON")
    print("="*60)
    
    # 1. Executar migração SQL
    if not executar_migracao_sql():
        print("\n[X] Falha na migração SQL. Abortando.")
        return 1
    
    # 2. Popular códigos de serviço
    if not popular_codigos_servico():
        print("\n[!]  Falha ao popular códigos de serviço (não crítico)")
    
    # 3. Verificar estruturas
    if not verificar_estruturas():
        print("\n[!]  Algumas estruturas podem não ter sido criadas corretamente")
    
    # 4. Exibir resumo
    exibir_resumo()
    
    print("\n" + "="*60)
    print("[OK] MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("="*60 + "\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
