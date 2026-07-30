#!/usr/bin/env python3
"""Backfill do XML autorizado das NF-e antigas.

O script tenta, nesta ordem:
1. Reutilizar um XML já armazenado com <protNFe>.
2. Reconstituir o XML autorizado a partir do XML assinado + protocolo já salvo.
3. Consultar a SEFAZ por chave usando o certificado ativo do cliente e montar
   o XML autorizado a partir da resposta.

Atualiza json_nfe.xml_content e json_nfe.xml_autorizado para que download,
e-mail e lote passem a entregar o XML completo.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import SessionLocal
from database.models import NFeEmitidas
from services.certificate_service import get_active_certificate_for_client
from services.nfe_service import NFeService
from services.sefaz_service import SefazService
from sqlalchemy.orm.attributes import flag_modified


def _parse_json_nfe(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _extract_digest_value(xml_content: str) -> Optional[str]:
    if not xml_content:
        return None

    import re

    match = re.search(r'<DigestValue>([^<]+)</DigestValue>', xml_content)
    if match:
        return match.group(1).strip()
    return None


def _has_protocolo(xml_content: str) -> bool:
    return bool(xml_content and '<protNFe' in xml_content)


def _build_xml_autorizado(xml_base: str, protocolo: str, data_autorizacao: Optional[Any], dig_val: Optional[str]) -> str:
    resultado = {
        'protocolo': protocolo,
        'data_autorizacao': str(data_autorizacao) if data_autorizacao else '',
        'digVal': dig_val or '',
        'ambiente_real': True,
        'status': '100',
        'mensagem': 'Autorizado o uso da NF-e',
    }
    return NFeService()._gerar_xml_protocolo(xml_base, resultado)


def _consulta_sefaz_por_chave(db, nfe) -> Optional[Dict[str, Any]]:
    certificado = get_active_certificate_for_client(db, nfe.cliente_id)
    if not certificado or not certificado.get('cert_data') or not certificado.get('password'):
        return None

    json_nfe = _parse_json_nfe(nfe.json_nfe)
    ambiente = json_nfe.get('ambiente', 'producao')
    if ambiente not in ('producao', 'homologacao'):
        ambiente = 'producao'

    sefaz = SefazService(
        ambiente=ambiente
    )

    return sefaz.consultar_nfe_por_chave(
        nfe.chave_acesso,
        certificado_pfx=certificado['cert_data'],
        senha_certificado=certificado['password']
    )


def backfill_xmls(cliente_id: Optional[int] = None, dry_run: bool = False, limit: Optional[int] = None) -> int:
    db = SessionLocal()
    atualizados = 0

    try:
        query = db.query(NFeEmitidas).filter(NFeEmitidas.status == 'AUTORIZADA')
        if cliente_id:
            query = query.filter(NFeEmitidas.cliente_id == cliente_id)
        query = query.order_by(NFeEmitidas.data_autorizacao.asc().nullslast())
        if limit:
            query = query.limit(limit)

        nfes = query.all()
        print(f'[BACKFILL] Encontradas {len(nfes)} NFe autorizadas para processar')

        for nfe in nfes:
            json_nfe = _parse_json_nfe(nfe.json_nfe)
            xml_base = json_nfe.get('xml_autorizado') or json_nfe.get('xml_content') or ''

            if not xml_base:
                print(f'[SKIP] NFe {nfe.nfe_emitida_id} sem XML base no JSON')
                continue

            if _has_protocolo(xml_base):
                if json_nfe.get('xml_autorizado') != xml_base or json_nfe.get('xml_content') != xml_base:
                    json_nfe['xml_autorizado'] = xml_base
                    json_nfe['xml_content'] = xml_base
                    json_nfe['xml_autorizado_atualizado_em'] = __import__('datetime').datetime.now().isoformat()
                    if not dry_run:
                        nfe.json_nfe = json_nfe
                        db.add(nfe)
                        db.commit()
                    atualizados += 1
                    print(f'[OK] NFe {nfe.nfe_emitida_id} já tinha protocolo; normalizado no JSON')
                else:
                    print(f'[OK] NFe {nfe.nfe_emitida_id} já contém XML autorizado')
                continue

            protocolo = getattr(nfe, 'protocolo_sefaz', None) or json_nfe.get('protocolo_sefaz') or json_nfe.get('protocolo_autorizacao')
            xml_final = None

            if protocolo:
                xml_final = _build_xml_autorizado(
                    xml_base,
                    protocolo,
                    nfe.data_autorizacao,
                    _extract_digest_value(xml_base)
                )
                print(f'[OK] NFe {nfe.nfe_emitida_id} reconstruída com protocolo salvo')
            else:
                print(f'[CONSULTA] NFe {nfe.nfe_emitida_id} sem protocolo salvo; consultando SEFAZ...')
                consulta = _consulta_sefaz_por_chave(db, nfe)
                if consulta and consulta.get('success') and consulta.get('protocolo'):
                    xml_final = _build_xml_autorizado(
                        xml_base,
                        consulta['protocolo'],
                        consulta.get('dhRecbto') or nfe.data_autorizacao,
                        consulta.get('digVal') or _extract_digest_value(xml_base)
                    )
                    if not getattr(nfe, 'protocolo_sefaz', None):
                        nfe.protocolo_sefaz = consulta['protocolo']
                    print(f"[OK] NFe {nfe.nfe_emitida_id} autorizada consultando SEFAZ")
                else:
                    print(f'[FAIL] NFe {nfe.nfe_emitida_id} não pôde ser consultada na SEFAZ')

            if not xml_final:
                continue

            json_nfe['xml_autorizado'] = xml_final
            json_nfe['xml_content'] = xml_final
            json_nfe['xml_autorizado_atualizado_em'] = __import__('datetime').datetime.now().isoformat()

            if not dry_run:
                nfe.json_nfe = json_nfe
                flag_modified(nfe, 'json_nfe')
                db.add(nfe)
                db.commit()

            atualizados += 1
            print(f'[UPDATE] NFe {nfe.nfe_emitida_id} atualizada')

        return atualizados

    except Exception as exc:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description='Backfill do XML autorizado das NF-e antigas')
    parser.add_argument('--cliente-id', type=int, help='Filtrar por cliente específico')
    parser.add_argument('--limit', type=int, help='Limitar quantidade de registros')
    parser.add_argument('--dry-run', action='store_true', help='Não grava alterações')
    args = parser.parse_args()

    total = backfill_xmls(cliente_id=args.cliente_id, dry_run=args.dry_run, limit=args.limit)
    print(f'[DONE] Total de registros processados/atualizados: {total}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())