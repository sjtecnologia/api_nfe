#!/usr/bin/env python3
"""
Teste de sugestão tributária com CEST
Testa a integração completa da API IA com sugestão automática de CEST
"""

import requests
import json

API_URL = "http://localhost:9000/api/sugestao"

# Produtos de teste (mix de produtos COM e SEM Substituição Tributária)
PRODUTOS_TESTE = [
    # Produtos COM ST (devem ter CEST)
    {
        "descricao": "Cerveja Heineken Long Neck 330ml",
        "tipo_item": "Produto",
        "uf_origem": "SP",
        "espera_cest": True,
        "segmento_esperado": "03"  # Cervejas
    },
    {
        "descricao": "Gasolina comum",
        "tipo_item": "Produto", 
        "uf_origem": "SP",
        "espera_cest": True,
        "segmento_esperado": "01"  # Combustíveis
    },
    {
        "descricao": "Pneu Pirelli 175/70 R13",
        "tipo_item": "Produto",
        "uf_origem": "SP", 
        "espera_cest": True,
        "segmento_esperado": "10"  # Autopeças
    },
    {
        "descricao": "Shampoo Pantene 400ml",
        "tipo_item": "Produto",
        "uf_origem": "SP",
        "espera_cest": True,
        "segmento_esperado": "17"  # Higiene pessoal
    },
    {
        "descricao": "Detergente Ypê 500ml",
        "tipo_item": "Produto",
        "uf_origem": "SP",
        "espera_cest": True,
        "segmento_esperado": "20"  # Limpeza
    },
    {
        "descricao": "Lâmpada LED Philips 9W",
        "tipo_item": "Produto",
        "uf_origem": "SP",
        "espera_cest": True,
        "segmento_esperado": "28"  # Materiais elétricos
    },
    
    # Produtos SEM ST (NÃO devem ter CEST)
    {
        "descricao": "Notebook Dell Inspiron 15",
        "tipo_item": "Produto",
        "uf_origem": "SP",
        "espera_cest": False
    },
    {
        "descricao": "Mouse USB sem fio",
        "tipo_item": "Produto",
        "uf_origem": "SP",
        "espera_cest": False
    },
    {
        "descricao": "Desenvolvimento de sistema de computador personalizado",
        "tipo_item": "Serviço",
        "uf_origem": "SP",
        "espera_cest": False
    },
    {
        "descricao": "Café torrado em grãos 500g",
        "tipo_item": "Produto",
        "uf_origem": "SP",
        "espera_cest": False
    }
]


def testar_sugestao(produto):
    """Testa sugestão para um produto"""
    print(f"\n{'=' * 80}")
    print(f"PRODUTO: {produto['descricao']}")
    print(f"{'=' * 80}")
    
    try:
        response = requests.post(API_URL, json=produto, timeout=15)
        
        if response.status_code == 200:
            response_data = response.json()
            resultado = response_data.get('classificacao', {})
            
            # Exibir resultado
            print(f"\n✅ Sugestão recebida:")
            print(f"   NCM: {resultado.get('ncm', 'N/A')}")
            print(f"   CFOP: {resultado.get('cfop', 'N/A')}")
            print(f"   CST: {resultado.get('cst', 'N/A')}")
            print(f"   CSOSN: {resultado.get('csosn', 'N/A')}")
            print(f"   CEST: {resultado.get('cest', 'N/A')}")
            
            if resultado.get('cest_fonte'):
                print(f"   Fonte CEST: {resultado.get('cest_fonte')}")
            
            # Validação
            tem_cest = resultado.get('cest') and resultado.get('cest') not in [None, 'null', 'N/A']
            
            if produto.get('espera_cest'):
                if tem_cest:
                    # Verificar segmento se especificado
                    if produto.get('segmento_esperado'):
                        segmento_cest = resultado.get('cest', '')[:2]
                        if segmento_cest == produto['segmento_esperado']:
                            print(f"\n   ✅ CEST CORRETO! Segmento: {segmento_cest}")
                        else:
                            print(f"\n   ⚠️ CEST com segmento diferente do esperado")
                            print(f"      Esperado: {produto['segmento_esperado']}, Recebido: {segmento_cest}")
                    else:
                        print(f"\n   ✅ CEST PRESENTE (produto sujeito a ST)")
                else:
                    print(f"\n   ❌ ERRO: Produto deveria ter CEST (ST) mas não foi sugerido!")
            else:
                if tem_cest:
                    print(f"\n   ⚠️ AVISO: Produto NÃO sujeito a ST mas CEST foi sugerido")
                else:
                    print(f"\n   ✅ CORRETO: Produto sem ST, CEST não aplicável")
            
            # Explicação
            if resultado.get('explicacao'):
                print(f"\n   📝 Explicação: {resultado.get('explicacao')[:150]}...")
            
            return True
            
        else:
            print(f"\n❌ Erro HTTP: {response.status_code}")
            print(f"   {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Erro na requisição: {e}")
        return False


def main():
    print("=" * 80)
    print("🧪 TESTE DE SUGESTÃO TRIBUTÁRIA COM CEST")
    print("=" * 80)
    print(f"API: {API_URL}")
    print(f"Total de testes: {len(PRODUTOS_TESTE)}")
    
    # Verificar API
    try:
        response = requests.get("http://localhost:9000/health", timeout=5)
        if response.status_code != 200:
            print("\n❌ API não está respondendo!")
            return
    except:
        print("\n❌ Não foi possível conectar à API!")
        print("   Execute: ./start_apis.sh")
        return
    
    print("✅ API respondendo\n")
    
    # Executar testes
    sucessos = 0
    falhas = 0
    
    for produto in PRODUTOS_TESTE:
        if testar_sugestao(produto):
            sucessos += 1
        else:
            falhas += 1
    
    # Resumo
    print(f"\n{'=' * 80}")
    print(f"RESUMO DOS TESTES")
    print(f"{'=' * 80}")
    print(f"✅ Sucessos: {sucessos}/{len(PRODUTOS_TESTE)}")
    print(f"❌ Falhas: {falhas}/{len(PRODUTOS_TESTE)}")
    
    if falhas == 0:
        print(f"\n🎉 Todos os testes passaram!")
    else:
        print(f"\n⚠️ Alguns testes falharam")


if __name__ == "__main__":
    main()
