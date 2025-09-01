# import_cfop_data.py
import pandas as pd
import psycopg2
from io import StringIO
import os
from datetime import datetime
import csv # Adicione esta linha para usar csv.QUOTE_NONE

# --- Configurações do Banco de Dados ---
# ATENÇÃO: Substitua pelos dados do seu PostgreSQL
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'sjtnfe')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'Mo@2508')
DB_PORT = os.getenv('DB_PORT', '5432')

# --- Configurações do Arquivo Excel e Tabela ---
EXCEL_FILE = 'CF.xlsx' # Certifique-se de que este arquivo está no mesmo diretório do script
TABLE_NAME = 'cfops'

def import_cfop_data_from_excel():
    conn = None
    try:
        # 1. Conectar ao PostgreSQL
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        cur = conn.cursor()
        print("Conexão com o banco de dados estabelecida com sucesso.")

        # 2. Ler o arquivo Excel com pandas
        print(f"Lendo o arquivo Excel: {EXCEL_FILE}...")
        try:
            # É importante garantir que o pandas leia o cabeçalho correto.
            # Se a primeira linha não é o cabeçalho real (como "GRUPO", "CFOP"),
            # você pode precisar especificar 'header=None' e depois tratar os nomes das colunas manualmente.
            # Ou se o cabeçalho está na segunda linha do Excel (índice 1), use header=1.
            # Por agora, vamos manter sem especificar o header, confiando no output anterior.
            df = pd.read_excel(EXCEL_FILE)
            print("Arquivo Excel lido com sucesso.")
            print("Colunas encontradas no Excel:", df.columns.tolist())
        except FileNotFoundError:
            print(f"Erro: O arquivo '{EXCEL_FILE}' não foi encontrado. Certifique-se de que ele está no mesmo diretório do script.")
            return
        except Exception as e:
            print(f"Erro ao ler o arquivo Excel: {e}")
            return

        # 3. Preparar os dados para importação
        # Renomear colunas para corresponder aos nomes da tabela do PostgreSQL
        df = df.rename(columns={
            "GRUPO": "tipo",
            "CFOP": "codigo",
            "DESCRICAO": "descricao",            
            "INICIO VIGENCIA": "data_vigencia_inicio"
        })

        # Adicionar colunas que não estão no Excel mas são esperadas no DB
        df['ativo'] = True
        # A coluna 'data_vigencia_fim' não está sendo preenchida nem renomeada.
        # Se ela for NOT NULL no DB, precisará de um valor.
        # Se ela for NULLABLE, pode ficar de fora da lista columns_to_insert ou ser None.
        # Assumindo que ela é NULLABLE e não será importada.

        # DEBUGGING: Verifique o DataFrame após renomear e adicionar colunas
        print("\nDEBUG: df.head() após renomear e adicionar 'ativo':")
        print(df.head())
        print("\nDEBUG: df.info() após renomear e adicionar 'ativo':")
        df.info()

        # Selecionar e reordenar as colunas para o comando COPY
        columns_to_insert = [
            "codigo",
            "descricao",
            "tipo",
            "data_vigencia_inicio",
            "ativo"
        ]
        df_to_insert = df[columns_to_insert]

        # DEBUGGING: Verifique df_to_insert antes da conversão para CSV
        print("\nDEBUG: df_to_insert.head() antes da conversão para CSV:")
        print(df_to_insert.head())
        print("\nDEBUG: df_to_insert.info() antes da conversão para CSV:")
        df_to_insert.info()

        # Substituir valores NaN (Not a Number) por None para COPY FROM
        df_to_insert = df_to_insert.where(pd.notnull(df_to_insert), None)

        # DEBUGGING: Verifique df_to_insert após NaN para None
        print("\nDEBUG: df_to_insert.head() após NaN para None:")
        print(df_to_insert.head())
        print("\nDEBUG: df_to_insert.info() após NaN para None:")
        df_to_insert.info()


        # Gerar string CSV em memória usando tab como delimitador
        csv_buffer = StringIO()
        print("Convertendo DataFrame para formato CSV em memória...")
        # Adição importante: quoting=csv.QUOTE_NONE para evitar que aspas duplas (")
        # sejam adicionadas em campos que contenham o delimitador (tab) ou que sejam strings.
        # Isso pode causar problemas com o COPY FROM se ele não espera aspas.
        df_to_insert.to_csv(csv_buffer, sep='\t', header=False, index=False, encoding='utf-8')
        csv_buffer.seek(0) # Voltar ao início do buffer

        # DEBUGGING: Imprima o conteúdo real do buffer CSV (primeiras 10 linhas)
        print("\nDEBUG: Conteúdo do buffer CSV (primeiras 10 linhas):")
        # Lendo algumas linhas para não imprimir o buffer inteiro se for grande
        temp_buffer_content = csv_buffer.read()
        csv_buffer.seek(0) # IMPORTANT: Rewind buffer again for cur.copy_from
        for i, line in enumerate(temp_buffer_content.splitlines()):
            if i >= 10: # Imprima as primeiras 10 linhas
                break
            print(line)


        # 4. Importar dados usando COPY FROM
        print(f"\nIniciando a importação para a tabela {TABLE_NAME}...")
        
        # Opcional: TRUNCATE TABLE antes de importar se for uma carga inicial limpa
        # Descomente a linha abaixo se você quiser apagar todos os dados existentes na tabela cfops antes de importar.
        # cur.execute(f"TRUNCATE TABLE {TABLE_NAME} RESTART IDENTITY;")
        # print("Tabela truncada e sequência de ID resetada.")

        try:
            cur.copy_from(
                csv_buffer,
                TABLE_NAME,
                sep='\t',
                columns=columns_to_insert
            )
            conn.commit()
            print("Dados importados com sucesso!")
            print(f"Total de linhas importadas: {cur.rowcount}")

        except psycopg2.IntegrityError as e:
            conn.rollback()
            if "duplicate key value violates unique constraint" in str(e):
                print(f"Erro de Integridade: Tentativa de inserir um 'codigo' CFOP duplicado. ({e})")
                print("Considere limpar a tabela ou ajustar o Excel para remover duplicatas se este for um erro inesperado.")
            else:
                print(f"Erro de Integridade do Banco de Dados: {e}")
        except psycopg2.DataError as e:
            conn.rollback()
            print(f"Erro de Dados: Verifique se os tipos de dados no Excel correspondem aos da tabela. ({e})")
            print("Isso pode ocorrer se, por exemplo, os campos de 'tipo' ou 'codigo' não foram alterados para os tamanhos corretos, ou se um valor (como data) está em um formato inválido.")
        except Exception as e:
            conn.rollback()
            print(f"Erro durante a importação: {e}")

    except psycopg2.Error as e:
        print(f"Erro de conexão com o banco de dados. Verifique as credenciais e se o banco está online: {e}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()
            print("Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("Variáveis de ambiente carregadas do .env (se existir).")
    except ImportError:
        print("Módulo 'python-dotenv' não encontrado. Usando variáveis de ambiente do sistema.")

    import_cfop_data_from_excel()