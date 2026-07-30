"""
Script de diagnóstico para identificar erros no servidor Windows
Executar: python diagnostico_servidor.py
"""

import sys
import os

print("=" * 80)
print("DIAGNÓSTICO DO SERVIDOR - NFe App")
print("=" * 80)

# Teste 1: Imports básicos
print("\n1️⃣ Testando imports básicos...")
try:
    from services.danfe_service import generate_danfe
    print("   [OK] services.danfe_service OK")
except Exception as e:
    print(f"   [X] ERRO: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from routes.nfe_routes import nfe_bp
    print("   [OK] routes.nfe_routes OK")
except Exception as e:
    print(f"   [X] ERRO: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Teste 2: Dependências do DANFE
print("\n2️⃣ Testando dependências do DANFE...")
engines_instaladas = []

try:
    import brazilnum
    print("   [OK] brazilnum instalado")
    engines_instaladas.append("brazilnum")
except:
    print("   [X] brazilnum NÃO instalado")

try:
    import BrazilFiscalReport
    print("   [OK] BrazilFiscalReport instalado")
    engines_instaladas.append("BrazilFiscalReport")
except:
    print("   [X] BrazilFiscalReport NÃO instalado")

try:
    import erpbrasil.edoc.pdf
    print("   [OK] erpbrasil.edoc.pdf instalado")
    engines_instaladas.append("erpbrasil.edoc.pdf")
except:
    print("   [X] erpbrasil.edoc.pdf NÃO instalado")

try:
    from brazilfiscalreport.danfe import DanfeConfig
    print("   [OK] DanfeConfig disponível")
    engines_instaladas.append("DanfeConfig")
except Exception as e:
    print(f"   [!] DanfeConfig não disponível: {e}")

# Teste 3: Banco de dados
print("\n3️⃣ Testando conexão com banco de dados...")
try:
    from database.connection import get_db_connection
    from sqlalchemy import text
    db = get_db_connection()
    
    # Verificar se coluna logo_path existe
    result = db.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'clientes' 
        AND column_name = 'logo_path'
    """)).fetchone()
    
    if result:
        print("   [OK] Coluna logo_path existe na tabela clientes")
        
        # Contar clientes com logo
        count = db.execute(text("SELECT COUNT(*) FROM clientes WHERE logo_path IS NOT NULL")).fetchone()
        print(f"   [DATA] {count[0]} cliente(s) com logo cadastrada")
    else:
        print("   [X] Coluna logo_path NÃO EXISTE")
        print("   [?] Execute: psql -U postgres -d nfe_db -f adicionar_campo_logo_cliente.sql")
    
    db.close()
    print("   [OK] Conexão com banco OK")
    
except Exception as e:
    print(f"   [X] ERRO no banco: {e}")
    import traceback
    traceback.print_exc()

# Teste 4: Estrutura de diretórios
print("\n4️⃣ Testando estrutura de diretórios...")

diretorios = [
    'static',
    'static/logos',
    'static/img',
    'static/danfe'
]

for dir_path in diretorios:
    if os.path.exists(dir_path):
        print(f"   [OK] {dir_path} existe")
        # Contar arquivos
        try:
            files = os.listdir(dir_path)
            print(f"      [?] {len(files)} arquivo(s)")
        except:
            pass
    else:
        print(f"   [X] {dir_path} NÃO EXISTE")
        print(f"      [?] Criar com: mkdir {dir_path}")

# Teste 5: Testar geração de DANFE com XML de exemplo
print("\n5️⃣ Testando geração de DANFE...")

xml_exemplo = """<?xml version="1.0" encoding="utf-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe xmlns="http://www.portalfiscal.inf.br/nfe">
    <infNFe Id="NFe12345678901234567890123456789012345678901234" versao="4.00">
      <ide>
        <cUF>35</cUF>
        <cNF>12345678</cNF>
        <natOp>VENDA</natOp>
        <mod>55</mod>
        <serie>1</serie>
        <nNF>1</nNF>
        <dhEmi>2025-12-02T10:00:00-03:00</dhEmi>
        <tpNF>1</tpNF>
        <idDest>1</idDest>
        <cMunFG>3550308</cMunFG>
        <tpImp>1</tpImp>
        <tpEmis>1</tpEmis>
        <cDV>0</cDV>
        <tpAmb>2</tpAmb>
        <finNFe>1</finNFe>
        <indFinal>1</indFinal>
        <indPres>1</indPres>
        <procEmi>0</procEmi>
        <verProc>1.0</verProc>
      </ide>
      <emit>
        <CNPJ>12345678000190</CNPJ>
        <xNome>EMPRESA TESTE</xNome>
        <xFant>TESTE</xFant>
        <enderEmit>
          <xLgr>RUA TESTE</xLgr>
          <nro>123</nro>
          <xBairro>CENTRO</xBairro>
          <cMun>3550308</cMun>
          <xMun>SAO PAULO</xMun>
          <UF>SP</UF>
          <CEP>01000000</CEP>
          <cPais>1058</cPais>
          <xPais>BRASIL</xPais>
        </enderEmit>
        <IE>123456789012</IE>
        <CRT>1</CRT>
      </emit>
      <dest>
        <CNPJ>98765432000199</CNPJ>
        <xNome>CLIENTE TESTE</xNome>
        <enderDest>
          <xLgr>RUA CLIENTE</xLgr>
          <nro>456</nro>
          <xBairro>CENTRO</xBairro>
          <cMun>3550308</cMun>
          <xMun>SAO PAULO</xMun>
          <UF>SP</UF>
          <CEP>02000000</CEP>
          <cPais>1058</cPais>
          <xPais>BRASIL</xPais>
        </enderDest>
        <indIEDest>1</indIEDest>
        <IE>987654321098</IE>
      </dest>
      <det nItem="1">
        <prod>
          <cProd>001</cProd>
          <cEAN></cEAN>
          <xProd>PRODUTO TESTE</xProd>
          <NCM>12345678</NCM>
          <CFOP>5102</CFOP>
          <uCom>UN</uCom>
          <qCom>1.0000</qCom>
          <vUnCom>100.00</vUnCom>
          <vProd>100.00</vProd>
          <cEANTrib></cEANTrib>
          <uTrib>UN</uTrib>
          <qTrib>1.0000</qTrib>
          <vUnTrib>100.00</vUnTrib>
          <indTot>1</indTot>
        </prod>
        <imposto>
          <ICMS>
            <ICMS00>
              <orig>0</orig>
              <CST>00</CST>
              <modBC>0</modBC>
              <vBC>100.00</vBC>
              <pICMS>18.00</pICMS>
              <vICMS>18.00</vICMS>
            </ICMS00>
          </ICMS>
        </imposto>
      </det>
      <total>
        <ICMSTot>
          <vBC>100.00</vBC>
          <vICMS>18.00</vICMS>
          <vICMSDeson>0.00</vICMSDeson>
          <vFCP>0.00</vFCP>
          <vBCST>0.00</vBCST>
          <vST>0.00</vST>
          <vFCPST>0.00</vFCPST>
          <vFCPSTRet>0.00</vFCPSTRet>
          <vProd>100.00</vProd>
          <vFrete>0.00</vFrete>
          <vSeg>0.00</vSeg>
          <vDesc>0.00</vDesc>
          <vII>0.00</vII>
          <vIPI>0.00</vIPI>
          <vIPIDevol>0.00</vIPIDevol>
          <vPIS>0.00</vPIS>
          <vCOFINS>0.00</vCOFINS>
          <vOutro>0.00</vOutro>
          <vNF>100.00</vNF>
        </ICMSTot>
      </total>
      <transp>
        <modFrete>9</modFrete>
      </transp>
    </infNFe>
  </NFe>
  <protNFe versao="4.00">
    <infProt>
      <tpAmb>2</tpAmb>
      <verAplic>SVRS202401</verAplic>
      <chNFe>12345678901234567890123456789012345678901234</chNFe>
      <dhRecbto>2025-12-02T10:00:00-03:00</dhRecbto>
      <nProt>123456789012345</nProt>
      <digVal>ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890123=</digVal>
      <cStat>100</cStat>
      <xMotivo>Autorizado o uso da NF-e</xMotivo>
    </infProt>
  </protNFe>
</nfeProc>"""

try:
    print("   [?] Tentando gerar DANFE de teste...")
    from services.danfe_service import generate_danfe
    pdf_path = generate_danfe(xml_exemplo, 999999, None)
    
    if pdf_path and os.path.exists(pdf_path):
        print(f"   [OK] DANFE gerado com sucesso: {pdf_path}")
        file_size = os.path.getsize(pdf_path)
        print(f"   [DATA] Tamanho: {file_size} bytes")
    else:
        print(f"   [!] DANFE retornou: {pdf_path}")
        
except Exception as e:
    print(f"   [X] ERRO ao gerar DANFE: {e}")
    import traceback
    traceback.print_exc()

# Resumo
print("\n" + "=" * 80)
print("RESUMO DO DIAGNÓSTICO")
print("=" * 80)
print(f"Engines instaladas: {len(engines_instaladas)}/4")
if len(engines_instaladas) < 3:
    print("[!] ATENÇÃO: Instale as engines faltantes!")
    print("   pip install brazilnum BrazilFiscalReport erpbrasil.edoc.pdf")

print("\n[?] PRÓXIMOS PASSOS:")
print("   1. Se houver erros de import: Reinicie o serviço")
print("   2. Se logo_path não existe: Execute a migration SQL")
print("   3. Se diretórios não existem: Crie-os manualmente")
print("   4. Se engines faltam: Instale com pip")
print("=" * 80)
