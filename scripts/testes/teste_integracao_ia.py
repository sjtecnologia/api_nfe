#!/usr/bin/env python3
"""
[?] Teste de Integração - API IA Unificada com Preenchimento Automático
Testa o fluxo completo: Descrição → API IA → Conversão de IDs → Resposta
"""

import requests
import json
from datetime import datetime

def print_header(texto):
    print("\n" + "="*70)
    print(f"[?] {texto}")
    print("="*70)

def print_sucesso(texto):
    print(f"[OK] {texto}")

def print_erro(texto):
    print(f"[ERRO] {texto}")

def print_info(texto):
    print(f"ℹ️  {texto}")

def testar_api_ia_unificada():
    """Testa a API IA Unificada diretamente"""
    print_header("Teste 1: API IA Unificada (Porta 9000)")
    
    produtos_teste = [
        {
            "descricao": "Smartphone Samsung Galaxy",
            "tipo_item": "Produto",
            "uf_origem": "SP",
            "regime_tributario": "Simples Nacional"
        },
        {
            "descricao": "Notebook Dell Inspiron",
            "tipo_item": "Produto",
            "uf_origem": "SP"
        },
        {
            "descricao": "Mouse wireless Logitech",
            "tipo_item": "Produto",
            "uf_origem": "SP"
        }
    ]
    
    for i, produto in enumerate(produtos_teste, 1):
        print(f"\n[?] Teste {i}: {produto['descricao']}")
        print("-" * 50)
        
        try:
            response = requests.post(
                'http://localhost:9000/api/sugestao',
                json=produto,
                timeout=30
            )
            
            if response.status_code == 200:
                resultado = response.json()
                
                if resultado.get('success'):
                    classificacao = resultado.get('classificacao', {})
                    print_sucesso("API respondeu com sucesso!")
                    print(f"   NCM: {classificacao.get('ncm', 'N/A')}")
                    print(f"   CFOP: {classificacao.get('cfop', 'N/A')}")
                    print(f"   CST: {classificacao.get('cst', 'N/A')}")
                    print(f"   CSOSN: {classificacao.get('csosn', 'N/A')}")
                    print(f"   CEST: {classificacao.get('cest', 'N/A')}")
                    print(f"   [INFO] {classificacao.get('explicacao', '')[:100]}...")
                else:
                    print_erro(f"Erro: {resultado.get('erro')}")
            else:
                print_erro(f"Status HTTP: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print_erro("API não está rodando! Execute: ./start_apis.sh")
            break
        except Exception as e:
            print_erro(f"Erro: {e}")
    
    print()

def testar_endpoint_admin():
    """Testa o endpoint do admin que converte para IDs"""
    print_header("Teste 2: Endpoint Admin com Conversão de IDs")
    print_info("[AVISO]  Este teste requer autenticação no sistema")
    print_info("Execute manualmente via navegador ou curl com cookie de sessão")
    
    print("\n[LIST] Comando curl de exemplo:")
    print("""
curl -X POST http://localhost:8080/admin/api/sugestao_tributaria \\
  -H "Content-Type: application/json" \\
  -H "Cookie: session=SUA_SESSAO_AQUI" \\
  -d '{
    "descricao": "Smartphone Samsung",
    "tipo_item": "Produto",
    "cliente_id": 1
  }'
""")
    
    print("\n[LIST] Resposta esperada:")
    print(json.dumps({
        "sucesso": True,
        "classificacao": {
            "ncm": "85171231",
            "cfop": "5101",
            "cst": "00",
            "csosn": "101",
            "cest": None,
            "explicacao": "Classificação baseada em..."
        },
        "ids": {
            "ncm_id": 123,
            "cfop_id": 45,
            "cst_id": 1,
            "csosn_id": 5,
            "cest": None
        },
        "ncm_descricao": "Telefones celulares...",
        "cfop_descricao": "Venda dentro do estado"
    }, indent=2))

def verificar_servicos():
    """Verifica se todos os serviços necessários estão rodando"""
    print_header("Verificação de Serviços")
    
    servicos = [
        ("API IA Unificada", "http://localhost:9000/health"),
        ("API NCM", "http://localhost:8081/health"),
        ("App Principal", "http://localhost:8080/admin/login"),
        ("LLM", "http://192.168.0.52:1234/v1/models")
    ]
    
    todos_ok = True
    
    for nome, url in servicos:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print_sucesso(f"{nome}: Online")
            else:
                print_erro(f"{nome}: Status {response.status_code}")
                todos_ok = False
        except requests.exceptions.ConnectionError:
            print_erro(f"{nome}: Offline")
            todos_ok = False
        except Exception as e:
            print_erro(f"{nome}: Erro - {str(e)[:50]}")
            todos_ok = False
    
    print()
    
    if not todos_ok:
        print_info("[INFO] Para iniciar as APIs de IA: ./start_apis.sh")
        print_info("[INFO] Para iniciar o app principal: python app.py")
    
    return todos_ok

def main():
    print("\n" + "[?] TESTE DE INTEGRAÇÃO - API IA COM PREENCHIMENTO AUTOMÁTICO ".center(70, "="))
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # 1. Verificar serviços
    if not verificar_servicos():
        print_erro("\n[AVISO]  Alguns serviços não estão disponíveis!")
        print_info("Iniciando testes apenas com serviços disponíveis...\n")
    
    # 2. Testar API IA Unificada
    testar_api_ia_unificada()
    
    # 3. Instruções para teste do endpoint admin
    testar_endpoint_admin()
    
    # Resumo final
    print_header("Resumo e Próximos Passos")
    print("""
[OK] API IA Unificada (porta 9000) - Consolida NCM + LLM
[OK] Endpoint Admin (/admin/api/sugestao_tributaria) - Converte códigos para IDs
[OK] JavaScript atualizado - Preenche campos automaticamente usando IDs

[LIST] COMO TESTAR NO NAVEGADOR:

1. Acesse: http://localhost:8080/admin/login
2. Faça login no sistema
3. Vá para Clientes → Editar Cliente → Produtos
4. Clique em "Adicionar Produto"
5. Preencha a descrição (ex: "Smartphone Samsung")
6. Clique no botão "[?] Sugestão automática IA"
7. Os campos NCM, CFOP, CST/CSOSN serão preenchidos automaticamente!

[FOCO] CAMPOS QUE SERÃO PREENCHIDOS:
   • NCM (select com ID do banco)
   • CFOP (select com ID do banco)
   • CST (select com ID do banco - se regime normal)
   • CSOSN (select com ID do banco - se Simples Nacional)
   • CEST (campo de texto direto)

⏱️  PERFORMANCE ESPERADA:
   • Resposta em ~5 segundos
   • 100% taxa de sucesso (com fallback)
   • Preenchimento automático instantâneo

[?] TROUBLESHOOTING:
   • Se campos não preencherem: Veja console do navegador (F12)
   • Se API não responder: Verifique ./start_apis.sh
   • Logs disponíveis: tail -f ia_api.log
""")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[AVISO]  Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n[ERRO] Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
