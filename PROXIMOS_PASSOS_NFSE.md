# 🔄 Próximos Passos - Integração dos Campos NFS-e

## 📋 Status Atual

✅ **Banco de Dados** - 15 novos campos adicionados  
✅ **Formulário HTML** - Campos presentes na tela de emissão  
✅ **Modelo Python** - Estruturas de dados definidas  

## 🎯 Pendências para Completar a Implementação

---

## 1️⃣ Atualizar Service Layer

**Arquivo:** `services/nfse_service.py`

### O que fazer:

1. **Mapear campos do formulário para o banco**
   ```python
   # Adicionar no método de criação/emissão
   nfse_data = {
       # ... campos existentes ...
       
       # Novos campos IBS/CBS
       'codigo_nbs': request.form.get('codigo_nbs'),
       'finalidade_nfse': request.form.get('finalidade_nfse'),
       'indicador_consumidor_final': request.form.get('indicador_consumidor_final'),
       'codigo_indicador_operacao': request.form.get('codigo_indicador_operacao'),
       'indicador_destinatario': request.form.get('indicador_destinatario'),
       'cst_ibs_cbs': request.form.get('cst_ibs_cbs'),
       'codigo_classificacao_tributaria': request.form.get('codigo_classificacao_tributaria'),
       'codigo_localidade_incidencia': request.form.get('codigo_localidade_incidencia'),
       'percentual_redutor': float(request.form.get('percentual_redutor', 0)),
       
       # Tributos Totais
       'percentual_total_tributos_federais': float(request.form.get('percentual_total_tributos_federais', 0)),
       'percentual_total_tributos_estaduais': float(request.form.get('percentual_total_tributos_estaduais', 0)),
       'percentual_total_tributos_municipais': float(request.form.get('percentual_total_tributos_municipais', 5)),
       
       # Regime
       'regime_especial_tributacao': request.form.get('regime_especial_tributacao'),
       'optante_simples_nacional': request.form.get('optante_simples_nacional') == 'on',
       'incentivador_cultural': request.form.get('incentivador_cultural') == 'on',
   }
   ```

2. **Adicionar validações**
   ```python
   def validar_campos_reforma_tributaria(dados):
       """Valida campos obrigatórios da Reforma Tributária"""
       erros = []
       
       # Código NBS obrigatório
       if not dados.get('codigo_nbs'):
           erros.append("Código NBS é obrigatório")
       
       # Validar formato (9 dígitos)
       if dados.get('codigo_nbs') and len(dados['codigo_nbs']) != 9:
           erros.append("Código NBS deve ter 9 dígitos")
       
       # CST IBS/CBS obrigatório
       if not dados.get('cst_ibs_cbs'):
           erros.append("CST IBS/CBS é obrigatório")
       
       # ... outras validações ...
       
       return erros
   ```

3. **Atualizar query de inserção**
   ```python
   # Incluir novos campos no INSERT
   query = """
       INSERT INTO nfse (
           cliente_id, numero_rps, serie_rps, tipo_rps,
           data_competencia, natureza_operacao,
           Tomadores_cpf_cnpj, Tomadores_razao_social, ...,
           codigo_servico, discriminacao,
           valor_servicos, aliquota_iss, ...,
           codigo_nbs, finalidade_nfse, indicador_consumidor_final,
           codigo_indicador_operacao, indicador_destinatario,
           cst_ibs_cbs, codigo_classificacao_tributaria,
           codigo_localidade_incidencia, percentual_redutor,
           percentual_total_tributos_federais,
           percentual_total_tributos_estaduais,
           percentual_total_tributos_municipais,
           regime_especial_tributacao, optante_simples_nacional,
           incentivador_cultural, ambiente, status
       ) VALUES (
           %s, %s, %s, %s, %s, %s, %s, %s, ...,
           %s, %s, %s, %s, %s, %s, %s, %s, %s,
           %s, %s, %s, %s, %s, %s, %s, %s,
           %s, %s, %s
       ) RETURNING id
   """
   ```

---

## 2️⃣ Atualizar Routes

**Arquivo:** `routes/nfse_routes.py`

### O que fazer:

1. **Rota de Emissão - Processar novos campos**
   ```python
   @nfse_bp.route('/emitir', methods=['POST'])
   def emitir_nfse():
       try:
           # Coletar dados do formulário
           dados = {
               # Campos existentes...
               
               # Novos campos
               'codigo_nbs': request.form.get('codigo_nbs'),
               'finalidade_nfse': request.form.get('finalidade_nfse', '0'),
               'indicador_consumidor_final': request.form.get('indicador_consumidor_final', '0'),
               # ... todos os outros campos ...
           }
           
           # Validar antes de enviar
           erros = validar_campos_reforma_tributaria(dados)
           if erros:
               return render_template('error.html', erros=erros)
           
           # Chamar service
           resultado = nfse_service.emitir_nfse(dados)
           
           return redirect(url_for('nfse.visualizar', id=resultado['id']))
           
       except Exception as e:
           logger.error(f"Erro ao emitir NFS-e: {e}")
           return render_template('error.html', erro=str(e))
   ```

2. **Rota de Visualização - Exibir novos campos**
   ```python
   @nfse_bp.route('/visualizar/<int:id>')
   def visualizar_nfse(id):
       nfse = nfse_service.buscar_por_id(id)
       
       # Carregar descrições para códigos
       nfse['descricao_nbs'] = obter_descricao_nbs(nfse['codigo_nbs'])
       nfse['descricao_cst'] = obter_descricao_cst(nfse['cst_ibs_cbs'])
       
       return render_template('nfse/visualizar.html', nfse=nfse)
   ```

---

## 3️⃣ Atualizar Gerador de XML

**Arquivo:** `services/nfse_xml_generator.py` ou similar

### O que fazer:

1. **Adicionar tags IBS/CBS no XML**
   ```python
   def gerar_xml_servico(servico):
       """Gera XML do serviço com campos da Reforma Tributária"""
       
       xml = f"""
       <Servico>
           <Valores>
               <ValorServicos>{servico['valor_servicos']:.2f}</ValorServicos>
               <!-- valores existentes -->
           </Valores>
           
           <IssRetido>{1 if servico['iss_retido'] else 2}</IssRetido>
           
           <!-- NOVOS CAMPOS - Reforma Tributária -->
           <CodigoNBS>{servico['codigo_nbs']}</CodigoNBS>
           
           <TributosReformaTributaria>
               <PercentualTotalTributosFederais>{servico['percentual_total_tributos_federais']:.2f}</PercentualTotalTributosFederais>
               <PercentualTotalTributosEstaduais>{servico['percentual_total_tributos_estaduais']:.2f}</PercentualTotalTributosEstaduais>
               <PercentualTotalTributosMunicipais>{servico['percentual_total_tributos_municipais']:.2f}</PercentualTotalTributosMunicipais>
           </TributosReformaTributaria>
           
           <IBSCBS>
               <FinalidadeNFSe>{servico['finalidade_nfse']}</FinalidadeNFSe>
               <IndicadorConsumidorFinal>{servico['indicador_consumidor_final']}</IndicadorConsumidorFinal>
               <CodigoIndicadorOperacao>{servico['codigo_indicador_operacao']}</CodigoIndicadorOperacao>
               <IndicadorDestinatario>{servico['indicador_destinatario']}</IndicadorDestinatario>
               <CSTIBSCBS>{servico['cst_ibs_cbs']}</CSTIBSCBS>
               <CodigoClassificacaoTributaria>{servico['codigo_classificacao_tributaria']}</CodigoClassificacaoTributaria>
               <CodigoLocalidadeIncidencia>{servico['codigo_localidade_incidencia']}</CodigoLocalidadeIncidencia>
               <PercentualRedutor>{servico['percentual_redutor']:.2f}</PercentualRedutor>
           </IBSCBS>
           
           <CodigoTributacaoMunicipio>{servico['codigo_servico']}</CodigoTributacaoMunicipio>
           <Discriminacao>{servico['discriminacao']}</Discriminacao>
           <CodigoMunicipioPrestacao>{servico['codigo_municipio_prestacao']}</CodigoMunicipioPrestacao>
       </Servico>
       """
       return xml
   ```

2. **Validar XML conforme schema GISS**
   - Verificar tags obrigatórias
   - Validar tipos e formatos
   - Testar com schema XSD do GISS

---

## 4️⃣ Atualizar Template de Visualização

**Arquivo:** `templates/admin/nfse/visualizar.html`

### O que fazer:

Adicionar seção para exibir os novos campos:

```html
<!-- Seção IBS/CBS - Reforma Tributária -->
<div class="card mb-4">
    <div class="card-header bg-success text-white">
        <h5><i class="fas fa-balance-scale"></i> IBS/CBS - Reforma Tributária</h5>
    </div>
    <div class="card-body">
        <div class="row">
            <div class="col-md-4">
                <strong>Código NBS:</strong><br>
                {{ nfse.codigo_nbs }} - {{ nfse.descricao_nbs }}
            </div>
            <div class="col-md-4">
                <strong>Finalidade:</strong><br>
                {{ nfse.finalidade_nfse }} - {{ nfse.finalidade_descricao }}
            </div>
            <div class="col-md-4">
                <strong>CST IBS/CBS:</strong><br>
                {{ nfse.cst_ibs_cbs }} - {{ nfse.cst_descricao }}
            </div>
        </div>
        <!-- mais campos... -->
    </div>
</div>

<!-- Seção Tributos Totais -->
<div class="card mb-4">
    <div class="card-header bg-warning">
        <h5><i class="fas fa-percentage"></i> Tributos Totais</h5>
    </div>
    <div class="card-body">
        <div class="row">
            <div class="col-md-4">
                <strong>Tributos Federais:</strong><br>
                {{ nfse.percentual_total_tributos_federais }}%
            </div>
            <div class="col-md-4">
                <strong>Tributos Estaduais:</strong><br>
                {{ nfse.percentual_total_tributos_estaduais }}%
            </div>
            <div class="col-md-4">
                <strong>Tributos Municipais:</strong><br>
                {{ nfse.percentual_total_tributos_municipais }}%
            </div>
        </div>
    </div>
</div>
```

---

## 5️⃣ Criar Testes

**Arquivo:** `tests/test_nfse_reforma.py`

### O que fazer:

```python
import pytest
from services.nfse_service import NFSeService

def test_emissao_com_campos_reforma():
    """Testa emissão de NFS-e com campos da Reforma Tributária"""
    
    dados = {
        'cliente_id': 1,
        'numero_rps': 1,
        'valor_servicos': 1000.00,
        'codigo_servico': '01.01',
        'discriminacao': 'Teste',
        
        # Campos da Reforma
        'codigo_nbs': '101010000',
        'finalidade_nfse': '0',
        'indicador_consumidor_final': '1',
        'codigo_indicador_operacao': '000001',
        'indicador_destinatario': '0',
        'cst_ibs_cbs': '001',
        'codigo_classificacao_tributaria': '000001',
        'codigo_localidade_incidencia': '3549805',
        'percentual_redutor': 0.00,
        'percentual_total_tributos_federais': 0.00,
        'percentual_total_tributos_estaduais': 0.00,
        'percentual_total_tributos_municipais': 5.00,
        # ... demais campos ...
    }
    
    service = NFSeService()
    resultado = service.emitir_nfse(dados)
    
    assert resultado['sucesso'] == True
    assert resultado['id'] > 0
    
    # Verificar se os campos foram salvos
    nfse = service.buscar_por_id(resultado['id'])
    assert nfse['codigo_nbs'] == '101010000'
    assert nfse['cst_ibs_cbs'] == '001'

def test_validacao_codigo_nbs_obrigatorio():
    """Testa validação de campo obrigatório"""
    
    dados = {
        # ... dados sem codigo_nbs ...
    }
    
    service = NFSeService()
    
    with pytest.raises(ValueError, match="Código NBS é obrigatório"):
        service.emitir_nfse(dados)
```

---

## 6️⃣ Testar Integração Completa

### Checklist de Testes:

#### Teste 1: Emissão Básica
- [ ] Preencher formulário com todos os campos
- [ ] Submeter para emissão
- [ ] Verificar salvamento no banco
- [ ] Conferir todos os 15 campos salvos corretamente

#### Teste 2: Geração de XML
- [ ] Gerar XML da NFS-e
- [ ] Verificar presença das tags IBS/CBS
- [ ] Validar XML contra schema XSD
- [ ] Conferir formatação dos valores

#### Teste 3: Envio para GISS (Homologação)
- [ ] Enviar XML para ambiente de homologação
- [ ] Verificar aceite ou rejeição
- [ ] Analisar mensagens de retorno
- [ ] Ajustar conforme necessário

#### Teste 4: Visualização
- [ ] Acessar tela de visualização
- [ ] Verificar exibição dos novos campos
- [ ] Conferir descrições e formatações
- [ ] Testar impressão/PDF

#### Teste 5: Validações
- [ ] Testar com código NBS inválido
- [ ] Testar com percentuais fora do range
- [ ] Testar campos obrigatórios vazios
- [ ] Verificar mensagens de erro

---

## 📅 Cronograma Sugerido

### Fase 1: Service e Routes (2-3 horas)
- Atualizar service layer
- Atualizar routes
- Testar salvamento no banco

### Fase 2: XML Generator (2-3 horas)
- Adicionar tags IBS/CBS
- Validar XML
- Testar formatação

### Fase 3: Templates (1-2 horas)
- Atualizar visualização
- Melhorar emissão se necessário
- Ajustar layouts

### Fase 4: Testes (2-3 horas)
- Criar testes unitários
- Testes de integração
- Testes com GISS

### Total Estimado: 7-11 horas

---

## 🎯 Critérios de Sucesso

A implementação estará completa quando:

✅ Todos os campos do formulário forem salvos no banco  
✅ XML for gerado com tags IBS/CBS corretas  
✅ GISS aceitar a NFS-e em homologação  
✅ Visualização exibir todos os campos  
✅ Validações impedirem dados inválidos  
✅ Testes passarem 100%  

---

## 📚 Recursos Úteis

- **Documentação GISS Online**: [consultar prefeitura]
- **Schema XSD**: Solicitar à prefeitura ou verificar no sistema
- **Lei Complementar 214/2025**: Consultar texto oficial
- **Tabela NBS**: Consultar IBGE

---

## 🆘 Suporte

Se encontrar dificuldades:
1. Verificar logs de erro detalhados
2. Testar cada componente isoladamente
3. Consultar documentação oficial GISS
4. Verificar exemplos de XML válidos

---

**Documento criado em:** 30/01/2026  
**Próxima revisão:** Após cada fase concluída
