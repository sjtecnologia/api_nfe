"""
Rotas de Relatórios - EmiteMax
Endpoints para geração de relatórios gerenciais

Desenvolvido por: EmiteMax
Data: 11/02/2026
"""

from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for, session
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from database.connection import get_db
from services.relatorio_service import RelatorioService
from auth.decorators import viewer_or_higher_required
from auth.permissions import get_accessible_client_ids
import io

relatorios_bp = Blueprint('relatorios', __name__, url_prefix='/relatorios')


@relatorios_bp.route('/')
@login_required
@viewer_or_higher_required()
def index():
    return render_template('relatorios/index.html')


@relatorios_bp.route('/notas-emitidas')
@login_required
@viewer_or_higher_required()
def notas_emitidas():
    db = next(get_db())
    
    # Obter filtros da URL
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    tipo_nota = request.args.get('tipo_nota', '')
    status = request.args.get('status', '')
    modelo = request.args.get('modelo', '')
    formato = request.args.get('formato', 'html')
    
    # Definir período padrão (últimos 6 meses para incluir dados históricos)
    if not data_inicio_str or not data_fim_str:
        hoje = datetime.now()
        # Período padrão: últimos 6 meses até hoje
        data_inicio = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if data_inicio.month <= 6:
            data_inicio = data_inicio.replace(year=data_inicio.year-1, month=12+data_inicio.month-6)
        else:
            data_inicio = data_inicio.replace(month=data_inicio.month-6)
        data_fim = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d')
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d')
            data_fim = data_fim.replace(hour=23, minute=59, second=59)
        except ValueError:
            flash('Datas inválidas. Usando período padrão.', 'warning')
            hoje = datetime.now()
            # Período padrão: últimos 6 meses até hoje
            data_inicio = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if data_inicio.month <= 6:
                data_inicio = data_inicio.replace(year=data_inicio.year-1, month=12+data_inicio.month-6)
            else:
                data_inicio = data_inicio.replace(month=data_inicio.month-6)
            data_fim = hoje
    
    # Obter clientes acessíveis
    accessible_client_ids = get_accessible_client_ids(db)
    if not accessible_client_ids:
        flash('Você não tem acesso a nenhum cliente.', 'warning')
        return redirect(url_for('home.home'))
    
    # EXIGIR cliente selecionado na sessão
    current_client_id = session.get('current_client_id')
    if not current_client_id or current_client_id not in accessible_client_ids:
        # Salvar URL de destino para retornar após seleção
        session['next_url'] = request.url
        flash('Por favor, selecione um cliente antes de acessar os relatórios.', 'warning')
        return redirect(url_for('home.home'))
    
    cliente_ids_filtro = [current_client_id]
    print(f"[INFO] Relatório Notas - Cliente ativo: {current_client_id}")
    
    # Gerar relatório
    relatorio_service = RelatorioService(db)
    dados = relatorio_service.relatorio_notas_emitidas(
        cliente_ids=cliente_ids_filtro,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tipo_nota=tipo_nota if tipo_nota else None,
        status=status if status else None,
        modelo=modelo if modelo else None
    )
    
    # Formatos de saída
    if formato == 'json':
        return jsonify(dados)
    elif formato == 'excel':
        return gerar_excel_notas_emitidas(dados)
    else:
        return render_template('relatorios/notas_emitidas.html', dados=dados)


@relatorios_bp.route('/faturamento')
@login_required
@viewer_or_higher_required()
def faturamento():
    db = next(get_db())
    
    # Obter filtros
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    agrupar_por = request.args.get('agrupar_por', 'mes')
    formato = request.args.get('formato', 'html')
    
    # Período padrão (últimos 12 meses)
    if not data_inicio_str or not data_fim_str:
        hoje = datetime.now()
        data_fim = hoje
        data_inicio = hoje - timedelta(days=365)
    else:
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d')
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d')
            data_fim = data_fim.replace(hour=23, minute=59, second=59)
        except ValueError:
            flash('Datas inválidas. Usando período padrão.', 'warning')
            hoje = datetime.now()
            data_fim = hoje
            data_inicio = hoje - timedelta(days=365)
    
    # Obter clientes acessíveis
    accessible_client_ids = get_accessible_client_ids(db)
    if not accessible_client_ids:
        flash('Você não tem acesso a nenhum cliente.', 'warning')
        return redirect(url_for('home.home'))
    
    # EXIGIR cliente selecionado na sessão
    current_client_id = session.get('current_client_id')
    if not current_client_id or current_client_id not in accessible_client_ids:
        # Salvar URL de destino para retornar após seleção
        session['next_url'] = request.url
        flash('Por favor, selecione um cliente antes de acessar os relatórios.', 'warning')
        return redirect(url_for('home.home'))
    
    cliente_ids_filtro = [current_client_id]
    
    # Gerar relatório
    relatorio_service = RelatorioService(db)
    dados = relatorio_service.relatorio_faturamento(
        cliente_ids=cliente_ids_filtro,
        data_inicio=data_inicio,
        data_fim=data_fim,
        agrupar_por=agrupar_por
    )
    
    if formato == 'json':
        return jsonify(dados)
    elif formato == 'excel':
        return gerar_excel_faturamento(dados)
    else:
        return render_template('relatorios/faturamento.html', dados=dados)


@relatorios_bp.route('/produtos')
@login_required
@viewer_or_higher_required()
def produtos():
    db = next(get_db())
    
    # Obter filtros
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    limite = int(request.args.get('limite', 50))
    formato = request.args.get('formato', 'html')
    
    # Período padrão (últimos 6 meses para incluir dados históricos)
    if not data_inicio_str or not data_fim_str:
        hoje = datetime.now()
        # Período padrão: últimos 6 meses até hoje
        data_inicio = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if data_inicio.month <= 6:
            data_inicio = data_inicio.replace(year=data_inicio.year-1, month=12+data_inicio.month-6)
        else:
            data_inicio = data_inicio.replace(month=data_inicio.month-6)
        data_fim = hoje
    else:
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d')
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d')
            data_fim = data_fim.replace(hour=23, minute=59, second=59)
        except ValueError:
            flash('Datas inválidas. Usando período padrão.', 'warning')
            hoje = datetime.now()
            # Período padrão: últimos 6 meses até hoje
            data_inicio = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if data_inicio.month <= 6:
                data_inicio = data_inicio.replace(year=data_inicio.year-1, month=12+data_inicio.month-6)
            else:
                data_inicio = data_inicio.replace(month=data_inicio.month-6)
            data_fim = hoje
    
    # Obter clientes acessíveis
    accessible_client_ids = get_accessible_client_ids(db)
    if not accessible_client_ids:
        flash('Você não tem acesso a nenhum cliente.', 'warning')
        return redirect(url_for('home.home'))
    
    # EXIGIR cliente selecionado na sessão
    current_client_id = session.get('current_client_id')
    if not current_client_id or current_client_id not in accessible_client_ids:
        # Salvar URL de destino para retornar após seleção
        session['next_url'] = request.url
        flash('Por favor, selecione um cliente antes de acessar os relatórios.', 'warning')
        return redirect(url_for('home.home'))
    
    cliente_ids_filtro = [current_client_id]
    
    # Gerar relatório
    relatorio_service = RelatorioService(db)
    dados = relatorio_service.relatorio_produtos(
        cliente_ids=cliente_ids_filtro,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limite=limite
    )
    
    if formato == 'json':
        return jsonify(dados)
    elif formato == 'excel':
        return gerar_excel_produtos(dados)
    else:
        return render_template('relatorios/produtos.html', dados=dados)


@relatorios_bp.route('/impostos')
@login_required
@viewer_or_higher_required()
def impostos():
    db = next(get_db())
    
    # Obter filtros
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    formato = request.args.get('formato', 'html')
    
    # Período padrão (últimos 6 meses para incluir dados históricos)
    if not data_inicio_str or not data_fim_str:
        hoje = datetime.now()
        # Período padrão: últimos 6 meses até hoje
        data_inicio = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if data_inicio.month <= 6:
            data_inicio = data_inicio.replace(year=data_inicio.year-1, month=12+data_inicio.month-6)
        else:
            data_inicio = data_inicio.replace(month=data_inicio.month-6)
        data_fim = hoje
    else:
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d')
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d')
            data_fim = data_fim.replace(hour=23, minute=59, second=59)
        except ValueError:
            flash('Datas inválidas. Usando período padrão.', 'warning')
            hoje = datetime.now()
            # Período padrão: últimos 6 meses até hoje
            data_inicio = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if data_inicio.month <= 6:
                data_inicio = data_inicio.replace(year=data_inicio.year-1, month=12+data_inicio.month-6)
            else:
                data_inicio = data_inicio.replace(month=data_inicio.month-6)
            data_fim = hoje
    
    # Obter clientes acessíveis
    accessible_client_ids = get_accessible_client_ids(db)
    if not accessible_client_ids:
        flash('Você não tem acesso a nenhum cliente.', 'warning')
        return redirect(url_for('home.home'))
    
    # EXIGIR cliente selecionado na sessão
    current_client_id = session.get('current_client_id')
    if not current_client_id or current_client_id not in accessible_client_ids:
        # Salvar URL de destino para retornar após seleção
        session['next_url'] = request.url
        flash('Por favor, selecione um cliente antes de acessar os relatórios.', 'warning')
        return redirect(url_for('home.home'))
    
    cliente_ids_filtro = [current_client_id]
    
    # Gerar relatório
    relatorio_service = RelatorioService(db)
    dados = relatorio_service.relatorio_impostos(
        cliente_ids=cliente_ids_filtro,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    
    if formato == 'json':
        return jsonify(dados)
    elif formato == 'excel':
        return gerar_excel_impostos(dados)
    else:
        return render_template('relatorios/impostos.html', dados=dados)


def gerar_excel_notas_emitidas(dados):
    """Gera arquivo Excel para relatório de notas emitidas"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, NamedStyle
        from openpyxl.utils import get_column_letter
    except ImportError:
        flash('Biblioteca openpyxl não encontrada. Instale para usar esta funcionalidade.', 'error')
        return redirect(request.referrer or '/relatorios')
    
    # Criar workbook
    wb = Workbook()
    ws = wb.active
    if ws is None:
        flash('Erro ao criar planilha Excel.', 'error')
        return redirect(request.referrer or '/relatorios')
    
    ws.title = "Notas Emitidas"
    
    # Cabeçalhos (mesma ordem da tela)
    headers = [
        'Número', 'Série', 'Tipo', 'Data Emissão', 
        'Status', 'Destinatário', 'Valor Total', 'Chave de Acesso'
    ]
    ws.append(headers)
    
    # Estilizar cabeçalho
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    
    for col_num, header in enumerate(headers, 1):
        col_letter = get_column_letter(col_num)
        cell = ws[f"{col_letter}1"]
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    
    # Criar estilo de moeda
    moeda_style = NamedStyle(name="moeda")
    moeda_style.number_format = 'R$ #,##0.00'
    
    try:
        wb.add_named_style(moeda_style)
    except ValueError:
        # Estilo já existe
        pass
    
    # Adicionar dados
    for nota in dados.get('notas', []):
        # Converter modelo numérico para texto amigável
        modelo = nota.get('modelo', '55')
        if modelo == '55':
            tipo_texto = 'NFe'
        elif modelo == '65':
            tipo_texto = 'NFCe'
        else:
            tipo_texto = f'Modelo {modelo}'
        
        row = [
            nota.get('numero_nfe', ''),
            nota.get('serie', ''),
            tipo_texto,  # Tipo (NFe/NFCe)
            nota.get('data_emissao', ''),
            nota.get('status', ''),
            nota.get('destinatario', ''),
            float(nota.get('valor_total', 0)) if nota.get('valor_total') else 0,
            nota.get('chave_acesso', '')
        ]
        ws.append(row)
    
    # Aplicar formatação de moeda na coluna Valor Total (coluna G = 7)
    for row in range(2, ws.max_row + 1):  # Começar da linha 2 (pular cabeçalho)
        cell = ws[f'G{row}']  # Coluna G é Valor Total
        cell.style = moeda_style
    
    # Ajustar largura das colunas
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column].width = adjusted_width
    
    # Criar resposta de download
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'notas_emitidas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )


def gerar_excel_faturamento(dados):
    """Gera arquivo Excel para relatório de faturamento"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, NamedStyle
        from openpyxl.utils import get_column_letter
    except ImportError:
        flash('Biblioteca openpyxl não encontrada. Instale para usar esta funcionalidade.', 'error')
        return redirect(request.referrer or '/relatorios')
    
    wb = Workbook()
    ws = wb.active
    if ws is None:
        flash('Erro ao criar planilha Excel.', 'error')
        return redirect(request.referrer or '/relatorios')
    
    ws.title = "Faturamento"
    
    # Estilo de moeda brasileira
    try:
        moeda_style = NamedStyle(name='moeda_brasileira', number_format='R$ #,##0.00')
        if 'moeda_brasileira' not in wb.named_styles:
            wb.add_named_style(moeda_style)
    except:
        pass
    
    # Cabeçalhos
    headers = ['Período', 'Quantidade NFes', 'Valor Total', 'ICMS', 'IPI', 'PIS', 'COFINS', 'Ticket Médio']
    ws.append(headers)
    
    # Estilizar cabeçalho
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="28a745", end_color="28a745", fill_type="solid")
    
    for col_num, header in enumerate(headers, 1):
        col_letter = get_column_letter(col_num)
        cell = ws[f"{col_letter}1"]
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    
    # Adicionar dados
    for item in dados.get('dados', []):
        row_num = ws.max_row + 1
        ws.append([
            item.get('periodo', ''),
            item.get('quantidade_notas', 0),
            item.get('valor_total', 0),
            item.get('total_icms', 0),
            item.get('total_ipi', 0),
            item.get('total_pis', 0),
            item.get('total_cofins', 0),
            item.get('ticket_medio', 0)
        ])
        
        # Aplicar formato moeda nas colunas de valores (C a H)
        for col in ['C', 'D', 'E', 'F', 'G', 'H']:
            try:
                ws[f'{col}{row_num}'].style = 'moeda_brasileira'
            except:
                pass
    
    # Ajustar largura das colunas
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column].width = adjusted_width
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'faturamento_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )


def gerar_excel_produtos(dados):
    """Gera arquivo Excel para relatório de produtos"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, NamedStyle
        from openpyxl.utils import get_column_letter
    except ImportError:
        flash('Biblioteca openpyxl não encontrada. Instale para usar esta funcionalidade.', 'error')
        return redirect(request.referrer or '/relatorios')
    
    wb = Workbook()
    ws = wb.active
    if ws is None:
        flash('Erro ao criar planilha Excel.', 'error')
        return redirect(request.referrer or '/relatorios')
    
    ws.title = "Produtos"
    
    # Criar estilos para formatação brasileira
    if 'moeda_brasileira' not in wb.named_styles:
        moeda_brasileira = NamedStyle(name="moeda_brasileira", number_format='R$ #,##0.00')
        wb.add_named_style(moeda_brasileira)
    
    if 'percentual' not in wb.named_styles:
        percentual = NamedStyle(name="percentual", number_format='0.0%')
        wb.add_named_style(percentual)
    
    # Cabeçalhos
    headers = [
        'Posição', 'Código', 'Descrição', 'NCM', 'Unidade', 
        'Quantidade', 'Valor Unit. Médio', 'Valor Total', 'ICMS', '% Vendas'
    ]
    ws.append(headers)
    
    # Estilizar cabeçalho
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="fd7e14", end_color="fd7e14", fill_type="solid")
    
    for col_num, header in enumerate(headers, 1):
        col_letter = get_column_letter(col_num)
        cell = ws[f"{col_letter}1"]
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    
    # Adicionar dados
    for idx, produto in enumerate(dados.get('produtos', []), 1):
        row = [
            idx,  # Posição
            produto.get('codigo', ''),
            produto.get('descricao', ''),
            produto.get('ncm', ''),
            produto.get('unidade', ''),
            int(produto.get('quantidade_total', 0)),
            produto.get('valor_medio_unitario', 0),
            produto.get('valor_total_vendas', 0),
            produto.get('total_icms', 0),
            produto.get('percentual_vendas', 0) / 100  # Converter para decimal para formato percentual
        ]
        ws.append(row)
        
        # Aplicar formatação às células de valores
        row_num = ws.max_row
        ws[f"G{row_num}"].style = 'moeda_brasileira'  # Valor Unit. Médio
        ws[f"H{row_num}"].style = 'moeda_brasileira'  # Valor Total
        ws[f"I{row_num}"].style = 'moeda_brasileira'  # ICMS
        ws[f"J{row_num}"].style = 'percentual'  # % Vendas
    
    # Ajustar largura das colunas manualmente para melhor visualização
    ws.column_dimensions['A'].width = 10  # Posição
    ws.column_dimensions['B'].width = 15  # Código
    ws.column_dimensions['C'].width = 40  # Descrição
    ws.column_dimensions['D'].width = 12  # NCM
    ws.column_dimensions['E'].width = 10  # Unidade
    ws.column_dimensions['F'].width = 12  # Quantidade
    ws.column_dimensions['G'].width = 18  # Valor Unit. Médio
    ws.column_dimensions['H'].width = 18  # Valor Total
    ws.column_dimensions['I'].width = 18  # ICMS
    ws.column_dimensions['J'].width = 12  # % Vendas
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'produtos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )


def gerar_excel_impostos(dados):
    """Gera arquivo Excel para relatório de impostos com 2 abas"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, NamedStyle
        from openpyxl.utils import get_column_letter
    except ImportError:
        flash('Biblioteca openpyxl não encontrada. Instale para usar esta funcionalidade.', 'error')
        return redirect(request.referrer or '/relatorios')
    
    wb = Workbook()
    wb.remove(wb.active)  # Remove a planilha padrão
    
    # Estilo de moeda brasileira
    try:
        moeda_style = NamedStyle(name='moeda_brasileira', number_format='R$ #,##0.00')
        if 'moeda_brasileira' not in wb.named_styles:
            wb.add_named_style(moeda_style)
    except:
        pass
    
    # Estilo de porcentagem
    try:
        percentual_style = NamedStyle(name='percentual', number_format='0.00"%"')
        if 'percentual' not in wb.named_styles:
            wb.add_named_style(percentual_style)
    except:
        pass
    
    # ===== ABA 1: DETALHAMENTO POR IMPOSTO =====
    ws_impostos = wb.create_sheet("Detalhamento por Imposto")
    
    # Cabeçalhos
    headers_impostos = ['Imposto', 'Valor', 'Alíquota Efetiva', '% do Total']
    ws_impostos.append(headers_impostos)
    
    # Estilizar cabeçalho
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="dc3545", end_color="dc3545", fill_type="solid")
    
    for col_num in range(1, len(headers_impostos) + 1):
        col_letter = get_column_letter(col_num)
        cell = ws_impostos[f"{col_letter}1"]
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    
    # Adicionar dados dos impostos
    impostos = dados.get('impostos', {})
    ordem_impostos = ['icms', 'ipi', 'pis', 'cofins', 'ibs', 'cbs']
    
    for nome in ordem_impostos:
        if nome in impostos:
            imposto = impostos[nome]
            row_num = ws_impostos.max_row + 1
            ws_impostos.append([
                nome.upper(),
                imposto.get('valor', 0),
                imposto.get('aliquota_efetiva', 0),
                imposto.get('percentual_total', 0)
            ])
            
            # Aplicar formatos
            ws_impostos[f'B{row_num}'].style = 'moeda_brasileira'
            ws_impostos[f'C{row_num}'].style = 'percentual'
            ws_impostos[f'D{row_num}'].style = 'percentual'
    
    # Ajustar largura das colunas
    ws_impostos.column_dimensions['A'].width = 15
    ws_impostos.column_dimensions['B'].width = 18
    ws_impostos.column_dimensions['C'].width = 18
    ws_impostos.column_dimensions['D'].width = 15
    
    # ===== ABA 2: DETALHAMENTO POR CFOP =====
    ws_cfop = wb.create_sheet("Detalhamento por CFOP")
    
    # Cabeçalhos
    headers_cfop = ['CFOP', 'Qtd Notas', 'Valor Total', 'ICMS', 'IPI', 'PIS', 'COFINS']
    ws_cfop.append(headers_cfop)
    
    # Estilizar cabeçalho
    for col_num in range(1, len(headers_cfop) + 1):
        col_letter = get_column_letter(col_num)
        cell = ws_cfop[f"{col_letter}1"]
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    
    # Adicionar dados por CFOP
    detalhamento_cfop = dados.get('detalhamento_cfop', [])
    for cfop_data in detalhamento_cfop:
        row_num = ws_cfop.max_row + 1
        ws_cfop.append([
            cfop_data.get('cfop', ''),
            cfop_data.get('quantidade_notas', 0),
            cfop_data.get('valor_total', 0),
            cfop_data.get('icms', 0),
            cfop_data.get('ipi', 0),
            cfop_data.get('pis', 0),
            cfop_data.get('cofins', 0)
        ])
        
        # Aplicar formato moeda nas colunas de valores (C a G)
        for col in ['C', 'D', 'E', 'F', 'G']:
            ws_cfop[f'{col}{row_num}'].style = 'moeda_brasileira'
    
    # Ajustar largura das colunas
    ws_cfop.column_dimensions['A'].width = 12
    ws_cfop.column_dimensions['B'].width = 12
    ws_cfop.column_dimensions['C'].width = 18
    ws_cfop.column_dimensions['D'].width = 18
    ws_cfop.column_dimensions['E'].width = 15
    ws_cfop.column_dimensions['F'].width = 15
    ws_cfop.column_dimensions['G'].width = 18
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'impostos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )
