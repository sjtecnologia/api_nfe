@nfe_bp.route('/cancelar/<int:nfe_id>', methods=['POST'])
@login_required
@editor_or_admin_required()
def cancelar_nfe(nfe_id):
    """Cancelar NFe na SEFAZ"""
    db = next(get_db())
    try:
        # Buscar NFe
        query = text("""
            SELECT n.*, c.cnpj as emitente_cnpj, c.razao_social as emitente_razao
            FROM nfe_emitidas n
            JOIN clientes c ON n.cliente_id = c.cliente_id
            WHERE n.nfe_emitida_id = :nfe_id
        """)
        result = db.execute(query, {'nfe_id': nfe_id})
        nfe = result.first()
        
        if not nfe:
            return jsonify({'success': False, 'message': 'NFe não encontrada'}), 404
        
        nfe_data = dict(nfe._mapping)
        
        # Validações
        if nfe_data.get('status', '').upper() != 'AUTORIZADA':
            return jsonify({'success': False, 'message': 'Apenas NFes autorizadas podem ser canceladas'}), 400
        
        chave_acesso = nfe_data.get('chave_acesso')
        if not chave_acesso or len(chave_acesso) != 44:
            return jsonify({'success': False, 'message': 'Chave de acesso inválida'}), 400
        
        protocolo = nfe_data.get('protocolo_autorizacao') or nfe_data.get('protocolo_sefaz')
        if not protocolo:
            return jsonify({'success': False, 'message': 'Protocolo não encontrado'}), 400
        
        # Verificar prazo de 24h
        from datetime import datetime, timedelta
        data_emissao = nfe_data.get('data_emissao')
        if data_emissao:
            if isinstance(data_emissao, str):
                data_emissao = datetime.fromisoformat(data_emissao.replace('Z', '+00:00'))
            if datetime.now() - data_emissao > timedelta(hours=24):
                return jsonify({'success': False, 'message': 'Prazo de cancelamento expirado (24 horas)'}), 400
        
        # Obter justificativa
        data = request.get_json()
        justificativa = data.get('justificativa', '').strip()
        
        if not justificativa or len(justificativa) < 15:
            return jsonify({'success': False, 'message': 'Justificativa deve ter no mínimo 15 caracteres'}), 400
        
        # Determinar ambiente
        ambiente = 'producao'
        if nfe_data.get('json_nfe'):
            json_nfe = nfe_data['json_nfe']
            if isinstance(json_nfe, str):
                import json
                json_nfe = json.loads(json_nfe)
            xml_content = json_nfe.get('xml_content', '')
            if '<tpAmb>2</tpAmb>' in xml_content:
                ambiente = 'homologacao'
        
        # Obter certificado
        from services.certificate_service import get_active_certificate_for_client
        certificado = get_active_certificate_for_client(db, nfe_data['cliente_id'])
        
        if not certificado:
            return jsonify({'success': False, 'message': 'Certificado não encontrado'}), 400
        
        # Cancelar na SEFAZ
        from services.sefaz_service import SefazService
        
        sefaz = SefazService(
            ambiente=ambiente,
            cert_path=certificado.get('cert_path'),
            key_path=certificado.get('key_path')
        )
        
        resultado = sefaz.cancelar_nfe(
            chave_nfe=chave_acesso,
            protocolo=protocolo,
            justificativa=justificativa,
            cnpj_emitente=nfe_data['emitente_cnpj']
        )
        
        if resultado.get('success'):
            # Atualizar no banco
            update_query = text("""
                UPDATE nfe_emitidas 
                SET status = 'CANCELADA',
                    protocolo_cancelamento = :protocolo,
                    data_cancelamento = :data_cancelamento,
                    justificativa_cancelamento = :justificativa
                WHERE nfe_emitida_id = :nfe_id
            """)
            db.execute(update_query, {
                'protocolo': resultado.get('protocolo'),
                'data_cancelamento': datetime.now(),
                'justificativa': justificativa,
                'nfe_id': nfe_id
            })
            db.commit()
            
            return jsonify({
                'success': True,
                'message': 'NFe cancelada com sucesso na SEFAZ',
                'protocolo': resultado.get('protocolo'),
                'data_cancelamento': resultado.get('data_cancelamento')
            })
        else:
            return jsonify({
                'success': False,
                'message': resultado.get('message', 'Erro ao cancelar na SEFAZ')
            })
            
    except Exception as e:
        db.rollback()
        print(f"[ERRO] Erro ao cancelar NFe: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erro ao cancelar: {str(e)}'
        }), 500
    finally:
        db.close()
