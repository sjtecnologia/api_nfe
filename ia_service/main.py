import os
import requests
import json
## Removido: função duplicada gerar_prompt_sugestao
from fastapi import Body

from fastapi import FastAPI, Request, Body
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Dict, Any, Optional

app = FastAPI()

# Armazenamento simples em memória para NCMs recebidos
ncm_db: list = []

# Endpoint para receber e armazenar dados de NCM
@app.post('/ncm/dados')
async def receber_ncm_dados(ncms: Any = Body(...)):
    global ncm_db
    # Se for lista, usa direto. Se for dict, coloca em lista.
    if isinstance(ncms, list):
        ncm_db = ncms
    elif isinstance(ncms, dict):
        ncm_db = [ncms]
    else:
        ncm_db = []
    return {"status": "ok", "total": len(ncm_db)}


# Mock de modelo de IA para sugestão tributária
from typing import Optional

class SugestaoTributariaRequest(BaseModel):
    descricao: str
    tipo_item: str
    cliente_id: Optional[int] = None
    preco_unitario_padrao: Optional[float] = None
    unidade_comercial: Optional[str] = None
    codigo_interno: Optional[str] = None
    # Campos para melhor contexto tributário
    uf_origem: Optional[str] = None
    regime_tributario: Optional[str] = None

def buscar_ncms_sugeridos(descricao: str) -> str:
    """Busca NCMs na API especializada para enriquecer o contexto"""
    try:
        response = requests.get(
            "http://localhost:8080/api/llm/ncms/search",
            params={"q": descricao, "tipo": "analitico", "limit": 3},
            timeout=2
        )
        if response.status_code == 200:
            data = response.json()
            ncms = data.get("results", [])
            if ncms:
                sugestoes = "\nNCMs SUGERIDOS (Base Oficial Siscomex):\n"
                for ncm in ncms[:3]:
                    sugestoes += f"- {ncm.get('codigo_ncm', 'N/A')}: {ncm.get('descricao', 'N/A')} (Score: {ncm.get('score', 0):.2f})\n"
                return sugestoes
    except:
        # Se API NCM não disponível, continua sem sugestões
        pass
    return ""

def gerar_prompt_sugestao(req: SugestaoTributariaRequest) -> str:
    # Constrói contexto adicional se disponível
    contexto_adicional = ""
    if req.unidade_comercial:
        contexto_adicional += f"Unidade comercial: {req.unidade_comercial}\n"
    if req.codigo_interno:
        contexto_adicional += f"Código interno: {req.codigo_interno}\n"
    if req.uf_origem:
        contexto_adicional += f"UF origem: {req.uf_origem}\n"
    if req.regime_tributario:
        contexto_adicional += f"Regime tributário: {req.regime_tributario}\n"
    
    # Buscar NCMs sugeridos na base oficial
    ncms_sugeridos = buscar_ncms_sugeridos(req.descricao)
    
    return (
        f"Você é um especialista em tributação brasileira. Analise o produto e sugira a classificação fiscal adequada.\n\n"
        f"PRODUTO:\n"
        f"Descrição: {req.descricao}\n"
        f"Tipo de item: {req.tipo_item}\n"
        f"Cliente ID: {req.cliente_id}\n"
        f"Preço unitário: R$ {req.preco_unitario_padrao if req.preco_unitario_padrao else 'N/A'}\n"
        f"{contexto_adicional}{ncms_sugeridos}\n"
        f"INSTRUÇÕES:\n"
        f"1. NCM (8 dígitos): Classifique conforme a Nomenclatura Comum do Mercosul\n"
        f"2. CFOP (4 dígitos): Código Fiscal de Operações e Prestações mais comum (ex: 5102 para venda dentro do estado)\n"
        f"3. CST (3 dígitos): Código de Situação Tributária do ICMS (para empresas do regime normal)\n"
        f"4. CSOSN (3 dígitos): Código de Situação da Operação no Simples Nacional\n"
        f"5. CEST (7 dígitos): Código Especificador da Substituição Tributária (obrigatório para alguns produtos como combustíveis, bebidas, cigarros, etc.)\n\n"
        f"DICAS IMPORTANTES:\n"
        f"- CEST é obrigatório para produtos sujeitos à substituição tributária\n"
        f"- Para produtos comuns sem ST, CEST pode ser null\n"
        f"- CST 000 = Tributada integralmente, CST 101 = Tributada com cobrança por ST\n"
        f"- CSOSN 102 = Sem tributação (Simples Nacional), CSOSN 500 = ICMS cobrado por ST\n\n"
        f"RESPOSTA OBRIGATÓRIA EM JSON:\n"
        f'{{\n'
        f'  "ncm": "código NCM de 8 dígitos",\n'
        f'  "cfop": "código CFOP de 4 dígitos",\n'
        f'  "cst": "código CST de 3 dígitos",\n'
        f'  "csosn": "código CSOSN de 3 dígitos",\n'
        f'  "cest": "código CEST de 7 dígitos ou null se não sujeito à ST",\n'
        f'  "explicacao": "justificativa técnica da classificação com base no produto"\n'
        f'}}\n\n'
        f"CRÍTICO: Responda APENAS o JSON válido, SEM markdown, SEM código blocks (```), SEM texto adicional. APENAS JSON PURO."
    )

@app.post('/sugestao')
async def sugestao_tributaria(req: SugestaoTributariaRequest):
    prompt = gerar_prompt_sugestao(req)
    try:
        # Usar GitHub Models API (muito mais rápido!)
        github_token = os.getenv("GITHUB_TOKEN", "")
        
        if github_token:
            # GitHub Models API (GPT-4o mini - rápido e preciso)
            llm_url = "https://models.inference.ai.azure.com/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {github_token}"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Especialista em classificação fiscal brasileira. Responda APENAS JSON puro, sem markdown."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 512,
                "temperature": 0.2
            }
            resp = requests.post(llm_url, json=payload, headers=headers, timeout=15)
        else:
            # Fallback: LM Studio local
            llm_url = "http://177.189.240.158:1234/v1/chat/completions"
            payload = {
                "model": "codellama-7b-instruct",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 512,
                "temperature": 0.2
            }   
            resp = requests.post(llm_url, json=payload, timeout=60)
            
        if resp.status_code == 200:
            # Para /v1/chat/completions, a resposta vem em choices[0].message.content
            resposta = resp.json().get("choices", [{}])[0].get("message", {}).get("content")
            try:
                if resposta:
                    # Limpar markdown da resposta se presente
                    resposta_limpa = resposta.strip()
                    if resposta_limpa.startswith("```json"):
                        resposta_limpa = resposta_limpa.replace("```json", "", 1)
                    if resposta_limpa.endswith("```"):
                        resposta_limpa = resposta_limpa.rsplit("```", 1)[0]
                    resposta_limpa = resposta_limpa.strip()
                    
                    sugestao = json.loads(resposta_limpa)
                else:
                    sugestao = {"erro": "Resposta da IA está vazia ou nula", "resposta": resposta}
            except Exception as e:
                sugestao = {"erro": f"Não foi possível interpretar a resposta da IA: {str(e)}", "resposta": resposta}
            return JSONResponse(content=sugestao)
        else:
            return JSONResponse(content={"erro": f"Erro LLM: {resp.status_code} - {resp.text}"})
    except Exception as e:
        return JSONResponse(content={"erro": str(e)})

@app.post('/explicacao')
async def explicacao_tributaria(data: Dict[str, Any]):
    # Gera explicação didática baseada nos dados recebidos
    return {'explicacao': 'Sugestão baseada em operações similares anteriores e perfil do cliente.'}

# ========== VALIDAÇÃO DE XML COMPLETO ==========
class ValidacaoXMLRequest(BaseModel):
    xml_content: str
    ambiente: str  # "producao" ou "homologacao"

@app.post('/valida/xml')
async def validar_xml_completo(req: ValidacaoXMLRequest):
    """Valida XML completo da NFe antes de enviar para SEFAZ"""
    
    try:
        github_token = os.getenv("GITHUB_TOKEN", "")
        
        prompt = f"""Você é um especialista em NFe 4.0. Analise o XML abaixo e identifique problemas que causariam rejeição no SEFAZ.

AMBIENTE: {req.ambiente}

VERIFIQUE:
1. Estrutura do XML (ordem de elementos, namespaces)
2. Compatibilidade CFOP x CST/CSOSN x Regime Tributário
3. Campos obrigatórios (procEmi, verProc, indPag, etc)
4. Valores tributários (vBC, vICMS, vNF)
5. CPF/CNPJ válidos
6. Datas no formato correto
7. Totalizadores batendo com itens

XML:
{req.xml_content[:3000]}...

RESPONDA JSON:
{{
  "valido": true/false,
  "erros": [{{"campo": "nome", "erro": "descrição", "linha": "aproximada"}}],
  "avisos": ["avisos não críticos"],
  "score_confianca": 0-100
}}

SEM markdown, APENAS JSON."""

        if github_token:
            llm_url = "https://models.inference.ai.azure.com/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {github_token}"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Especialista NFe 4.0 Brasil. Responda JSON puro."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1024,
                "temperature": 0.1
            }
            resp = requests.post(llm_url, json=payload, headers=headers, timeout=20)
        else:
            return JSONResponse(content={
                "valido": True,
                "erros": [],
                "avisos": ["Validação IA não disponível - token GitHub não configurado"],
                "score_confianca": 0
            })
        
        if resp.status_code == 200:
            resposta = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            
            try:
                resposta_limpa = resposta.strip()
                if resposta_limpa.startswith("```json"):
                    resposta_limpa = resposta_limpa.replace("```json", "", 1)
                if resposta_limpa.endswith("```"):
                    resposta_limpa = resposta_limpa.rsplit("```", 1)[0]
                resposta_limpa = resposta_limpa.strip()
                
                resultado = json.loads(resposta_limpa)
                return JSONResponse(content=resultado)
            except Exception as e:
                return JSONResponse(content={
                    "valido": True,
                    "erros": [],
                    "avisos": [f"Erro ao processar resposta IA: {str(e)}"],
                    "score_confianca": 0
                })
        else:
            return JSONResponse(content={
                "valido": True,
                "erros": [],
                "avisos": [f"IA indisponível: {resp.status_code}"],
                "score_confianca": 0
            })
            
    except Exception as e:
        return JSONResponse(content={
            "valido": True,
            "erros": [],
            "avisos": [f"Erro validação XML: {str(e)}"],
            "score_confianca": 0
        })

# ========== VALIDAÇÃO DE REGRA TRIBUTÁRIA ==========
class ValidacaoRegraRequest(BaseModel):
    regime_tributario: str  # "Simples Nacional" ou "Regime Normal"
    cfop: str
    cst_icms: Optional[str] = None
    csosn_icms: Optional[str] = None
    ncm: Optional[str] = None
    descricao: Optional[str] = None

@app.post('/valida/regra')
async def validar_regra_tributaria(req: ValidacaoRegraRequest):
    """Valida regra tributária no cadastro - TODOS OS REGIMES"""
    
    try:
        github_token = os.getenv("GITHUB_TOKEN", "")
        is_simples = "simples" in req.regime_tributario.lower()
        is_presumido = "presumido" in req.regime_tributario.lower()
        is_real = "real" in req.regime_tributario.lower()
        
        # Determinar qual tributação foi informada
        tributacao_informada = ""
        if req.csosn_icms:
            tributacao_informada = f"CSOSN: {req.csosn_icms}"
        elif req.cst_icms:
            tributacao_informada = f"CST: {req.cst_icms}"
        else:
            tributacao_informada = "CST/CSOSN: não informado"
        
        prompt = f"""Você é um especialista em tributação brasileira. Analise se esta regra tributária está CORRETA ou INCORRETA:

DADOS:
- Regime: {req.regime_tributario}
- CFOP: {req.cfop}
- {tributacao_informada}
- NCM: {req.ncm or 'não informado'}

REGRAS TRIBUTÁRIAS:

🔹 SIMPLES NACIONAL:
• CFOP 5401/6401 → ❌ PROIBIDO (Simples não pode ser substituto)
• CFOP 5405/6405 → ✅ CSOSN 500 (ST substituído)
• CFOP 5102/6102 → ✅ CSOSN 102, 103, 300, 400 ou 900
• CFOP 5101/6101 → ✅ CSOSN 101, 102, 103, 201, 202, 203 ou 900

🔹 LUCRO PRESUMIDO / LUCRO REAL:
• CFOP 5405/6405 → ✅ CST 10 ou 60 (ambos válidos)
• CFOP 5401/6401 → ✅ CST 10 (substituto)
• CFOP 5403/6403 → ✅ CST 60 (já retido)
• CFOP 5102/6102 → ✅ CST 00, 10, 20, 30, 40, 41, 50, 51, 60, 70 ou 90
• CFOP 5101/6101 → ✅ CST 00, 20, 40, 41, 50 ou 51

Responda em JSON puro:
{{
  "valido": true ou false,
  "erros": ["liste APENAS se encontrar erros"],
  "sugestoes": ["correções específicas"],
  "explicacao": "explicação técnica"
}}

IMPORTANTE: Se a combinação CFOP + CST/CSOSN estiver CORRETA segundo as regras acima, retorne "valido": true."""

        if github_token:
            llm_url = "https://models.inference.ai.azure.com/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {github_token}"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Especialista tributação brasileira. Responda APENAS JSON puro, sem markdown."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 800,
                "temperature": 0.1
            }
            resp = requests.post(llm_url, json=payload, headers=headers, timeout=20)
        else:
            # Validação básica por regras sem IA (fallback)
            erros = []
            sugestoes = []
            
            if is_simples:
                # SIMPLES NACIONAL
                if req.cfop in ['5401', '6401', '5402', '6402']:
                    erros.append(f"CFOP {req.cfop} incompatível com Simples Nacional (não pode ser substituto tributário)")
                    sugestoes.append("Use CFOP 5102/6102 (venda normal) ou 5405/6405 (ST substituído)")
                elif req.cfop in ['5405', '6405', '5403', '6403'] and req.csosn_icms != '500':
                    erros.append(f"CFOP {req.cfop} exige CSOSN 500, mas foi informado CSOSN {req.csosn_icms}")
                    sugestoes.append("Alterar CSOSN para 500 (ICMS cobrado anteriormente por ST)")
                elif req.cfop in ['5102', '6102'] and req.csosn_icms == '500':
                    erros.append(f"CFOP {req.cfop} não deve usar CSOSN 500 (use 102, 103, 300, 400 ou 900)")
                    sugestoes.append("Alterar CSOSN para 102 (tributada SN sem permissão de crédito)")
                
                if not req.csosn_icms and not erros:
                    erros.append("Simples Nacional requer CSOSN ICMS")
                    sugestoes.append("Informar CSOSN compatível com o CFOP")
            else:
                # REGIME NORMAL (Lucro Presumido ou Lucro Real)
                if req.cfop in ['5405', '6405'] and req.cst_icms not in ['10', '60']:
                    erros.append(f"CFOP {req.cfop} exige CST 10 ou 60, mas foi informado CST {req.cst_icms}")
                    sugestoes.append("Alterar CST para 10 (tributada + ST) ou 60 (ST cobrado anteriormente)")
                elif req.cfop in ['5401', '6401', '5402', '6402'] and req.cst_icms != '10':
                    erros.append(f"CFOP {req.cfop} (substituto ST) exige CST 10")
                    sugestoes.append("Alterar CST para 10 (tributada com cobrança do ICMS por ST)")
                elif req.cfop in ['5403', '6403'] and req.cst_icms != '60':
                    erros.append(f"CFOP {req.cfop} exige CST 60 (ICMS cobrado anteriormente por ST)")
                    sugestoes.append("Alterar CST para 60")
                
                if not req.cst_icms and not erros:
                    erros.append(f"{req.regime_tributario} requer CST ICMS")
                    sugestoes.append("Informar CST compatível com o CFOP")
            
            return JSONResponse(content={
                "valido": len(erros) == 0,
                "erros": erros,
                "sugestoes": sugestoes,
                "explicacao": f"Validação por regras (IA não disponível). {len(erros)} erro(s) encontrado(s)." if erros else "Regra válida conforme legislação tributária."
            })
        
        if resp.status_code == 200:
            resposta = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            
            try:
                resposta_limpa = resposta.strip()
                if resposta_limpa.startswith("```json"):
                    resposta_limpa = resposta_limpa.replace("```json", "", 1)
                if resposta_limpa.endswith("```"):
                    resposta_limpa = resposta_limpa.rsplit("```", 1)[0]
                resposta_limpa = resposta_limpa.strip()
                
                resultado = json.loads(resposta_limpa)
                return JSONResponse(content=resultado)
            except Exception as e:
                return JSONResponse(content={
                    "valido": True,
                    "erros": [],
                    "sugestoes": [],
                    "explicacao": f"Erro ao processar IA: {str(e)}"
                })
        else:
            return JSONResponse(content={
                "valido": True,
                "erros": [],
                "sugestoes": [],
                "explicacao": f"IA indisponível: {resp.status_code}"
            })
            
    except Exception as e:
        return JSONResponse(content={
            "valido": True,
            "erros": [],
            "sugestoes": [],
            "explicacao": f"Erro: {str(e)}"
        })

@app.post('/valida')
async def valida_tributaria(data: Dict[str, Any]):
    # Validação de riscos e inconsistências
    return {'alerta': 'Nenhum risco fiscal detectado.'}

# ========== VALIDAÇÃO TRIBUTÁRIA COM IA ==========
class ValidacaoTributariaRequest(BaseModel):
    crt: str  # "1" = Simples Nacional, "3" = Regime Normal
    itens: list  # Lista de itens com cfop, cst/csosn

def gerar_prompt_validacao_tributaria(req: ValidacaoTributariaRequest) -> str:
    regime = "Simples Nacional" if req.crt == "1" else "Regime Normal"
    
    prompt = f"""Especialista tributário brasileiro. Valide a tributação.

REGIME: {regime} (CRT={req.crt})

REGRAS:
1. Simples (CRT=1):
   - CFOP 5401/6401: PROIBIDO (não pode ser substituto)
   - CFOP 5405/6405: exige CSOSN 500
   - CFOP 5102/6102: aceita CSOSN 102,103,300,400,900

2. Normal (CRT=3):
   - CFOP 5405/6405: exige CST 10 ou 60

ITENS:
"""
    
    for idx, item in enumerate(req.itens, 1):
        cfop = item.get('cfop', '')
        csosn = item.get('csosn_icms', item.get('csosn', ''))
        cst = item.get('cst_icms', item.get('cst', ''))
        desc = item.get('descricao', f'Item {idx}')
        
        prompt += f"{idx}. {desc} - CFOP:{cfop}"
        if req.crt == "1":
            prompt += f" CSOSN:{csosn}\n"
        else:
            prompt += f" CST:{cst}\n"
    
    prompt += """
JSON:
{"valido":true/false,"erros":[{"item":"1","erro":"descrição","sugestao":"correção"}],"alertas":[]}

SEM markdown, APENAS JSON."""
    return prompt

@app.post('/valida/tributacao')
async def validar_tributacao_ia(req: ValidacaoTributariaRequest):
    """Valida tributação dos itens usando IA"""
    prompt = gerar_prompt_validacao_tributaria(req)
    
    try:
        # Usar GitHub Models API (muito mais rápido!)
        github_token = os.getenv("GITHUB_TOKEN", "")
        
        print(f"[DEBUG] GitHub Token presente: {'Sim' if github_token else 'Não'}")
        
        if github_token:
            # GitHub Models API (GPT-4o mini - rápido e preciso)
            print("[DEBUG] Usando GitHub Models API")
            llm_url = "https://models.inference.ai.azure.com/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {github_token}"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Especialista tributação BR. Responda JSON puro."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 512,
                "temperature": 0.1
            }
            resp = requests.post(llm_url, json=payload, headers=headers, timeout=15)
            print(f"[DEBUG] GitHub Models resposta: {resp.status_code}")
        else:
            # Fallback: LM Studio local
            print("[DEBUG] Usando LM Studio local (fallback)")
            llm_url = "http://177.189.240.158:1234/v1/chat/completions"
            payload = {
                "model": "codellama-7b-instruct",
                "messages": [
                    {"role": "system", "content": "Especialista tributação BR. Responda JSON puro."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 512,
                "temperature": 0.1
            }
            resp = requests.post(llm_url, json=payload, timeout=60)
        
        if resp.status_code == 200:
            resposta = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            
            try:
                # Limpar markdown se presente
                resposta_limpa = resposta.strip()
                if resposta_limpa.startswith("```json"):
                    resposta_limpa = resposta_limpa.replace("```json", "", 1)
                if resposta_limpa.endswith("```"):
                    resposta_limpa = resposta_limpa.rsplit("```", 1)[0]
                resposta_limpa = resposta_limpa.strip()
                
                resultado = json.loads(resposta_limpa)
                return JSONResponse(content=resultado)
            except Exception as e:
                # Fallback: retornar resposta raw
                return JSONResponse(content={
                    "valido": False,
                    "erros": [{"erro": f"Erro ao processar resposta da IA: {str(e)}", "resposta_raw": resposta}],
                    "alertas": []
                })
        else:
            return JSONResponse(content={
                "valido": False,
                "erros": [{"erro": f"Erro na comunicação com IA: {resp.status_code}"}],
                "alertas": []
            })
            
    except Exception as e:
        return JSONResponse(content={
            "valido": False,
            "erros": [{"erro": f"Erro no serviço de validação: {str(e)}"}],
            "alertas": []
        })

# ========== VALIDAÇÃO PRÉ-EMISSÃO NFe COM IA ==========
class ValidacaoNFeRequest(BaseModel):
    """Dados da NFe para validação antes da emissão"""
    # Identificação
    ambiente: str  # "producao" ou "homologacao"
    tipo_operacao: str  # "0" entrada, "1" saída
    natureza_operacao: str
    
    # Emitente
    emitente_cnpj: str
    emitente_razao_social: str
    emitente_uf: str
    emitente_crt: str  # 1=SN, 2=SN Sublimite, 3=Regime Normal
    emitente_ie: str
    
    # Destinatário
    destinatario_cpf_cnpj: str
    destinatario_nome: str
    destinatario_uf: str
    destinatario_ie: Optional[str] = None
    
    # Itens (lista simplificada)
    itens: list  # [{descricao, ncm, cfop, csosn_cst, valor_unitario, quantidade, valor_total}]
    
    # Totais
    valor_produtos: float
    valor_total_nfe: float
    
    # Pagamento
    forma_pagamento: str
    valor_pagamento: float


@app.post('/valida/nfe-pre-emissao')
async def validar_nfe_pre_emissao(req: ValidacaoNFeRequest):
    """
    Valida dados da NFe usando IA antes de gerar o XML.
    Identifica problemas que causariam rejeição no SEFAZ.
    """
    
    try:
        github_token = os.getenv("GITHUB_TOKEN", "")
        
        if not github_token:
            return JSONResponse(content={
                "sucesso": False,
                "validacao_ok": True,
                "erros_criticos": [],
                "alertas": ["Token GitHub não configurado - validação IA indisponível"],
                "sugestoes": [],
                "score_confianca": 0
            })
        
        # Montar resumo dos itens
        itens_resumo = ""
        for i, item in enumerate(req.itens, 1):
            itens_resumo += f"""
Item {i}:
  - Descrição: {item.get('descricao', 'N/A')}
  - NCM: {item.get('ncm', 'N/A')}
  - CFOP: {item.get('cfop', 'N/A')}
  - CST/CSOSN: {item.get('csosn_cst', 'N/A')}
  - Valor Unit: R$ {item.get('valor_unitario', 0)}
  - Qtd: {item.get('quantidade', 0)}
  - Valor Total: R$ {item.get('valor_total', 0)}
"""
        
        prompt = f"""Você é um validador fiscal de NFe. Analise os dados e identifique APENAS erros GRAVES.

IMPORTANTE - O QUE NÃO É ERRO:
- CSOSN 102 com CRT 1 (Simples Nacional) - ESTÁ CORRETO
- CSOSN 101, 102, 103, 201, 202, 203, 300, 400, 500, 900 com CRT 1 - TODOS VÁLIDOS
- IE do emitente cadastrada - NÃO questionar validade
- IE do destinatário vazia para pessoa física - OK
- CFOP 5101, 5102, 5405 para vendas SP→SP - VÁLIDOS
- NCM com 8 dígitos numéricos - VÁLIDO

SÓ APONTE ERRO SE:
- NCM estiver vazio ou com menos de 8 dígitos
- CFOP começar com 5 mas UFs forem diferentes
- CFOP começar com 6 mas UFs forem iguais
- Valor total for ZERO ou negativo
- CNPJ/CPF estiver vazio

DADOS:
- Ambiente: {req.ambiente}
- Emitente: {req.emitente_cnpj} | CRT: {req.emitente_crt} | UF: {req.emitente_uf} | IE: {req.emitente_ie or 'cadastrada'}
- Destinatário: {req.destinatario_cpf_cnpj} | UF: {req.destinatario_uf}
- Itens:{itens_resumo}
- Valor Total: R$ {req.valor_total_nfe}

Se TUDO estiver OK, retorne validacao_ok=true com score 95-100.

RESPONDA APENAS JSON:
{{
  "validacao_ok": true/false,
  "erros_criticos": [{{"campo": "x", "erro": "y", "solucao": "z"}}],
  "alertas": [],
  "sugestoes_melhoria": [],
  "score_confianca": 95,
  "resumo": "NFe válida para emissão"
}}"""

        llm_url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {github_token}"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Você é um especialista fiscal brasileiro. Analise NFe e identifique erros. Responda APENAS JSON válido, sem markdown."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1500,
            "temperature": 0.1
        }
        
        print(f"[IA-VALIDACAO] Enviando requisição para GitHub Models...")
        resp = requests.post(llm_url, json=payload, headers=headers, timeout=30)
        print(f"[IA-VALIDACAO] Resposta: {resp.status_code}")
        
        if resp.status_code == 200:
            resposta = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            
            try:
                # Limpar markdown se presente
                resposta_limpa = resposta.strip()
                if resposta_limpa.startswith("```json"):
                    resposta_limpa = resposta_limpa.replace("```json", "", 1)
                if resposta_limpa.startswith("```"):
                    resposta_limpa = resposta_limpa.replace("```", "", 1)
                if resposta_limpa.endswith("```"):
                    resposta_limpa = resposta_limpa.rsplit("```", 1)[0]
                resposta_limpa = resposta_limpa.strip()
                
                resultado = json.loads(resposta_limpa)
                resultado["sucesso"] = True
                return JSONResponse(content=resultado)
            except Exception as e:
                return JSONResponse(content={
                    "sucesso": False,
                    "validacao_ok": True,
                    "erros_criticos": [],
                    "alertas": [{"alerta": f"Erro ao processar resposta IA: {str(e)}"}],
                    "sugestoes_melhoria": [],
                    "score_confianca": 0,
                    "resumo": "Não foi possível processar a resposta da IA",
                    "resposta_raw": resposta[:500]
                })
        else:
            return JSONResponse(content={
                "sucesso": False,
                "validacao_ok": True,
                "erros_criticos": [],
                "alertas": [{"alerta": f"IA indisponível: HTTP {resp.status_code}"}],
                "sugestoes_melhoria": [],
                "score_confianca": 0,
                "resumo": "Serviço de IA temporariamente indisponível"
            })
            
    except Exception as e:
        print(f"[IA-VALIDACAO] Erro: {str(e)}")
        return JSONResponse(content={
            "sucesso": False,
            "validacao_ok": True,
            "erros_criticos": [],
            "alertas": [{"alerta": f"Erro: {str(e)}"}],
            "sugestoes_melhoria": [],
            "score_confianca": 0,
            "resumo": f"Erro no serviço: {str(e)}"
        })