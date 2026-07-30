"""
Módulo AI NCM - Sistema de Inteligência Artificial para Sugestão de NCM
Baseado na Lei Complementar 214/2025
"""

__version__ = '1.0.0'
__author__ = 'Sistema NFe'
__description__ = 'Sistema de IA para sugestão de códigos NCM com embasamento legal'

from .predicao.motor_ia_ncm import MotorIANCM
from .embasamento.lei_complementar import BuscadorLeiComplementar
from .embasamento.justificativa import GeradorJustificativa

__all__ = [
    'MotorIANCM',
    'BuscadorLeiComplementar',
    'GeradorJustificativa',
]
