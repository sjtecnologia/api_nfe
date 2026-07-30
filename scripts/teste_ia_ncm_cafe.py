#!/usr/bin/env python3
from ai_ncm.predicao.motor_ia_ncm import MotorIANCM

print("=" * 70)
print("TESTE DE CLASSIFICAÇÃO IA - NCM CAFÉ TORRADO")
print("=" * 70)

motor = MotorIANCM()
resultado = motor.sugerir_ncm("café torrado", "Café em grão torrado não descafeinado")

ncm = resultado.get("ncm_sugerido", {})
print(f"\n✅ NCM SUGERIDO: {ncm.get('codigo')}")
print(f"📝 Descrição: {ncm.get('descricao', '')}")
print(f"💯 Confiança: {ncm.get('confianca'):.2%}")

print("\n🔍 Top 5 Alternativas:")
for i, alt in enumerate(resultado.get("alternativas", [])[:5], 1):
    codigo = alt.get('codigo', 'N/A')
    descricao = alt.get('descricao', 'N/A')[:60]
    confianca = alt.get('confianca', 0)
    print(f"  {i}. {codigo:12} - {descricao:60} ({confianca:.2%})")

print("\n" + "=" * 70)
