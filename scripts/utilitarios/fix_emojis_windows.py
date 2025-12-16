#!/usr/bin/env python3
"""Remove TODOS os emojis recursivamente"""
import os, re
REPLACEMENTS = {'[OK]':'[OK]','[X]':'[X]','[!]':'[!]','[IN]':'[IN]','[OUT]':'[OUT]','[DATA]':'[DATA]','[LIST]':'[LIST]','[LOG]':'[LOG]','[USER]':'[USER]','[ADMIN]':'[ADMIN]','[SEARCH]':'[SEARCH]','[CLIENT]':'[CLIENT]','[SAVE]':'[SAVE]','-->':'-->','[START]':'[START]','[AUTH]':'[AUTH]','[KEY]':'[KEY]','[UNLOCK]':'[UNLOCK]','[BUILD]':'[BUILD]','[ERROR]':'[ERROR]','[RED]':'[RED]','[TRACE]':'[TRACE]'}
def clean(t):
 for e,r in REPLACEMENTS.items(): t=t.replace(e,r)
 return re.sub(r'[\U0001F000-\U0001FFFF]','[?]',t)
for r,ds,fs in os.walk('.'):
 ds[:]=[d for d in ds if d not in ['venv','.git','__pycache__']]
 for f in [f for f in fs if f.endswith('.py')]:
  p=os.path.join(r,f)
  try:
   with open(p,'r',encoding='utf-8') as file: c=file.read()
   n=clean(c)
   if n!=c:
    with open(p,'w',encoding='utf-8') as file: file.write(n)
    print(f'[OK] {p}')
  except: pass
print('[DONE]')
