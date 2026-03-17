import subprocess, os, re

with open('/home/ubuntu/api_nfe/.env') as f:
    env_vars = {}
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env_vars[k.strip()] = v.strip()

db_url = env_vars.get('DATABASE_URL', '')
m = re.match(r'postgresql://([^:]+):(.+)@([^:]+):(\d+)/(.+)', db_url)
user, pwd, host, port, dbname = m.groups()
my_env = os.environ.copy()
my_env['PGPASSWORD'] = pwd
my_env['PGSSLMODE'] = 'require'

# Verificar constraint
q = "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='clientes'::regclass AND contype='c';"
r = subprocess.run(['psql', '-h', host, '-p', port, '-U', user, '-d', dbname, '-c', q],
                   env=my_env, capture_output=True, text=True)
print("=== CHECK CONSTRAINTS ===")
print(r.stdout)
print(r.stderr[:500])

# Verificar cliente 30
q2 = "SELECT cliente_id, cnpj, cpf, produtor_rural, razao_social FROM clientes WHERE cliente_id=30;"
r2 = subprocess.run(['psql', '-h', host, '-p', port, '-U', user, '-d', dbname, '-c', q2],
                    env=my_env, capture_output=True, text=True)
print("=== CLIENTE 30 ===")
print(r2.stdout)
print(r2.stderr[:500])
