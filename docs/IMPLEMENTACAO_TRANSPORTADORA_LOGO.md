# Implementação de Campos de Transportadora e Logo do Cliente

## 📋 Resumo das Alterações

### 1. ✅ Campos Faltantes de Transportadora

**Problema identificado:** O DANFE oficial da SEFAZ possui campos que não existiam no formulário de emissão:
- RNTC (Registro Nacional de Transportador de Carga - ANTT)
- Marca dos volumes
- Numeração dos volumes

**Arquivos modificados:**

#### `templates/admin/nfes/emitir.html`
- ✅ Adicionado campo `transportadoraANTT` (RNTC/ANTT) - max 20 caracteres
- ✅ Adicionado campo `volumeMarca` - max 60 caracteres
- ✅ Adicionado campo `volumeNumeracao` - max 60 caracteres

#### `routes/nfe_routes.py`
- ✅ Captura de `transportadoraANTT` no `form_data_initial`
- ✅ Captura de `volumeMarca` no `form_data_initial`
- ✅ Captura de `volumeNumeracao` no `form_data_initial`

#### `services/nfe_service.py`
- ✅ Geração da tag `<RNTC>` no XML (dentro de `<transp>`)
- ✅ Geração da tag `<marca>` no XML (dentro de `<vol>`)
- ✅ Geração da tag `<nVol>` no XML (dentro de `<vol>`)

**Estrutura XML gerada:**
```xml
<transp>
    <modFrete>0</modFrete>
    <transporta>
        <CNPJ>12345678000190</CNPJ>
        <xNome>Transportadora ABC</xNome>
        <IE>123456789</IE>
        <xEnder>Rua XYZ, 100</xEnder>
        <xMun>São Paulo</xMun>
        <UF>SP</UF>
    </transporta>
    <RNTC>12345678</RNTC>  <!-- NOVO -->
    <veicTransp>
        <placa>ABC1234</placa>
        <UF>SP</UF>
    </veicTransp>
    <vol>
        <qVol>10</qVol>
        <esp>Caixa</esp>
        <marca>Marca XYZ</marca>  <!-- NOVO -->
        <nVol>001-010</nVol>      <!-- NOVO -->
        <pesoB>100.500</pesoB>
        <pesoL>95.300</pesoL>
    </vol>
</transp>
```

---

### 2. ✅ Sistema de Logo do Cliente

**Funcionalidade:** Cada cliente pode ter sua própria logo que será exibida no DANFE (PDF da NFe).

#### Banco de Dados

**Arquivo:** `adicionar_campo_logo_cliente.sql`
```sql
ALTER TABLE clientes 
ADD COLUMN IF NOT EXISTS logo_path VARCHAR(255) DEFAULT NULL;
```

**Executar:**
```bash
psql -U postgres -d nome_do_banco -f adicionar_campo_logo_cliente.sql
```

#### Modelo SQLAlchemy

**Arquivo:** `database/models.py`
```python
class Cliente(Base):
    # ... campos existentes ...
    logo_path = Column(String(255), nullable=True)  # ✅ NOVO
```

#### Formulário de Cliente

**Arquivo:** `templates/admin/clientes/form.html`
- ✅ Adicionado campo de upload `<input type="file" name="logo_file" accept="image/png,image/jpeg,image/jpg,image/gif">`
- ✅ Preview da logo atual (se existir)
- ✅ Suporte para PNG, JPG, JPEG e GIF
- ✅ Tamanho recomendado: 300x100 pixels

#### Rotas de Cliente

**Arquivo:** `routes/admin_routes.py`

**`create_cliente()`:**
- ✅ Processa upload da logo
- ✅ Valida formato (PNG, JPG, GIF)
- ✅ Gera nome único: `cliente_{timestamp}.ext`
- ✅ Salva em `static/logos/`
- ✅ Armazena caminho relativo no banco: `logos/cliente_1234567890.png`

**`edit_cliente()`:**
- ✅ Permite substituir logo existente
- ✅ Remove logo antiga automaticamente
- ✅ Mantém logo atual se não houver novo upload

#### Geração de DANFE

**Arquivo:** `services/danfe_service.py`

**Função `generate_danfe()` modificada:**
```python
def generate_danfe(xml_content, nfe_id, cliente_id=None):
    # 1. Buscar logo do cliente no banco (PRIORIDADE)
    if cliente_id:
        result = db.execute("SELECT logo_path FROM clientes WHERE cliente_id = :cid", {'cid': cliente_id})
        if result and result[0]:
            logo_path = os.path.join('static', result[0])
    
    # 2. Fallback para logo padrão (static/img/logo.png)
    if not logo_path:
        logo_path = 'static/img/logo.png'
    
    # 3. Passar logo_path para generate_danfe_nfelib()
    generate_danfe_nfelib(xml_content, output_pdf_path, logo_path)
```

**Arquivo:** `routes/nfe_routes.py`
- ✅ Atualizado para passar `cliente_id` em todas as chamadas de `generate_danfe()`
- ✅ Linha 396: Geração automática após emissão
- ✅ Linha 852: Rota de geração manual
- ✅ Linha 914: Rota de download

---

## 🚀 Como Usar

### Upload de Logo do Cliente

1. Acesse **Admin → Clientes**
2. Clique em **Editar** no cliente desejado
3. Na seção **"Logo do Cliente"**, clique em **"Escolher arquivo"**
4. Selecione uma imagem PNG, JPG ou GIF (recomendado: 300x100px)
5. Clique em **"Salvar"**
6. A logo será exibida automaticamente em todos os DANFEs deste cliente

### Campos de Transportadora na Emissão de NFe

1. Acesse **Emitir NFe**
2. Selecione o cliente
3. Na seção **"Dados de Transporte"**:
   - Escolha a **Modalidade do Frete** (diferente de "9 - Sem frete")
   - Preencha os **Dados da Transportadora**:
     - Razão Social
     - CNPJ/CPF
     - Endereço, Município, UF
     - Inscrição Estadual
     - **🆕 RNTC (ANTT)** - Registro Nacional de Transportador
   - Preencha os **Dados do Veículo**:
     - Placa
     - UF
   - Preencha os **Dados dos Volumes**:
     - Quantidade
     - Espécie (ex: Caixa, Pacote)
     - **🆕 Marca** - Marca dos volumes
     - **🆕 Numeração** - Numeração dos volumes
     - Peso Bruto (Kg)
     - Peso Líquido (Kg)
4. Marque **"Gerar DANFE automaticamente"**
5. Clique em **"Emitir NFe"**
6. O DANFE gerado conterá **todos os dados da transportadora** e a **logo do cliente**

---

## 📁 Estrutura de Arquivos

```
api_nfe/
├── static/
│   ├── logos/                    # ✅ NOVO - Logos dos clientes
│   │   ├── cliente_1733164800.png
│   │   ├── cliente_1733164850.jpg
│   │   └── ...
│   ├── danfe/                    # DANFEs gerados
│   └── img/                      # Logo padrão (fallback)
│       └── logo.png
├── templates/
│   └── admin/
│       ├── clientes/
│       │   └── form.html         # ✅ Campo de upload de logo
│       └── nfes/
│           └── emitir.html       # ✅ Campos ANTT, Marca, Numeração
├── routes/
│   ├── admin_routes.py           # ✅ Upload de logo
│   └── nfe_routes.py             # ✅ Passa cliente_id para DANFE
├── services/
│   ├── danfe_service.py          # ✅ Busca logo do cliente
│   └── nfe_service.py            # ✅ Gera XML com RNTC, marca, nVol
├── database/
│   └── models.py                 # ✅ Campo logo_path
└── adicionar_campo_logo_cliente.sql  # ✅ NOVO - Migração SQL
```

---

## ⚠️ Ações Necessárias

### 1. Executar Migração SQL
```bash
# Windows PowerShell
cd C:\nfe_app
.\venv\Scripts\Activate.ps1
python -c "from database.connection import get_db_connection; db = get_db_connection(); db.execute(open('adicionar_campo_logo_cliente.sql').read()); db.commit(); db.close()"

# Ou via psql
psql -U postgres -d nome_do_banco -f adicionar_campo_logo_cliente.sql
```

### 2. Criar Diretório de Logos
```bash
mkdir static\logos
```

### 3. Reiniciar Serviço
```bash
nssm restart NFe_Backend
```

---

## 🧪 Testes Recomendados

### Teste 1: Upload de Logo
1. Editar cliente
2. Fazer upload de logo PNG (300x100px)
3. Verificar que aparece no formulário
4. Salvar e reabrir - logo deve estar visível

### Teste 2: Campos de Transportadora
1. Emitir NFe em Homologação
2. Modalidade Frete = "0 - Por conta do emitente"
3. Preencher TODOS os campos da transportadora (incluindo ANTT, Marca, Numeração)
4. Gerar DANFE automaticamente
5. Verificar no PDF:
   - Logo do cliente aparece
   - Dados da transportadora completos
   - RNTC/ANTT visível
   - Marca e numeração dos volumes visíveis

### Teste 3: Logo no DANFE
1. Cliente com logo cadastrada
2. Cliente sem logo (deve usar logo padrão)
3. Emitir NFe de cada cliente
4. Verificar que as logos corretas aparecem nos DANFEs

---

## 📝 Notas Técnicas

### Formatos de Imagem Suportados
- PNG (recomendado - suporta transparência)
- JPG/JPEG
- GIF

### Tamanho Recomendado
- Largura: 300px
- Altura: 100px
- Proporção: 3:1
- Tamanho máximo: 5MB (implícito)

### Fallback de Logo
Se o cliente não tiver logo cadastrada, o sistema usa automaticamente:
1. `static/logos/default.png` (se existir)
2. `static/img/logo.png`
3. `static/img/logo_empresa.png`
4. Sem logo (apenas texto)

### Segurança
- Apenas formatos de imagem permitidos
- Nome de arquivo sanitizado com `secure_filename()`
- Nome único gerado com timestamp
- Caminho relativo armazenado no banco (evita path traversal)

---

## ✅ Status da Implementação

| Item | Status |
|------|--------|
| Campos de transportadora no formulário | ✅ Completo |
| Captura de dados no backend | ✅ Completo |
| Geração de XML com novos campos | ✅ Completo |
| Migração SQL para logo | ✅ Completo |
| Modelo Cliente com logo_path | ✅ Completo |
| Formulário de upload de logo | ✅ Completo |
| Upload e armazenamento | ✅ Completo |
| Integração logo no DANFE | ✅ Completo |
| Testes | ⏳ Pendente |

---

## 📞 Suporte

Para dúvidas ou problemas:
1. Verificar logs do serviço: `nssm status NFe_Backend`
2. Verificar arquivo de log: `C:\nfe_app\logs\app.log`
3. Testar em ambiente de Homologação primeiro
4. Verificar permissões da pasta `static/logos`

---

**Data de Implementação:** 02/12/2025
**Versão:** 1.0
