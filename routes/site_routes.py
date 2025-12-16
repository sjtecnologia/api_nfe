"""
Rotas para o site de vendas e gestão de assinaturas
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from database.connection import SessionLocal
from database.models import Cliente, PlanoNfe, AssinaturaCliente, User
import stripe
import os

site_bp = Blueprint('site', __name__, url_prefix='/api/site')

# Configurar Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', '')

@site_bp.route('/planos', methods=['GET'])
def listar_planos():
    """Lista todos os planos disponíveis para venda"""
    try:
        db = SessionLocal()
        
        planos = db.query(PlanoNfe).filter(PlanoNfe.ativo == True).all()
        
        result = []
        for plano in planos:
            result.append({
                'id': plano.plano_id,
                'nome': plano.nome_plano,
                'descricao': plano.descricao,
                'preco_mensal': float(plano.preco_mensal),
                'limite_nfe_mes': plano.limite_nfe_mes,
                'recursos': [
                    f"Até {plano.limite_nfe_mes} NFe/mês",
                    "Suporte via email",
                    "Certificado digital A1",
                    "Emissão de NFe e NFCe",
                    "Relatórios gerenciais",
                    "Múltiplos usuários",
                    "API REST completa",
                    "Sugestão de NCM com IA" if plano.plano_id >= 2 else None,
                    "Suporte prioritário" if plano.plano_id >= 3 else None,
                    "Gestor de clientes" if plano.plano_id >= 3 else None,
                ],
                'popular': plano.plano_id == 2  # Plano intermediário como popular
            })
        
        db.close()
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Erro ao listar planos: {e}")
        return jsonify({'error': str(e)}), 500


@site_bp.route('/cadastro', methods=['POST'])
def cadastrar_empresa():
    """Cadastra nova empresa interessada"""
    try:
        data = request.json
        
        # Validar dados obrigatórios
        required = ['cnpj', 'razao_social', 'email', 'telefone', 'nome_responsavel']
        for field in required:
            if not data.get(field):
                return jsonify({'error': f'Campo {field} é obrigatório'}), 400
        
        db = SessionLocal()
        
        # Verificar se CNPJ já existe
        cliente_existe = db.query(Cliente).filter(Cliente.cnpj == data['cnpj']).first()
        if cliente_existe:
            db.close()
            return jsonify({'error': 'CNPJ já cadastrado'}), 400
        
        # Verificar se email já existe
        user_existe = db.query(User).filter(User.email == data['email']).first()
        if user_existe:
            db.close()
            return jsonify({'error': 'Email já cadastrado'}), 400
        
        # Criar cliente
        novo_cliente = Cliente(
            cnpj=data['cnpj'],
            razao_social=data['razao_social'],
            nome_fantasia=data.get('nome_fantasia', data['razao_social']),
            email_contato=data['email'],
            telefone_contato=data['telefone'],
            regime_tributario_id=1,  # Padrão: Simples Nacional
            ativo=False,  # Ativo após pagamento
            data_cadastro=datetime.now(),
            ambiente='homologacao'  # Começa em homologação
        )
        
        db.add(novo_cliente)
        db.flush()  # Para obter o cliente_id
        
        # Criar usuário
        from werkzeug.security import generate_password_hash
        
        novo_user = User(
            username=data['email'],
            email=data['email'],
            password_hash=generate_password_hash(data.get('senha', 'Trocar@123')),
            nome_completo=data['nome_responsavel'],
            ativo=False,  # Ativo após pagamento
            created_at=datetime.now()
        )
        
        db.add(novo_user)
        db.flush()
        
        # Associar user ao cliente
        from database.models import UserClient
        
        user_client = UserClient(
            user_id=novo_user.user_id,
            cliente_id=novo_cliente.cliente_id
        )
        
        db.add(user_client)
        db.commit()
        
        result = {
            'cliente_id': novo_cliente.cliente_id,
            'user_id': novo_user.user_id,
            'email': novo_user.email,
            'mensagem': 'Cadastro realizado com sucesso! Complete o pagamento para ativar sua conta.'
        }
        
        db.close()
        return jsonify(result), 201
        
    except Exception as e:
        print(f"Erro ao cadastrar empresa: {e}")
        return jsonify({'error': str(e)}), 500


@site_bp.route('/checkout', methods=['POST'])
def criar_checkout_stripe():
    """Cria sessão de checkout no Stripe"""
    try:
        data = request.json
        
        cliente_id = data.get('cliente_id')
        plano_id = data.get('plano_id')
        
        if not cliente_id or not plano_id:
            return jsonify({'error': 'cliente_id e plano_id são obrigatórios'}), 400
        
        db = SessionLocal()
        
        # Buscar cliente
        cliente = db.query(Cliente).filter(Cliente.cliente_id == cliente_id).first()
        if not cliente:
            db.close()
            return jsonify({'error': 'Cliente não encontrado'}), 404
        
        # Buscar plano
        plano = db.query(PlanoNfe).filter(PlanoNfe.plano_id == plano_id).first()
        if not plano:
            db.close()
            return jsonify({'error': 'Plano não encontrado'}), 404
        
        # Criar sessão de checkout no Stripe
        session = stripe.checkout.Session.create(
            mode='subscription',
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': plano.nome_plano,
                        'description': plano.descricao,
                    },
                    'unit_amount': int(float(plano.preco_mensal) * 100),  # em centavos
                    'recurring': {
                        'interval': 'month',
                    },
                },
                'quantity': 1,
            }],
            success_url=f"{os.getenv('NEXT_PUBLIC_SITE_URL')}/dashboard?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{os.getenv('NEXT_PUBLIC_SITE_URL')}/pricing",
            customer_email=cliente.email_contato,
            metadata={
                'cliente_id': str(cliente_id),
                'plano_id': str(plano_id),
                'cnpj': cliente.cnpj,
            },
        )
        
        db.close()
        
        return jsonify({
            'checkout_url': session.url,
            'session_id': session.id
        }), 200
        
    except Exception as e:
        print(f"Erro ao criar checkout: {e}")
        return jsonify({'error': str(e)}), 500


@site_bp.route('/webhook/stripe', methods=['POST'])
def webhook_stripe():
    """Webhook para processar eventos do Stripe"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        print(f"Payload inválido: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        print(f"Assinatura inválida: {e}")
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Processar evento
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Ativar assinatura
        ativar_assinatura(session)
        
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        
        # Renovar assinatura
        renovar_assinatura(invoice)
        
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        
        # Cancelar assinatura
        cancelar_assinatura(subscription)
    
    return jsonify({'status': 'success'}), 200


def ativar_assinatura(session):
    """Ativa assinatura após pagamento bem-sucedido"""
    try:
        db = SessionLocal()
        
        cliente_id = int(session['metadata']['cliente_id'])
        plano_id = int(session['metadata']['plano_id'])
        
        # Buscar cliente
        cliente = db.query(Cliente).filter(Cliente.cliente_id == cliente_id).first()
        if not cliente:
            print(f"Cliente {cliente_id} não encontrado")
            db.close()
            return
        
        # Buscar plano
        plano = db.query(PlanoNfe).filter(PlanoNfe.plano_id == plano_id).first()
        if not plano:
            print(f"Plano {plano_id} não encontrado")
            db.close()
            return
        
        # Criar assinatura
        assinatura = AssinaturaCliente(
            cliente_id=cliente_id,
            plano_id=plano_id,
            data_inicio=datetime.now(),
            data_fim=datetime.now() + timedelta(days=30),
            status='ativa',
            stripe_subscription_id=session.get('subscription'),
            stripe_customer_id=session.get('customer'),
            valor_pago=float(plano.preco_mensal),
            forma_pagamento='stripe',
            data_pagamento=datetime.now()
        )
        
        db.add(assinatura)
        
        # Ativar cliente
        cliente.ativo = True
        cliente.data_atualizacao = datetime.now()
        
        # Ativar usuários do cliente
        from database.models import UserClient
        user_clients = db.query(UserClient).filter(UserClient.cliente_id == cliente_id).all()
        
        for uc in user_clients:
            user = db.query(User).filter(User.user_id == uc.user_id).first()
            if user:
                user.ativo = True
        
        db.commit()
        db.close()
        
        print(f"✅ Assinatura ativada para cliente {cliente_id}")
        
        # Aqui você pode enviar email de boas-vindas
        
    except Exception as e:
        print(f"Erro ao ativar assinatura: {e}")


def renovar_assinatura(invoice):
    """Renova assinatura após pagamento mensal"""
    try:
        db = SessionLocal()
        
        subscription_id = invoice.get('subscription')
        
        # Buscar assinatura
        assinatura = db.query(AssinaturaCliente).filter(
            AssinaturaCliente.stripe_subscription_id == subscription_id
        ).first()
        
        if not assinatura:
            print(f"Assinatura {subscription_id} não encontrada")
            db.close()
            return
        
        # Renovar por mais 30 dias
        assinatura.data_fim = assinatura.data_fim + timedelta(days=30)
        assinatura.status = 'ativa'
        assinatura.data_pagamento = datetime.now()
        
        db.commit()
        db.close()
        
        print(f"✅ Assinatura renovada: {subscription_id}")
        
    except Exception as e:
        print(f"Erro ao renovar assinatura: {e}")


def cancelar_assinatura(subscription):
    """Cancela assinatura"""
    try:
        db = SessionLocal()
        
        subscription_id = subscription.get('id')
        
        # Buscar assinatura
        assinatura = db.query(AssinaturaCliente).filter(
            AssinaturaCliente.stripe_subscription_id == subscription_id
        ).first()
        
        if not assinatura:
            print(f"Assinatura {subscription_id} não encontrada")
            db.close()
            return
        
        # Cancelar
        assinatura.status = 'cancelada'
        assinatura.data_cancelamento = datetime.now()
        
        # Desativar cliente se não tiver outra assinatura ativa
        outras_ativas = db.query(AssinaturaCliente).filter(
            AssinaturaCliente.cliente_id == assinatura.cliente_id,
            AssinaturaCliente.status == 'ativa',
            AssinaturaCliente.assinatura_id != assinatura.assinatura_id
        ).count()
        
        if outras_ativas == 0:
            cliente = db.query(Cliente).filter(
                Cliente.cliente_id == assinatura.cliente_id
            ).first()
            if cliente:
                cliente.ativo = False
        
        db.commit()
        db.close()
        
        print(f"✅ Assinatura cancelada: {subscription_id}")
        
    except Exception as e:
        print(f"Erro ao cancelar assinatura: {e}")


@site_bp.route('/assinatura/cliente/<int:cliente_id>', methods=['GET'])
def obter_assinatura_cliente(cliente_id):
    """Retorna assinatura ativa do cliente"""
    try:
        db = SessionLocal()
        
        assinatura = db.query(AssinaturaCliente).filter(
            AssinaturaCliente.cliente_id == cliente_id,
            AssinaturaCliente.status == 'ativa'
        ).order_by(AssinaturaCliente.data_inicio.desc()).first()
        
        if not assinatura:
            db.close()
            return jsonify({'error': 'Assinatura não encontrada'}), 404
        
        plano = db.query(PlanoNfe).filter(
            PlanoNfe.plano_id == assinatura.plano_id
        ).first()
        
        result = {
            'assinatura_id': assinatura.assinatura_id,
            'status': assinatura.status,
            'data_inicio': assinatura.data_inicio.isoformat(),
            'data_fim': assinatura.data_fim.isoformat(),
            'plano': {
                'id': plano.plano_id,
                'nome': plano.nome_plano,
                'preco': float(plano.preco_mensal),
                'limite_nfe': plano.limite_nfe_mes
            },
            'dias_restantes': (assinatura.data_fim - datetime.now()).days
        }
        
        db.close()
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Erro ao obter assinatura: {e}")
        return jsonify({'error': str(e)}), 500
