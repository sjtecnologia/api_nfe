import json
import psycopg2
from psycopg2 import Error

def import_cfop_data(json_file_path, db_config):
    """
    Importa dados CFOP de um arquivo JSON para uma tabela PostgreSQL.

    Args:
        json_file_path (str): Caminho para o arquivo JSON contendo os dados CFOP.
        db_config (dict): Dicionário com as configurações de conexão ao banco de dados.
                          Ex: {'host': 'localhost', 'database': 'seu_banco',
                               'user': 'seu_usuario', 'password': 'sua_senha'}
    """
    conn = None
    try:
        # Conectar ao banco de dados PostgreSQL
        print("Conectando ao banco de dados PostgreSQL...")
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        print("Conexão bem-sucedida.")

        # Abrir e carregar o arquivo JSON
        print(f"Lendo o arquivo JSON: {json_file_path}...")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            cfop_data = json.load(f)
        print(f"Total de {len(cfop_data)} registros encontrados no JSON.")

        # Consulta SQL para inserção de dados
        # Certifique-se de que os nomes das colunas abaixo correspondem à sua tabela no banco de dados.
        # Ajuste a tabela 'cfops' e as colunas conforme a sua necessidade.
        insert_sql = """
        INSERT INTO cfops (cfop, descricao, observacao, tipooperacao, identificadordestinooperacao)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (cfop) DO UPDATE SET
            descricao = EXCLUDED.descricao,
            observacao = EXCLUDED.observacao,
            tipooperacao = EXCLUDED.tipooperacao,
            identificadordestinooperacao = EXCLUDED.identificadordestinooperacao;
        """

        # Inserir cada registro no banco de dados
        print("Iniciando a importação dos dados...")
        for record in cfop_data:
            # Extrair os dados do registro
            cfop = record.get('cfop')
            descricao = record.get('descricao')
            observacao = record.get('observacao')
            tipooperacao = record.get('tipooperacao')
            identificadordestinooperacao = record.get('identificadordestinooperacao')

            # Executar a inserção
            cursor.execute(insert_sql, (cfop, descricao, observacao, tipooperacao, identificadordestinooperacao))
        
        # Commit das transações
        conn.commit()
        print("Importação concluída com sucesso!")

    except (Exception, Error) as error:
        print(f"Erro ao importar dados: {error}")
        if conn:
            conn.rollback()  # Reverter em caso de erro
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("Conexão ao banco de dados PostgreSQL fechada.")

if __name__ == "__main__":
    # --- Configurações do Banco de Dados (ALTERAR PARA SEUS DADOS) ---
    db_settings = {
        'host': 'localhost',  # Ou o IP/nome do host do seu servidor PostgreSQL
        'database': 'sjtnfe', # O nome do seu banco de dados
        'user': 'postgres',       # Seu usuário do PostgreSQL
        'password': 'Mo@2508'     # Sua senha do PostgreSQL
    }

    # --- Caminho para o seu arquivo JSON ---
    json_file = 'tabela_cfop.json' # Certifique-se de que este arquivo esteja no mesmo diretório do script, ou forneça o caminho completo

    # Iniciar a importação
    import_cfop_data(json_file, db_settings)
