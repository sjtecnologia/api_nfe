#!/usr/bin/env python3
"""
🧪 Teste Expandido de CEST - Base Completa
Testa todos os novos segmentos adicionados
"""

import requests
import json
from datetime import datetime

API_URL = "http://localhost:9000/api/sugestao"

# Produtos organizados por segmento CEST
PRODUTOS_POR_SEGMENTO = {
    "01 - Combustíveis": [
        {"descricao": "Gasolina comum", "espera_cest": True, "segmento": "01"},
        {"descricao": "Óleo Diesel S10", "espera_cest": True, "segmento": "01"},
        {"descricao": "GLP Gás de cozinha 13kg", "espera_cest": True, "segmento": "01"},
    ],
    
    "02 - Bebidas Alcoólicas": [
        {"descricao": "Whisky Johnnie Walker Red Label", "espera_cest": True, "segmento": "02"},
        {"descricao": "Vinho tinto seco 750ml", "espera_cest": True, "segmento": "02"},
    ],
    
    "03 - Cervejas e Refrigerantes": [
        {"descricao": "Cerveja Heineken 350ml", "espera_cest": True, "segmento": "03"},
        {"descricao": "Refrigerante Coca-Cola 2L", "espera_cest": True, "segmento": "03"},
        {"descricao": "Água mineral Crystal 500ml", "espera_cest": True, "segmento": "03"},
    ],
    
    "04 - Sorvetes": [
        {"descricao": "Sorvete Kibon napolitano 2L", "espera_cest": True, "segmento": "04"},
        {"descricao": "Picolé de frutas", "espera_cest": True, "segmento": "04"},
    ],
    
    "05 - Chocolates": [
        {"descricao": "Chocolate Lacta ao leite 90g", "espera_cest": True, "segmento": "05"},
        {"descricao": "Bombom Ferrero Rocher", "espera_cest": True, "segmento": "05"},
    ],
    
    "06 - Cigarros": [
        {"descricao": "Cigarro Marlboro Red", "espera_cest": True, "segmento": "06"},
    ],
    
    "07 - Artefatos Domésticos": [
        {"descricao": "Jogo de panelas antiaderente", "espera_cest": True, "segmento": "07"},
        {"descricao": "Talheres inox 24 peças", "espera_cest": True, "segmento": "07"},
    ],
    
    "08 - Ferramentas": [
        {"descricao": "Furadeira elétrica 500W", "espera_cest": True, "segmento": "08"},
        {"descricao": "Jogo de chaves de fenda", "espera_cest": True, "segmento": "08"},
    ],
    
    "09 - Lâminas e Isqueiros": [
        {"descricao": "Lâmina de barbear Gillette", "espera_cest": True, "segmento": "09"},
        {"descricao": "Isqueiro descartável BIC", "espera_cest": True, "segmento": "09"},
    ],
    
    "10 - Autopeças": [
        {"descricao": "Pneu Pirelli 175/70 R13", "espera_cest": True, "segmento": "10"},
        {"descricao": "Bateria Moura 60Ah", "espera_cest": True, "segmento": "10"},
        {"descricao": "Filtro de óleo motor", "espera_cest": True, "segmento": "10"},
    ],
    
    "17 - Higiene Pessoal": [
        {"descricao": "Shampoo Pantene 400ml", "espera_cest": True, "segmento": "17"},
        {"descricao": "Sabonete Dove 90g", "espera_cest": True, "segmento": "17"},
        {"descricao": "Desodorante Rexona Roll-on", "espera_cest": True, "segmento": "17"},
        {"descricao": "Perfume Natura Humor", "espera_cest": True, "segmento": "17"},
        {"descricao": "Creme dental Colgate 90g", "espera_cest": True, "segmento": "17"},
    ],
    
    "20 - Produtos de Limpeza": [
        {"descricao": "Detergente Ypê 500ml", "espera_cest": True, "segmento": "20"},
        {"descricao": "Água sanitária Qboa 1L", "espera_cest": True, "segmento": "20"},
        {"descricao": "Desinfetante Pinho Sol", "espera_cest": True, "segmento": "20"},
    ],
    
    "21 - Materiais de Construção": [
        {"descricao": "Tinta látex branca 18L", "espera_cest": True, "segmento": "21"},
        {"descricao": "Cimento Portland 50kg", "espera_cest": True, "segmento": "21"},
        {"descricao": "Argamassa AC2 20kg", "espera_cest": True, "segmento": "21"},
    ],
    
    "22 - Medicamentos Humano": [
        {"descricao": "Dipirona 500mg 20 comprimidos", "espera_cest": True, "segmento": "22"},
        {"descricao": "Vitamina C 500mg", "espera_cest": True, "segmento": "22"},
    ],
    
    "23 - Medicamentos Veterinário": [
        {"descricao": "Ração Golden para cães 15kg", "espera_cest": True, "segmento": "23"},
        {"descricao": "Vermífugo para gatos", "espera_cest": True, "segmento": "23"},
    ],
    
    "24 - Papéis": [
        {"descricao": "Papel sulfite A4 210x297", "espera_cest": True, "segmento": "24"},
        {"descricao": "Papel toalha folha dupla", "espera_cest": True, "segmento": "24"},
    ],
    
    "25 - Artefatos Plásticos": [
        {"descricao": "Balde plástico 10L", "espera_cest": True, "segmento": "25"},
        {"descricao": "Copo descartável 200ml", "espera_cest": True, "segmento": "25"},
    ],
    
    "26 - Cosméticos": [
        {"descricao": "Tintura para cabelo Cor&Ton", "espera_cest": True, "segmento": "26"},
        {"descricao": "Máscara capilar Elseve", "espera_cest": True, "segmento": "26"},
    ],
    
    "28 - Materiais Elétricos": [
        {"descricao": "Lâmpada LED 9W branca", "espera_cest": True, "segmento": "28"},
        {"descricao": "Fio elétrico 2,5mm 100m", "espera_cest": True, "segmento": "28"},
        {"descricao": "Tomada padrão novo 10A", "espera_cest": True, "segmento": "28"},
    ],
    
    "Produtos SEM ST": [
        {"descricao": "Notebook Dell Inspiron", "espera_cest": False},
        {"descricao": "Mouse USB sem fio", "espera_cest": False},
        {"descricao": "Livro programação Python", "espera_cest": False},
        {"descricao": "Café torrado em grãos 500g", "espera_cest": False},
    ]
}


def testar_produto(produto, segmento_nome):
    """Testa um produto específico"""
    try:
        response = requests.post(
            API_URL, 
            json={
                "descricao": produto["descricao"],
                "tipo_item": "Produto",
                "uf_origem": "SP"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            resultado = data.get('classificacao', {})
            
            ncm = resultado.get('ncm', 'N/A')
            cest = resultado.get('cest', None)
            cest_fonte = resultado.get('cest_fonte', '')
            
            tem_cest = cest and cest not in [None, 'null', 'N/A']
            
            # Verificar se está correto
            correto = False
            emoji = "❌"
            
            if produto.get('espera_cest'):
                if tem_cest:
                    segmento_recebido = str(cest)[:2]
                    segmento_esperado = produto.get('segmento', '')
                    
                    if segmento_recebido == segmento_esperado:
                        correto = True
                        emoji = "✅"
                    else:
                        emoji = "⚠️"
            else:
                if not tem_cest:
                    correto = True
                    emoji = "✅"
            
            return {
                'sucesso': True,
                'correto': correto,
                'produto': produto["descricao"],
                'ncm': ncm,
                'cest': cest if tem_cest else "---",
                'emoji': emoji,
                'cest_fonte': cest_fonte
            }
            
        else:
            return {
                'sucesso': False,
                'produto': produto["descricao"],
                'erro': f"HTTP {response.status_code}"
            }
            
    except Exception as e:
        return {
            'sucesso': False,
            'produto': produto["descricao"],
            'erro': str(e)
        }


def main():
    print("=" * 100)
    print("🧪 TESTE EXPANDIDO - BASE CEST COMPLETA")
    print("=" * 100)
    print(f"🕐 Início: {datetime.now().strftime('%H:%M:%S')}")
    print(f"📡 API: {API_URL}\n")
    
    # Verificar API
    try:
        response = requests.get("http://localhost:9000/health", timeout=5)
        if response.status_code != 200:
            print("❌ API não disponível!")
            return
        print("✅ API respondendo\n")
    except:
        print("❌ Erro ao conectar à API!")
        return
    
    total_testes = sum(len(produtos) for produtos in PRODUTOS_POR_SEGMENTO.values())
    sucessos = 0
    falhas = 0
    corretos = 0
    
    # Testar cada segmento
    for segmento_nome, produtos in PRODUTOS_POR_SEGMENTO.items():
        print(f"\n{'=' * 100}")
        print(f"📦 {segmento_nome} ({len(produtos)} produtos)")
        print(f"{'=' * 100}")
        
        for produto in produtos:
            resultado = testar_produto(produto, segmento_nome)
            
            if resultado['sucesso']:
                sucessos += 1
                if resultado['correto']:
                    corretos += 1
                
                print(f"{resultado['emoji']} {resultado['produto'][:50]:50} | NCM: {resultado['ncm']:8} | CEST: {resultado['cest']:12}")
                if resultado.get('cest_fonte'):
                    print(f"   └─ {resultado['cest_fonte']}")
            else:
                falhas += 1
                print(f"❌ {resultado['produto'][:50]:50} | ERRO: {resultado.get('erro', 'Desconhecido')}")
    
    # Resumo final
    print(f"\n{'=' * 100}")
    print(f"📊 RESUMO FINAL")
    print(f"{'=' * 100}")
    print(f"Total de testes: {total_testes}")
    print(f"✅ Sucessos: {sucessos}/{total_testes} ({sucessos*100//total_testes}%)")
    print(f"🎯 Corretos: {corretos}/{total_testes} ({corretos*100//total_testes}%)")
    print(f"❌ Falhas: {falhas}/{total_testes}")
    print(f"🕐 Término: {datetime.now().strftime('%H:%M:%S')}\n")
    
    if corretos == total_testes:
        print("🎉 PERFEITO! Todos os testes passaram com sucesso!")
    elif corretos >= total_testes * 0.9:
        print("✅ Excelente! Mais de 90% de acerto!")
    elif corretos >= total_testes * 0.8:
        print("👍 Bom! Mais de 80% de acerto!")
    else:
        print("⚠️ Precisa melhorias - menos de 80% de acerto")


if __name__ == "__main__":
    main()
