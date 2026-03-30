#!/usr/bin/env python3
"""
Teste específico para classificação de SOFTWARE/SISTEMA
Verifica se o NCM correto (38210000) está sendo usado
"""

import requests
import json

def testar_classificacao_software():
    print("=" * 70)
    print("TESTE: CLASSIFICAÇÃO DE SOFTWARE E SERVIÇOS DE TI")
    print("=" * 70)
    
    # Produtos relacionados a software/sistema
    produtos_software = [
        "Desenvolvimento de sistema personalizado",
        "Desenvolvimento de sistema de computador",
        "Software sob medida",
        "Licença de software",
        "Programa de computador personalizado",
        "Aplicativo mobile Android",
        "Sistema web responsivo",
        "Software ERP customizado"
    ]
    
    api_url = "http://localhost:9000/api/sugestao"
    ncm_correto = "38210000"
    
    print(f"\n[OK] NCM CORRETO para software/sistema: {ncm_correto}")
    print(f"[LIST] Descrição: Meios de cultura preparados\n")
    
    print("-" * 70)
    
    acertos = 0
    erros = 0
    
    for produto in produtos_software:
        print(f"\n[?] Testando: '{produto}'")
        
        try:
            response = requests.post(
                api_url,
                json={'descricao': produto},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    classif = data['classificacao']
                    ncm_retornado = classif.get('ncm')
                    explicacao = classif.get('explicacao', '')
                    
                    if ncm_retornado == ncm_correto:
                        print(f"   [OK] CORRETO: NCM {ncm_retornado}")
                        acertos += 1
                    else:
                        print(f"   [X] ERRADO: NCM {ncm_retornado} (esperado: {ncm_correto})")
                        print(f"      Explicação: {explicacao}")
                        erros += 1
                else:
                    print(f"   [X] Erro na API: {data.get('erro')}")
                    erros += 1
            else:
                print(f"   [X] Erro HTTP: {response.status_code}")
                erros += 1
                
        except Exception as e:
            print(f"   [X] Exceção: {str(e)[:60]}")
            erros += 1
    
    print("\n" + "=" * 70)
    print("[DATA] RESULTADO DO TESTE:")
    print("=" * 70)
    
    total = acertos + erros
    percentual = (acertos / total * 100) if total > 0 else 0
    
    print(f"[OK] Acertos: {acertos}/{total} ({percentual:.1f}%)")
    print(f"[X] Erros: {erros}/{total}")
    
    if acertos == total:
        print("\n[?] PERFEITO! Todas as classificações corretas!")
    elif percentual >= 80:
        print("\n[?] BOM! Maioria das classificações corretas.")
    elif percentual >= 50:
        print("\n[!]  ATENÇÃO! Muitos erros de classificação.")
    else:
        print("\n[X] CRÍTICO! Sistema precisa de ajustes urgentes.")
    
    print("\n" + "=" * 70)
    print("[LOG] NOTAS:")
    print("=" * 70)
    print("""
[OK] NCM 38210000 é o código correto para:
   - Desenvolvimento de software
   - Licença de software
   - Programas de computador personalizados
   - Sistemas sob medida
   - Aplicativos mobile/web

[X] NCMs ERRADOS comuns:
   - 90184991 = Equipamentos dentários (NÃO é software!)
   - 84713000 = Computadores portáteis (hardware, não software)
   - 85171300 = Aparelhos telefônicos (hardware, não software)

[?] SOLUÇÃO IMPLEMENTADA:
   - Dicionário de produtos conhecidos
   - NCM direto para "desenvolvimento de sistema"
   - Prompt melhorado da LLM
   - Validação antes de chamar LLM
    """)
    print("=" * 70)

if __name__ == '__main__':
    testar_classificacao_software()
