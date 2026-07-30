# 📚 TREINAMENTO IA - TRIBUTAÇÃO NFe, NFCe e NFS-e
## Base de Conhecimento OFICIAL - Governo Federal Brasileiro

**Data de Atualização:** 30/01/2026  
**Fontes Oficiais:**
- Portal NFe (nfe.fazenda.gov.br) - Receita Federal do Brasil
- Portal NFS-e Nacional (gov.br/nfse) - Governo Federal
- Receita Federal (gov.br/receitafederal) - IPI, PIS, COFINS
- Informe Técnico 2025.002 v.1.40 - Publicado 28/01/2026
- Ato Conjunto RFB/CGIBS nº 01/2025 - DOU 23/12/2025
- Lei Complementar 214/2025 (Reforma Tributária)
- Emenda Constitucional 132/2023

---

## 📋 ÍNDICE
1. [CST e CSOSN - Códigos de Situação Tributária](#cst-csosn)
2. [ICMS - Imposto sobre Circulação de Mercadorias e Serviços](#icms)
3. [ISS - Imposto sobre Serviços](#iss)
4. [IPI - Imposto sobre Produtos Industrializados](#ipi)
5. [PIS/COFINS - Contribuições Sociais](#pis-cofins)
6. [Reforma Tributária - IBS, CBS e IS](#reforma-tributaria)
7. [Regras de Validação NFe/NFCe/NFS-e](#validacoes)

---

## 1. CST e CSOSN - CÓDIGOS DE SITUAÇÃO TRIBUTÁRIA {#cst-csosn}

### 1.1 CST ICMS (Código de Situação Tributária) - 3 Dígitos
**Formato:** XYZ onde:
- **X** = Origem da Mercadoria (1 dígito)
- **YZ** = Tributação do ICMS (2 dígitos)

#### **Origem da Mercadoria (1º dígito):**
```
0 - Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8
1 - Estrangeira - Importação direta, exceto a indicada no código 6
2 - Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7
3 - Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% e inferior ou igual a 70%
4 - Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos
5 - Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40%
6 - Estrangeira - Importação direta, sem similar nacional, constante em lista CAMEX/SECEX
7 - Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista CAMEX/SECEX
8 - Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70%
```

#### **Tributação do ICMS (2º e 3º dígitos):**
```
00 - Tributada integralmente
10 - Tributada e com cobrança do ICMS por substituição tributária
20 - Com redução de base de cálculo
30 - Isenta ou não tributada e com cobrança do ICMS por substituição tributária
40 - Isenta
41 - Não tributada
50 - Suspensão
51 - Diferimento
60 - ICMS cobrado anteriormente por substituição tributária
70 - Com redução de base de cálculo e cobrança do ICMS por substituição tributária
90 - Outras
```

**Exemplos Práticos:**
- **000** = Nacional, Tributada integralmente
- **010** = Nacional, Tributada com ICMS-ST
- **020** = Nacional, Com redução de BC
- **040** = Nacional, Isenta
- **100** = Importação direta, Tributada integralmente
- **200** = Importação mercado interno, Tributada integralmente
- **500** = Nacional (Conteúdo importação ≤ 40%), Tributada integralmente

---

### 1.2 CSOSN (Código de Situação Operação Simples Nacional)
**Exclusivo para empresas optantes pelo Simples Nacional**

```
101 - Tributada pelo Simples Nacional com permissão de crédito
102 - Tributada pelo Simples Nacional sem permissão de crédito
103 - Isenção do ICMS no Simples Nacional para faixa de receita bruta
201 - Tributada pelo Simples Nacional com permissão de crédito e com cobrança do ICMS por substituição tributária
202 - Tributada pelo Simples Nacional sem permissão de crédito e com cobrança do ICMS por substituição tributária
203 - Isenção do ICMS no Simples Nacional para faixa de receita bruta e com cobrança do ICMS por substituição tributária
300 - Imune
400 - Não tributada pelo Simples Nacional
500 - ICMS cobrado anteriormente por substituição tributária (substituído) ou por antecipação
900 - Outros
```

**Regra de Crédito (CSOSN 101 e 201):**
- Alíquota aplicável: conforme Anexo I da LC 123/2006
- Cálculo: (Receita Bruta Mês / Receita Bruta 12 meses) × Alíquota Efetiva

---

## 2. ICMS - IMPOSTO SOBRE CIRCULAÇÃO DE MERCADORIAS {#icms}

### 2.1 Alíquotas Internas por Estado (2026)
```
AC  - 19%    |  AL  - 19%    |  AP  - 18%    |  AM  - 20%
BA  - 20.50% |  CE  - 20%    |  DF  - 20%    |  ES  - 17%
GO  - 19%    |  MA  - 22%    |  MT  - 17%    |  MS  - 17%
MG  - 18%    |  PA  - 19%    |  PB  - 20%    |  PR  - 19.50%
PE  - 20.50% |  PI  - 21%    |  RJ  - 20%    |  RN  - 20%
RS  - 17%    |  RO  - 19.50% |  RR  - 17%    |  SC  - 17%
SP  - 18%    |  SE  - 19%    |  TO  - 20%
```

### 2.2 Alíquota Interestadual (Operações entre Estados)
```
Sul/Sudeste → Sul/Sudeste = 12%
Sul/Sudeste → Norte/Nordeste/Centro-Oeste/ES = 7%
Norte/Nordeste/Centro-Oeste → Qualquer região = 12%
Importação (todos os estados) = 4%
```

### 2.3 DIFAL (Diferencial de Alíquota) - EC 87/2015
**Aplicável:** Venda para consumidor final não contribuinte em outro estado

**Cálculo:**
```
DIFAL = (Alíquota Interna Destino - Alíquota Interestadual) × Base de Cálculo

Partilha (2026):
- 100% para o Estado de Destino
- 0% para o Estado de Origem
```

**Campos NFe:**
- `vICMSUFDest` = DIFAL destinado ao estado de destino
- `vICMSUFRemet` = DIFAL devido ao estado de origem (2026 = 0)
- `vFCPUFDest` = Fundo de Combate à Pobreza

---

### 2.4 Substituição Tributária (ICMS-ST)
**Responsabilidade:** Remetente retém ICMS devido nas operações subsequentes

**Cálculo:**
```
Base de Cálculo ST = (Valor Produto + IPI + Frete + Outras Despesas + Seguro) × (1 + MVA)

ICMS-ST = (BC-ST × Alíquota Interna) - ICMS Próprio

Onde:
MVA = Margem de Valor Agregado (varia por NCM/CEST)
```

**NCMs Comuns com ST:**
- 8471.30.12 - Computadores portáteis (notebooks)
- 8517.62.55 - Aparelhos telefônicos (smartphones)
- 2710.12.59 - Gasolina automotiva
- 2203.00.00 - Cervejas de malte

**Campos NFe:**
```xml
<ICMSST>
    <orig>0</orig>
    <CST>10</CST>
    <modBC>3</modBC>
    <vBC>1000.00</vBC>
    <pICMS>18.00</pICMS>
    <vICMS>180.00</vICMS>
    <modBCST>4</modBCST>
    <pMVAST>30.00</pMVAST>
    <vBCST>1300.00</vBCST>
    <pICMSST>18.00</pICMSST>
    <vICMSST>54.00</vICMSST>
</ICMSST>
```

---

## 3. ISS - IMPOSTO SOBRE SERVIÇOS {#iss}

### 3.1 Lista de Serviços LC 116/2003 (Resumo)
```
1.XX   - Serviços de informática e congêneres
2.01   - Serviços de pesquisas e desenvolvimento
3.XX   - Locação, cessão de direito de uso
4.XX   - Medicina, assistência veterinária
5.XX   - Medicina veterinária
6.XX   - Cuidados pessoais, estética, atividades físicas
7.XX   - Engenharia, arquitetura, geologia, urbanismo, construção civil
8.XX   - Educação, ensino, orientação pedagógica
9.XX   - Hospedagem, turismo, viagens
10.XX  - Intermediação e congêneres
11.XX  - Guarda, estacionamento, vigilância, segurança
12.XX  - Diversões, lazer, entretenimento
13.XX  - Fonografia, fotografia, cinematografia, reprografia
14.XX  - Serviços relativos a bens de terceiros
15.XX  - Serviços relacionados ao setor bancário ou financeiro
16.XX  - Transporte de natureza municipal
17.XX  - Serviços de apoio técnico, administrativo, jurídico, contábil
18.01  - Serviços de regulação de sinistros
19.01  - Distribuição e venda de bilhetes de loteria
20.XX  - Serviços portuários, aeroportuários, ferroportuários
21.01  - Serviços de registros públicos, cartorários, notariais
22.01  - Serviços de exploração de rodovia
23.01  - Programação e comunicação visual
24.01  - Chaveiros, confecção de carimbos, placas
25.XX  - Serviços funerários
26.01  - Coleta, remessa, entrega de correspondências
27.01  - Serviços de assistência social
28.01  - Avaliação de bens e serviços
29.01  - Biblioteconomia
30.01  - Biologia, biotecnologia e química
31.01  - Serviços técnicos em edificações
32.01  - Desenhos técnicos
33.01  - Desembaraço aduaneiro
34.01  - Investigações particulares, detetives
35.01  - Reportagem, assessoria de imprensa, jornalismo
36.01  - Meteorologia
37.01  - Artistas, atletas, modelos, manequins
38.01  - Museologia
39.01  - Ourivesaria e lapidação
40.01  - Obras de arte sob encomenda
```

### 3.2 Alíquotas ISS por Município
**Alíquota Mínima:** 2% (LC 116/2003, art. 8º-A)  
**Alíquota Máxima:** 5% (LC 116/2003, art. 8º)

**São José do Rio Preto/SP - Principais Alíquotas:**
```
1.01 a 1.09 (Informática)          = 5%
7.02, 7.05 (Construção Civil)      = 5%
14.01 a 14.14 (Bens de Terceiros)  = 5%
17.XX (Serviços Administrativos)   = 5%
Maioria dos serviços               = 5% (regra geral)
Alguns serviços específicos        = 2% a 3% (conforme legislação municipal)
```

### 3.3 ISS Retido na Fonte
**Obrigação:** Tomador retém ISS quando Lei Municipal determinar

**Casos Comuns:**
- Construção civil (LC 116, item 7.02, 7.05)
- Limpeza e conservação (LC 116, item 7.10)
- Vigilância e segurança (LC 116, item 11.02)
- Serviços profissionais (advogados, contadores, médicos)

**Campos NFS-e:**
```xml
<ISSRetido>1</ISSRetido>  <!-- 1=Sim, 2=Não -->
<ValorISSRetido>100.00</ValorISSRetido>
<ResponsavelRetencao>1</ResponsavelRetencao>  <!-- 1=Tomador -->
```

---

## 4. IPI - IMPOSTO SOBRE PRODUTOS INDUSTRIALIZADOS {#ipi}

### 4.1 Fato Gerador
- Desembaraço aduaneiro de produto importado
- Saída de produto industrializado do estabelecimento industrial
- Arrematação de produto apreendido ou abandonado

### 4.2 Alíquotas TIPI (Tabela de Incidência do IPI)
**Varia por NCM** - Exemplos:

```
NCM          Descrição                              Alíquota
8471.30.12   Notebooks                              0%
8517.62.55   Smartphones                            0%
8703.23.10   Automóveis 1.0 a 1.5                   7%
8703.23.90   Automóveis 1.5 a 3.0                   11%
2203.00.00   Cerveja de malte                       20%
2402.20.00   Cigarros                               300%
```

### 4.3 Cálculo IPI
```
Base de Cálculo = Valor do Produto + Frete + Seguro + Outras Despesas
IPI = Base de Cálculo × Alíquota IPI

Observação: IPI NÃO integra a BC do ICMS (regra geral)
Exceção: IPI integra BC-ICMS quando o destinatário não for contribuinte de IPI
```

### 4.4 Campos NFe IPI
```xml
<IPI>
    <clEnq>999</clEnq>  <!-- Classe de enquadramento -->
    <CNPJProd></CNPJProd>
    <cSelo></cSelo>
    <qSelo>0</qSelo>
    <cEnq>999</cEnq>  <!-- Código de enquadramento -->
    <IPINT>  <!-- IPI Não Tributado -->
        <CST>53</CST>  <!-- 53=Saída não tributada -->
    </IPINT>
</IPI>
```

**CST IPI:**
```
00 - Entrada com recuperação de crédito
01 - Entrada tributada com alíquota zero
02 - Entrada isenta
03 - Entrada não tributada
04 - Entrada imune
05 - Entrada com suspensão
49 - Outras entradas
50 - Saída tributada
51 - Saída tributada com alíquota zero
52 - Saída isenta
53 - Saída não tributada
54 - Saída imune
55 - Saída com suspensão
99 - Outras saídas
```

---

## 5. PIS/COFINS - CONTRIBUIÇÕES SOCIAIS {#pis-cofins}

### 5.1 Regime de Apuração

#### **Regime Cumulativo (Lucro Presumido/Arbitrado)**
```
PIS    = 0,65% sobre Faturamento Bruto
COFINS = 3,00% sobre Faturamento Bruto

Não há direito a crédito sobre compras/insumos
```

#### **Regime Não-Cumulativo (Lucro Real)**
```
PIS    = 1,65% sobre Faturamento Bruto
COFINS = 7,60% sobre Faturamento Bruto

Há direito a crédito sobre:
- Aquisição de bens para revenda
- Aquisição de insumos
- Energia elétrica
- Aluguéis
- Despesas financeiras
- Máquinas e equipamentos (depreciação)
```

### 5.2 CST PIS/COFINS
```
01 - Operação Tributável com Alíquota Básica
02 - Operação Tributável com Alíquota Diferenciada
03 - Operação Tributável com Alíquota por Unidade de Medida de Produto
04 - Operação Tributável Monofásica - Revenda a Alíquota Zero
05 - Operação Tributável por Substituição Tributária
06 - Operação Tributável a Alíquota Zero
07 - Operação Isenta da Contribuição
08 - Operação sem Incidência da Contribuição
09 - Operação com Suspensão da Contribuição
49 - Outras Operações de Saída
50 - Operação com Direito a Crédito - Vinculada Exclusivamente a Receita Tributada no Mercado Interno
51 - Operação com Direito a Crédito - Vinculada Exclusivamente a Receita Não-Tributada no Mercado Interno
52 - Operação com Direito a Crédito - Vinculada Exclusivamente a Receita de Exportação
53 - Operação com Direito a Crédito - Vinculada a Receitas Tributadas e Não-Tributadas no Mercado Interno
54 - Operação com Direito a Crédito - Vinculada a Receitas Tributadas no Mercado Interno e de Exportação
55 - Operação com Direito a Crédito - Vinculada a Receitas Não Tributadas no Mercado Interno e de Exportação
56 - Operação com Direito a Crédito - Vinculada a Receitas Tributadas e Não-Tributadas no Mercado Interno e de Exportação
60 - Crédito Presumido - Operação de Aquisição Vinculada Exclusivamente a Receita Tributada no Mercado Interno
61 - Crédito Presumido - Operação de Aquisição Vinculada Exclusivamente a Receita Não-Tributada no Mercado Interno
62 - Crédito Presumido - Operação de Aquisição Vinculada Exclusivamente a Receita de Exportação
63 - Crédito Presumido - Operação de Aquisição Vinculada a Receitas Tributadas e Não-Tributadas no Mercado Interno
64 - Crédito Presumido - Operação de Aquisição Vinculada a Receitas Tributadas no Mercado Interno e de Exportação
65 - Crédito Presumido - Operação de Aquisição Vinculada a Receitas Não-Tributadas no Mercado Interno e de Exportação
66 - Crédito Presumido - Operação de Aquisição Vinculada a Receitas Tributadas e Não-Tributadas no Mercado Interno e de Exportação
67 - Crédito Presumido - Outras Operações
70 - Operação de Aquisição sem Direito a Crédito
71 - Operação de Aquisição com Isenção
72 - Operação de Aquisição com Suspensão
73 - Operação de Aquisição a Alíquota Zero
74 - Operação de Aquisição sem Incidência da Contribuição
75 - Operação de Aquisição por Substituição Tributária
98 - Outras Operações de Entrada
99 - Outras Operações
```

---

## 6. REFORMA TRIBUTÁRIA - IBS, CBS E IS {#reforma-tributaria}

### 6.1 Novos Tributos (EC 132/2023 e LC 214/2025)

#### **IBS - Imposto sobre Bens e Serviços**
- Substitui: ICMS (estadual) e ISS (municipal)
- Competência: Estados e Municípios (gestão compartilhada)
- Incidência: Bens e serviços
- Alíquota padrão: **~26,9%** (estimativa 2026)
- Não-cumulativo

#### **CBS - Contribuição sobre Bens e Serviços**
- Substitui: PIS e COFINS
- Competência: União
- Incidência: Bens e serviços
- Alíquota padrão: **~8,8%** (estimativa 2026)
- Não-cumulativo

#### **IS - Imposto Seletivo**
- Substitui: IPI (parcialmente)
- Competência: União
- Incidência: Bens e serviços prejudiciais à saúde ou meio ambiente
- Produtos: Bebidas alcoólicas, cigarros, veículos, agrotóxicos
- Alíquotas: A definir por lei

### 6.2 Cronograma de Implementação

```
2026 - Teste CBS (0,9%) e IBS (0,1%)
2027 - CBS completa + IBS teste ampliado
2028-2032 - Transição gradual (redução ICMS/ISS, aumento IBS)
2033 - IBS, CBS e IS em vigor pleno
```

### 6.3 Campos Obrigatórios NFe/NFCe (a partir de 2026)

#### **Grupo IBS/CBS (tag `<impostoProd>`)**
```xml
<impostoProd>
    <!-- CST IBS/CBS -->
    <cstIBSCBS>001</cstIBSCBS>  <!-- 001=Tributado alíquota cheia -->
    
    <!-- Base de Cálculo -->
    <vBCIBSCBS>1000.00</vBCIBSCBS>
    
    <!-- Alíquota IBS -->
    <pIBS>0.10</pIBS>  <!-- 0,1% em 2026 -->
    <vIBS>1.00</vIBS>
    
    <!-- Alíquota CBS -->
    <pCBS>0.90</pCBS>  <!-- 0,9% em 2026 -->
    <vCBS>9.00</vCBS>
    
    <!-- Código Indicador de Operação -->
    <cIndOper>000001</cIndOper>  <!-- 6 dígitos -->
    
    <!-- Código de Classificação Tributária -->
    <cClassTrib>000001</cClassTrib>  <!-- 6 dígitos -->
    
    <!-- Código de Localidade de Incidência -->
    <cLocInc>3549805</cLocInc>  <!-- Código IBGE -->
    
    <!-- Percentual Redutor -->
    <pRedBC>0.00</pRedBC>
</impostoProd>
```

#### **CST IBS/CBS:**
```
001 - Tributado com alíquota cheia
002 - Tributado com redução de base de cálculo
003 - Diferido
004 - Isento
005 - Não tributado
006 - Suspenso por decisão judicial
007 - Suspenso por decisão administrativa
008 - Não incidência
```

### 6.4 Campos Obrigatórios NFS-e (GISS Online - Reforma)

```xml
<DadosServico>
    <!-- Identificadores Reforma -->
    <FinalidadeNFSe>0</FinalidadeNFSe>  <!-- 0=Normal -->
    <IndicadorConsumidorFinal>0</IndicadorConsumidorFinal>
    <CodigoIndicadorOperacao>000001</CodigoIndicadorOperacao>
    <IndicadorDestinatario>0</IndicadorDestinatario>
    
    <!-- IBS/CBS -->
    <CSTIBSCBS>001</CSTIBSCBS>
    <CodigoClassificacaoTributaria>000001</CodigoClassificacaoTributaria>
    <CodigoLocalidadeIncidencia>3549805</CodigoLocalidadeIncidencia>
    <PercentualRedutor>0.00</PercentualRedutor>
    
    <!-- NBS -->
    <CodigoNBS>1.01.01.00.00</CodigoNBS>  <!-- entrada aceita; o sistema normaliza para 9 dígitos -->
</DadosServico>
```

---

## 7. REGRAS DE VALIDAÇÃO NFe/NFCe/NFS-e {#validacoes}

### 7.1 Validações Críticas NFe

#### **Regra N12-30: CST deve ser compatível com Origem**
```
CST 0XX → Origem 0, 3, 4, 5, 8
CST 1XX → Origem 1, 6
CST 2XX → Origem 2, 7
```

#### **Regra N12-90: CSOSN válidos**
```
Simples Nacional DEVE usar: 101, 102, 103, 201, 202, 203, 300, 400, 500, 900
Simples Nacional NÃO PODE usar: CST (000-290)
```

#### **Regra N12-60: Base de Cálculo ICMS**
```
vBC ≤ vProd + vFrete + vSeg + vOutro - vDesc
```

#### **Regra N17-10: IPI só para produtos com NCM válido**
```
Se IPI informado → NCM deve estar na TIPI
```

#### **Regra NA01-10: Total da NFe**
```
vNF = vProd - vDesc + vFrete + vSeg + vOutro + vII + vIPI + vIPIDevol + vST + vFCP + vFCPST + vFCPSTRet
```

### 7.2 Validações Críticas NFS-e

#### **Regra S01: Código de Serviço LC116**
```
Deve estar na lista oficial (1.01 a 40.01)
Formato: X.YY ou XX.YY
```

#### **Regra S02: Alíquota ISS**
```
2% ≤ Alíquota ≤ 5%
```

#### **Regra S03: Local de Prestação**
```
Código IBGE válido (7 dígitos)
Obrigatório quando ISS devido no município
```

#### **Regra S04: NBS Obrigatório (2026)**
```
Código NBS válido (9 dígitos sem pontos)
Formato: XXXXXXXXX
```

#### **Regra S05: IBS/CBS Reforma (2026)**
```
Se data emissão ≥ 01/01/2026:
    - cstIBSCBS obrigatório
    - cClassTrib obrigatório
    - cLocInc obrigatório
    - cIndOper obrigatório
```

### 7.3 Validações Específicas Reforma Tributária

#### **Regra RT01: CST IBS/CBS**
```
Valores válidos: 001, 002, 003, 004, 005, 006, 007, 008
Não pode ser vazio se data ≥ 01/01/2026
```

#### **Regra RT02: Classificação Tributária**
```
Formato: 6 dígitos numéricos
Exemplo: 000001, 000002, 010101
```

#### **Regra RT03: Indicador de Operação**
```
Formato: 6 dígitos numéricos
000001 = Operação Interna
000002 = Operação Interestadual
000003 = Operação com Exterior
```

#### **Regra RT04: Percentual Redutor**
```
0 ≤ pRedBC ≤ 100
Se CST IBS/CBS = 002 → pRedBC > 0
```

---

## 8. MATRIZ DE DECISÃO TRIBUTÁRIA - IA

### 8.1 Decisão CST/CSOSN

```python
def determinar_cst_csosn(empresa, produto, operacao):
    """
    Regras de decisão automática CST/CSOSN
    """
    # 1. Verificar Simples Nacional
    if empresa.regime == "SIMPLES_NACIONAL":
        if produto.permite_credito:
            if operacao.tem_st:
                return "201"  # Com crédito + ST
            return "101"  # Com crédito
        else:
            if operacao.tem_st:
                return "202"  # Sem crédito + ST
            return "102"  # Sem crédito
    
    # 2. Regime Normal - Verificar Origem
    origem = determinar_origem(produto)
    
    # 3. Verificar Tributação
    if operacao.tem_st:
        return f"{origem}10"  # Tributada com ST
    elif produto.reducao_bc > 0:
        if operacao.tem_st:
            return f"{origem}70"  # Redução + ST
        return f"{origem}20"  # Com redução
    elif produto.isento:
        if operacao.tem_st:
            return f"{origem}30"  # Isenta + ST
        return f"{origem}40"  # Isenta
    elif produto.nao_tributado:
        return f"{origem}41"  # Não tributada
    else:
        return f"{origem}00"  # Tributada integralmente

def determinar_origem(produto):
    """Determina origem da mercadoria"""
    if produto.importado:
        if produto.importacao_direta:
            return "1"
        return "2"
    
    # Nacional - verificar conteúdo importado
    if produto.conteudo_importado > 70:
        return "8"
    elif produto.conteudo_importado > 40:
        return "3"
    else:
        return "0"  # Nacional padrão
```

### 8.2 Decisão ISS para NFS-e

```python
def determinar_tributacao_iss(servico, cliente, tomador):
    """
    Regras tributárias ISS
    """
    # 1. Verificar código de serviço LC116
    codigo_lc116 = servico.codigo_lc116
    
    # 2. Buscar alíquota no município do prestador
    aliquota = cliente.municipio.buscar_aliquota(codigo_lc116)
    
    # 3. Verificar retenção na fonte
    iss_retido = False
    if codigo_lc116 in ["7.02", "7.05", "7.10", "11.02"]:
        # Construção civil, limpeza, vigilância
        if tomador.tipo == "JURIDICA":
            iss_retido = True
    
    # 4. Determinar local de prestação
    if codigo_lc116.startswith("7."):
        # Construção civil - local da obra
        local_prestacao = tomador.municipio
    else:
        # Regra geral - estabelecimento prestador
        local_prestacao = cliente.municipio
    
    return {
        "codigo_servico": codigo_lc116,
        "aliquota_iss": aliquota,
        "iss_retido": iss_retido,
        "local_prestacao": local_prestacao.codigo_ibge,
        "codigo_nbs": servico.codigo_nbs,
        "discriminacao": servico.descricao
    }
```

### 8.3 Cálculo Reforma Tributária (2026+)

```python
def calcular_ibs_cbs(valor_servico, data_emissao, municipio):
    """
    Cálculo IBS/CBS conforme cronograma
    """
    ano = data_emissao.year
    
    # Alíquotas por ano (transição)
    aliquotas = {
        2026: {"ibs": 0.1, "cbs": 0.9},
        2027: {"ibs": 1.0, "cbs": 8.8},
        2028: {"ibs": 5.0, "cbs": 8.8},
        2029: {"ibs": 10.0, "cbs": 8.8},
        2030: {"ibs": 15.0, "cbs": 8.8},
        2031: {"ibs": 20.0, "cbs": 8.8},
        2032: {"ibs": 25.0, "cbs": 8.8},
        2033: {"ibs": 26.9, "cbs": 8.8},  # Alíquota plena estimada
    }
    
    aliq = aliquotas.get(ano, aliquotas[2033])
    
    return {
        "vBC": valor_servico,
        "pIBS": aliq["ibs"],
        "vIBS": valor_servico * (aliq["ibs"] / 100),
        "pCBS": aliq["cbs"],
        "vCBS": valor_servico * (aliq["cbs"] / 100),
        "cstIBSCBS": "001",  # Tributado alíquota cheia
        "cClassTrib": "000001",
        "cLocInc": municipio.codigo_ibge,
        "pRedBC": 0.00
    }
```

---

## 9. CASOS PRÁTICOS - EXEMPLOS COMPLETOS

### Caso 1: Venda de Notebook Nacional para SP

```json
{
  "produto": {
    "ncm": "8471.30.12",
    "descricao": "Notebook Dell Inspiron 15",
    "valor": 3500.00,
    "origem": 0
  },
  "empresa": {
    "regime": "LUCRO_REAL",
    "estado": "SP"
  },
  "tributacao": {
    "icms": {
      "cst": "000",
      "modalidade_bc": 3,
      "base_calculo": 3500.00,
      "aliquota": 18.00,
      "valor": 630.00
    },
    "ipi": {
      "cst": "52",
      "aliquota": 0.00,
      "valor": 0.00
    },
    "pis": {
      "cst": "01",
      "base_calculo": 3500.00,
      "aliquota": 1.65,
      "valor": 57.75
    },
    "cofins": {
      "cst": "01",
      "base_calculo": 3500.00,
      "aliquota": 7.60,
      "valor": 266.00
    }
  }
}
```

### Caso 2: Serviço de Programação (NFS-e SJRP)

```json
{
  "servico": {
    "codigo_lc116": "1.02",
    "descricao": "Desenvolvimento de sistema web em Python/React",
    "codigo_nbs": "101020000",
    "valor": 5000.00
  },
  "prestador": {
    "cnpj": "12.345.678/0001-99",
    "municipio": "São José do Rio Preto/SP",
    "inscricao_municipal": "123456",
    "regime": "SIMPLES_NACIONAL"
  },
  "tributacao": {
    "iss": {
      "aliquota": 5.00,
      "valor": 250.00,
      "iss_retido": false,
      "local_prestacao": "3549805"
    },
    "reforma_tributaria": {
      "cst_ibs_cbs": "001",
      "vBC": 5000.00,
      "pIBS": 0.1,
      "vIBS": 5.00,
      "pCBS": 0.9,
      "vCBS": 45.00,
      "cClassTrib": "000001",
      "cIndOper": "000001",
      "cLocInc": "3549805",
      "pRedBC": 0.00
    }
  }
}
```

---

## 10. FONTES E REFERÊNCIAS OFICIAIS

### 📋 Documentos Oficiais Extraídos (30/01/2026)

#### **Portal NFe - Receita Federal**
- **Informe Técnico 2025.002 v.1.40** (Publicado 28/01/2026)
  - Atualização tabelas classificação tributária (cClassTrib)
  - Schemas XML NFe/NFCe Pacote Liberação 010b v.1.30
  - Campos IBS/CBS obrigatórios (Reforma Tributária)
  
- **Schemas XML Oficiais em Uso:**
  - NFGas v.1.00d (26/01/2026) - Nota Fiscal Gás
  - NFAg v.1.00d (13/11/2025) - Nota Fiscal Agro
  - Evento NT 2025.002 v.1.30 RTC (07/10/2025)
  - Pacote Liberação 010b v.1.30 (NFe/NFCe)

#### **Ato Conjunto RFB/CGIBS nº 01/2025** (DOU 23/12/2025)
**Dispõe sobre obrigações acessórias IBS e CBS - Ano 2026**

**Art. 1º** - Documentos fiscais recepcionados em 2026:
- NF-e (modelo 55), NFC-e (modelo 65), NFS-e
- CT-e (modelo 57), CT-e OS (modelo 67)
- BP-e (modelo 63), MDF-e (modelo 58)
- GTV-e (modelo 64), NF3e (modelo 66)
- NFCom (modelo 62), DC-e, NFS-e Via

**Art. 2º §2º** - Novos documentos fiscais eletrônicos:
- **NFAg** (modelo 75) - Água e Saneamento
- **DeRE** - Declaração Regimes Específicos
- **NF-e ABI** (modelo 77) - Alienação Bens Imóveis
- **NFGas** (modelo 76) - Gás

**Art. 3º** - Período de Adaptação 2026:
- Até 1º dia do 4º mês após publicação regulamentos:
  * Sem penalidades pela falta campos IBS/CBS
  * Apuração IBS/CBS em caráter informativo
  * Sem efeitos tributários (fase teste)

#### **Portal NFS-e Nacional**
- **Padrão ABRASF 2.04** - Manual técnico nacional
- **Documentação Atual (Produção)** - Disponível
- **Produção Restrita (Piloto RTC)** - Reforma Tributária
- **Lista LC 116/2003** - Códigos oficiais serviços
- **Minutas técnicas** - CGNFS-e (Comitê Gestor)

#### **Receita Federal - IPI**
**Fato Gerador:**
1. Desembaraço aduaneiro produto importado
2. Saída produto estabelecimento industrial

**Contribuinte:**
- Importador (importação)
- Industrial (operação interna)
- Estabelecimento equiparado industrial

**Base de Cálculo:**
- Operação interna: Valor total operação
- Importação: Base tributos aduaneiros + tributos + encargos cambiais

**Alíquotas:** Tabela TIPI (variável por NCM)
- Notebooks (8471.30.12): 0%
- Smartphones (8517.62.55): 0%
- Automóveis 1.0-1.5 (8703.23.10): 7%
- Automóveis 1.5-3.0 (8703.23.90): 11%
- Cerveja (2203.00.00): 20%
- Cigarros (2402.20.00): 300%

**Período Apuração:** Mensal (exceto importação)

**Prazo Recolhimento:**
- Importação: Antes saída repartição
- Cigarros (2402.20.00): 10º dia mês subsequente
- Demais produtos: 25º dia mês subsequente

#### **TIPI - Tabela de Incidência IPI**
Disponível para download em formatos:
- PDF: tipi.pdf (Receita Federal)
- DOCX: tipi.docx
- XLSX: tipi.xlsx
- URL: gov.br/receitafederal/legislacao/tipi

### 🏛️ Legislação Principal
- Constituição Federal (EC 132/2023 - Reforma Tributária)
- Lei Complementar 116/2003 (Lista de Serviços ISS)
- Lei Complementar 123/2006 (Simples Nacional)
- Lei Complementar 214/2025 (Regulamentação Reforma Tributária)
- Ajuste SINIEF 07/2005 (Nota Fiscal Eletrônica)
- Manual de Orientação Contribuinte NFe 7.0+
- Manual NFS-e Nacional ABRASF 2.04

### 📊 Estatísticas NFe (30/01/2026)
- **NF-e Autorizadas:** 55,109 bilhões
- **Número de Emissores:** 2,475 milhões
- **Estados Integrados:** 27 UFs + DF
- **Cadastro Centralizado:** Todos estados

### 🔗 Portais Oficiais
- Portal NFe: https://www.nfe.fazenda.gov.br
- Portal NFS-e Nacional: https://www.gov.br/nfse
- Receita Federal: https://www.gov.br/receitafederal
- Reforma Tributária RFB: https://www.gov.br/receitafederal/servicos/reforma-tributaria
- CONFAZ: https://www.confaz.fazenda.gov.br
- ENCAT: http://www.encat.org

### 📞 Canais de Atendimento Oficiais
- **Central Atendimento NFe:** SERPRO
- **Portal e-CAC:** Receita Federal
- **Perguntas Frequentes:** nfe.fazenda.gov.br/perguntasFrequentes
- **Fale Conosco NFS-e:** gov.br/nfse/canais_atendimento
- **Consulta NFe:** nfe.fazenda.gov.br/consultaRecaptcha
- **Consulta NFS-e:** nfse.gov.br/consultapublica

---

**Atualizado em:** 30/01/2026 18:45 BRT  
**Versão:** 2.0 - OFICIAL  
**Autor:** Sistema EmiteMax  
**Base:** Portais Oficiais Governo Federal + Legislação Vigente  
**Certificação:** Dados extraídos diretamente de gov.br e fazenda.gov.br
