import subprocess, os, re

with open('/home/ubuntu/api_nfe/.env') as f:
    env_vars = {}
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env_vars[k.strip()] = v.strip()

db_url = env_vars.get('DATABASE_URL','')
m = re.match(r'postgresql://([^:]+):(.+)@([^:]+):(\d+)/(.+)', db_url)
user, pwd, host, port, dbname = m.groups()
my_env = os.environ.copy()
my_env['PGPASSWORD'] = pwd
my_env['PGSSLMODE'] = 'require'

q = "SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name='clientes' AND column_name IN ('cnpj','cpf','produtor_rural') ORDER BY column_name;"
r = subprocess.run(['psql','-h',host,'-p',port,'-U',user,'-d',dbname,'-c',q],env=my_env,capture_output=True,text=True)
print(r.stdout)
print(r.stderr[:500])
