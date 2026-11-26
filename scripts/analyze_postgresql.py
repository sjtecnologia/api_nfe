"""
Script para analisar a estrutura completa do banco PostgreSQL
e gerar informações para criar formulário de produtos completo
"""

import sys
import os
import json
from datetime import datetime

# Adicionar o diretório pai ao path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ psycopg2 não instalado!")
    print("Execute: pip install psycopg2-binary")
    sys.exit(1)

# Importar configurações
from config.settings import SQLALCHEMY_DATABASE_URL

def parse_database_url(url):
    """Parse da URL do banco para extrair parâmetros"""
    # postgresql://postgres:***SENHA_LOCAL_DEV***@localhost:5432/sjtnfe
    import re
    
    pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
    match = re.match(pattern, url)
    
    if match:
        return {
            'user': match.group(1),
            'password': match.group(2),
            'host': match.group(3),
            'port': int(match.group(4)),
            'database': match.group(5)
        }
    else:
        raise ValueError(f"URL inválida: {url}")

def analyze_postgresql():
    """Analisa toda a estrutura do banco PostgreSQL"""
    
    try:
        # Parse da URL de conexão
        db_config = parse_database_url(SQLALCHEMY_DATABASE_URL)
        print(f"🔗 Configuração do banco:")
        print(f"  • Host: {db_config['host']}:{db_config['port']}")
        print(f"  • Database: {db_config['database']}")
        print(f"  • User: {db_config['user']}")
        
        # Conectar ao banco
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['database'],
            user=db_config['user'],
            password=db_config['password']
        )
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("\n🔍 ANALISANDO ESTRUTURA DO BANCO POSTGRESQL")
        print("=" * 60)
        
        # 1. Listar todas as tabelas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        print(f"\n📋 TABELAS ENCONTRADAS ({len(tables)}):")
        for table in tables:
            print(f"  • {table['table_name']}")
        
        # 2. Analisar estrutura da tabela produtos
        print("\n" + "=" * 60)
        print("🏷️  ESTRUTURA DA TABELA 'produtos'")
        print("=" * 60)
        
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns 
            WHERE table_name = 'produtos' 
            ORDER BY ordinal_position
        """)
        
        produtos_columns = cursor.fetchall()
        
        if produtos_columns:
            print("\nCOLUNAS DA TABELA PRODUTOS:")
            for col in produtos_columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f"DEFAULT: {col['column_default']}" if col['column_default'] else ""
                
                # Informações de tamanho/precisão
                size_info = ""
                if col['character_maximum_length']:
                    size_info = f"({col['character_maximum_length']})"
                elif col['numeric_precision']:
                    if col['numeric_scale']:
                        size_info = f"({col['numeric_precision']},{col['numeric_scale']})"
                    else:
                        size_info = f"({col['numeric_precision']})"
                
                print(f"  • {col['column_name']:25} | {col['data_type']}{size_info:15} | {nullable:8} | {default}")
        else:
            print("❌ Tabela 'produtos' não encontrada!")
            return
        
        # 3. Analisar tabelas relacionadas
        related_tables = ['ncms', 'cfops', 'clientes', 'unidades_medida']
        
        for table_name in related_tables:
            try:
                print(f"\n" + "-" * 40)
                print(f"📊 TABELA: {table_name.upper()}")
                print("-" * 40)
                
                cursor.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns 
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
                
                columns = cursor.fetchall()
                
                if columns:
                    print("ESTRUTURA:")
                    for col in columns:
                        nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                        print(f"  • {col['column_name']:20} | {col['data_type']:15} | {nullable:8}")
                    
                    # Mostrar alguns dados de exemplo
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                    sample_data = cursor.fetchall()
                    
                    if sample_data:
                        print("\nDADOS DE EXEMPLO:")
                        for row in sample_data:
                            print(f"  → {dict(row)}")
                    else:
                        print("  ⚠️  Tabela vazia")
                else:
                    print("  ❌ Tabela não encontrada")
                    
            except Exception as e:
                print(f"  ⚠️  Erro ao analisar {table_name}: {e}")
        
        # 4. Verificar Foreign Keys da tabela produtos
        print(f"\n" + "=" * 60)
        print("🔗 FOREIGN KEYS DA TABELA PRODUTOS")
        print("=" * 60)
        
        cursor.execute("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE constraint_type = 'FOREIGN KEY'
            AND tc.table_name = 'produtos'
        """)
        
        foreign_keys = cursor.fetchall()
        
        if foreign_keys:
            for fk in foreign_keys:
                print(f"  • {fk['column_name']:20} → {fk['foreign_table_name']}.{fk['foreign_column_name']}")
        else:
            print("  ❌ Nenhuma Foreign Key encontrada")
        
        # 5. Analisar dados existentes na tabela produtos
        print(f"\n" + "=" * 60)
        print("📦 DADOS EXISTENTES NA TABELA PRODUTOS")
        print("=" * 60)
        
        cursor.execute("SELECT COUNT(*) as total FROM produtos")
        total_produtos = cursor.fetchone()['total']
        print(f"Total de produtos: {total_produtos}")
        
        if total_produtos > 0:
            cursor.execute("""
                SELECT produto_id, codigo_interno, descricao, unidade_comercial, 
                       preco_unitario_padrao, ncm_id, cliente_id, ativo
                FROM produtos 
                LIMIT 3
            """)
            
            sample_produtos = cursor.fetchall()
            print("\nEXEMPLOS DE PRODUTOS:")
            for produto in sample_produtos:
                desc = produto['descricao'][:30] + "..." if produto['descricao'] and len(produto['descricao']) > 30 else produto['descricao']
                print(f"  → ID: {produto['produto_id']} | Código: {produto['codigo_interno']} | Desc: {desc}")
        
        # 6. Verificar tabelas específicas importantes
        check_specific_tables_internal(cursor)
        
        # 7. Gerar sugestões para o formulário
        print(f"\n" + "=" * 60)
        print("💡 SUGESTÕES PARA O FORMULÁRIO DE PRODUTOS")
        print("=" * 60)
        
        suggestions = generate_form_suggestions(cursor, produtos_columns)
        
        for suggestion in suggestions:
            print(f"  • {suggestion}")
        
        # 8. Salvar análise em arquivo JSON
        analysis_data = {
            "timestamp": datetime.now().isoformat(),
            "database_type": "PostgreSQL",
            "database_config": {
                "host": db_config['host'],
                "port": db_config['port'],
                "database": db_config['database']
            },
            "tables": [t['table_name'] for t in tables],
            "produtos_columns": [
                {
                    "name": col['column_name'],
                    "type": col['data_type'],
                    "nullable": col['is_nullable'] == 'YES',
                    "default": col['column_default'],
                    "max_length": col['character_maximum_length'],
                    "precision": col['numeric_precision'],
                    "scale": col['numeric_scale']
                }
                for col in produtos_columns
            ],
            "foreign_keys": [
                {
                    "from_column": fk['column_name'],
                    "to_table": fk['foreign_table_name'],
                    "to_column": fk['foreign_column_name']
                }
                for fk in foreign_keys
            ],
            "total_produtos": total_produtos
        }
        
        with open('../database_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Análise salva em: ../database_analysis.json")
        
    except psycopg2.Error as e:
        print(f"❌ Erro ao conectar com PostgreSQL: {e}")
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def generate_form_suggestions(cursor, produtos_columns):
    """Gera sugestões para campos do formulário baseado na estrutura PostgreSQL"""
    
    suggestions = []
    
    for col in produtos_columns:
        name = col['column_name']
        data_type = col['data_type']
        nullable = col['is_nullable'] == 'YES'
        max_length = col['character_maximum_length']
        
        required_text = "optional" if nullable else "required"
        
        if name == 'produto_id':
            suggestions.append(f"{name}: Campo oculto (Primary Key)")
        elif name.endswith('_id') and name != 'produto_id':
            # Foreign Key - dropdown
            if name == 'cliente_id':
                suggestions.append(f"{name}: SELECT da tabela 'clientes' (nome_fantasia) - {required_text}")
            elif name == 'ncm_id':
                suggestions.append(f"{name}: SELECT da tabela 'ncms' (codigo + descricao) - {required_text}")
            elif name == 'cfop_id':
                suggestions.append(f"{name}: SELECT da tabela 'cfops' (codigo + descricao) - {required_text}")
            else:
                table_name = name.replace('_id', 's')
                suggestions.append(f"{name}: SELECT da tabela '{table_name}' - {required_text}")
        elif 'preco' in name.lower() or 'valor' in name.lower():
            suggestions.append(f"{name}: Input number step='0.01' (formato moeda R$) - {required_text}")
        elif 'descricao' in name.lower():
            max_text = f" maxlength='{max_length}'" if max_length else ""
            suggestions.append(f"{name}: Textarea{max_text} - {required_text}")
        elif name == 'ativo':
            suggestions.append(f"{name}: Checkbox (ativo/inativo) - default true")
        elif 'codigo' in name.lower():
            max_text = f" maxlength='{max_length}'" if max_length else ""
            suggestions.append(f"{name}: Input text{max_text} (validação única) - {required_text}")
        elif 'unidade' in name.lower():
            suggestions.append(f"{name}: Input text ou SELECT (UN, KG, LT, etc) - {required_text}")
        elif data_type == 'integer':
            suggestions.append(f"{name}: Input number - {required_text}")
        elif data_type in ['numeric', 'decimal', 'real', 'double precision']:
            suggestions.append(f"{name}: Input number step='0.01' - {required_text}")
        elif data_type in ['character varying', 'varchar', 'text']:
            max_text = f" maxlength='{max_length}'" if max_length else ""
            suggestions.append(f"{name}: Input text{max_text} - {required_text}")
        elif data_type == 'boolean':
            suggestions.append(f"{name}: Checkbox - {required_text}")
        elif data_type in ['date']:
            suggestions.append(f"{name}: Input date - {required_text}")
        elif data_type in ['timestamp', 'timestamptz']:
            suggestions.append(f"{name}: Input datetime-local - {required_text}")
        else:
            suggestions.append(f"{name}: Input text (tipo: {data_type}) - {required_text}")
    
    return suggestions

def check_specific_tables_internal(cursor):
    """Verifica tabelas específicas importantes para o formulário"""
    
    print(f"\n" + "=" * 60)
    print("🎯 VERIFICAÇÃO DE TABELAS ESPECÍFICAS")
    print("=" * 60)
    
    # Verificar NCMs
    try:
        cursor.execute("SELECT COUNT(*) as total FROM ncms")
        ncm_count = cursor.fetchone()['total']
        print(f"📊 NCMs disponíveis: {ncm_count}")
        
        if ncm_count > 0:
            cursor.execute("SELECT ncm_id, codigo, descricao FROM ncms LIMIT 3")
            ncms = cursor.fetchall()
            print("   Exemplos:")
            for ncm in ncms:
                desc = ncm['descricao'][:40] + "..." if ncm['descricao'] and len(ncm['descricao']) > 40 else ncm['descricao']
                print(f"     → {ncm['ncm_id']}: {ncm['codigo']} - {desc}")
    except Exception as e:
        print(f"❌ Erro na tabela NCMs: {e}")
    
    # Verificar CFOPs
    try:
        cursor.execute("SELECT COUNT(*) as total FROM cfops")
        cfop_count = cursor.fetchone()['total']
        print(f"📊 CFOPs disponíveis: {cfop_count}")
        
        if cfop_count > 0:
            cursor.execute("SELECT cfop_id, codigo, descricao FROM cfops LIMIT 3")
            cfops = cursor.fetchall()
            print("   Exemplos:")
            for cfop in cfops:
                desc = cfop['descricao'][:40] + "..." if cfop['descricao'] and len(cfop['descricao']) > 40 else cfop['descricao']
                print(f"     → {cfop['cfop_id']}: {cfop['codigo']} - {desc}")
    except Exception as e:
        print(f"❌ Erro na tabela CFOPs: {e}")
    
    # Verificar Clientes
    try:
        cursor.execute("SELECT COUNT(*) as total FROM clientes")
        cliente_count = cursor.fetchone()['total']
        print(f"📊 Clientes disponíveis: {cliente_count}")
        
        if cliente_count > 0:
            cursor.execute("SELECT cliente_id, nome_fantasia, razao_social FROM clientes LIMIT 3")
            clientes = cursor.fetchall()
            print("   Exemplos:")
            for cliente in clientes:
                print(f"     → {cliente['cliente_id']}: {cliente['nome_fantasia']} ({cliente['razao_social']})")
    except Exception as e:
        print(f"❌ Erro na tabela Clientes: {e}")

if __name__ == "__main__":
    print("🚀 INICIANDO ANÁLISE DO BANCO POSTGRESQL")
    print("=" * 60)
    
    analyze_postgresql()
    
    print(f"\n" + "=" * 60)
    print("✅ ANÁLISE CONCLUÍDA!")
    print("=" * 60)
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. Analise o resultado acima")
    print("2. Verifique o arquivo 'database_analysis.json' gerado")
    print("3. Use as informações para criar o formulário completo")