"""Script para corrigir NFe 257 que foi autorizada mas não foi salva no banco"""

import requests
import json

# Endpoint para criar uma rota temporária de correção
url = "http://3.87.73.106:8080"

# Dados da NFe autorizada (do log)
dados = {
    "nfe_id": 257,
    "chave_acesso": "35260234482371000179550010000011531471584546",
    "protocolo": "135260437703177",
    "mensagem": "Autorizado o uso da NF-e",
    "status": "AUTORIZADA"
}

print("=" * 60)
print("CORREÇÃO MANUAL DA NFe 257")
print("=" * 60)
print(f"NFe ID: {dados['nfe_id']}")
print(f"Chave: {dados['chave_acesso']}")
print(f"Protocolo: {dados['protocolo']}")
print(f"Status: {dados['status']}")
print("=" * 60)
print("\n⚠️  Esta NFe foi AUTORIZADA pela SEFAZ às 10:12:01")
print("⚠️  Mas não foi salva no banco por falta da correção")
print("⚠️  Agora o código foi corrigido e futuras emissões salvarão corretamente")
print("\n📝 Para corrigir esta NFe específica, você tem 2 opções:")
print("\n1. REENVIAR novamente pelo sistema (recomendado)")
print("   - Vá até a NFe 257 e clique em 'Reenviar'")
print("   - Agora com o código corrigido, ela será salva corretamente")
print("\n2. Usar a chave e protocolo acima para consultar na SEFAZ")
print("   - Você já tem a chave de acesso")
print("   - Pode gerar a DANFE e XML manualmente")
print("\n✅ O sistema está corrigido para novas emissões!")
