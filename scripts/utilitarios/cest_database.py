#!/usr/bin/env python3
"""
Base de dados de CEST (Código Especificador da Substituição Tributária)
Baseado no Convênio ICMS 142/2018 - CONFAZ

O CEST é obrigatório para produtos sujeitos à Substituição Tributária (ST)
Formato: XX.XXX.XX onde:
- XX: Segmento (01 a 28)
- XXX: Item dentro do segmento
- XX: Subitem
"""

CEST_DATABASE = {
    # Segmento 01: Combustíveis e Lubrificantes
    "01": {
        "nome": "Combustíveis e Lubrificantes",
        "descricao": "Combustíveis, lubrificantes, aditivos, fluídos e outros produtos automotivos",
        "produtos": {
            "01.001.00": ["Gasolina automotiva", "gasolina comum", "gasolina premium"],
            "01.001.01": ["Álcool hidratado", "etanol hidratado", "alcool combustível"],
            "01.002.00": ["Óleo diesel", "diesel", "diesel s10"],
            "01.003.00": ["GNV", "gás natural veicular"],
            "01.004.00": ["Querosene de aviação", "QAV", "combustível aviação"],
            "01.005.00": ["Óleo combustível", "óleo BPF"],
            "01.006.00": ["Gás liquefeito de petróleo", "GLP", "gás de cozinha", "botijão"],
            "01.007.00": ["Lubrificante para motor", "óleo lubrificante", "óleo motor"],
            "01.008.00": ["Fluido de freio"],
            "01.009.00": ["Aditivo", "aditivo combustível", "aditivo radiador"],
        }
    },
    
    # Segmento 02: Bebidas alcoólicas, exceto cerveja e chope
    "02": {
        "nome": "Bebidas alcoólicas, exceto cerveja e chope",
        "descricao": "Aguardente, vodka, whisky, licor, vinho e outras bebidas alcoólicas",
        "produtos": {
            "02.001.00": ["Aguardente", "cachaça", "pinga"],
            "02.002.00": ["Vodka", "vodca"],
            "02.003.00": ["Whisky", "uísque"],
            "02.004.00": ["Licor"],
            "02.005.00": ["Vinho", "vinho tinto", "vinho branco", "vinho rosé"],
            "02.006.00": ["Conhaque"],
            "02.007.00": ["Gin"],
            "02.008.00": ["Rum"],
            "02.009.00": ["Tequila"],
        }
    },
    
    # Segmento 03: Cervejas, chopes, refrigerantes, águas e outras bebidas
    "03": {
        "nome": "Cervejas, chopes, refrigerantes, águas e outras bebidas",
        "descricao": "Bebidas não alcoólicas e cervejas",
        "produtos": {
            "03.001.00": ["Cerveja", "cerveja lata", "cerveja long neck", "cerveja garrafa"],
            "03.002.00": ["Chope", "chopp"],
            "03.003.00": ["Refrigerante", "coca-cola", "pepsi", "guaraná", "fanta"],
            "03.004.00": ["Água mineral", "água", "água com gás", "água sem gás"],
            "03.005.00": ["Isotônico", "gatorade", "energético"],
            "03.006.00": ["Bebida energética", "red bull", "monster"],
            "03.007.00": ["Suco", "suco natural", "néctar"],
            "03.008.00": ["Chá gelado", "chá preto"],
        }
    },
    
    # Segmento 04: Sorvetes e preparados para fabricação de sorvetes em máquinas
    "04": {
        "nome": "Sorvetes e preparados para fabricação de sorvetes",
        "descricao": "Sorvetes de qualquer espécie e preparados para fabricação",
        "produtos": {
            "04.001.00": ["Sorvete", "gelado", "picolé", "ice cream"],
            "04.002.00": ["Preparado para sorvete", "base sorvete", "mix sorvete"],
            "04.003.00": ["Casquinha", "cone sorvete", "wafer sorvete"],
        }
    },
    
    # Segmento 05: Chocolates
    "05": {
        "nome": "Chocolates",
        "descricao": "Chocolates e produtos de chocolate",
        "produtos": {
            "05.001.00": ["Chocolate", "chocolate barra", "tablete chocolate"],
            "05.002.00": ["Bombom", "bombons", "trufa"],
            "05.003.00": ["Chocolate branco"],
            "05.004.00": ["Chocolate em pó", "achocolatado", "cacau em pó"],
        }
    },
    
    # Segmento 06: Cigarros e outros produtos derivados do fumo
    "06": {
        "nome": "Cigarros e outros produtos derivados do fumo",
        "descricao": "Cigarros, charutos, fumo e outros produtos do tabaco",
        "produtos": {
            "06.001.00": ["Cigarro", "cigarros", "maço cigarro"],
            "06.002.00": ["Charuto"],
            "06.003.00": ["Cigarrilha"],
            "06.004.00": ["Fumo", "tabaco", "fumo de rolo"],
        }
    },
    
    # Segmento 07: Artefatos de uso doméstico
    "07": {
        "nome": "Artefatos de uso doméstico",
        "descricao": "Utensílios e artefatos de uso doméstico",
        "produtos": {
            "07.001.00": ["Panela", "panelas", "jogo panelas"],
            "07.002.00": ["Frigideira", "frigideiras"],
            "07.003.00": ["Talheres", "garfo", "faca", "colher"],
            "07.004.00": ["Louça", "pratos", "copos", "xícaras"],
            "07.005.00": ["Assadeira", "forma", "fôrma"],
        }
    },
    
    # Segmento 08: Ferramentas
    "08": {
        "nome": "Ferramentas",
        "descricao": "Ferramentas manuais e elétricas",
        "produtos": {
            "08.001.00": ["Martelo"],
            "08.002.00": ["Chave de fenda", "chave philips"],
            "08.003.00": ["Alicate"],
            "08.004.00": ["Furadeira", "furadeira elétrica"],
            "08.005.00": ["Serra", "serrote"],
            "08.006.00": ["Parafusadeira"],
        }
    },
    
    # Segmento 09: Lâminas de barbear, aparelhos de barbear e isqueiros
    "09": {
        "nome": "Lâminas e aparelhos de barbear, isqueiros",
        "descricao": "Produtos para barbear e isqueiros",
        "produtos": {
            "09.001.00": ["Lâmina de barbear", "lâmina gillette"],
            "09.002.00": ["Aparelho de barbear", "barbeador", "gilete"],
            "09.003.00": ["Isqueiro", "acendedor"],
        }
    },
    
    # Segmento 10: Autopeças
    "10": {
        "nome": "Autopeças",
        "descricao": "Peças, partes e acessórios para veículos automotores",
        "produtos": {
            "10.001.00": ["Pneu", "pneus", "pneu aro", "pneu radial"],
            "10.002.00": ["Câmara de ar"],
            "10.003.00": ["Protetores de borracha"],
            "10.004.00": ["Bateria", "bateria automotiva", "acumulador"],
            "10.005.00": ["Amortecedor"],
            "10.006.00": ["Filtros", "filtro óleo", "filtro ar", "filtro combustível"],
            "10.007.00": ["Bomba de combustível"],
            "10.008.00": ["Velas de ignição"],
            "10.009.00": ["Cabos de vela"],
            "10.010.00": ["Correias"],
        }
    },
    
    # Segmento 17: Produtos de higiene pessoal
    "17": {
        "nome": "Produtos de higiene pessoal",
        "descricao": "Produtos de perfumaria, cosméticos e de higiene pessoal",
        "produtos": {
            "17.001.00": ["Papel higiênico"],
            "17.002.00": ["Absorvente higiênico", "absorvente feminino"],
            "17.003.00": ["Fralda", "fralda descartável", "fralda infantil"],
            "17.004.00": ["Sabonete", "sabonete barra", "sabonete líquido"],
            "17.005.00": ["Shampoo", "xampu", "champô", "shampoo cabelo"],
            "17.006.00": ["Condicionador", "condicionador cabelo", "creme cabelo"],
            "17.007.00": ["Creme dental", "pasta de dente", "pasta dental"],
            "17.008.00": ["Desodorante", "desodorante roll-on", "desodorante spray"],
            "17.009.00": ["Perfume", "colônia", "eau de toilette", "eau de parfum", "fragrância"],
            "17.010.00": ["Loção", "loção corporal", "hidratante", "creme hidratante"],
            "17.011.00": ["Protetor solar", "filtro solar", "bloqueador solar"],
            "17.012.00": ["Maquiagem", "base", "batom", "rímel", "máscara"],
            "17.013.00": ["Esmalte", "esmalte unha", "verniz unha"],
            "17.014.00": ["Creme", "creme facial", "creme pele"],
            "17.015.00": ["Gel", "gel cabelo", "gel fixador"],
        }
    },
    
    # Segmento 20: Produtos de limpeza
    "20": {
        "nome": "Produtos de limpeza",
        "descricao": "Detergentes, sabões, desinfetantes e outros produtos de limpeza",
        "produtos": {
            "20.001.00": ["Detergente", "detergente líquido"],
            "20.002.00": ["Sabão em pó", "sabão", "sabonete lava roupa"],
            "20.003.00": ["Amaciante", "amaciante de roupa"],
            "20.004.00": ["Água sanitária", "alvejante"],
            "20.005.00": ["Desinfetante"],
            "20.006.00": ["Limpa vidros"],
            "20.007.00": ["Lustra móveis"],
            "20.008.00": ["Esponja de limpeza"],
        }
    },
    
    # Segmento 21: Materiais de construção e congêneres
    "21": {
        "nome": "Materiais de construção e congêneres",
        "descricao": "Cimento, argamassa, cal, tintas, vernizes e outros materiais",
        "produtos": {
            "21.001.00": ["Cimento", "cimento portland"],
            "21.002.00": ["Argamassa", "argamassa colante"],
            "21.003.00": ["Cal", "cal hidratada"],
            "21.004.00": ["Tinta", "tinta latex", "tinta acrílica", "tinta parede"],
            "21.005.00": ["Verniz", "verniz madeira"],
            "21.006.00": ["Massa corrida", "massa acrílica"],
            "21.007.00": ["Rejunte", "rejunte porcelanato"],
            "21.008.00": ["Impermeabilizante", "impermeabilização"],
            "21.009.00": ["Solvente", "thinner", "aguarrás"],
            "21.010.00": ["Selador", "selador parede"],
        }
    },
    
    # Segmento 22: Medicamentos de uso humano e outros produtos farmacêuticos
    "22": {
        "nome": "Medicamentos de uso humano e outros produtos farmacêuticos",
        "descricao": "Medicamentos, suplementos e produtos farmacêuticos",
        "produtos": {
            "22.001.00": ["Medicamento", "remédio", "comprimido", "cápsula"],
            "22.002.00": ["Vitamina", "suplemento vitamínico"],
            "22.003.00": ["Antibiótico"],
            "22.004.00": ["Anti-inflamatório", "anti inflamatório"],
            "22.005.00": ["Antialérgico", "anti alérgico"],
            "22.006.00": ["Xarope", "xarope tosse"],
        }
    },
    
    # Segmento 23: Medicamentos de uso veterinário
    "23": {
        "nome": "Medicamentos de uso veterinário",
        "descricao": "Medicamentos e produtos veterinários",
        "produtos": {
            "23.001.00": ["Medicamento veterinário", "remédio animal", "vacina animal"],
            "23.002.00": ["Ração", "ração pet", "ração cachorro", "ração gato"],
            "23.003.00": ["Vermífugo", "antiparasitário"],
        }
    },
    
    # Segmento 24: Papéis
    "24": {
        "nome": "Papéis",
        "descricao": "Papéis diversos para uso comercial e industrial",
        "produtos": {
            "24.001.00": ["Papel sulfite", "papel A4", "papel ofício"],
            "24.002.00": ["Papel toalha", "toalha papel"],
            "24.003.00": ["Guardanapo", "guardanapo papel"],
            "24.004.00": ["Lenço papel", "lenço descartável"],
        }
    },
    
    # Segmento 25: Artefatos de plástico para uso doméstico
    "25": {
        "nome": "Artefatos de plástico para uso doméstico",
        "descricao": "Produtos plásticos para uso residencial",
        "produtos": {
            "25.001.00": ["Balde", "balde plástico"],
            "25.002.00": ["Bacia", "bacia plástica"],
            "25.003.00": ["Copo plástico", "copo descartável"],
            "25.004.00": ["Prato plástico", "prato descartável"],
            "25.005.00": ["Garrafa plástica", "garrafa pet"],
        }
    },
    
    # Segmento 26: Cosméticos
    "26": {
        "nome": "Cosméticos",
        "descricao": "Produtos cosméticos e de beleza",
        "produtos": {
            "26.001.00": ["Tintura cabelo", "coloração", "tinta cabelo"],
            "26.002.00": ["Creme alisante", "alisante", "relaxante"],
            "26.003.00": ["Máscara capilar", "máscara cabelo"],
            "26.004.00": ["Serum", "sérum facial", "serum capilar"],
            "26.005.00": ["Removedor", "removedor esmalte", "acetona"],
        }
    },
    
    # Segmento 28: Materiais elétricos
    "28": {
        "nome": "Materiais elétricos",
        "descricao": "Fios, cabos, lâmpadas e outros materiais elétricos",
        "produtos": {
            "28.001.00": ["Lâmpada", "lâmpada led", "lâmpada fluorescente", "lâmpada incandescente"],
            "28.002.00": ["Reator", "reator eletrônico"],
            "28.003.00": ["Starter", "ignitor"],
            "28.004.00": ["Fio elétrico", "cabo elétrico", "fio cobre"],
            "28.005.00": ["Tomada", "tomada padrão", "tomada energia"],
            "28.006.00": ["Interruptor", "interruptor luz"],
            "28.007.00": ["Disjuntor", "disjuntor termomagnético"],
            "28.008.00": ["Fusível", "fusível elétrico"],
            "28.009.00": ["Plugue", "pino", "plug elétrico"],
            "28.010.00": ["Extensão elétrica", "extensão", "benjamim"],
        }
    }
}


def buscar_cest_por_produto(descricao_produto: str) -> dict | None:
    """
    Busca CEST baseado na descrição do produto
    
    Args:
        descricao_produto: Descrição do produto
        
    Returns:
        dict com 'cest', 'segmento', 'confianca' ou None se não encontrado
    """
    descricao_lower = descricao_produto.lower()
    palavras = descricao_lower.split()
    
    melhor_match = None
    maior_confianca = 0
    
    for segmento_codigo, segmento_data in CEST_DATABASE.items():
        for cest, palavras_chave in segmento_data["produtos"].items():
            # Verifica se alguma palavra-chave aparece na descrição
            for palavra_chave in palavras_chave:
                palavra_chave_lower = palavra_chave.lower()
                
                # Match exato
                if palavra_chave_lower in descricao_lower:
                    confianca = 90
                    
                    # Aumenta confiança se for palavra completa
                    if palavra_chave_lower in palavras:
                        confianca = 95
                    
                    if confianca > maior_confianca:
                        maior_confianca = confianca
                        melhor_match = {
                            'cest': cest,
                            'segmento': segmento_data['nome'],
                            'segmento_codigo': segmento_codigo,
                            'confianca': confianca,
                            'palavra_chave_encontrada': palavra_chave
                        }
                
                # Match parcial (palavras em comum)
                elif any(palavra in palavra_chave_lower for palavra in palavras if len(palavra) > 3):
                    confianca = 60
                    
                    if confianca > maior_confianca:
                        maior_confianca = confianca
                        melhor_match = {
                            'cest': cest,
                            'segmento': segmento_data['nome'],
                            'segmento_codigo': segmento_codigo,
                            'confianca': confianca,
                            'palavra_chave_encontrada': palavra_chave
                        }
    
    return melhor_match


def listar_segmentos():
    """Lista todos os segmentos CEST disponíveis"""
    print("=" * 80)
    print("SEGMENTOS CEST - Substituição Tributária")
    print("=" * 80)
    
    for codigo, data in CEST_DATABASE.items():
        print(f"\n{codigo} - {data['nome']}")
        print(f"    {data['descricao']}")
        print(f"    {len(data['produtos'])} códigos CEST cadastrados")


if __name__ == "__main__":
    # Testes
    produtos_teste = [
        "Gasolina comum",
        "Cerveja lata 350ml",
        "Cigarro marlboro",
        "Shampoo dove 400ml",
        "Pneu 175/70 R13",
        "Bateria automotiva 60Ah",
        "Refrigerante coca-cola 2L",
        "Água mineral 500ml",
        "Detergente líquido",
        "Lâmpada LED 12W"
    ]
    
    print("=" * 80)
    print("TESTE: Busca de CEST por descrição de produto")
    print("=" * 80)
    
    for produto in produtos_teste:
        resultado = buscar_cest_por_produto(produto)
        
        if resultado:
            print(f"\n[OK] {produto}")
            print(f"   CEST: {resultado['cest']}")
            print(f"   Segmento: {resultado['segmento']}")
            print(f"   Confiança: {resultado['confianca']}%")
            print(f"   Palavra-chave: {resultado['palavra_chave_encontrada']}")
        else:
            print(f"\n[X] {produto}")
            print(f"   CEST: Não encontrado (produto não sujeito a ST)")
    
    print("\n" + "=" * 80)
    listar_segmentos()
