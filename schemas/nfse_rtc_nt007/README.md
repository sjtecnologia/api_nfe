# Schemas XSD - NFS-e RTC NT007 v1.03.00

## 📋 Instruções para Download

Os schemas XSD oficiais da Nota Técnica 007 devem ser baixados do portal oficial da Receita Federal.

### 🔗 Link para Download

**Portal NFS-e Gov.br:**
https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/rtc

**Procurar por:**
- "Esquemas XSD - AnexoVI-LeiautesRN_RTC_IBSCBS-V1.03.00 - NT007"

### 📦 Arquivos Esperados

Após o download e extração, este diretório deve conter:

```
schemas/nfse_rtc_nt007/
├── README.md (este arquivo)
├── nfse_v1.03.00.xsd
├── tipos_v1.03.00.xsd
├── cabecalho_v1.03.00.xsd
├── ibscbs_v1.03.00.xsd
└── xmldsig-core-schema.xsd
```

### ⚠️ Importante

- Os arquivos XSD não estão incluídos no repositório devido a direitos autorais
- Devem ser baixados diretamente da fonte oficial
- Manter sempre a versão mais recente

### 🧪 Validação

Após baixar os schemas, execute o script de validação:

```bash
cd /Users/renato/Documents/Developement/api_nfe
python3 schemas/nfse_rtc_nt007/validar_xml_com_xsd.py test_nfse_nt007_output.xml
```

### 📅 Última Atualização

- **Data:** 09/02/2026
- **Versão NT:** 007
- **Versão Layout:** 1.03.00
- **Versão AnexoVII:** 1.01.00
