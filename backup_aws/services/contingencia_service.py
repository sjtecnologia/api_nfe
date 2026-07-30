"""
Serviço de Contingência NFe - EmiteMax
======================================

Gerencia a entrada e saída do modo de contingência quando a SEFAZ 
autorizadora está indisponível.

Modos suportados:
- SVC-AN (tpEmis=6): SEFAZ Virtual de Contingência - Ambiente Nacional
- SVC-RS (tpEmis=7): SEFAZ Virtual de Contingência - Rio Grande do Sul

A escolha entre SVC-AN e SVC-RS depende da UF do emitente.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import threading
import time


class ContingenciaService:
    """Gerencia o estado de contingência do sistema NFe"""
    
    # Mapeamento UF → SVC (qual SEFAZ Virtual usar)
    # SVC-RS (tpEmis=7) para UFs que usam SEFAZ Virtual RS
    # SVC-AN (tpEmis=6) para UFs que usam SEFAZ Virtual AN
    UF_SVC_MAP = {
        # SVC-RS (tpEmis=7)
        'AC': 'SVC-RS', 'AL': 'SVC-RS', 'AP': 'SVC-RS', 'DF': 'SVC-RS',
        'ES': 'SVC-RS', 'MG': 'SVC-RS', 'PB': 'SVC-RS', 'RJ': 'SVC-RS',
        'RN': 'SVC-RS', 'RO': 'SVC-RS', 'RR': 'SVC-RS', 'SC': 'SVC-RS',
        'SE': 'SVC-RS', 'SP': 'SVC-RS', 'TO': 'SVC-RS',
        # SVC-AN (tpEmis=6)
        'AM': 'SVC-AN', 'BA': 'SVC-AN', 'CE': 'SVC-AN', 'GO': 'SVC-AN',
        'MA': 'SVC-AN', 'MS': 'SVC-AN', 'MT': 'SVC-AN', 'PA': 'SVC-AN',
        'PE': 'SVC-AN', 'PI': 'SVC-AN', 'PR': 'SVC-AN', 'RS': 'SVC-AN',
    }
    
    # URLs SVC-AN (Ambiente Nacional)
    SVC_AN_HOMOLOGACAO = {
        'autorizacao': 'https://hom.svc.fazenda.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx',
        'consulta': 'https://hom.svc.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx',
        'status_servico': 'https://hom.svc.fazenda.gov.br/NFeStatusServico4/NFeStatusServico4.asmx',
    }
    SVC_AN_PRODUCAO = {
        'autorizacao': 'https://www.svc.fazenda.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx',
        'consulta': 'https://www.svc.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx',
        'status_servico': 'https://www.svc.fazenda.gov.br/NFeStatusServico4/NFeStatusServico4.asmx',
    }
    
    # URLs SVC-RS (Rio Grande do Sul)
    SVC_RS_HOMOLOGACAO = {
        'autorizacao': 'https://nfe-homologacao.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx',
        'consulta': 'https://nfe-homologacao.svrs.rs.gov.br/ws/NfeConsultaProtocolo/NfeConsultaProtocolo4.asmx',
        'status_servico': 'https://nfe-homologacao.svrs.rs.gov.br/ws/NfeStatusServico/NfeStatusServico4.asmx',
    }
    SVC_RS_PRODUCAO = {
        'autorizacao': 'https://nfe.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx',
        'consulta': 'https://nfe.svrs.rs.gov.br/ws/NfeConsultaProtocolo/NfeConsultaProtocolo4.asmx',
        'status_servico': 'https://nfe.svrs.rs.gov.br/ws/NfeStatusServico/NfeStatusServico4.asmx',
    }
    
    # Códigos de rejeição que indicam SEFAZ fora do ar (devem acionar contingência)
    CODIGOS_SEFAZ_INDISPONIVEL = [
        '108',  # Serviço Paralisado Momentaneamente
        '109',  # Serviço Paralisado sem Previsão
        '999',  # Erro genérico de serviço
    ]
    
    # Erros de comunicação que indicam SEFAZ fora do ar
    ERROS_COMUNICACAO = [
        'ConnectionError', 'ConnectTimeout', 'ReadTimeout', 'Timeout',
        'SSLError', 'ConnectionRefusedError', 'ConnectionResetError',
        'ERRO_ENVIO', 'ERRO_HTTP', 'ERRO_COMUNICACAO',
    ]
    
    def __init__(self):
        self._contingencia_ativa = {}  # {uf: {'ativo': bool, 'inicio': datetime, 'tipo': str, 'motivo': str}}
        self._lock = threading.Lock()
        # Tempo mínimo em contingência antes de tentar voltar ao normal (5 minutos)
        self.tempo_minimo_contingencia = timedelta(minutes=5)
        # Tempo máximo em contingência antes de forçar nova tentativa (30 minutos)
        self.tempo_maximo_contingencia = timedelta(minutes=30)
    
    def obter_tipo_contingencia(self, uf: str) -> str:
        """Retorna o tipo de contingência para a UF (SVC-AN ou SVC-RS)"""
        return self.UF_SVC_MAP.get(uf.upper(), 'SVC-RS')
    
    def obter_tp_emis(self, uf: str) -> str:
        """Retorna o tpEmis para contingência da UF"""
        tipo = self.obter_tipo_contingencia(uf)
        return '6' if tipo == 'SVC-AN' else '7'
    
    def obter_urls_contingencia(self, uf: str, ambiente: str) -> Dict[str, str]:
        """Retorna as URLs do SVC correto para a UF e ambiente"""
        tipo = self.obter_tipo_contingencia(uf)
        
        if tipo == 'SVC-AN':
            return self.SVC_AN_HOMOLOGACAO if ambiente == 'homologacao' else self.SVC_AN_PRODUCAO
        else:
            return self.SVC_RS_HOMOLOGACAO if ambiente == 'homologacao' else self.SVC_RS_PRODUCAO
    
    def ativar_contingencia(self, uf: str, motivo: str = 'SEFAZ indisponível') -> Dict[str, Any]:
        """
        Ativa o modo de contingência para uma UF.
        
        Args:
            uf: Unidade Federativa
            motivo: Motivo da entrada em contingência
            
        Returns:
            Dict com informações da contingência ativada
        """
        uf = uf.upper()
        tipo = self.obter_tipo_contingencia(uf)
        tp_emis = self.obter_tp_emis(uf)
        
        with self._lock:
            self._contingencia_ativa[uf] = {
                'ativo': True,
                'inicio': datetime.now(),
                'tipo': tipo,
                'tp_emis': tp_emis,
                'motivo': motivo,
                'tentativas_falhas': 0,
            }
        
        print(f"🔴 [CONTINGÊNCIA] ATIVADA para UF={uf}")
        print(f"   Tipo: {tipo} (tpEmis={tp_emis})")
        print(f"   Motivo: {motivo}")
        print(f"   Horário: {datetime.now().isoformat()}")
        
        return {
            'contingencia_ativa': True,
            'tipo': tipo,
            'tp_emis': tp_emis,
            'motivo': motivo,
            'inicio': datetime.now().isoformat(),
        }
    
    def desativar_contingencia(self, uf: str) -> Dict[str, Any]:
        """Desativa o modo de contingência para uma UF"""
        uf = uf.upper()
        
        with self._lock:
            info_anterior = self._contingencia_ativa.pop(uf, None)
        
        duracao = None
        if info_anterior and info_anterior.get('inicio'):
            duracao = (datetime.now() - info_anterior['inicio']).total_seconds()
        
        print(f"🟢 [CONTINGÊNCIA] DESATIVADA para UF={uf}")
        if duracao:
            print(f"   Duração: {duracao:.0f} segundos")
        
        return {
            'contingencia_ativa': False,
            'uf': uf,
            'duracao_segundos': duracao,
        }
    
    def esta_em_contingencia(self, uf: str) -> bool:
        """Verifica se a UF está em modo de contingência"""
        uf = uf.upper()
        with self._lock:
            info = self._contingencia_ativa.get(uf, {})
            if not info.get('ativo'):
                return False
            
            # Verificar se ultrapassou o tempo máximo de contingência
            inicio = info.get('inicio')
            if inicio and (datetime.now() - inicio) > self.tempo_maximo_contingencia:
                print(f"⏰ [CONTINGÊNCIA] Tempo máximo expirado para UF={uf}, desativando automaticamente")
                self._contingencia_ativa.pop(uf, None)
                return False
            
            return True
    
    def obter_info_contingencia(self, uf: str) -> Optional[Dict[str, Any]]:
        """Retorna informações sobre o estado de contingência da UF"""
        uf = uf.upper()
        with self._lock:
            info = self._contingencia_ativa.get(uf)
            if info:
                return {
                    **info,
                    'duracao_segundos': (datetime.now() - info['inicio']).total_seconds() if info.get('inicio') else 0,
                }
            return None
    
    def deve_entrar_em_contingencia(self, erro: Dict[str, Any]) -> bool:
        """
        Analisa o resultado de um envio SEFAZ e determina se deve entrar em contingência.
        
        Args:
            erro: Dict com resultado do envio (status, codigo, mensagem, etc.)
            
        Returns:
            True se o erro indica indisponibilidade da SEFAZ
        """
        status = str(erro.get('status', ''))
        codigo = str(erro.get('codigo', ''))
        mensagem = str(erro.get('mensagem', '') or erro.get('message', ''))
        
        # 1. Verificar códigos de rejeição que indicam SEFAZ indisponível
        if codigo in self.CODIGOS_SEFAZ_INDISPONIVEL:
            print(f"🔴 [CONTINGÊNCIA] Código SEFAZ {codigo} indica indisponibilidade")
            return True
        
        # 2. Verificar erros de comunicação
        for erro_tipo in self.ERROS_COMUNICACAO:
            if erro_tipo in status or erro_tipo in mensagem:
                print(f"🔴 [CONTINGÊNCIA] Erro de comunicação detectado: {erro_tipo}")
                return True
        
        # 3. Verificar timeout/conexão
        mensagem_lower = mensagem.lower()
        if any(kw in mensagem_lower for kw in ['timeout', 'timed out', 'connection refused', 
                                                  'connection reset', 'connection error',
                                                  'ssl', 'eof occurred', 'broken pipe']):
            print(f"🔴 [CONTINGÊNCIA] Erro de rede detectado: {mensagem[:100]}")
            return True
        
        # 4. Erros HTTP 500+ indicam problema no servidor
        if codigo.isdigit() and int(codigo) >= 500:
            print(f"🔴 [CONTINGÊNCIA] HTTP {codigo} indica servidor SEFAZ com problemas")
            return True
        
        return False
    
    def registrar_sucesso_sefaz(self, uf: str):
        """
        Registra que uma emissão na SEFAZ normal foi bem-sucedida.
        Se estiver em contingência, desativa.
        """
        uf = uf.upper()
        if self.esta_em_contingencia(uf):
            print(f"🟢 [CONTINGÊNCIA] SEFAZ normal respondeu OK para UF={uf}, saindo da contingência")
            self.desativar_contingencia(uf)
    
    def obter_status_geral(self) -> Dict[str, Any]:
        """Retorna o status geral de contingência de todas as UFs"""
        with self._lock:
            ufs_em_contingencia = {}
            for uf, info in self._contingencia_ativa.items():
                if info.get('ativo'):
                    ufs_em_contingencia[uf] = {
                        'tipo': info.get('tipo'),
                        'tp_emis': info.get('tp_emis'),
                        'motivo': info.get('motivo'),
                        'inicio': info.get('inicio', '').isoformat() if info.get('inicio') else None,
                        'duracao_segundos': (datetime.now() - info['inicio']).total_seconds() if info.get('inicio') else 0,
                    }
        
        return {
            'contingencia_ativa': len(ufs_em_contingencia) > 0,
            'ufs_em_contingencia': ufs_em_contingencia,
            'total_ufs_contingencia': len(ufs_em_contingencia),
        }


# Instância global do serviço de contingência
contingencia_service = ContingenciaService()
