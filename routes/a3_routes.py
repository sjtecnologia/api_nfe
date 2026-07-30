"""
Rotas para gerenciamento de certificados A3
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from database.connection import get_db
from services.pkcs11_service import get_pkcs11_service
from services.certificate_service import process_certificate_a3_registration

a3_bp = Blueprint('a3', __name__, url_prefix='/a3')


@a3_bp.route('/detect-tokens', methods=['GET'])
@login_required
def detect_tokens():
    """API: Detecta tokens A3 conectados"""
    try:
        pkcs11 = get_pkcs11_service()
        
        if not pkcs11.pkcs11_available:
            return jsonify({
                'success': False,
                'message': 'PyKCS11 não está instalado. Instale com: pip install PyKCS11',
                'tokens': []
            }), 503
        
        # Detectar bibliotecas
        libraries = pkcs11.detect_libraries()
        
        if not libraries:
            return jsonify({
                'success': False,
                'message': 'Nenhuma biblioteca PKCS#11 encontrada no sistema',
                'tokens': [],
                'help': 'Instale os drivers do seu token (SafeNet, Certisign, etc)'
            }), 404
        
        # Listar tokens em cada biblioteca
        all_tokens = []
        for lib in libraries:
            tokens = pkcs11.list_tokens(lib['path'])
            for token in tokens:
                token['library_info'] = {
                    'fabricante': lib['fabricante'],
                    'nome': lib['nome']
                }
                all_tokens.append(token)
        
        return jsonify({
            'success': True,
            'tokens': all_tokens,
            'libraries': libraries
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erro ao detectar tokens: {str(e)}'
        }), 500


@a3_bp.route('/list-certificates', methods=['POST'])
@login_required
def list_certificates():
    """API: Lista certificados em um token específico"""
    try:
        data = request.get_json()
        
        library_path = data.get('library_path')
        slot_id = data.get('slot_id')
        pin = data.get('pin')
        
        if not all([library_path, slot_id is not None, pin]):
            return jsonify({
                'success': False,
                'message': 'Dados incompletos'
            }), 400
        
        pkcs11 = get_pkcs11_service()
        certificates = pkcs11.list_certificates_in_token(library_path, int(slot_id), pin)
        
        # Serializar datas para JSON
        for cert in certificates:
            cert['not_before'] = cert['not_before'].isoformat() if cert['not_before'] else None
            cert['not_after'] = cert['not_after'].isoformat() if cert['not_after'] else None
            del cert['cert_der']  # Remover dados binários
        
        return jsonify({
            'success': True,
            'certificates': certificates
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erro ao listar certificados: {str(e)}'
        }), 500


@a3_bp.route('/register', methods=['POST'])
@login_required
def register_certificate():
    """Registra um certificado A3 no sistema"""
    try:
        cliente_id = request.form.get('cliente_id')
        
        if not cliente_id:
            flash('Cliente não especificado', 'danger')
            return redirect(request.referrer or url_for('main.dashboard'))
        
        # Verificar permissão
        if not current_user.can_access_client(int(cliente_id)):
            flash('Você não tem permissão para acessar este cliente', 'danger')
            return redirect(url_for('main.dashboard'))
        
        a3_data = {
            'library_path': request.form.get('library_path'),
            'slot_id': int(request.form.get('slot_id')),
            'pin': request.form.get('pin'),
            'cert_label': request.form.get('cert_label')
        }
        
        db = next(get_db())
        success, cert_obj = process_certificate_a3_registration(db, int(cliente_id), a3_data)
        
        if success:
            return redirect(url_for('clientes.view_client', cliente_id=cliente_id))
        else:
            return redirect(request.referrer or url_for('clientes.view_client', cliente_id=cliente_id))
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'Erro ao registrar certificado A3: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('main.dashboard'))


@a3_bp.route('/select/<int:cliente_id>', methods=['GET'])
@login_required
def select_certificate(cliente_id):
    """Página de seleção de certificado A3"""
    
    # Verificar permissão
    if not current_user.can_access_client(cliente_id):
        flash('Você não tem permissão para acessar este cliente', 'danger')
        return redirect(url_for('main.dashboard'))
    
    return render_template('a3/select_certificate.html', cliente_id=cliente_id)
