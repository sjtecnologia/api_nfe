"""
Serviço de Webhooks
Envia notificações HTTP para URLs cadastradas quando eventos ocorrem
"""
from database.connection import get_db
from database.models import Webhook, WebhookQueue
import requests
import json
import hmac
import hashlib
from datetime import datetime, timedelta
import threading


def trigger_webhook(cliente_id, evento, payload):
    """
    Adiciona um webhook à fila de envio
    
    Args:
        cliente_id: ID do cliente
        evento: Nome do evento (ex: 'nfe.autorizada', 'nfe.cancelada')
        payload: Dict com os dados do evento
    """
    try:
        db = next(get_db())
        
        # Buscar webhooks ativos para este evento
        webhooks = db.query(Webhook).filter_by(
            cliente_id=cliente_id,
            ativo=True
        ).all()
        
        for webhook in webhooks:
            if webhook.supports_event(evento):
                # Adicionar à fila
                queue_item = WebhookQueue(
                    webhook_id=webhook.webhook_id,
                    evento=evento,
                    payload=json.dumps(payload),
                    max_tentativas=webhook.retry_count
                )
                db.add(queue_item)
        
        db.commit()
        
        # Processar fila em background
        threading.Thread(target=process_webhook_queue, daemon=True).start()
    
    except Exception as e:
        print(f"[WARN] Erro ao adicionar webhook à fila: {e}")


def calculate_signature(payload_str, secret):
    """
    Calcula assinatura HMAC-SHA256 do payload
    
    Args:
        payload_str: String JSON do payload
        secret: Secret do webhook
        
    Returns:
        str: Assinatura hex
    """
    if not secret:
        return None
    
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature


def send_webhook(queue_item):
    """
    Envia um webhook HTTP
    
    Args:
        queue_item: WebhookQueue object
        
    Returns:
        tuple: (sucesso, mensagem_erro)
    """
    try:
        db = next(get_db())
        webhook = db.query(Webhook).filter_by(webhook_id=queue_item.webhook_id).first()
        
        if not webhook or not webhook.ativo:
            return False, "Webhook inativo ou não encontrado"
        
        # Preparar payload
        payload_dict = json.loads(queue_item.payload)
        payload_dict['evento'] = queue_item.evento
        payload_dict['timestamp'] = datetime.now().isoformat()
        payload_dict['webhook_id'] = webhook.webhook_id
        
        payload_str = json.dumps(payload_dict)
        
        # Calcular assinatura
        signature = calculate_signature(payload_str, webhook.secret)
        
        # Headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'EmiteMax-Webhook/1.0',
            'X-EmiteMax-Event': queue_item.evento,
            'X-EmiteMax-Delivery': str(queue_item.queue_id)
        }
        
        if signature:
            headers['X-EmiteMax-Signature'] = f'sha256={signature}'
        
        # Enviar requisição
        response = requests.post(
            webhook.url,
            data=payload_str,
            headers=headers,
            timeout=webhook.timeout_seconds
        )
        
        # Verificar resposta
        if 200 <= response.status_code < 300:
            # Sucesso
            webhook.ultimo_sucesso = datetime.now()
            webhook.total_sucessos += 1
            queue_item.status = 'sent'
            queue_item.processado_em = datetime.now()
            db.commit()
            return True, None
        else:
            # Erro HTTP
            erro_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            return False, erro_msg
    
    except requests.Timeout:
        return False, "Timeout na requisição"
    except requests.ConnectionError as e:
        return False, f"Erro de conexão: {str(e)}"
    except Exception as e:
        return False, f"Erro inesperado: {str(e)}"


def process_webhook_queue():
    """
    Processa a fila de webhooks pendentes
    Executado em background thread
    """
    try:
        db = next(get_db())
        
        # Buscar itens pendentes ou que devem ser retentados
        agora = datetime.now()
        
        pending_items = db.query(WebhookQueue).filter(
            WebhookQueue.status == 'pending',
            WebhookQueue.tentativas < WebhookQueue.max_tentativas,
            (WebhookQueue.proximo_retry.is_(None) | (WebhookQueue.proximo_retry <= agora))
        ).limit(10).all()
        
        for item in pending_items:
            # Marcar como processando
            item.status = 'processing'
            item.tentativas += 1
            db.commit()
            
            # Enviar
            sucesso, erro = send_webhook(item)
            
            if not sucesso:
                # Falhou - agendar retry
                item.status = 'pending'
                item.erro = erro
                
                # Backoff exponencial: 1min, 5min, 15min
                delays = [1, 5, 15]
                delay_idx = min(item.tentativas - 1, len(delays) - 1)
                item.proximo_retry = datetime.now() + timedelta(minutes=delays[delay_idx])
                
                # Atualizar webhook
                webhook = db.query(Webhook).filter_by(webhook_id=item.webhook_id).first()
                if webhook:
                    webhook.ultima_tentativa = datetime.now()
                    webhook.total_falhas += 1
                
                # Se atingiu max tentativas, marcar como failed
                if item.tentativas >= item.max_tentativas:
                    item.status = 'failed'
                    item.processado_em = datetime.now()
                
                db.commit()
            
            # Pequeno delay entre envios
            import time
            time.sleep(0.1)
    
    except Exception as e:
        print(f"[WARN] Erro ao processar fila de webhooks: {e}")
        import traceback
        traceback.print_exc()


def cleanup_old_webhook_logs():
    """
    Remove registros antigos da fila de webhooks
    Manter apenas últimos 30 dias
    """
    try:
        db = next(get_db())
        trinta_dias_atras = datetime.now() - timedelta(days=30)
        
        deleted = db.query(WebhookQueue).filter(
            WebhookQueue.criado_em < trinta_dias_atras,
            WebhookQueue.status.in_(['sent', 'failed'])
        ).delete()
        
        db.commit()
        print(f"[CLEAN] Removidos {deleted} logs antigos de webhooks")
    except Exception as e:
        print(f"[WARN] Erro ao limpar logs de webhooks: {e}")
