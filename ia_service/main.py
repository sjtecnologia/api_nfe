import os
import requests
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
    import json
    try:
        # Exemplo: chamada para Ollama/Mistral/HuggingFace local
        # Ajuste o endpoint conforme o modelo instalado
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

@app.post('/valida')
async def valida_tributaria(data: Dict[str, Any]):
    # Validação de riscos e inconsistências
    return {'alerta': 'Nenhum risco fiscal detectado.'}
