# EmiteMax — Continuação: C3-Cont + C2-Cont + Roteiro final de homologação/deploy

**Data:** 06/10/2026
**Status atual:** P1–P8 e C1–C7 implementados (285 testes aprovados, 29 ignorados, 0 falhas). Nenhum deploy realizado.
**Pendências:** C3-Cont (PDF do Tipo 2 em ReportLab) e C2-Cont (validação de ordem das tags contra XSD oficial).

> Regra transversal de todos os prompts: preservar o comportamento atual em produção; se qualquer teste existente quebrar, reverter as alterações e relatar; NENHUM prompt executa deploy.

---

## Bloco A — C3-Cont: Gerar PDF do DANFE Simplificado Tipo 2 em ReportLab nativo

**Contexto:** o DANFE A4 não possui conversor HTML→PDF; o caminho produtivo gera PDF em ReportLab diretamente a partir do XML. Decisão: gerar o PDF do Tipo 2 também em ReportLab, reutilizando os helpers do A4, sem adicionar nenhuma dependência de sistema à AWS e sem alterar o requirements além do que já existe.

1. Em `services/danfe_service.py`, identifique e **liste** os helpers ReportLab do fallback A4: registro de fontes, funções de formatação de valores (vírgula decimal + ponto de milhar), definição de página, cores/estilos. **Não os modifique.**
2. Em `services/danfe_simplificado_tipo2_service.py`, adicione a função `gerar_danfe_tipo2_pdf(dados_nfe, protocolo=None, caminho_pdf=None)` que:
   a. **Reutiliza** os helpers do passo 1 (fontes e formatação de valores) — não crie formatação divergente;
   b. Cria página com largura de **56mm (≈158,74pt)** e margens laterais de **2mm**;
   c. Imprime as divisões **I a IX na mesma ordem e com os mesmos textos** do `danfe_tipo2.html` (use o template atual como referência de conteúdo);
   d. Gera a imagem do QR com a lib `qrcode` já declarada e desenha com **mínimo 25×25mm + quiet zone 3mm**, usando a mesma URL de `gerar_qrcode_tipo2`;
   e. Aplica os textos fixos: contingência em 2 pontos, "EMITIDA EM AMBIENTE DE HOMOLOGAÇÃO - SEM VALOR FISCAL", "Via do Estabelecimento";
   f. Retorna o **caminho do PDF** (mesmo padrão de retorno de `generate_danfe`).
3. Renomeie a geração HTML existente para `gerar_danfe_tipo2_html(...)` (uso apenas em preview/testes). Transforme `gerar_danfe_tipo2(...)` em um **wrapper** que: chama `gerar_danfe_tipo2_pdf` e retorna o caminho do PDF; em erro, registra `ERRO_DANFE_TIPO2: <msg>` e **re-lança a exceção** para o fallback da rota (não embrulhe silenciosamente).
4. Em `routes/nfe_routes.py`, ajuste o ponto do P3:
   - `usa_danfe_tipo2 == True` → entregue o PDF do Tipo 2 pela **mesma rota/mecanismo de download do A4** (resolução do caminho por ID da NF-e + `send_file`/download);
   - Dentro do `except` → registre `ERRO_DANFE_TIPO2` e entregue o **A4 como hoje** (nunca interromper a emissão);
   - Flag `False`/ausente → comportamento idêntico ao atual;
   - Em **contingência**, passe para `gerar_qrcode_tipo2` a **`private_key` do mesmo certificado usado na assinatura da NF-e**; se a chave não estiver disponível, registre `ERRO_DANFE_TIPO2` e entregue o A4 — **nunca gere QR offline sem assinatura**.
5. Confirme que o import do helper `_sign_data` (de `services/xml_signature_service_old.py`) continua funcionando após as mudanças — **não mova esse helper** de arquivo nesta tarefa.
6. Atualize `tests/test_danfe_tipo2.py`:
   a. Testes de conteúdo continuam validando `gerar_danfe_tipo2_html` (divisões e mensagens);
   b. Adicione teste: `gerar_danfe_tipo2` retorna um caminho de arquivo que inicia com `b'%PDF'` e não está vazio;
   c. Testes de URL do QR (online/offline) seguem apontando para `gerar_qrcode_tipo2`.
7. Rode `python -m py_compile` nos arquivos tocados e `pytest tests/ -q`. Se algum teste existente quebrar, **reverta as alterações** e relate quais falharam. Não faça deploy.

---

## Bloco B — C2-Cont: Validar posição das tags do leiaute NT 2026.008 contra XSD oficial

**Contexto:** o leiaute local (`.txt` e XSD `PL_010b`) **não contém** os campos da NT 2026.008. A validação final de ordem precisa ser feita contra um XSD oficial atualizado, usando `lxml` (já dependência do projeto).

1. Obtenha o **XSD oficial mais recente** do leiaute NFe 4.00 que inclua `vUnComLiq` (I11b), `vProdLiq` (I11c), `vProdLiqTot` (W01a) e `ICMSPrevistoPagtoAntecip`/`vICMSPrevisto` (NB01/NB02): procure no Portal Nacional da NF-e (nfe.fazenda.gov.br → área de leiaute/esquemas) ou na documentação ENCAT/CGIBS da NT 2026.008. Salve em pasta nova `Documentacao/xsd_nt2026/`. Se não conseguir baixar, use o XSD local em `Documentacao/Documentacao sefaz/PL_010b_NT2025_002_v1.21/leiauteNFe_v4.00.xsd` como base e **liste explicitamente** o que ficou sem confirmação.
2. Crie `scripts/validar_xml_xsd.py` que receba caminhos de XML e XSD, valide com `lxml.etree.XMLSchema` e imprima os erros de forma objetiva (linha/mensagem/conteúdo).
3. Monte um **XML mínimo completo em memória** (sem banco) cobrindo: `ide`, `emit`, `det` com os campos novos, total com `vProdLiqTot` e grupos obrigatórios mínimos. Use o serializador existente se ele funcionar sem banco; caso contrário, monte com `lxml`/ElementTree seguindo **exatamente a ordem do XSD oficial**. Salve o XML em `tests/fixtures/xml_nt2026_008_minimo.xml`.
4. Confirme a ordem dos 3 pontos **pelo XSD oficial** (não pelo `.txt` local):
   a. `Det/Prod`: `vUnComLiq` e `vProdLiq` logo após `vProd` (ajuste se o XSD indicar outra posição);
   b. Total: `vProdLiqTot` na posição exata do XSD;
   c. `NB01/ICMSPrevistoPagtoAntecip`: posição exata dentro do grupo de imposto/ICMS — mova a injeção do elemento com `lxml` (insert relativo ao elemento-âncora do XSD), **sem mover tags preexistentes**.
5. Rode o script com o XML mínimo: deve retornar **zero erros**. Se houver erro de sequência, ajuste **apenas a ordem de inserção das tags novas** até passar. Registre a saída.
6. Adicione um teste em `tests/` que valide o XML mínimo contra o XSD oficial (para regressão futura).
7. Rode `pytest tests/ -q`. Se quebrar, reverta e relate. **Não faça deploy.**
8. Relate: (a) XSD usado (nome/versão/fonte), (b) resultado da validação, (c) posição final de cada tag nova confirmada. Se não conseguir obter o XSD oficial, deixe um `# TODO: validar com XSD oficial na homologação` e registre que **o teste definitivo será o envio em tpAmb=2 na SEFAZ**.

---

## Bloco C — Roteiro final de homologação SEFAZ e deploy AWS (executar APÓS os Blocos A e B)

### C.1 — Homologação SEFAZ (tpAmb=2): bateria mínima
- NF-e normal (sem campos especiais);
- NF-e com desconto/frete/outras despesas (confere totais);
- NF-e em **contingência offline** (confere QR assinado, dia com 2 dígitos e vNF com ponto decimal);
- NF-e com **pagamento antecipado `tpNFDebito=06`** (confere `ICMSPrevistoPagtoAntecip`/`vICMSPrevisto`);
- **NFC-e modelo 65** (deve NÃO conter o grupo NB01);
- NF-e com IBS/CBS destacado (confere `vProdLiq`/`vUnComLiq` e `vProdLiqTot`; se o ambiente de homologação permitir data futura, testar composição 2027 — caso contrário, confiar nos testes unitários de `vigencia_reforma`).
- Conferir **ausência de rejeições 1278/1279/1280/1281/1282/1283** e de erros de leiaute (ordem de tags).

### C.2 — Preparação de deploy na AWS
- Cada bloco em **branch própria** (`feat/nt-2026-003-danfe-tipo2`, `feat/nt-2026-008-valor-liquido`), revisão e merge controlado — zero merge direto na main.
- **Backup do RDS antes de qualquer ALTER:** `pg_dump` do banco de produção e validação de restauração em staging.
- Aplicar a migration `migracao_danfe_tipo2.sql` (flag `usa_danfe_tipo2`) **somente na janela de deploy**, após o backup validado.
- Confirmar `requirements.txt` com `qrcode` e dependências do Tipo 2; ambiente executa `pip install -r requirements.txt`.
- **Nenhuma dependência de sistema nova** (ReportLab já presente — Bloco A usa helpers existentes).
- **Rollback pronto:** artefato/anterior da mesma release disponível para reversão imediata.

### C.3 — Janela de deploy
- Executar em **horário de baixo volume**; aplicar migration + deploy; conferir `/health` e logs de erro 500.
- Emitir **nota de teste em produção (tpAmb=1) sem valor** e conferir protocolo e DANFE (A4 e Tipo 2, se flag ativa).
- Monitorar `ERRO_DANFE_TIPO2` e rejeições da SEFAZ nos logs após o deploy.

### C.4 — Pós-deploy e comunicação
- Ativar `usa_danfe_tipo2` **apenas para cliente piloto** primeiro; liberar gradualmente.
- Comunicar clientes (cartilha IBS/CBS já pronta): os campos novos **não alteram o valor faturado**.
- **Agenda regulatória:** produção da NT 2026.008 em **03/11/2026** (campos de valor líquido em uso conforme regra I11c); composição do vProd com IBS/CBS **somente a partir de 01/01/2027**; obrigatoriedade do grupo NB01 (regra NB01-30) **a partir de 01/03/2027** — não ativar antes.
- Confirmar com o consultor tributário a abordagem conservadora para 2026 (vProd sem IBS/CBS).

---

## Observações finais
- Os Blocos A e B são independentes; ordem sugerida: **A (PDF) → B (validação)** para validar com a ordem final de tags.
- Após cada bloco: `pytest tests/ -q` deve manter 285+ aprovados, 0 falhas.
- Nenhum bloco deste arquivo executa deploy — homologação e deploy exigem o roteiro do Bloco C.