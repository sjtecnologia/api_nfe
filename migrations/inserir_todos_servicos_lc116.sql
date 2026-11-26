-- =====================================================
-- POPULAÇÃO COMPLETA - CÓDIGOS DE SERVIÇO LC116
-- Total: 199 serviços (todas as 40 seções)
-- =====================================================

-- Usar INSERT ... ON CONFLICT DO NOTHING para evitar duplicatas

INSERT INTO codigos_servico_lc116 (codigo, descricao, item_pai, ativo) VALUES
-- SEÇÃO 1: INFORMÁTICA E CONGÊNERES
('1.01', 'Análise e desenvolvimento de sistemas', '1', true),
('1.02', 'Programação', '1', true),
('1.03', 'Processamento de dados, textos, imagens, vídeos, páginas eletrônicas, aplicativos e sistemas de informação, entre outros formatos, e congêneres', '1', true),
('1.04', 'Elaboração de programas de computadores, inclusive de jogos eletrônicos, independentemente da arquitetura construtiva da máquina em que o programa será executado, incluindo tablets, smartphones e congêneres', '1', true),
('1.05', 'Licenciamento ou cessão de direito de uso de programas de computação', '1', true),
('1.06', 'Assessoria e consultoria em informática', '1', true),
('1.07', 'Suporte técnico em informática, inclusive instalação, configuração e manutenção de programas de computação e bancos de dados', '1', true),
('1.08', 'Planejamento, confecção, manutenção e atualização de páginas eletrônicas', '1', true),
('1.09', 'Disponibilização, sem cessão definitiva, de conteúdos de áudio, vídeo, imagem e texto por meio da internet', '1', true),

-- SEÇÃO 2: PESQUISAS
('2.01', 'Serviços de pesquisas e desenvolvimento de qualquer natureza', '2', true),

-- SEÇÃO 3: LOCAÇÃO, CESSÃO, LICENCIAMENTO
('3.02', 'Cessão de direito de uso de marcas e de sinais de propaganda', '3', true),
('3.03', 'Exploração de salões de festas, centro de convenções, stands, escritórios virtuais, quadras esportivas, estádios, ginásios, auditórios, casas de espetáculos, parques de diversões, canchas e congêneres', '3', true),
('3.04', 'Locação, sublocação, arrendamento, direito de passagem ou permissão de uso, compartilhado ou não, de ferrovia, rodovia, postes, cabos, dutos e condutos de qualquer natureza', '3', true),
('3.05', 'Cessão de andaimes, palcos, coberturas e outras estruturas de uso temporário', '3', true),

-- SEÇÃO 4: MEDICINA E SAÚDE
('4.01', 'Medicina e biomedicina', '4', true),
('4.02', 'Análises clínicas, patologia, eletricidade médica, radioterapia, quimioterapia, ultra-sonografia, ressonância magnética, radiologia, tomografia e congêneres', '4', true),
('4.03', 'Hospitais, clínicas, laboratórios, sanatórios, manicômios, casas de saúde, prontos-socorros, ambulatórios e congêneres', '4', true),
('4.04', 'Instrumentação cirúrgica', '4', true),
('4.05', 'Acupuntura', '4', true),
('4.06', 'Enfermagem, inclusive serviços auxiliares', '4', true),
('4.07', 'Serviços farmacêuticos', '4', true),
('4.08', 'Terapia ocupacional, fisioterapia e fonoaudiologia', '4', true),
('4.09', 'Terapias de qualquer espécie destinadas ao tratamento físico, orgânico e mental', '4', true),
('4.10', 'Nutrição', '4', true),
('4.11', 'Obstetrícia', '4', true),
('4.12', 'Odontologia', '4', true),
('4.13', 'Ortóptica', '4', true),
('4.14', 'Próteses sob encomenda', '4', true),
('4.15', 'Psicanálise', '4', true),
('4.16', 'Psicologia', '4', true),
('4.17', 'Casas de repouso e de recuperação, creches, asilos e congêneres', '4', true),
('4.18', 'Inseminação artificial, fertilização in vitro e congêneres', '4', true),
('4.19', 'Bancos de sangue, leite, pele, olhos, óvulos, sêmen e congêneres', '4', true),
('4.20', 'Coleta de sangue, leite, tecidos, sêmen, órgãos e materiais biológicos de qualquer espécie', '4', true),
('4.21', 'Unidade de atendimento, assistência ou tratamento móvel e congêneres', '4', true),
('4.22', 'Planos de medicina de grupo ou individual e convênios para prestação de assistência médica, hospitalar, odontológica e congêneres', '4', true),
('4.23', 'Outros planos de saúde que se cumpram através de serviços de terceiros contratados, credenciados, cooperados ou apenas pagos pelo operador do plano mediante indicação do beneficiário', '4', true),

-- SEÇÃO 5: MEDICINA VETERINÁRIA
('5.01', 'Medicina veterinária e zootecnia', '5', true),
('5.02', 'Hospitais, clínicas, ambulatórios, prontos-socorros e congêneres, na área veterinária', '5', true),
('5.03', 'Laboratórios de análise na área veterinária', '5', true),
('5.04', 'Inseminação artificial, fertilização in vitro e congêneres', '5', true),
('5.05', 'Bancos de sangue e de órgãos e congêneres', '5', true),
('5.06', 'Coleta de sangue, leite, tecidos, sêmen, órgãos e materiais biológicos de qualquer espécie', '5', true),
('5.07', 'Unidade de atendimento, assistência ou tratamento móvel e congêneres', '5', true),
('5.08', 'Guarda, tratamento, amestramento, embelezamento, alojamento e congêneres', '5', true),
('5.09', 'Planos de atendimento e assistência médico-veterinária', '5', true),

-- SEÇÃO 6: CUIDADOS PESSOAIS
('6.01', 'Barbearia, cabeleireiros, manicuros, pedicuros e congêneres', '6', true),
('6.02', 'Esteticistas, tratamento de pele, depilação e congêneres', '6', true),
('6.03', 'Banhos, duchas, sauna, massagens e congêneres', '6', true),
('6.04', 'Ginástica, dança, esportes, natação, artes marciais e demais atividades físicas', '6', true),
('6.05', 'Centros de emagrecimento, spa e congêneres', '6', true),
('6.06', 'Aplicação de tatuagens, piercings e congêneres', '6', true),

-- SEÇÃO 7: ENGENHARIA, ARQUITETURA, GEOLOGIA, URBANISMO, CONSTRUÇÃO CIVIL
('7.01', 'Engenharia, agronomia, agrimensura, arquitetura, urbanismo, geologia e congêneres', '7', true),
('7.02', 'Execução, por administração, empreitada ou subempreitada, de obras de construção civil, hidráulica ou elétrica e de outras obras semelhantes', '7', true),
('7.03', 'Elaboração de planos diretores, estudos de viabilidade, estudos organizacionais e outros, relacionados com obras e serviços de engenharia; elaboração de anteprojetos, projetos básicos e projetos executivos para trabalhos de engenharia', '7', true),
('7.04', 'Demolição', '7', true),
('7.05', 'Reparação, conservação e reforma de edifícios, estradas, pontes, portos e congêneres', '7', true),
('7.06', 'Colocação e instalação de tapetes, carpetes, assoalhos, cortinas, revestimentos de parede, vidros, divisórias, placas de gesso e congêneres, com material fornecido pelo tomador do serviço', '7', true),
('7.07', 'Recuperação, raspagem, polimento e lustração de pisos e congêneres', '7', true),
('7.08', 'Calafetação', '7', true),
('7.09', 'Varrição, coleta, remoção, incineração, tratamento, reciclagem, separação e destinação final de lixo, rejeitos e outros resíduos quaisquer', '7', true),
('7.10', 'Limpeza, manutenção e conservação de vias e logradouros públicos, imóveis, chaminés, piscinas, parques, jardins e congêneres', '7', true),
('7.11', 'Decoração e jardinagem, inclusive corte e poda de árvores', '7', true),
('7.12', 'Controle e tratamento de efluentes de qualquer natureza e de agentes físicos, químicos e biológicos', '7', true),
('7.13', 'Dedetização, desinfecção, desinsetização, imunização, higienização, desratização, pulverização e congêneres', '7', true),
('7.16', 'Florestamento, reflorestamento, semeadura, adubação, reparação de solo, plantio, silagem, colheita, corte e descascamento de árvores, silvicultura, exploração florestal e dos serviços congêneres indissociáveis da formação, manutenção e colheita de florestas, para quaisquer fins e por quaisquer meios', '7', true),
('7.17', 'Escoramento, contenção de encostas e serviços congêneres', '7', true),
('7.18', 'Limpeza e dragagem de rios, portos, canais, baías, lagos, lagoas, represas, açudes e congêneres', '7', true),
('7.19', 'Acompanhamento e fiscalização da execução de obras de engenharia, arquitetura e urbanismo', '7', true),
('7.20', 'Aerofotogrametria (inclusive interpretação), cartografia, mapeamento, levantamentos topográficos, batimétricos, geográficos, geodésicos, geológicos, geofísicos e congêneres', '7', true),
('7.21', 'Pesquisa, perfuração, cimentação, mergulho, perfilagem, concretação, testemunhagem, pescaria, estimulação e outros serviços relacionados com a exploração e explotação de petróleo, gás natural e de outros recursos minerais', '7', true),
('7.22', 'Nucleação e bombardeamento de nuvens e congêneres', '7', true),

-- SEÇÃO 8: EDUCAÇÃO
('8.01', 'Ensino regular pré-escolar, fundamental, médio e superior', '8', true),
('8.02', 'Instrução, treinamento, orientação pedagógica e educacional, avaliação de conhecimentos de qualquer natureza', '8', true),

-- SEÇÃO 9: HOSPEDAGEM, TURISMO, VIAGENS E CONGÊNERES
('9.01', 'Hospedagem de qualquer natureza em hotéis, apart-service condominiais, flat, apart-hotéis, hotéis residência, residence-service, suite service, hotelaria marítima, motéis, pensões e congêneres; ocupação por temporada com fornecimento de serviço', '9', true),
('9.02', 'Agenciamento, organização, promoção, intermediação e execução de programas de turismo, passeios, viagens, excursões, hospedagens e congêneres', '9', true),
('9.03', 'Guias de turismo', '9', true),

-- SEÇÃO 10: INTERMEDIAÇÃO E CONGÊNERES
('10.01', 'Agenciamento, corretagem ou intermediação de câmbio, de seguros, de cartões de crédito, de planos de saúde e de planos de previdência privada', '10', true),
('10.02', 'Agenciamento, corretagem ou intermediação de títulos em geral, valores mobiliários e contratos quaisquer', '10', true),
('10.03', 'Agenciamento, corretagem ou intermediação de direitos de propriedade industrial, artística ou literária', '10', true),
('10.04', 'Agenciamento, corretagem ou intermediação de contratos de arrendamento mercantil (leasing), de franquia (franchising) e de faturização (factoring)', '10', true),
('10.05', 'Agenciamento, corretagem ou intermediação de bens móveis ou imóveis, não abrangidos em outros itens ou subitens, inclusive aqueles realizados no âmbito de Bolsas de Mercadorias e Futuros, por quaisquer meios', '10', true),
('10.06', 'Agenciamento marítimo', '10', true),
('10.07', 'Agenciamento de notícias', '10', true),
('10.08', 'Agenciamento de publicidade e propaganda, inclusive o agenciamento de veiculação por quaisquer meios', '10', true),
('10.09', 'Representação de qualquer natureza, inclusive comercial', '10', true),
('10.10', 'Distribuição de bens de terceiros', '10', true),

-- SEÇÃO 11: GUARDA E ESTACIONAMENTO
('11.01', 'Guarda e estacionamento de veículos terrestres automotores, de aeronaves e de embarcações', '11', true),
('11.02', 'Vigilância, segurança ou monitoramento de bens, pessoas e semoventes', '11', true),
('11.03', 'Escolta, inclusive de veículos e cargas', '11', true),
('11.04', 'Armazenamento, depósito, carga, descarga, arrumação e guarda de bens de qualquer espécie', '11', true),

-- SEÇÃO 12: DIVERSÕES, LAZER, ENTRETENIMENTO E CONGÊNERES
('12.01', 'Espetáculos teatrais', '12', true),
('12.02', 'Exibições cinematográficas', '12', true),
('12.03', 'Espetáculos circenses', '12', true),
('12.04', 'Programas de auditório', '12', true),
('12.05', 'Parques de diversões, centros de lazer e congêneres', '12', true),
('12.06', 'Boates, taxi-dancing e congêneres', '12', true),
('12.07', 'Shows, ballet, danças, desfiles, bailes, óperas, concertos, recitais, festivais e congêneres', '12', true),
('12.08', 'Feiras, exposições, congressos e congêneres', '12', true),
('12.09', 'Bilhares, boliches e diversões eletrônicas ou não', '12', true),
('12.10', 'Corridas e competições de animais', '12', true),
('12.11', 'Competições esportivas ou de destreza física ou intelectual, com ou sem a participação do espectador', '12', true),
('12.12', 'Execução de música', '12', true),
('12.13', 'Produção, mediante ou sem encomenda prévia, de eventos, espetáculos, entrevistas, shows, ballet, danças, desfiles, bailes, teatros, óperas, concertos, recitais, festivais e congêneres', '12', true),
('12.14', 'Fornecimento de música para ambientes fechados ou não, mediante transmissão por qualquer processo', '12', true),
('12.15', 'Desfiles de blocos carnavalescos ou folclóricos, trios elétricos e congêneres', '12', true),
('12.16', 'Exibição de filmes, entrevistas, musicais, espetáculos, shows, concertos, desfiles, óperas, competições esportivas, de destreza intelectual ou congêneres', '12', true),
('12.17', 'Recreação e animação, inclusive em festas e eventos de qualquer natureza', '12', true),

-- SEÇÃO 13: FONOGRAFIA, FOTOGRAFIA, CINEMATOGRAFIA E REPROGRAFIA
('13.02', 'Fonografia ou gravação de sons, inclusive trucagem, dublagem, mixagem e congêneres', '13', true),
('13.03', 'Fotografia e cinematografia, inclusive revelação, ampliação, cópia, reprodução, trucagem e congêneres', '13', true),
('13.04', 'Reprografia, microfilmagem e digitalização', '13', true),
('13.05', 'Composição gráfica, inclusive confecção de impressos gráficos, fotocomposição, clicheria, zincografia, litografia e fotolitografia', '13', true),

-- SEÇÃO 14: SERVIÇOS RELATIVOS A BENS DE TERCEIROS
('14.01', 'Lubrificação, limpeza, lustração, revisão, carga e recarga, conserto, restauração, blindagem, manutenção e conservação de máquinas, veículos, aparelhos, equipamentos, motores, elevadores ou de qualquer objeto', '14', true),
('14.02', 'Assistência técnica', '14', true),
('14.03', 'Recondicionamento de motores', '14', true),
('14.04', 'Recauchutagem ou regeneração de pneus', '14', true),
('14.05', 'Restauração, recondicionamento, acondicionamento, pintura, beneficiamento, lavagem, secagem, tingimento, galvanoplastia, anodização, corte, recorte, plastificação, costura, acabamento, polimento e congêneres, de objetos quaisquer', '14', true),
('14.06', 'Instalação e montagem de aparelhos, máquinas e equipamentos, inclusive montagem industrial, prestados ao usuário final, exclusivamente com material por ele fornecido', '14', true),
('14.07', 'Colocação de molduras e congêneres', '14', true),
('14.08', 'Encadernação, gravação e douração de livros, revistas e congêneres', '14', true),
('14.09', 'Alfaiataria e costura, quando o material for fornecido pelo usuário final, exceto aviamento', '14', true),
('14.10', 'Tinturaria e lavanderia', '14', true),
('14.11', 'Tapeçaria e reforma de estofamentos em geral', '14', true),
('14.12', 'Funilaria e lanternagem', '14', true),
('14.13', 'Carpintaria e serralheria', '14', true),
('14.14', 'Guincho intramunicipal, guindaste e içamento', '14', true),

-- SEÇÃO 15: SERVIÇOS RELACIONADOS AO SETOR BANCÁRIO OU FINANCEIRO
('15.01', 'Administração de fundos quaisquer, de consórcio, de cartão de crédito ou débito e congêneres, de carteira de clientes, de cheques pré-datados e congêneres', '15', true),
('15.02', 'Abertura de contas em geral, inclusive conta-corrente, conta de investimentos e aplicação e caderneta de poupança, no País e no exterior, bem como a manutenção das referidas contas ativas e inativas', '15', true),
('15.03', 'Locação e manutenção de cofres particulares, de terminais eletrônicos, de terminais de atendimento e de bens e equipamentos em geral', '15', true),
('15.04', 'Fornecimento ou emissão de atestados em geral, inclusive atestado de idoneidade, atestado de capacidade financeira e congêneres', '15', true),
('15.05', 'Cadastro, elaboração de ficha cadastral, renovação cadastral e congêneres, inclusão ou exclusão no Cadastro de Emitentes de Cheques sem Fundos - CCF ou em quaisquer outros bancos cadastrais', '15', true),
('15.06', 'Emissão, reemissão e fornecimento de avisos, comprovantes e documentos em geral; abono de firmas; coleta e entrega de documentos, bens e valores; comunicação com outra agência ou com a administração central; licenciamento eletrônico de veículos; transferência de veículos; agenciamento fiduciário ou depositário; devolução de bens em custódia', '15', true),
('15.07', 'Acesso, movimentação, atendimento e consulta a contas em geral, por qualquer meio ou processo, inclusive por telefone, fac-símile, internet e telex, acesso a terminais de atendimento, inclusive vinte e quatro horas; acesso a outro banco e à rede compartilhada; fornecimento de saldo, extrato e demais informações relativas a contas em geral, por qualquer meio ou processo', '15', true),
('15.08', 'Emissão, reemissão, alteração, cessão, substituição, cancelamento e registro de contrato de crédito; estudo, análise e avaliação de operações de crédito; emissão, concessão, alteração ou contratação de aval, fiança, anuência e congêneres; serviços relativos a abertura de crédito, para quaisquer fins', '15', true),
('15.09', 'Arrendamento mercantil (leasing) de quaisquer bens, inclusive cessão de direitos e obrigações, substituição de garantia, alteração, cancelamento e registro de contrato, e demais serviços relacionados ao arrendamento mercantil (leasing)', '15', true),
('15.10', 'Serviços relacionados a cobranças, recebimentos ou pagamentos em geral, de títulos quaisquer, de contas ou carnês, de câmbio, de tributos e por conta de terceiros, inclusive os efetuados por meio eletrônico, automático ou por máquinas de atendimento; fornecimento de posição de cobrança, recebimento ou pagamento; emissão de carnês, fichas de compensação, impressos e documentos em geral', '15', true),
('15.11', 'Devolução de títulos, protesto de títulos, sustação de protesto, manutenção de títulos, reapresentação de títulos, e demais serviços a eles relacionados', '15', true),
('15.12', 'Custódia em geral, inclusive de títulos e valores mobiliários', '15', true),
('15.13', 'Serviços relacionados a operações de câmbio em geral, edição, alteração, prorrogação, cancelamento e baixa de contrato de câmbio; emissão de registro de exportação ou de crédito; cobrança ou depósito no exterior; emissão, fornecimento e cancelamento de cheques de viagem; fornecimento, transferência, cancelamento e demais serviços relativos a carta de crédito de importação, exportação e garantias recebidas; envio e recebimento de mensagens em geral relacionadas a operações de câmbio', '15', true),
('15.14', 'Fornecimento, emissão, reemissão, renovação e manutenção de cartão magnético, cartão de crédito, cartão de débito, cartão salário e congêneres', '15', true),
('15.15', 'Compensação de cheques e títulos quaisquer; serviços relacionados a depósito, inclusive depósito identificado, a saque de contas quaisquer, por qualquer meio ou processo, inclusive em terminais eletrônicos e de atendimento', '15', true),
('15.16', 'Emissão, reemissão, liquidação, alteração, cancelamento e baixa de ordens de pagamento, ordens de crédito e similares, por qualquer meio ou processo; serviços relacionados à transferência de valores, dados, fundos, pagamentos e similares, inclusive entre contas em geral', '15', true),
('15.17', 'Emissão, fornecimento, devolução, sustação, cancelamento e oposição de cheques quaisquer, avulso ou por talão', '15', true),
('15.18', 'Serviços relacionados a crédito imobiliário, avaliação e vistoria de imóvel ou obra, análise técnica e jurídica, emissão, reemissão, alteração, transferência e renegociação de contrato, emissão e reemissão do termo de quitação e demais serviços relacionados a crédito imobiliário', '15', true),

-- SEÇÃO 16: SERVIÇOS DE TRANSPORTE DE NATUREZA MUNICIPAL
('16.01', 'Serviços de transporte coletivo municipal rodoviário, metroviário, ferroviário e aquaviário de passageiros', '16', true),
('16.02', 'Outros serviços de transporte de natureza municipal', '16', true),

-- SEÇÃO 17: SERVIÇOS DE APOIO TÉCNICO, ADMINISTRATIVO, JURÍDICO, CONTÁBIL, COMERCIAL E CONGÊNERES
('17.01', 'Assessoria ou consultoria de qualquer natureza, não contida em outros itens desta lista; análise, exame, pesquisa, coleta, compilação e fornecimento de dados e informações de qualquer natureza, inclusive cadastro e similares', '17', true),
('17.02', 'Datilografia, digitação, estenografia, expediente, secretaria em geral, resposta audível, redação, edição, interpretação, revisão, tradução, apoio e infra-estrutura administrativa e congêneres', '17', true),
('17.03', 'Planejamento, coordenação, programação ou organização técnica, financeira ou administrativa', '17', true),
('17.04', 'Recrutamento, agenciamento, seleção e colocação de mão-de-obra', '17', true),
('17.05', 'Fornecimento de mão-de-obra, mesmo em caráter temporário, inclusive de empregados ou trabalhadores, avulsos ou temporários, contratados pelo prestador de serviço', '17', true),
('17.06', 'Propaganda e publicidade, inclusive promoção de vendas, planejamento de campanhas ou sistemas de publicidade, elaboração de desenhos, textos e demais materiais publicitários', '17', true),
('17.08', 'Franquia (franchising)', '17', true),
('17.09', 'Perícias, laudos, exames técnicos e análises técnicas', '17', true),
('17.10', 'Planejamento, organização e administração de feiras, exposições, congressos e congêneres', '17', true),
('17.11', 'Organização de festas e recepções; bufê (exceto o fornecimento de alimentação e bebidas, que fica sujeito ao ICMS)', '17', true),
('17.12', 'Administração em geral, inclusive de bens e negócios de terceiros', '17', true),
('17.13', 'Leilão e congêneres', '17', true),
('17.14', 'Advocacia', '17', true),
('17.15', 'Arbitragem de qualquer espécie, inclusive jurídica', '17', true),
('17.16', 'Auditoria', '17', true),
('17.17', 'Análise de Organização e Métodos', '17', true),
('17.18', 'Atuária e cálculos técnicos de qualquer natureza', '17', true),
('17.19', 'Contabilidade, inclusive serviços técnicos e auxiliares', '17', true),
('17.20', 'Consultoria e assessoria econômica ou financeira', '17', true),
('17.21', 'Estatística', '17', true),
('17.22', 'Cobrança em geral', '17', true),
('17.23', 'Assessoria, análise, avaliação, atendimento, consulta, cadastro, seleção, gerenciamento de informações, administração de contas a receber ou a pagar e em geral, relacionados a operações de faturização (factoring)', '17', true),
('17.24', 'Apresentação de palestras, conferências, seminários e congêneres', '17', true),
('17.25', 'Inserção de textos, desenhos e outros materiais de propaganda e publicidade, em qualquer meio', '17', true),

-- SEÇÃO 18: SERVIÇOS DE REGULAÇÃO DE SINISTROS
('18.01', 'Serviços de regulação de sinistros vinculados a contratos de seguros; inspeção e avaliação de riscos para cobertura de contratos de seguros; prevenção e gerência de riscos seguráveis e congêneres', '18', true),

-- SEÇÃO 19: SERVIÇOS DE DISTRIBUIÇÃO E VENDA DE BILHETES E DEMAIS PRODUTOS DE LOTERIA
('19.01', 'Serviços de distribuição e venda de bilhetes e demais produtos de loteria, bingos, cartões, pules ou cupons de apostas, sorteios, prêmios, inclusive os decorrentes de títulos de capitalização e congêneres', '19', true),

-- SEÇÃO 20: SERVIÇOS PORTUÁRIOS, AEROPORTUÁRIOS, FERROPORTUÁRIOS, DE TERMINAIS RODOVIÁRIOS, FERROVIÁRIOS E METROVIÁRIOS
('20.01', 'Serviços portuários, ferroportuários, utilização de porto, movimentação de passageiros, reboque de embarcações, rebocador escoteiro, atracação, desatracação, serviços de praticagem, capatazia, armazenagem de qualquer natureza, serviços acessórios, movimentação de mercadorias, serviços de apoio marítimo, de movimentação ao largo, serviços de armadores, estiva, conferência, logística e congêneres', '20', true),
('20.02', 'Serviços aeroportuários, utilização de aeroporto, movimentação de passageiros, armazenagem de qualquer natureza, capatazia, movimentação de aeronaves, serviços de apoio aeroportuários, serviços acessórios, movimentação de mercadorias, logística e congêneres', '20', true),
('20.03', 'Serviços de terminais rodoviários, ferroviários, metroviários, movimentação de passageiros, mercadorias, inclusive suas operações, logística e congêneres', '20', true),

-- SEÇÃO 21: SERVIÇOS DE REGISTROS PÚBLICOS, CARTORÁRIOS E NOTARIAIS
('21.01', 'Serviços de registros públicos, cartorários e notariais', '21', true),

-- SEÇÃO 22: SERVIÇOS DE EXPLORAÇÃO DE RODOVIA
('22.01', 'Serviços de exploração de rodovia mediante cobrança de preço ou pedágio dos usuários, envolvendo execução de serviços de conservação, manutenção, melhoramentos para adequação de capacidade e segurança de trânsito, operação, monitoração, assistência aos usuários e outros serviços definidos em contratos, atos de concessão ou de permissão ou em normas oficiais', '22', true),

-- SEÇÃO 23: SERVIÇOS DE PROGRAMAÇÃO E COMUNICAÇÃO VISUAL
('23.01', 'Serviços de programação e comunicação visual, desenho industrial e congêneres', '23', true),

-- SEÇÃO 24: SERVIÇOS DE CHAVEIROS, CONFECÇÃO DE CARIMBOS, PLACAS, SINALIZAÇÃO VISUAL, BANNERS, ADESIVOS E CONGÊNERES
('24.01', 'Serviços de chaveiros, confecção de carimbos, placas, sinalização visual, banners, adesivos e congêneres', '24', true),

-- SEÇÃO 25: SERVIÇOS FUNERÁRIOS
('25.01', 'Funerais, inclusive fornecimento de caixão, urna ou esquifes; aluguel de capela; transporte do corpo cadavérico; fornecimento de flores, coroas e outros paramentos; desembaraço de certidão de óbito; fornecimento de véu, essa e outros adornos; embalsamento, embelezamento, conservação ou restauração de cadáveres', '25', true),
('25.02', 'Translado intramunicipal e cremação de corpos e partes de corpos cadavéricos', '25', true),
('25.03', 'Planos ou convênio funerários', '25', true),
('25.04', 'Manutenção e conservação de jazigos e cemitérios', '25', true),
('25.05', 'Cessão de uso de espaços em cemitérios para sepultamento', '25', true),

-- SEÇÃO 26: SERVIÇOS DE COLETA, REMESSA OU ENTREGA DE CORRESPONDÊNCIAS
('26.01', 'Serviços de coleta, remessa ou entrega de correspondências, documentos, objetos, bens ou valores, inclusive pelos correios e suas agências franqueadas; courrier e congêneres', '26', true),

-- SEÇÃO 27: SERVIÇOS DE ASSISTÊNCIA SOCIAL
('27.01', 'Serviços de assistência social', '27', true),

-- SEÇÃO 28: SERVIÇOS DE AVALIAÇÃO DE BENS E SERVIÇOS DE QUALQUER NATUREZA
('28.01', 'Serviços de avaliação de bens e serviços de qualquer natureza', '28', true),

-- SEÇÃO 29: SERVIÇOS DE BIBLIOTECONOMIA
('29.01', 'Serviços de biblioteconomia', '29', true),

-- SEÇÃO 30: SERVIÇOS DE BIOLOGIA, BIOTECNOLOGIA E QUÍMICA
('30.01', 'Serviços de biologia, biotecnologia e química', '30', true),

-- SEÇÃO 31: SERVIÇOS TÉCNICOS EM EDIFICAÇÕES, ELETRÔNICA, ELETROTÉCNICA, MECÂNICA, TELECOMUNICAÇÕES E CONGÊNERES
('31.01', 'Serviços técnicos em edificações, eletrônica, eletrotécnica, mecânica, telecomunicações e congêneres', '31', true),

-- SEÇÃO 32: SERVIÇOS DE DESENHOS TÉCNICOS
('32.01', 'Serviços de desenhos técnicos', '32', true),

-- SEÇÃO 33: SERVIÇOS DE DESEMBARAÇO ADUANEIRO
('33.01', 'Serviços de desembaraço aduaneiro, comissários, despachantes e congêneres', '33', true),

-- SEÇÃO 34: SERVIÇOS DE INVESTIGAÇÕES PARTICULARES, DETETIVES E CONGÊNERES
('34.01', 'Serviços de investigações particulares, detetives e congêneres', '34', true),

-- SEÇÃO 35: SERVIÇOS DE REPORTAGEM, ASSESSORIA DE IMPRENSA, JORNALISMO E RELAÇÕES PÚBLICAS
('35.01', 'Serviços de reportagem, assessoria de imprensa, jornalismo e relações públicas', '35', true),

-- SEÇÃO 36: SERVIÇOS DE METEOROLOGIA
('36.01', 'Serviços de meteorologia', '36', true),

-- SEÇÃO 37: SERVIÇOS DE ARTISTAS, ATLETAS, MODELOS E MANEQUINS
('37.01', 'Serviços de artistas, atletas, modelos e manequins', '37', true),

-- SEÇÃO 38: SERVIÇOS DE MUSEOLOGIA
('38.01', 'Serviços de museologia', '38', true),

-- SEÇÃO 39: SERVIÇOS DE OURIVESARIA E LAPIDAÇÃO
('39.01', 'Serviços de ourivesaria e lapidação (quando o material for fornecido pelo tomador do serviço)', '39', true),

-- SEÇÃO 40: OBRAS DE ARTE SOB ENCOMENDA
('40.01', 'Obras de arte sob encomenda', '40', true)

ON CONFLICT (codigo) DO NOTHING;

-- Verificar quantos foram inseridos
SELECT 
    (SELECT COUNT(*) FROM codigos_servico_lc116) as total_atual,
    199 as total_esperado;
