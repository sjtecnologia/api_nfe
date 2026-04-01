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
if not m:
    print('URL nao parseada:', db_url[:50])
    exit(1)

user, pwd, host, port, dbname = m.groups()
print(f'Conectando a {host}:{port}/{dbname} como {user}')

my_env = os.environ.copy()
my_env['PGPASSWORD'] = pwd
my_env['PGSSLMODE'] = 'require'

result = subprocess.run(
    ['psql', '-h', host, '-p', port, '-U', user, '-d', dbname,
     '-f', '/home/ubuntu/api_nfe/database/migration_produtor_rural.sql'],
    env=my_env, capture_output=True, text=True
)
print('STDOUT:', result.stdout[:3000])
print('STDERR:', result.stderr[:1000])
print('EXIT:', result.returncode)
