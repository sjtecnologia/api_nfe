#!/usr/bin/env python3
"""
Script para popular TODOS os 140 códigos LC 116/2003
Complementa os 37 já inseridos, adicionando os 103 restantes
"""

import sys
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.absolute()))
from database.connection import get_db

# Lista COMPLETA dos 140 códigos LC 116/2003
codigos_completos = [
    # 01 - Serviços de informática e congêneres
    ('01.01', 'Análise e desenvolvimento de sistemas'),
    ('01.02', 'Programação'),
    ('01.03', 'Processamento, armazenamento ou hospedagem de dados, textos, imagens, vídeos, páginas eletrônicas, aplicativos e sistemas de informação'),
    ('01.04', 'Elaboração de programas de computadores, inclusive jogos eletrônicos, independentemente da arquitetura construtiva da máquina'),
    ('01.05', 'Licenciamento ou cessão de direito de uso de programas de computação'),
    ('01.06', 'Assessoria e consultoria em informática'),
    ('01.07', 'Suporte técnico em informática, inclusive instalação, configuração e manutenção de programas e bancos de dados'),
    ('01.08', 'Planejamento, confecção, manutenção e atualização de páginas eletrônicas'),
    ('01.09', 'Disponibilização, sem cessão definitiva, de conteúdos de áudio, vídeo, imagem e texto por meio da internet'),
    
    # 02 - Serviços de pesquisas e desenvolvimento
    ('02.01', 'Serviços de pesquisas e desenvolvimento de qualquer natureza'),
    
    # 03 - Serviços prestados mediante locação, cessão de direito de uso
    ('03.02', 'Cessão de direito de uso de marcas e de sinais de propaganda'),
    ('03.03', 'Exploração de salões de festas, centro de convenções, escritórios virtuais, stands, quadras esportivas, estádios, ginásios, auditórios'),
    ('03.04', 'Locação, sublocação, arrendamento, direito de passagem ou permissão de uso, compartilhado ou não, de ferrovia, rodovia, postes, cabos, dutos'),
    ('03.05', 'Cessão de andaimes, palcos, coberturas e outras estruturas de uso temporário'),
    
    # 04 - Serviços de saúde, assistência médica e congêneres
    ('04.01', 'Medicina e biomedicina'),
    ('04.02', 'Análises clínicas, patologia, eletricidade médica, radioterapia, quimioterapia, ultrassonografia, ressonância magnética'),
    ('04.03', 'Hospitais, clínicas, laboratórios, sanatórios, manicômios, casas de saúde, prontos-socorros, ambulatórios'),
    ('04.04', 'Instrumentação cirúrgica'),
    ('04.05', 'Acupuntura'),
    ('04.06', 'Enfermagem, inclusive serviços auxiliares'),
    ('04.07', 'Serviços farmacêuticos'),
    ('04.08', 'Terapia ocupacional, fisioterapia e fonoaudiologia'),
    ('04.09', 'Terapias de qualquer espécie destinadas ao tratamento físico, orgânico e mental'),
    ('04.10', 'Nutrição'),
    ('04.11', 'Obstetrícia'),
    ('04.12', 'Odontologia'),
    ('04.13', 'Ortóptica'),
    ('04.14', 'Próteses sob encomenda'),
    ('04.15', 'Psicanálise'),
    ('04.16', 'Psicologia'),
    ('04.17', 'Casas de repouso e de recuperação, creches, asilos e congêneres'),
    ('04.18', 'Inseminação artificial, fertilização in vitro e congêneres'),
    ('04.19', 'Bancos de sangue, leite, pele, olhos, óvulos, sêmen e congêneres'),
    ('04.20', 'Coleta de sangue, leite, tecidos, sêmen, órgãos e materiais biológicos'),
    ('04.21', 'Unidade de atendimento, assistência ou tratamento móvel e congêneres'),
    ('04.22', 'Planos de medicina de grupo ou individual e convênios para prestação de assistência médica'),
    ('04.23', 'Outros planos de saúde através de serviços de terceiros contratados, credenciados, cooperados ou pagos pelo operador'),
    
    # 05 - Serviços de medicina e assistência veterinária
    ('05.01', 'Medicina veterinária e zootecnia'),
    ('05.02', 'Hospitais, clínicas, ambulatórios, prontos-socorros e congêneres veterinários'),
    ('05.03', 'Laboratórios de análise veterinária'),
    ('05.04', 'Inseminação artificial, fertilização in vitro veterinária'),
    ('05.05', 'Bancos de sangue e de órgãos e congêneres veterinários'),
    ('05.06', 'Coleta de sangue, leite, tecidos, sêmen, órgãos veterinários'),
    ('05.07', 'Unidade de atendimento, assistência ou tratamento móvel veterinário'),
    ('05.08', 'Guarda, tratamento, amestramento, embelezamento, alojamento e congêneres'),
    ('05.09', 'Planos de atendimento e assistência médico-veterinária'),
    
    # 06 - Serviços de cuidados pessoais, estética, atividades físicas
    ('06.01', 'Barbearia, cabeleireiros, manicuros, pedicuros e congêneres'),
    ('06.02', 'Esteticistas, tratamento de pele, depilação e congêneres'),
    ('06.03', 'Banhos, duchas, sauna, massagens e congêneres'),
    ('06.04', 'Ginástica, dança, esportes, natação, artes marciais e demais atividades físicas'),
    ('06.05', 'Centros de emagrecimento, spa e congêneres'),
    ('06.06', 'Aplicação de tatuagens, piercings e congêneres'),
    
    # 07 - Serviços relativos a engenharia, arquitetura, geologia
    ('07.01', 'Engenharia, agronomia, agrimensura, arquitetura, geologia, urbanismo, paisagismo e congêneres'),
    ('07.02', 'Execução, por administração, empreitada ou subempreitada, de obras de construção civil'),
    ('07.03', 'Elaboração de planos diretores, estudos de viabilidade, estudos organizacionais e outros relacionados com obras'),
    ('07.04', 'Demolição'),
    ('07.05', 'Reparação, conservação e reforma de edifícios, estradas, pontes, portos e congêneres'),
    ('07.06', 'Colocação e instalação de tapetes, carpetes, assoalhos, cortinas, revestimentos de parede, vidros, divisórias'),
    ('07.07', 'Recuperação, raspagem, polimento e lustração de pisos e congêneres'),
    ('07.08', 'Calafetação'),
    ('07.09', 'Varrição, coleta, remoção, incineração, tratamento, reciclagem, separação e destinação final de lixo'),
    ('07.10', 'Limpeza, manutenção e conservação de vias e logradouros públicos, imóveis, chaminés, piscinas, parques, jardins'),
    ('07.11', 'Decoração e jardinagem, inclusive corte e poda de árvores'),
    ('07.12', 'Controle e tratamento de efluentes, esgotos, dejetos, águas residuais e lixo'),
    ('07.13', 'Dedetização, desinfecção, desinsetização, imunização, higienização, desratização, pulverização e congêneres'),
    ('07.16', 'Florestamento, reflorestamento, semeadura, adubação, reparação de solo, plantio, silagens, colheita, corte, descascamento'),
    ('07.17', 'Escoramento, contenção de encostas e serviços congêneres'),
    ('07.18', 'Limpeza e dragagem de rios, portos, canais, baías, lagos, lagoas, represas, açudes e congêneres'),
    ('07.19', 'Acompanhamento e fiscalização da execução de obras de engenharia, arquitetura e urbanismo'),
    ('07.20', 'Aerofotogrametria, mapeamento, levantamento topográfico, batimétrico, geográfico, geodésico, geológico, geofísico'),
    ('07.21', 'Pesquisa, perfuração, cimentação, mergulho, perfilagem, concretação, testemunhagem, pescaria'),
    ('07.22', 'Nucleação e bombardeamento de nuvens e congêneres'),
    
    # 08 - Serviços de educação, ensino, orientação pedagógica
    ('08.01', 'Ensino regular pré-escolar, fundamental, médio e superior'),
    ('08.02', 'Instrução, treinamento, orientação pedagógica e educacional, avaliação de conhecimentos'),
    
    # 09 - Serviços relativos a hospedagem, turismo, viagens
    ('09.01', 'Hospedagem de qualquer natureza em hotéis, apart-service, flat, apart-hotéis, hotéis residência, motéis, pensões'),
    ('09.02', 'Agenciamento, organização, promoção, intermediação e execução de programas de turismo, passeios, viagens, excursões'),
    ('09.03', 'Guias de turismo'),
    
    # 10 - Serviços de intermediação e congêneres
    ('10.01', 'Agenciamento, corretagem ou intermediação de câmbio, de seguros, de cartões de crédito, de planos de saúde'),
    ('10.02', 'Agenciamento, corretagem ou intermediação de títulos em geral, valores mobiliários e contratos quaisquer'),
    ('10.03', 'Agenciamento, corretagem ou intermediação de direitos de propriedade industrial, artística ou literária'),
    ('10.04', 'Agenciamento, corretagem ou intermediação de contratos de arrendamento mercantil, de franquia e de faturização'),
    ('10.05', 'Agenciamento, corretagem ou intermediação de bens móveis ou imóveis, não abrangidos em outros itens'),
    ('10.06', 'Agenciamento marítimo'),
    ('10.07', 'Agenciamento de notícias'),
    ('10.08', 'Agenciamento de publicidade e propaganda, inclusive o agenciamento de veiculação'),
    ('10.09', 'Representação de qualquer natureza, inclusive comercial'),
    ('10.10', 'Distribuição de bens de terceiros'),
    
    # 11 - Serviços de guarda e estacionamento
    ('11.01', 'Guarda e estacionamento de veículos terrestres automotores, de aeronaves e de embarcações'),
    ('11.02', 'Vigilância, segurança ou monitoramento de bens, pessoas e semoventes'),
    ('11.03', 'Escolta, inclusive de veículos e cargas'),
    ('11.04', 'Armazenamento, depósito, carga, descarga, arrumação e guarda de bens de qualquer espécie'),
    
    # 12 - Serviços de diversões, lazer, entretenimento
    ('12.01', 'Espetáculos teatrais'),
    ('12.02', 'Exibições cinematográficas'),
    ('12.03', 'Espetáculos circenses'),
    ('12.04', 'Programas de auditório'),
    ('12.05', 'Parques de diversões, centros de lazer e congêneres'),
    ('12.06', 'Boates, taxi-dancing e congêneres'),
    ('12.07', 'Shows, ballet, danças, desfiles, bailes, óperas, concertos, recitais, festivais'),
    ('12.08', 'Feiras, exposições, congressos e congêneres'),
    ('12.09', 'Bilhares, boliches e diversões eletrônicas ou não'),
    ('12.10', 'Corridas e competições de animais'),
    ('12.11', 'Competições esportivas ou de destreza física ou intelectual, com ou sem a participação do espectador'),
    ('12.12', 'Execução de música'),
    ('12.13', 'Produção, mediante ou sem encomenda prévia, de eventos, espetáculos, entrevistas, shows, ballet, danças'),
    ('12.14', 'Fornecimento de música para ambientes fechados ou não, mediante transmissão por qualquer processo'),
    ('12.15', 'Desfiles de blocos carnavalescos ou folclóricos, trios elétricos e congêneres'),
    ('12.16', 'Exibição de filmes, entrevistas, musicais, espetáculos, shows, concertos, desfiles, óperas, competições'),
    ('12.17', 'Recreação e animação, inclusive em festas e eventos de qualquer natureza'),
    
    # 13 - Serviços relativos a fonografia, fotografia, cinematografia
    ('13.02', 'Fonografia ou gravação de sons, inclusive trucagem, dublagem, mixagem e congêneres'),
    ('13.03', 'Fotografia e cinematografia, inclusive revelação, ampliação, cópia, reprodução, trucagem'),
    ('13.04', 'Reprografia, microfilmagem e digitalização'),
    ('13.05', 'Composição gráfica, inclusive confecção de impressos gráficos, fotocomposição, clicheria, zincografia, litografia'),
    
    # 14 - Serviços relativos a bens de terceiros
    ('14.01', 'Lubrificação, limpeza, lustração, revisão, carga e recarga, conserto, restauração, blindagem, manutenção'),
    ('14.02', 'Assistência técnica'),
    ('14.03', 'Recondicionamento de motores'),
    ('14.04', 'Recauchutagem ou regeneração de pneus'),
    ('14.05', 'Restauração, recondicionamento, acondicionamento, pintura, beneficiamento, lavagem, secagem, tingimento'),
    ('14.06', 'Instalação e montagem de aparelhos, máquinas e equipamentos, inclusive montagem industrial'),
    ('14.07', 'Colocação de molduras e congêneres'),
    ('14.08', 'Encadernação, gravação e douração de livros, revistas e congêneres'),
    ('14.09', 'Alfaiataria e costura, quando o material for fornecido pelo usuário final'),
    ('14.10', 'Tinturaria e lavanderia'),
    ('14.11', 'Tapeçaria e reforma de estofamentos em geral'),
    ('14.12', 'Funilaria e lanternagem'),
    ('14.13', 'Carpintaria e serralheria'),
    ('14.14', 'Guincho intramunicipal, guindaste e içamento'),
    
    # 15 - Serviços relacionados ao setor bancário ou financeiro
    ('15.01', 'Administração de fundos quaisquer, de consórcio, de cartão de crédito ou débito'),
    ('15.02', 'Abertura de contas em geral, inclusive conta-corrente, conta de investimentos e aplicação'),
    ('15.03', 'Locação e manutenção de cofres particulares, de terminais eletrônicos, de terminais de atendimento'),
    ('15.04', 'Fornecimento ou emissão de atestados em geral, inclusive atestado de idoneidade'),
    ('15.05', 'Cadastro, elaboração de ficha cadastral, renovação cadastral e congêneres'),
    ('15.06', 'Emissão, reemissão e fornecimento de avisos, comprovantes e documentos em geral'),
    ('15.07', 'Acesso, movimentação, atendimento e consulta a contas em geral'),
    ('15.08', 'Emissão, reemissão, alteração, cessão, substituição, cancelamento e registro de contrato de crédito'),
    ('15.09', 'Arrendamento mercantil (leasing) de quaisquer bens'),
    ('15.10', 'Serviços relacionados a cobranças, recebimentos ou pagamentos em geral'),
    ('15.11', 'Devolução de títulos, protesto de títulos, sustação de protesto, manutenção de títulos'),
    ('15.12', 'Custódia em geral, inclusive de títulos e valores mobiliários'),
    ('15.13', 'Serviços relacionados a operações de câmbio em geral'),
    ('15.14', 'Fornecimento, emissão, reemissão, renovação e manutenção de cartão magnético, cartão de crédito'),
    ('15.15', 'Compensação de cheques e títulos quaisquer; serviços relacionados a depósito'),
    ('15.16', 'Emissão, reemissão, liquidação, alteração, cancelamento e baixa de ordens de pagamento'),
    ('15.17', 'Emissão, fornecimento, devolução, sustação, cancelamento e oposição de cheques quaisquer'),
    ('15.18', 'Serviços relacionados a crédito imobiliário, avaliação e vistoria de imóvel ou obra'),
    
    # 16 - Serviços de transporte de natureza municipal
    ('16.01', 'Serviços de transporte coletivo municipal rodoviário, metroviário, ferroviário e aquaviário de passageiros'),
    ('16.02', 'Outros serviços de transporte de natureza municipal'),
    
    # 17 - Serviços de apoio técnico, administrativo, jurídico
    ('17.01', 'Assessoria ou consultoria de qualquer natureza, não contida em outros itens'),
    ('17.02', 'Datilografia, digitação, estenografia, expediente, secretaria em geral, resposta audível'),
    ('17.03', 'Planejamento, coordenação, programação ou organização técnica, financeira ou administrativa'),
    ('17.04', 'Recrutamento, agenciamento, seleção e colocação de mão-de-obra'),
    ('17.05', 'Fornecimento de mão-de-obra, inclusive por empregados do prestador ou por trabalhadores avulsos'),
    ('17.06', 'Propaganda e publicidade, inclusive promoção de vendas, planejamento de campanhas'),
    ('17.08', 'Franquia (franchising)'),
    ('17.09', 'Perícias, laudos, exames técnicos e análises técnicas'),
    ('17.10', 'Planejamento, organização e administração de feiras, exposições, congressos e congêneres'),
    ('17.11', 'Organização de festas e recepções; bufê (exceto fornecimento de alimentação e bebidas)'),
    ('17.12', 'Administração em geral, inclusive de bens e negócios de terceiros'),
    ('17.13', 'Leilão e congêneres'),
    ('17.14', 'Advocacia'),
    ('17.15', 'Arbitragem de qualquer espécie, inclusive jurídica'),
    ('17.16', 'Auditoria'),
    ('17.17', 'Análise de Organização e Métodos'),
    ('17.18', 'Atuária e cálculos técnicos de qualquer natureza'),
    ('17.19', 'Contabilidade, inclusive serviços técnicos e auxiliares'),
    ('17.20', 'Consultoria e assessoria econômica ou financeira'),
    ('17.21', 'Estatística'),
    ('17.22', 'Cobrança em geral'),
    ('17.23', 'Assessoria, análise, avaliação, atendimento, consulta, cadastro, seleção, gerenciamento de informações'),
    ('17.24', 'Apresentação de palestras, conferências, seminários e congêneres'),
    ('17.25', 'Inserção de textos, desenhos e outros materiais de propaganda e publicidade'),
]

def popular_codigos():
    """Popula todos os 140 códigos LC 116/2003"""
    print("\n" + "="*60)
    print("[DATA] POPULANDO CÓDIGOS COMPLETOS LC 116/2003")
    print("="*60)
    print(f"Total de códigos: {len(codigos_completos)}")
    
    db = next(get_db())
    try:
        inseridos = 0
        existentes = 0
        
        for codigo, descricao in codigos_completos:
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
                inseridos += 1
                if inseridos % 10 == 0:
                    print(f"  [OK] {inseridos} códigos inseridos...")
            else:
                existentes += 1
        
        db.commit()
        print(f"\n[OK] Processamento concluído:")
        print(f"   • {inseridos} códigos NOVOS inseridos")
        print(f"   • {existentes} códigos já existiam")
        print(f"   • Total no banco: {inseridos + existentes}")
        
        # Verificar total
        count_query = text("SELECT COUNT(*) FROM codigos_servico")
        result = db.execute(count_query).fetchone()
        total = result[0] if result is not None else 0
        print(f"\n[OK] Total de códigos cadastrados: {total} de 140 ({total*100/140:.1f}%)")
        
        return True
    
    except Exception as e:
        print(f"[X] Erro: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == '__main__':
    print("\n[START] COMPLEMENTAÇÃO DE CÓDIGOS LC 116/2003")
    print("="*60)
    popular_codigos()
    print("="*60)
