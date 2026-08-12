import os
import requests
import json
from pathlib import Path
from dotenv import load_dotenv
## Removido: função duplicada gerar_prompt_sugestao
from fastapi import Body

# Carrega variáveis de ambiente tanto do diretório atual quanto da raiz do projeto.
_CURRENT_DIR = Path(__file__).resolve().parent
load_dotenv(_CURRENT_DIR / ".env")
load_dotenv(_CURRENT_DIR.parent / ".env")
load_dotenv(_CURRENT_DIR.parent / ".env.local", override=True)

_AI_PROVIDER_URL = os.getenv("AI_PROVIDER_URL", "").strip()
_AI_PROVIDER_MODEL = os.getenv("AI_PROVIDER_MODEL", "").strip()
_AI_PROVIDER_API_KEY = os.getenv("AI_PROVIDER_API_KEY", "").strip()
_LLM_FALLBACK_URL = os.getenv(
    "LLM_FALLBACK_URL",
    os.getenv("LLM_URL", "http://localhost:1234/v1/chat/completions"),
)
_LLM_FALLBACK_MODEL = os.getenv("LLM_MODEL", "codellama-7b-instruct").strip()

from fastapi import FastAPI, Request, Body
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Dict, Any, Optional

app = FastAPI()


def _resolve_llm_config(default_model: str, allow_fallback: bool = True) -> tuple[Optional[str], dict[str, str], Optional[str], str]:
    """Resolve provider principal por ambiente e fallback opcional."""
    if _AI_PROVIDER_URL:
        headers = {"Content-Type": "application/json"}
        if _AI_PROVIDER_API_KEY:
            headers["Authorization"] = f"Bearer {_AI_PROVIDER_API_KEY}"
        return _AI_PROVIDER_URL, headers, (_AI_PROVIDER_MODEL or default_model), "provider"

    if allow_fallback and _LLM_FALLBACK_URL:
        return _LLM_FALLBACK_URL, {"Content-Type": "application/json"}, (_LLM_FALLBACK_MODEL or default_model), "fallback"

    return None, {}, None, "unconfigured"


def _post_chat_completion(
    *,
    system_message: Optional[str],
    user_message: str,
    default_model: str,
    max_tokens: int,
    temperature: float,
    timeout: int,
    allow_fallback: bool = True,
) -> requests.Response:
    llm_url, headers, model_name, source = _resolve_llm_config(default_model=default_model, allow_fallback=allow_fallback)

    if not llm_url or not model_name:
        raise RuntimeError("Nenhum provider de IA configurado. Defina AI_PROVIDER_URL ou LLM_FALLBACK_URL.")

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    response = requests.post(llm_url, json=payload, headers=headers, timeout=timeout)
    response.llm_source = source
    response.llm_url = llm_url
    response.llm_model = model_name
    return response

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
        resp = _post_chat_completion(
            system_message="Especialista em classificação fiscal brasileira. Responda APENAS JSON puro, sem markdown.",
            user_message=prompt,
            default_model="gpt-4o-mini",
            max_tokens=512,
            temperature=0.2,
            timeout=60,
            allow_fallback=True,
        )
            
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

        llm_url, _headers, _model, _source = _resolve_llm_config(default_model="gpt-4o-mini", allow_fallback=False)
        if not llm_url:
            return JSONResponse(content={
                "valido": True,
                "erros": [],
                "avisos": ["Validação IA não disponível - provider não configurado"],
                "score_confianca": 0
            })
        resp = _post_chat_completion(
            system_message="Especialista NFe 4.0 Brasil. Responda JSON puro.",
            user_message=prompt,
            default_model="gpt-4o-mini",
            max_tokens=1024,
            temperature=0.1,
            timeout=20,
            allow_fallback=False,
        )
        
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

        llm_url, _headers, _model, _source = _resolve_llm_config(default_model="gpt-4o-mini", allow_fallback=False)
        if not llm_url:
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

        resp = _post_chat_completion(
            system_message="Especialista em tributação brasileira. Responda APENAS JSON puro.",
            user_message=prompt,
            default_model="gpt-4o-mini",
            max_tokens=512,
            temperature=0.1,
            timeout=30,
            allow_fallback=False,
        )
        
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
        resp = _post_chat_completion(
            system_message="Especialista tributação BR. Responda JSON puro.",
            user_message=prompt,
            default_model="gpt-4o-mini",
            max_tokens=512,
            temperature=0.1,
            timeout=60,
            allow_fallback=True,
        )
        
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
        llm_url, _headers, _model, _source = _resolve_llm_config(default_model="gpt-4o-mini", allow_fallback=False)
        if not llm_url:
            return JSONResponse(content={
                "sucesso": False,
                "validacao_ok": True,
                "erros_criticos": [],
                "alertas": ["Provider de IA não configurado - validação IA indisponível"],
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
- CFOP 5101, 5102, 5405 para vendas SP→SP (mesmo estado) - VÁLIDOS
- CFOP 6101, 6102, 6108, 6405 para vendas entre estados diferentes - VÁLIDOS
- NCM com 8 dígitos numéricos - VÁLIDO
- CRT 3 (Lucro Presumido) PODE SIM emitir CFOP 6xxx (interestadual) - TOTALMENTE VÁLIDO
- CRT 1, 2 ou 3 podem usar CFOP 5xxx ou 6xxx conforme a operação - TODOS VÁLIDOS
- CFOP 1xxx (1101, 1201, 1202, etc.) = entrada interna - VÁLIDO quando UF emitente = UF destinatário
- CFOP 2xxx (2101, 2201, 2202, etc.) = entrada interestadual - VÁLIDO quando UF emitente ≠ UF destinatário
- NF-e de DEVOLUÇÃO (finNFe=4) com CFOP 1201, 1202, 2201, 2202, 5201, 5202, 6201, 6202 - TODOS VÁLIDOS
- IE do destinatário inválida ou ausente gera indIEDest=9 automaticamente - NÃO é erro na validação prévia

SÓ APONTE ERRO SE:
- NCM estiver vazio ou com menos de 8 dígitos
- CFOP começar com 5 e UFs forem DIFERENTES (deveria ser 6xxx)
- CFOP começar com 6 e UFs forem IGUAIS (deveria ser 5xxx)
- CFOP começar com 1 e UFs forem DIFERENTES (deveria ser 2xxx)
- CFOP começar com 2 e UFs forem IGUAIS (deveria ser 1xxx)
- Valor total for ZERO ou negativo
- CNPJ/CPF estiver vazio

REGRAS CFOP:
- CFOP 1xxx: Entrada INTERNA - VÁLIDO somente se UF emitente = UF destinatário
- CFOP 2xxx: Entrada INTERESTADUAL - VÁLIDO somente se UF emitente ≠ UF destinatário
- CFOP 3xxx: Entrada EXTERIOR
- CFOP 5xxx: Saída INTERNA - VÁLIDO somente se UF emitente = UF destinatário
- CFOP 6xxx: Saída INTERESTADUAL - VÁLIDO somente se UF emitente ≠ UF destinatário
- CFOP 7xxx: Saída EXTERIOR
- NÃO existe restrição de CRT para nenhum CFOP!

EXEMPLOS CORRETOS (NÃO SÃO ERROS):
- CFOP 2202 com Emitente SP e Destinatário MT → CORRETO (2xxx = entrada interestadual, UFs diferentes = OK)
- CFOP 2201 com Emitente SP e Destinatário RJ → CORRETO (entrada interestadual)
- CFOP 6202 com Emitente SP e Destinatário MT → CORRETO (6xxx = saída interestadual, UFs diferentes = OK)
- CFOP 5202 com Emitente SP e Destinatário SP → CORRETO (5xxx = saída interna, mesma UF = OK)
- CFOP 1202 com Emitente SP e Destinatário SP → CORRETO (1xxx = entrada interna, mesma UF = OK)

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

        print(f"[IA-VALIDACAO] Enviando requisição para provider configurado...")
        resp = _post_chat_completion(
            system_message="Você é um especialista fiscal brasileiro. Analise NFe e identifique erros. Responda APENAS JSON válido, sem markdown.",
            user_message=prompt,
            default_model="gpt-4o-mini",
            max_tokens=1500,
            temperature=0.1,
            timeout=30,
            allow_fallback=False,
        )
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


# =====================================================================
# VALIDAÇÃO DE REGRAS TRIBUTÁRIAS DE SERVIÇO (NFS-e)
# =====================================================================

class ValidacaoRegraServicoRequest(BaseModel):
    tipo: str
    codigo_servico_lc116: str
    codigo_nbs: Optional[str] = None
    descricao_servico: Optional[str] = None
    aliquota_iss: Optional[str] = None
    iss_retido: Optional[bool] = False
    cst_ibs_cbs: Optional[str] = None
    regime_tributario_id: Optional[int] = None
    regime_tributario_nome: Optional[str] = None


@app.post('/valida/regra-servico')
async def validar_regra_servico(req: ValidacaoRegraServicoRequest):
    """
    Valida regra tributária de serviço (NFS-e) - LC 116/2003 e Reforma Tributária
    """
    try:
        github_token = os.getenv("GITHUB_TOKEN", "")
        
        # Construir prompt de validação
        prompt = f"""Você é um especialista em tributação de serviços no Brasil (ISS, LC 116/2003 e Reforma Tributária LC 214/2025).

Analise se esta regra tributária de NFS-e está CORRETA ou INCORRETA:

DADOS INFORMADOS:
- Código Serviço LC116: {req.codigo_servico_lc116}
- Código NBS: {req.codigo_nbs or 'não informado'}
- Descrição: {req.descricao_servico or 'não informada'}
- Alíquota ISS: {req.aliquota_iss}%
- ISS Retido: {'Sim' if req.iss_retido else 'Não'}
- CST IBS/CBS: {req.cst_ibs_cbs or 'não informado'}
- Regime Tributário: {req.regime_tributario_nome or 'não informado'}

CONHECIMENTO BASE OFICIAL (Receita Federal e Gov.br):

📌 LC 116/2003 - LISTA DE SERVIÇOS:
A Lista de Serviços está organizada em 40 categorias (1.00 a 40.01).
Exemplos:
• 1.01 - Análise e desenvolvimento de sistemas
• 1.02 - Programação
• 1.03 - Processamento, armazenamento ou hospedagem de dados
• 17.05 - Fornecimento de mão-de-obra (exceto temporária)
• 17.09 - Perícias, laudos, exames técnicos

📌 CÓDIGO NBS (Nomenclatura Brasileira de Serviços):
• Estrutura: 9 dígitos no formato X.XXXX (ex: 1.0101, 1.0102)
• Obrigatório a partir de 2026 (Reforma Tributária LC 214/2025)
• Cada código LC116 pode ter MÚLTIPLOS códigos NBS associados
• O código NBS especifica COM MAIS DETALHE o serviço dentro da categoria LC116
• NÃO há relação 1:1 entre LC116 e NBS - é uma hierarquia (1 LC116 → N códigos NBS)

IMPORTANTE SOBRE NBS:
- Um código LC116 (ex: 1.02) pode ter vários NBS diferentes (1.0201, 1.0202, 1.0203...)
- O sistema armazena a relação no banco de dados (tabela servicos_lc116_nbs)
- Se o NBS informado está cadastrado no sistema, considere VÁLIDO
- NÃO invalide se o NBS não estiver "relacionado" - pode ser um cadastro novo válido

📌 ISS (Imposto Sobre Serviços):
• Alíquota: entre 2% e 5% conforme município (LC 116/2003)
• São José do Rio Preto-SP: 5% (padrão), 2% (construção civil, alguns serviços)
• ISS Retido: tomador retém quando for pessoa jurídica e serviço específico permitir
• Base de cálculo: preço do serviço

📌 REFORMA TRIBUTÁRIA (LC 214/2025 - Emenda Constitucional 132/2023):

CST IBS/CBS - Código de Situação Tributária (3 dígitos):
• 001 - Tributado integralmente (PADRÃO para todos os regimes)
• 002 - Tributado com redução de base de cálculo
• 003 - Diferido
• 004 - Isento (incentivos fiscais específicos)
• 005 - Não tributado (fora do campo de incidência)
• 006 - Suspenso por decisão judicial
• 007 - Suspenso por procedimento administrativo
• 008 - Não incidência

IBS (Imposto sobre Bens e Serviços):
• Substitui ICMS nos estados e ISS nos municípios
• Alíquota padrão: 27,5% (estimativa 2026-2033)
• Período de transição: 2026-2033
• Aplicável a TODOS os regimes (Simples, Presumido, Real)

CBS (Contribuição sobre Bens e Serviços):
• Substitui PIS e COFINS
• Alíquota padrão: 12% (estimativa 2026-2033)
• Aplicável a TODOS os regimes (Simples, Presumido, Real)

SIMPLES NACIONAL E REFORMA TRIBUTÁRIA:
• CST IBS/CBS 001 (Tributado) É VÁLIDO para Simples Nacional
• Empresas do Simples pagarão IBS/CBS de forma simplificada via DAS
• Alíquotas já incluídas nos anexos do Simples Nacional
• Não há incompatibilidade entre Simples e CST 001

📌 VALIDAÇÕES QUE VOCÊ DEVE FAZER:
1. ✅ Alíquota ISS entre 2% e 5%
2. ✅ Código LC116 deve estar no formato correto (ex: 1.01, 17.05)
3. ✅ CST IBS/CBS deve estar entre 001 e 008
4. ❌ NÃO invalidar por "NBS não relacionado" - pode ser cadastro novo válido
5. ❌ NÃO invalidar CST 001 para Simples Nacional - é compatível

Responda APENAS em JSON puro (sem markdown):
{{
  "valido": true ou false,
  "erros": ["liste APENAS erros REAIS baseados nas regras acima"],
  "sugestoes": ["correções específicas apenas se houver erro"],
  "explicacao": "explicação técnica curta e objetiva"
}}

IMPORTANTE: 
- Seja GENEROSO na validação - aceite se estiver tecnicamente correto
- NÃO crie erros fictícios sobre "relação NBS/LC116" - o banco controla isso
- CST 001 é VÁLIDO para qualquer regime incluindo Simples Nacional
- Se os valores estão dentro dos parâmetros legais, retorne "valido": true"""

        llm_url, _headers, _model, _source = _resolve_llm_config(default_model="gpt-4o-mini", allow_fallback=False)
        if llm_url:
            resp = _post_chat_completion(
                system_message="Especialista em tributação de serviços no Brasil. Responda APENAS JSON puro, sem markdown.",
                user_message=prompt,
                default_model="gpt-4o-mini",
                max_tokens=1000,
                temperature=0.1,
                timeout=20,
                allow_fallback=False,
            )

            if resp.status_code == 200:
                resposta = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                
                try:
                    # Limpar markdown se houver
                    resposta_limpa = resposta.strip()
                    if resposta_limpa.startswith("```json"):
                        resposta_limpa = resposta_limpa.replace("```json", "").replace("```", "").strip()
                    elif resposta_limpa.startswith("```"):
                        resposta_limpa = resposta_limpa.replace("```", "").strip()
                    
                    resultado = json.loads(resposta_limpa)
                    
                    # Garantir estrutura mínima
                    if "valido" not in resultado:
                        resultado["valido"] = True
                    if "erros" not in resultado:
                        resultado["erros"] = []
                    if "sugestoes" not in resultado:
                        resultado["sugestoes"] = []
                    if "explicacao" not in resultado:
                        resultado["explicacao"] = "Regra analisada com sucesso."
                    
                    return JSONResponse(content=resultado)
                    
                except json.JSONDecodeError as e:
                    print(f"[IA-VALIDACAO-SERVICO] Erro ao parsear JSON: {str(e)}")
                    print(f"[IA-VALIDACAO-SERVICO] Resposta raw: {resposta[:500]}")
                    
                    return JSONResponse(content={
                        "valido": True,
                        "erros": [],
                        "sugestoes": [],
                        "explicacao": "Não foi possível validar com IA. Resposta fora do formato esperado."
                    })
            else:
                print(f"[IA-VALIDACAO-SERVICO] Erro HTTP {resp.status_code}: {resp.text}")
                return JSONResponse(content={
                    "valido": True,
                    "erros": [],
                    "sugestoes": [],
                    "explicacao": "Serviço de IA temporariamente indisponível."
                })
        else:
            # Validação básica sem IA (fallback)
            erros = []
            sugestoes = []
            
            # Validar alíquota ISS
            try:
                aliquota = float(req.aliquota_iss or 0)
                if aliquota < 2 or aliquota > 5:
                    erros.append(f"Alíquota ISS de {aliquota}% está fora do intervalo permitido (2% a 5%)")
                    sugestoes.append("Ajustar alíquota ISS entre 2% e 5% conforme legislação municipal")
            except:
                pass
            
            # Validar código LC116
            if not req.codigo_servico_lc116:
                erros.append("Código de Serviço LC 116 é obrigatório")
                sugestoes.append("Informar um código válido da Lista de Serviços LC 116/2003")
            
            # Validar código NBS (obrigatório a partir de 2026)
            if not req.codigo_nbs:
                erros.append("Código NBS será obrigatório a partir de 2026 (Reforma Tributária)")
                sugestoes.append("Informar o código NBS correspondente ao serviço")
            
            return JSONResponse(content={
                "valido": len(erros) == 0,
                "erros": erros,
                "sugestoes": sugestoes,
                "explicacao": f"Validação por regras básicas (IA não disponível). {len(erros)} erro(s) encontrado(s)." if erros else "Regra válida conforme validação básica."
            })
            
    except Exception as e:
        print(f"[IA-VALIDACAO-SERVICO] Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return JSONResponse(content={
            "valido": True,
            "erros": [],
            "sugestoes": [],
            "explicacao": f"Erro ao validar: {str(e)}"
        })


# =====================================================================
# VALIDAÇÃO DE NFS-e ANTES DA EMISSÃO
# =====================================================================

class ValidacaoNFSeRequest(BaseModel):
    ambiente: str
    tipo_documento: str
    prestador: Optional[Dict[str, Any]] = None
    tomador: Optional[Dict[str, Any]] = None
    servico: Optional[Dict[str, Any]] = None
    reforma_tributaria: Optional[Dict[str, Any]] = None
    informacoes_complementares: Optional[str] = None


@app.post('/valida/nfse-pre-emissao')
async def validar_nfse_pre_emissao(req: ValidacaoNFSeRequest):
    """
    Valida dados da NFS-e usando IA antes da emissão.
    Identifica problemas fiscais, tributários e de conformidade.
    """
    
    try:
        llm_url, _headers, _model, _source = _resolve_llm_config(default_model="gpt-4o-mini", allow_fallback=False)
        if not llm_url:
            return JSONResponse(content={
                "sucesso": False,
                "validacao_ok": True,
                "erros_criticos": [],
            "alertas": [{"alerta": "Provider de IA não configurado - validação IA indisponível"}],
                "sugestoes_melhoria": [],
                "score_confianca": 0,
                "resumo": "IA indisponível"
            })
        
        # Extrair dados principais
        prestador = req.prestador or {}
        tomador = req.tomador or {}
        servico = req.servico or {}
        reforma = req.reforma_tributaria or {}
        
        # Construir prompt de validação
        prompt = f"""Você é um especialista em NFS-e e tributação de serviços no Brasil.

Analise os dados desta NFS-e e identifique APENAS erros GRAVES ou CRÍTICOS que impediriam a emissão.

IMPORTANTE - O QUE NÃO É ERRO:
- Regime tributário Simples Nacional com ISS - VÁLIDO
- Alíquota ISS entre 2% e 5% - VÁLIDA
- CST IBS/CBS 001 para todos os regimes - VÁLIDO
- Código NBS relacionado ao LC116 - VÁLIDO (sistema valida relação)
- IE do prestador cadastrada - NÃO questionar
- CPF/CNPJ em formato válido - OK

SÓ APONTE ERRO SE:
- Código de Serviço LC116 estiver vazio ou inválido
- Valor do serviço for ZERO ou negativo
- CNPJ do Prestador estiver vazio ou inválido
- CNPJ/CPF do Tomador estiver vazio
- Alíquota ISS fora de 2-5%
- Discriminação do serviço estiver vazia
- CST IBS/CBS fora da faixa 001-008

DADOS DA NFS-e:
Ambiente: {req.ambiente}
Tipo: {req.tipo_documento}

PRESTADOR:
- CNPJ: {prestador.get('cnpj', 'N/A')}
- Razão Social: {prestador.get('razao_social', 'N/A')}
- Município: {prestador.get('municipio', 'N/A')} - {prestador.get('uf', 'N/A')}

TOMADOR:
- CPF/CNPJ: {tomador.get('cpf_cnpj', 'N/A')}
- Nome/Razão: {tomador.get('nome_razao', 'N/A')}
- Município: {tomador.get('municipio', 'N/A')} - {tomador.get('uf', 'N/A')}

SERVIÇO:
- Código LC116: {servico.get('codigo_servico', 'N/A')}
- Discriminação: {servico.get('discriminacao', 'N/A')[:100]}...
- Valor do Serviço: R$ {servico.get('valor_servicos', 0)}
- Alíquota ISS: {servico.get('aliquota_iss', 0)}%
- Valor ISS: R$ {servico.get('valor_iss', 0)}
- Base de Cálculo: R$ {servico.get('base_calculo', 0)}

REFORMA TRIBUTÁRIA:
- CST IBS/CBS: {reforma.get('cst_ibs_cbs', 'N/A')}
- Indicador Consumidor Final: {reforma.get('indicador_consumidor_final', 'N/A')}
- Percentual Tributos Federais: {reforma.get('percentual_tributos_federais', 0)}%
- Percentual Redutor: {reforma.get('percentual_redutor', 0)}%

Se TUDO estiver OK, retorne validacao_ok=true com score 95-100.

RESPONDA APENAS JSON válido (sem markdown):
{{
  "sucesso": true,
  "validacao_ok": true/false,
  "erros_criticos": [{{"campo": "x", "erro": "y", "solucao": "z"}}],
  "alertas": [{{"campo": "x", "alerta": "y", "sugestao": "z"}}],
  "sugestoes_melhoria": ["sugestão 1", "sugestão 2"],
  "score_confianca": 95,
  "resumo": "NFS-e válida para emissão"
}}"""

        print(f"[IA-VALIDACAO-NFSE] Enviando requisição para provider configurado...")
        resp = _post_chat_completion(
            system_message="Você é um especialista fiscal brasileiro em NFS-e. Analise os dados e identifique erros. Responda APENAS JSON válido, sem markdown.",
            user_message=prompt,
            default_model="gpt-4o-mini",
            max_tokens=2000,
            temperature=0.1,
            timeout=30,
            allow_fallback=False,
        )
        print(f"[IA-VALIDACAO-NFSE] Resposta: {resp.status_code}")
        
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
                print(f"[IA-VALIDACAO-NFSE] Erro ao parsear JSON: {str(e)}")
                print(f"[IA-VALIDACAO-NFSE] Resposta bruta: {resposta[:500]}")
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
            print(f"[IA-VALIDACAO-NFSE] Erro HTTP {resp.status_code}: {resp.text}")
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
        print(f"[IA-VALIDACAO-NFSE] Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return JSONResponse(content={
            "sucesso": False,
            "validacao_ok": True,
            "erros_criticos": [],
            "alertas": [{"alerta": f"Erro: {str(e)}"}],
            "sugestoes_melhoria": [],
            "score_confianca": 0,
            "resumo": f"Erro no serviço: {str(e)}"
        })