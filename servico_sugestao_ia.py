"""
🦙 Serviço de Sugestão IA Integrado com NCM + LLM + CEST
Combina o gerador de prompts NCM com consulta à Llama-3.1-8B para resposta rápida
"""

import requests
import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass

# Importar base de CEST
try:
    from cest_database import buscar_cest_por_produto, CEST_DATABASE
    CEST_DISPONIVEL = True
    print("[OK] Base CEST carregada com sucesso")
except ImportError:
    CEST_DISPONIVEL = False
    buscar_cest_por_produto = None
    CEST_DATABASE = None
    print("[AVISO] Base CEST nao disponivel")

@dataclass
class SugestaoRequest:
    """Dados para solicitação de sugestão tributária"""
    descricao: str
    tipo_item: str
    cliente_id: Optional[int] = None
    uf_origem: Optional[str] = None
    regime_tributario: Optional[str] = None
    unidade_comercial: Optional[str] = "UN"
    codigo_interno: Optional[str] = None

class ServicoSugestaoIA:
    """Serviço integrado para sugestão tributária usando NCM + LLM"""
    
    def __init__(self, 
                 ncm_api_url: str = "http://localhost:8081",
                 llm_url: str = "http://192.168.0.52:1234"):
        self.ncm_api_url = ncm_api_url
        self.llm_url = llm_url
        
        # System prompt otimizado para Llama-3.1-8B com Lei Complementar 214/2025 (Reforma Tributária)
        self.system_prompt = """Você é especialista em classificação NCM e Lei Complementar 214/2025.

FORMATO JSON (preencha com dados reais do produto):
{
  "ncm": "código de 8 dígitos",
  "cfop": "5101",
  "cst": "00",
  "csosn": "101",
  "cest": null,
  "explicacao": "descreva o NCM e cite benefícios da LC 214/2025"
}

BENEFÍCIOS LC 214/2025 (sempre mencione na explicação):
- Café (NCM inicia com 09.01): Anexo I - redução 100% IBS/CBS Cesta Básica
- Ovos (NCM inicia com 04.07): Anexo XV - redução 100% IBS/CBS
- TODAS Hortaliças (NCM inicia com 07): Anexo XV - redução 100% IBS/CBS
- TODAS Frutas (NCM inicia com 08): Anexo XV - redução 100% IBS/CBS

Se NCM começa com 07 ou 08, SEMPRE cite: "Anexo XV LC 214/2025 - redução 100% IBS/CBS"."""

    def buscar_ncm_oficial(self, produto: str, limite: int = 3) -> List[Dict]:
        """Busca NCMs na API oficial"""
        try:
            # 1. Verificar se há NCM direto conhecido
            ncm_direto = self._obter_ncm_direto(produto)
            if ncm_direto:
                # Busca os detalhes deste NCM específico
                response = requests.get(
                    f"{self.ncm_api_url}/api/llm/ncms/search",
                    params={"q": ncm_direto, "tipo": "analitico", "limit": 1},
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    resultados = data.get("resultados", [])
                    if resultados:
                        print(f"✅ Usando NCM direto: {ncm_direto}")
                        return resultados
            
            # 2. Tentar busca com produto completo
            print(f"🔍 Buscando NCMs para: {produto}")
            response = requests.get(
                f"{self.ncm_api_url}/api/llm/ncms/search",
                params={"q": produto, "tipo": "analitico", "limit": limite},
                timeout=10
            )
            
            print(f"📡 Status API: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                resultados = data.get("resultados", [])
                print(f"📊 Encontrados {len(resultados)} NCMs")
                
                # Se não encontrar, tentar com palavras-chave
                if len(resultados) == 0:
                    palavras_chave = self._extrair_palavras_chave(produto)
                    for palavra in palavras_chave:
                        print(f"🔍 Tentando palavra-chave: {palavra}")
                        response = requests.get(
                            f"{self.ncm_api_url}/api/llm/ncms/search",
                            params={"q": palavra, "tipo": "analitico", "limit": limite},
                            timeout=10
                        )
                        if response.status_code == 200:
                            data = response.json()
                            novos_resultados = data.get("resultados", [])
                            if novos_resultados:
                                print(f"✅ Encontrados {len(novos_resultados)} NCMs com '{palavra}'")
                                return novos_resultados[:limite]
                
                return resultados
        except Exception as e:
            print(f"❌ Erro na API NCM: {e}")
        return []

    def _obter_ncm_direto(self, produto: str) -> Optional[str]:
        """
        Retorna NCM direto para casos conhecidos e críticos
        Evita classificação errada pela LLM
        """
        produto_lower = produto.lower()
        
        # Dicionário de produtos específicos com NCM correto
        ncm_direto = {
            # Software e Serviços de TI (TODOS retornam 38210000)
            'desenvolvimento de sistema': '38210000',
            'desenvolvimento de software': '38210000',
            'sistema de computador': '38210000',
            'sistema personalizado': '38210000',
            'software': '38210000',
            'programa de computador': '38210000',
            'aplicativo': '38210000',
            'aplicação': '38210000',
            'app ': '38210000',
            'mobile': '38210000',
            'android': '38210000',
            'ios': '38210000',
            'web': '38210000',
            'site': '38210000',
            'portal': '38210000',
            'plataforma': '38210000',
            'sistema web': '38210000',
            'sistema mobile': '38210000',
            'licença': '38210000',
            'sob medida': '38210000',
            'customizado': '38210000',
            'personalizado': '38210000',
            'erp': '38210000',
            'crm': '38210000',
            'api': '38210000',
            'backend': '38210000',
            'frontend': '38210000',
            
            # Eletrônicos comuns
            'mouse': '84716053',
            'teclado': '84716052',
            'monitor': '85285900',
            'impressora': '84433210',
            'notebook': '84713000',
            'smartphone': '85171300',
            'tablet': '85171300',
            
            # Cabos e acessórios
            'cabo hdmi': '85444900',
            'cabo usb': '85444900',
            'carregador': '85044030',
            'fonte de alimentação': '85044030',
            
            # Livros e mídia
            'livro': '49011000',
            'revista': '49021000',
            'cd': '85234920',
            'dvd': '85234920',
            
            # Bebidas e alimentos
            'cerveja': '22030000',
            'refrigerante': '22021000',
            'água mineral': '22011000',
            'café': '09012100',
            'açúcar': '17011400',
            'leite': '04012000',
            
            # Combustíveis
            'gasolina': '27101921',
            'diesel': '27101912',
            'etanol': '22071000',
            'álcool': '22071000',
            
            # Higiene e limpeza
            'sabonete': '34011190',
            'detergente': '34022000',
            'desinfetante': '38089290',
            'água sanitária': '28281010',
            'amaciante': '34024290',
            
            # Cosméticos e perfumaria
            'perfume': '33030010',
            'desodorante': '33072000',
            'batom': '33041000',
            'esmalte': '33043000',
            'maquiagem': '33049900',
        }
        
        # Verifica correspondências
        for chave, ncm in ncm_direto.items():
            if chave in produto_lower:
                print(f"✅ NCM direto encontrado: {produto} → {ncm} ({chave})")
                return ncm
        
        return None

    def _extrair_palavras_chave(self, produto: str) -> List[str]:
        """Extrai palavras-chave do produto para busca"""
        palavras_comum = {
            # Eletrônicos
            'smartphone': ['smartphone', 'telefone', 'celular'],
            'notebook': ['notebook', 'computador', 'laptop'],
            'mouse': ['mouse', 'rato'],
            'teclado': ['teclado'],
            'monitor': ['monitor', 'display', 'tela'],
            'impressora': ['impressora'],
            'computador': ['computador', 'pc', 'desktop'],
            
            # Alimentos e bebidas
            'café': ['café', 'coffee'],
            'açúcar': ['açúcar', 'sugar'],
            'cerveja': ['cerveja', 'beer'],
            'refrigerante': ['refrigerante', 'bebida gaseificada'],
            'água': ['água', 'water'],
            'leite': ['leite', 'milk'],
            
            # Combustíveis
            'gasolina': ['gasolina', 'combustível'],
            'diesel': ['diesel', 'óleo diesel'],
            'etanol': ['etanol', 'álcool', 'alcool'],
            
            # Autopeças
            'pneu': ['pneu', 'tire'],
            'bateria': ['bateria', 'acumulador'],
            'amortecedor': ['amortecedor'],
            'filtro': ['filtro'],
            
            # Higiene e limpeza
            'shampoo': ['shampoo', 'xampu', 'champô'],
            'condicionador': ['condicionador'],
            'sabonete': ['sabonete'],
            'detergente': ['detergente'],
            'desinfetante': ['desinfetante'],
            'amaciante': ['amaciante'],
            
            # Cosméticos
            'perfume': ['perfume', 'colônia', 'fragrância'],
            'desodorante': ['desodorante'],
            'batom': ['batom'],
            'esmalte': ['esmalte'],
            'maquiagem': ['maquiagem'],
            
            # Materiais de construção
            'cimento': ['cimento'],
            'tinta': ['tinta'],
            'argamassa': ['argamassa'],
            
            # Materiais elétricos
            'lâmpada': ['lâmpada', 'lampada'],
            'fio': ['fio', 'cabo'],
            'tomada': ['tomada'],
            'interruptor': ['interruptor']
        }
        
        produto_lower = produto.lower()
        
        # Verificar palavras conhecidas
        for key, variants in palavras_comum.items():
            if any(variant in produto_lower for variant in variants):
                return variants[:2]  # Retorna até 2 variantes
        
        # Fallback: usar palavras do produto
        palavras = produto.lower().split()
        return [palavra for palavra in palavras if len(palavra) > 3][:2]

    def gerar_prompt_classificacao(self, request: SugestaoRequest) -> str:
        """Gera prompt completo para classificação"""
        produto = request.descricao
        
        # Busca NCMs oficiais
        ncms = self.buscar_ncm_oficial(produto)
        
        if not ncms:
            return f"Não foram encontrados NCMs para '{produto}' na base oficial."
        
        prompt = f"""Baseado nos dados NCM oficiais abaixo, classifique "{produto}":

**DADOS NCM OFICIAIS ENCONTRADOS:**

"""
        
        for i, ncm in enumerate(ncms, 1):
            tipo_status = "✅ Pode usar" if ncm.get('tipo') == 'analitico' else "❌ Não usar em NFe"
            prompt += f"""{i}. **NCM {ncm.get('codigo_formatado', ncm.get('codigo', ''))}**
   Descrição: {ncm.get('descricao', '')}
   Tipo: {ncm.get('tipo', '').title()}
   Status NFe: {tipo_status}

"""
        
        # Adiciona contexto do cliente se disponível
        if request.uf_origem:
            prompt += f"**CONTEXTO FISCAL:**\n"
            prompt += f"- UF Origem: {request.uf_origem}\n"
            if request.regime_tributario:
                prompt += f"- Regime: {request.regime_tributario}\n"
            prompt += "\n"
        
        prompt += f"""**INSTRUÇÃO:** Classifique "{produto}" para Nota Fiscal Eletrônica.

**RESPOSTA OBRIGATÓRIA (JSON):**"""
        
        return prompt

    async def consultar_llm(self, prompt: str) -> Dict:
        """Consulta a LLM com o prompt gerado"""
        try:
            payload = {
                "model": "meta-llama-3.1-8b-instruct",  # Nome correto do modelo
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 200,  # Reduzido para 200 tokens = resposta mais rápida
                "temperature": 0.1,  # Mais determinística
            }
            
            print(f"🤖 Consultando LLM...")
            start_time = time.time()
            
            response = requests.post(
                f"{self.llm_url}/v1/chat/completions",
                json=payload,
                timeout=120  # Timeout aumentado para 120s para LLM lenta
            )
            
            elapsed = time.time() - start_time
            print(f"⏱️ LLM respondeu em {elapsed:.2f}s")
            
            if response.status_code == 200:
                data = response.json()
                resposta = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Limpar e parsear resposta
                return self._parsear_resposta_llm(resposta)
            else:
                return {"erro": f"Erro LLM: {response.status_code} - {response.text}"}
                
        except requests.exceptions.Timeout:
            print("⏰ Timeout da LLM - usando fallback")
            return self._gerar_resposta_fallback(prompt)
        except Exception as e:
            print(f"❌ Erro LLM - usando fallback: {e}")
            return self._gerar_resposta_fallback(prompt)

    def _gerar_resposta_fallback(self, prompt: str) -> Dict:
        """Gera resposta básica quando LLM não está disponível"""
        # Extrair dados do NCM do prompt
        import re
        
        # Buscar código NCM no prompt
        ncm_match = re.search(r'\*\*NCM (\d{2}\.\d{2}\.\d{2}\.\d{2})\*\*', prompt)
        if ncm_match:
            ncm = ncm_match.group(1).replace('.', '')
            
            # Buscar UF para determinar CFOP
            cfop = "5101"  # Padrão venda dentro do estado
            if "UF Origem:" in prompt:
                cfop = "5101"  # Pode ser melhorado com lógica de UF
            
            return {
                "ncm": ncm,
                "cfop": cfop,
                "cst": "00",
                "csosn": "101", 
                "cest": None,
                "explicacao": "Classificação automática baseada no NCM encontrado (LLM indisponível)",
                "modo": "fallback-ncm"
            }
        
        # Se não encontrou NCM no prompt, tentar extrair do texto
        # Buscar descrição do produto
        produto_match = re.search(r'Produto/Serviço:\s*(.+)', prompt)
        if produto_match:
            produto = produto_match.group(1).strip()
            print(f"🔄 Usando fallback para produto: {produto}")
            # Criar um SugestaoRequest básico e chamar _gerar_sugestao_basica
            from dataclasses import dataclass
            request = SugestaoRequest(
                descricao=produto,
                tipo_item='Produto',
                uf_origem='SP',
                regime_tributario='Simples Nacional'
            )
            return self._gerar_sugestao_basica(request)
        
        # Último recurso
        return {
            "ncm": "00000000",
            "cfop": "5101",
            "cst": None,
            "csosn": "101", 
            "cest": None,
            "explicacao": "Sugestão genérica (APIs indisponíveis). ATENÇÃO: Revise e corrija o NCM!",
            "modo": "fallback-generico"
        }

    def _parsear_resposta_llm(self, resposta: str) -> Dict:
        """Parseia e limpa a resposta da LLM"""
        try:
            # Remove markdown se presente
            resposta_limpa = resposta.strip()
            if resposta_limpa.startswith("```json"):
                resposta_limpa = resposta_limpa.replace("```json", "", 1)
            if resposta_limpa.endswith("```"):
                resposta_limpa = resposta_limpa.rsplit("```", 1)[0]
            resposta_limpa = resposta_limpa.strip()
            
            # Tentar parsear JSON
            resultado = json.loads(resposta_limpa)
            
            # Validar campos obrigatórios
            if not isinstance(resultado, dict):
                return {"erro": "Resposta não é um objeto JSON válido"}
            
            # Garantir que temos pelo menos NCM
            if not resultado.get("ncm"):
                return {"erro": "LLM não retornou código NCM"}
            
            return resultado
            
        except json.JSONDecodeError as e:
            return {
                "erro": f"Resposta JSON inválida: {str(e)}", 
                "resposta_bruta": resposta
            }

    def _gerar_sugestao_basica(self, request: SugestaoRequest) -> Dict:
        """Gera sugestão básica usando regras heurísticas quando APIs não estão disponíveis"""
        produto_lower = request.descricao.lower()
        
        # NCM genérico baseado em palavras-chave (produtos mais comuns)
        ncm_map = {
            # Informática
            'software': '85234910',
            'sistema': '85234910',
            'programa': '85234910',
            'mouse': '84716053',
            'teclado': '84716052',
            'monitor': '85285900',
            'computador': '84713000',
            'notebook': '84713010',
            'impressora': '84433210',
            'scanner': '84716051',
            'webcam': '85258020',
            'pendrive': '85235190',
            'hd externo': '84717012',
            'ssd': '84717012',
            
            # Celulares e Tablets
            'celular': '85171231',
            'smartphone': '85171231',
            'iphone': '85171231',
            'tablet': '85171270',
            'ipad': '85171270',
            
            # Eletrônicos
            'tv': '85287190',
            'televisão': '85287190',
            'televisao': '85287190',
            'ar condicionado': '84151011',
            'geladeira': '84182100',
            'micro-ondas': '85165000',
            'fogão': '85163100',
            'fogao': '85163100',
            'ventilador': '84145100',
            
            # Móveis e Decoração
            'cadeira': '94013000',
            'mesa': '94036000',
            'estante': '94035000',
            'sofá': '94011000',
            'sofa': '94011000',
            
            # Vestuário
            'camiseta': '61091000',
            'calça': '62034200',
            'calca': '62034200',
            'jaqueta': '62033100',
            'sapato': '64041100',
            'tênis': '64041900',
            'tenis': '64041900',
            
            # Livros e Papelaria
            'livro': '49019900',
            'caderno': '48201000',
            'caneta': '96081000',
            'lápis': '96091000',
            'lapis': '96091000',
        }
        
        ncm = '00000000'  # NCM padrão quando não encontrado
        for palavra, codigo in ncm_map.items():
            if palavra in produto_lower:
                ncm = codigo
                break
        
        # Determinar CFOP baseado em UF
        cfop = "5101"  # Padrão: venda dentro do estado
        if request.uf_origem:
            cfop = "5101"  # Simplificado
        
        # Determinar CST/CSOSN baseado em regime
        if request.regime_tributario == 'Simples Nacional':
            csosn = "101"  # Tributado pelo Simples Nacional
            cst = None
        else:
            cst = "00"  # Tributada integralmente
            csosn = None
        
        resultado = {
            "ncm": ncm,
            "cfop": cfop,
            "cst": cst,
            "csosn": csosn,
            "cest": None,
            "explicacao": "Sugestão básica gerada por regras heurísticas (APIs offline). Verifique e ajuste conforme necessário.",
            "modo": "fallback"
        }
        
        # Tentar sugerir CEST se disponível
        if CEST_DISPONIVEL and ncm != '00000000':
            cest_sugerido = self._sugerir_cest(request.descricao, ncm)
            if cest_sugerido:
                resultado["cest"] = cest_sugerido
        
        return resultado

    def _sugerir_cest(self, produto: str, ncm: str) -> Optional[str]:
        """
        Sugere CEST baseado no produto e NCM
        
        Args:
            produto: Descrição do produto
            ncm: Código NCM (8 dígitos)
            
        Returns:
            Código CEST (XX.XXX.XX) ou None
        """
        if not CEST_DISPONIVEL or buscar_cest_por_produto is None:
            return None
        
        try:
            # Busca CEST pela descrição do produto
            resultado = buscar_cest_por_produto(produto)
            
            if resultado and resultado.get('confianca', 0) >= 60:
                cest = resultado.get('cest')
                print(f"✅ CEST sugerido: {cest} (confiança: {resultado.get('confianca')}%)")
                print(f"   Segmento: {resultado.get('segmento')}")
                print(f"   Palavra-chave: {resultado.get('palavra_chave_encontrada')}")
                return cest
            else:
                print(f"ℹ️ Produto não sujeito a ST - CEST não necessário")
                return None
                
        except Exception as e:
            print(f"⚠️ Erro ao sugerir CEST: {e}")
            return None

    async def gerar_sugestao(self, request: SugestaoRequest) -> Dict:
        """Método principal para gerar sugestão tributária"""
        print(f"🎯 Iniciando sugestão para: {request.descricao}")
        
        # 1. Verificar conectividade
        apis_status = self._verificar_apis()
        
        # Se nenhuma API está disponível, usar fallback básico
        if not apis_status["ncm"] and not apis_status["llm"]:
            print("⚠️ Modo fallback total - gerando sugestão básica")
            return self._gerar_sugestao_basica(request)
        
        # 2. Gerar prompt com dados NCM oficiais (se API disponível)
        if apis_status["ncm"]:
            print(f"📋 Gerando prompt...")
            prompt = self.gerar_prompt_classificacao(request)
            
            if "Não foram encontrados NCMs" in prompt:
                print("⚠️ NCM não encontrado via API - usando fallback")
                return self._gerar_sugestao_basica(request)
            
            # 3. Consultar LLM com dados NCM (se disponível)
            if apis_status["llm"]:
                print(f"🤖 Consultando IA...")
                resultado = await self.consultar_llm(prompt)
            else:
                print(f"⚙️ LLM offline - usando primeiro NCM encontrado")
                resultado = self._gerar_resposta_fallback(prompt)
        else:
            # Sem API NCM, usar fallback direto
            print("⚙️ API NCM offline - usando regras heurísticas")
            resultado = self._gerar_sugestao_basica(request)
        
        # 4. Sugerir CEST se disponível
        if "erro" not in resultado:
            print(f"✅ Sugestão gerada com sucesso!")
            
            # Tentar sugerir CEST baseado no produto
            if CEST_DISPONIVEL:
                ncm = resultado.get("ncm", "")
                cest_sugerido = self._sugerir_cest(request.descricao, ncm)
                
                # Se LLM não retornou CEST ou retornou null, usar nossa sugestão
                if not resultado.get("cest") or resultado.get("cest") == "null":
                    resultado["cest"] = cest_sugerido
                    if cest_sugerido:
                        resultado["cest_fonte"] = "Base CONFAZ (automático)"
        else:
            print(f"❌ Erro na sugestão: {resultado.get('erro')}")
        
        return resultado

    def _verificar_apis(self) -> Dict[str, bool]:
        """Verifica quais APIs estão disponíveis"""
        status = {"ncm": False, "llm": False}
        
        try:
            # Verifica API NCM
            ncm_response = requests.get(f"{self.ncm_api_url}/health", timeout=2)
            if ncm_response.status_code == 200:
                status["ncm"] = True
                print("✅ API NCM disponível")
            else:
                print("⚠️ API NCM não disponível - usando fallback")
        except Exception as e:
            print(f"⚠️ API NCM offline: {str(e)[:50]} - usando fallback")
        
        try:
            # Verifica LLM (endpoint models)
            llm_response = requests.get(f"{self.llm_url}/v1/models", timeout=2)
            if llm_response.status_code == 200:
                status["llm"] = True
                print("✅ LLM disponível")
            else:
                print("⚠️ LLM não disponível - usando regras heurísticas")
        except Exception as e:
            print(f"⚠️ LLM offline: {str(e)[:50]} - usando regras heurísticas")
        
        return status

# Instância global do serviço
servico_sugestao = ServicoSugestaoIA()