"""
Exemplo de Uso do Sistema IA NCM
Demonstra como utilizar o motor de sugestão de NCM
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from ai_ncm.predicao.motor_ia_ncm import MotorIANCM
from ai_ncm.embasamento.lei_complementar import BuscadorLeiComplementar
from ai_ncm.embasamento.justificativa import GeradorJustificativa
from ai_ncm.embasamento.formatador import FormatadorResposta


def exemplo_sugestao_simples():
    """Exemplo 1: Sugestão simples de NCM"""
    print("=" * 80)
    print("EXEMPLO 1: Sugestão Simples de NCM")
    print("=" * 80)
    print()
    
    # Inicializa motor
    motor = MotorIANCM()
    
    # Produto de exemplo
    descricao = "Cadeira de escritório giratória com rodas e ajuste de altura"
    
    print(f"[LOG] Produto: {descricao}")
    print()
    
    # Obtém sugestão
    resultado = motor.sugerir_ncm(descricao=descricao, top_n=3)
    
    if resultado['sucesso']:
        print(f"[OK] NCM Sugerido: {resultado['ncm']}")
        print(f"[LIST] Descrição: {resultado['descricao']}")
        print(f"[?] Confiança: {resultado['confianca']:.1%}")
        print()
        
        print("[?] Alternativas:")
        for i, alt in enumerate(resultado.get('alternativas', [])[:3], 1):
            print(f"   {i}. {alt['ncm']} - {alt['descricao']} ({alt['confianca']:.1%})")
        print()
    else:
        print(f"[X] Erro: {resultado.get('erro', 'Desconhecido')}")
    
    print()


def exemplo_com_contexto_detalhado():
    """Exemplo 2: Sugestão com contexto e detalhes"""
    print("=" * 80)
    print("EXEMPLO 2: Sugestão com Contexto Detalhado")
    print("=" * 80)
    print()
    
    motor = MotorIANCM()
    
    descricao = "Notebook para uso profissional"
    contexto = "Equipamento de informática para revenda"
    detalhes = {
        "marca": "Dell",
        "modelo": "Inspiron 15",
        "processador": "Intel Core i5",
        "memoria": "8GB RAM",
        "armazenamento": "SSD 256GB"
    }
    
    print(f"[LOG] Produto: {descricao}")
    print(f"[?] Contexto: {contexto}")
    print(f"ℹ️  Detalhes: {detalhes}")
    print()
    
    resultado = motor.sugerir_ncm(
        descricao=descricao,
        contexto=contexto,
        detalhes_adicionais=str(detalhes),
        top_n=3
    )
    
    if resultado['sucesso']:
        print(f"[OK] NCM Sugerido: {resultado['ncm']}")
        print(f"[LIST] Descrição: {resultado['descricao']}")
        print(f"[?] Confiança: {resultado['confianca']:.1%}")
        print()
        
        # Mostra base legal
        if 'base_legal' in resultado:
            print("⚖️  Base Legal:")
            for artigo in resultado['base_legal'].get('artigos_relacionados', [])[:2]:
                print(f"   • {artigo.get('numero', 'N/A')}: {artigo.get('texto', '')[:100]}...")
        print()
    
    print()


def exemplo_justificativa_completa():
    """Exemplo 3: Justificativa legal completa"""
    print("=" * 80)
    print("EXEMPLO 3: Justificativa Legal Completa")
    print("=" * 80)
    print()
    
    motor = MotorIANCM()
    gerador = GeradorJustificativa()
    
    descricao = "Mouse sem fio Logitech MX Master 3"
    
    # Obtém sugestão
    resultado = motor.sugerir_ncm(descricao=descricao)
    
    if resultado['sucesso']:
        # Gera justificativa completa
        justificativa = gerador.gerar_justificativa_completa(
            ncm_codigo=resultado['ncm'],
            ncm_descricao=resultado['descricao'],
            descricao_produto=descricao,
            artigos_relacionados=resultado.get('base_legal', {}).get('artigos_relacionados', []),
            confianca=resultado['confianca']
        )
        
        # Exibe formatado
        texto_formatado = gerador.formatar_para_exibicao(justificativa)
        print(texto_formatado)
    
    print()


def exemplo_busca_lei_complementar():
    """Exemplo 4: Busca na Lei Complementar 214/2025"""
    print("=" * 80)
    print("EXEMPLO 4: Busca na Lei Complementar 214/2025")
    print("=" * 80)
    print()
    
    buscador = BuscadorLeiComplementar()
    
    # Busca artigo específico
    print("[SEARCH] Buscando Art. 4º...")
    artigo = buscador.buscar_artigo('4º')
    if artigo:
        print(f"   {artigo.get('artigo', 'N/A')}: {artigo.get('conteudo', '')[:200]}...")
    print()
    
    # Busca por palavra-chave
    print("[SEARCH] Buscando palavra-chave: 'NCM'...")
    resultados = buscador.buscar_por_palavra_chave('NCM', max_resultados=3)
    for res in resultados:
        print(f"   Art. {res.get('artigo', 'N/A')}: {res.get('contexto', '')[:100]}...")
    print()
    
    # Estatísticas
    print("[DATA] Estatísticas da Lei:")
    stats = buscador.obter_estatisticas()
    print(f"   • Total de artigos: {stats.get('total_artigos', 0)}")
    print(f"   • Referências NCM: {stats.get('total_referencias_ncm', 0)}")
    print(f"   • Menções a alíquotas: {stats.get('total_aliquotas', 0)}")
    print()


def exemplo_formatacao_multipla():
    """Exemplo 5: Formatar resposta em diferentes formatos"""
    print("=" * 80)
    print("EXEMPLO 5: Formatação em Múltiplos Formatos")
    print("=" * 80)
    print()
    
    motor = MotorIANCM()
    gerador = GeradorJustificativa()
    formatador = FormatadorResposta()
    
    descricao = "Teclado mecânico gamer RGB"
    resultado = motor.sugerir_ncm(descricao=descricao)
    
    if resultado['sucesso']:
        # Gera justificativa
        justificativa = gerador.gerar_justificativa_completa(
            ncm_codigo=resultado['ncm'],
            ncm_descricao=resultado['descricao'],
            descricao_produto=descricao,
            artigos_relacionados=resultado.get('base_legal', {}).get('artigos_relacionados', []),
            confianca=resultado['confianca']
        )
        
        # Formato JSON
        print("[?] FORMATO JSON:")
        print(formatador.formatar_json(justificativa, pretty=True)[:300])
        print("...\n")
        
        # Formato Texto
        print("[?] FORMATO TEXTO:")
        texto = formatador.formatar_texto_simples(justificativa)
        print('\n'.join(texto.split('\n')[:15]))
        print("...\n")
        
        # Formato HTML (apenas início)
        print("[?] FORMATO HTML:")
        html = formatador.formatar_html(justificativa)
        print('\n'.join(html.split('\n')[:10]))
        print("...\n")


def exemplo_feedback_continuo():
    """Exemplo 6: Sistema de feedback para aprendizado contínuo"""
    print("=" * 80)
    print("EXEMPLO 6: Feedback para Aprendizado Contínuo")
    print("=" * 80)
    print()
    
    motor = MotorIANCM()
    
    # Sugestão inicial
    descricao = "Caneta esferográfica azul"
    resultado = motor.sugerir_ncm(descricao=descricao)
    
    print(f"[LOG] Produto: {descricao}")
    print(f"[?] IA Sugeriu: {resultado.get('ncm', 'N/A')}")
    print()
    
    # Usuário confirma ou corrige
    ncm_correto = "9608.10.00"  # Usuário sabe o NCM correto
    
    print(f"[OK] Usuário confirma NCM: {ncm_correto}")
    
    # Registra feedback
    motor.registrar_feedback(
        descricao=descricao,
        ncm_sugerido=resultado.get('ncm', ''),
        ncm_confirmado=ncm_correto,
        aprovado=(resultado.get('ncm') == ncm_correto),
        usuario_id=1
    )
    
    print("[SAVE] Feedback registrado no sistema")
    print("[?] O modelo será retreinado automaticamente após 50 exemplos")
    print()


def menu_interativo():
    """Menu interativo para testar o sistema"""
    print("\n")
    print("=" * 80)
    print("[?] SISTEMA IA NCM - MENU INTERATIVO")
    print("=" * 80)
    print()
    print("Selecione um exemplo:")
    print("  1. Sugestão simples de NCM")
    print("  2. Sugestão com contexto detalhado")
    print("  3. Justificativa legal completa")
    print("  4. Busca na Lei Complementar 214/2025")
    print("  5. Formatação em múltiplos formatos")
    print("  6. Sistema de feedback contínuo")
    print("  7. Executar todos os exemplos")
    print("  0. Sair")
    print()
    
    opcao = input("Digite o número da opção: ").strip()
    
    if opcao == '1':
        exemplo_sugestao_simples()
    elif opcao == '2':
        exemplo_com_contexto_detalhado()
    elif opcao == '3':
        exemplo_justificativa_completa()
    elif opcao == '4':
        exemplo_busca_lei_complementar()
    elif opcao == '5':
        exemplo_formatacao_multipla()
    elif opcao == '6':
        exemplo_feedback_continuo()
    elif opcao == '7':
        exemplo_sugestao_simples()
        exemplo_com_contexto_detalhado()
        exemplo_justificativa_completa()
        exemplo_busca_lei_complementar()
        exemplo_formatacao_multipla()
        exemplo_feedback_continuo()
    elif opcao == '0':
        print("[?] Encerrando...")
        return
    else:
        print("[X] Opção inválida!")
    
    # Continua no menu
    input("\nPressione ENTER para voltar ao menu...")
    menu_interativo()


if __name__ == '__main__':
    print("\n")
    print("[START] INICIANDO EXEMPLOS DO SISTEMA IA NCM")
    print()
    
    try:
        menu_interativo()
    except KeyboardInterrupt:
        print("\n\n[?] Programa interrompido pelo usuário")
    except Exception as e:
        print(f"\n[X] Erro: {e}")
        import traceback
        traceback.print_exc()
