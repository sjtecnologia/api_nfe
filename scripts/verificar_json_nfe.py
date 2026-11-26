"""
Verificar estrutura do JSON das notas
"""
from database.connection import get_db
from sqlalchemy import text
import json

def verificar_json():
    """Verifica estrutura do JSON"""
    db = next(get_db())
    
    result = db.execute(text("""
        SELECT 
            numero,
            valor_total,
            json_nfe
        FROM nfe_emitidas
        WHERE cliente_id = 11 
        AND UPPER(status) = 'AUTORIZADA'
        AND json_nfe IS NOT NULL
        LIMIT 1
    """)).fetchone()
    
    if result:
        print(f"\n{'='*80}")
        print(f"NFe {result.numero} - R$ {result.valor_total}")
        print(f"{'='*80}\n")
        
        if result.json_nfe:
            dados = result.json_nfe
            print("Estrutura do JSON:")
            print(json.dumps(dados, indent=2, ensure_ascii=False)[:3000])
            
            # Verificar se tem os dados de impostos
            if 'NFe' in dados:
                nfe = dados['NFe']
                if 'infNFe' in nfe:
                    infnfe = nfe['infNFe']
                    if 'total' in infnfe:
                        total = infnfe['total']
                        print(f"\n\n🔍 Seção 'total' encontrada:")
                        print(json.dumps(total, indent=2, ensure_ascii=False))
                    else:
                        print("\n❌ Não encontrou seção 'total' em infNFe")
                        print(f"Chaves disponíveis em infNFe: {list(infnfe.keys())}")
                else:
                    print("\n❌ Não encontrou 'infNFe' em NFe")
                    print(f"Chaves disponíveis em NFe: {list(nfe.keys())}")
            else:
                print("\n❌ Não encontrou 'NFe' no JSON")
                print(f"Chaves principais: {list(dados.keys())}")
        else:
            print("JSON é NULL")
    else:
        print("Nenhuma nota encontrada")

if __name__ == "__main__":
    verificar_json()
