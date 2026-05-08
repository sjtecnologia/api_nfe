#!/usr/bin/env python3
"""
Update DANFE for NFe 1155 via API route
"""
import subprocess
import json

# Query database via API route
cmd = '''
curl -s http://localhost:8080/api/nfe/262/generate-danfe
'''

result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

print("Status response:")
print(result.stdout)

if result.stderr:
    print("Errors:")
    print(result.stderr)
