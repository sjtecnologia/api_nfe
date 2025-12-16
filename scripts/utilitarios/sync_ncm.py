#!/usr/bin/env python3
"""
Comando CLI para sincronização de NCMs
Usage: python sync_ncm.py [--force]
"""
import sys
import argparse
from pathlib import Path

# Adiciona o diretório do projeto ao path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.ncm_service import ncm_service

def main():
    parser = argparse.ArgumentParser(description='Sincronizar NCMs com a Receita Federal')
    parser.add_argument('--force', action='store_true', 
                       help='Força sincronização mesmo se já foi feita recentemente')
    parser.add_argument('--stats', action='store_true',
                       help='Mostra apenas estatísticas dos NCMs')
    
    args = parser.parse_args()
    
    if args.stats:
        # Mostra estatísticas
        stats = ncm_service.get_ncm_stats()
        print("\n[DATA] ESTATÍSTICAS DE NCM")
        print("=" * 40)
        print(f"NCMs no banco local: {stats['local_count']:,}")
        print(f"Última sincronização: {stats['last_sync'] or 'Nunca'}")
        print(f"Dias desde última sync: {stats['days_since_sync'] or 'N/A'}")
        print(f"Precisa sincronizar: {'Sim' if stats['should_sync'] else 'Não'}")
        return
    
    # Executa sincronização
    print("[START] Iniciando sincronização de NCMs...")
    result = ncm_service.full_sync(force=args.force)
    
    if result['success']:
        print(f"[OK] {result['message']}")
        if 'inserted' in result:
            print(f"   Inseridos: {result['inserted']:,}")
            print(f"   Atualizados: {result['updated']:,}")
            print(f"   Total no banco: {result['local_count']:,}")
    else:
        print(f"[X] {result['message']}")
        sys.exit(1)

if __name__ == '__main__':
    main()