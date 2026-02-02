# INSTRUÇÕES PARA DIAGNÓSTICO DO E172

## Passo 1: Copiar arquivo de diagnóstico para o servidor

```bash
scp diagnostico_assinatura.py root@137.184.152.149:/root/api_nfe/
```

## Passo 2: No servidor, executar o diagnóstico

```bash
ssh root@137.184.152.149
cd /root/api_nfe
python3 diagnostico_assinatura.py > diagnostico_resultado.txt
cat diagnostico_resultado.txt
```

## Passo 3: Analisar o resultado

O script vai verificar:
1. ✅ Estrutura do XML (LoteRps, Signature)
2. ✅ Reference URI correto (#1)
3. ✅ Transforms (deve ter apenas canonicalization)
4. ✅ DigestMethod (deve ser SHA1)
5. ✅ **RECALCULAR DIGEST** - compara digest calculado vs assinatura
6. ✅ SignatureMethod (deve ser RSA-SHA1)
7. ✅ Certificado (validade, subject, issuer)
8. ✅ Resposta do GISS

## Passo 4: Verificar resultado

Se o script mostrar:
- **"DIGESTS DIFERENTES"** → O problema é a canonicalização
- **"DIGESTS CONFEREM"** → O problema é certificado ou CNPJ

## Passo 5 (se necessário): Atualizar código com logs

Se precisar de mais detalhes, copie também o nfse_service.py atualizado:

```bash
scp services/nfse_service.py root@137.184.152.149:/root/api_nfe/services/
ssh root@137.184.152.149
systemctl restart api_nfe
```

O código atualizado já tem logs que salvam:
- `/tmp/lote_rps_c14n.xml` - LoteRps canonicalizado
- DigestValue calculado manualmente nos logs
- DigestValue da assinatura nos logs

## Arquivos de debug no servidor

Após emissão, verifique:
- `/tmp/last_generated_nfse.xml` - XML antes de assinar
- `/tmp/last_signed_nfse.xml` - XML depois de assinar
- `/tmp/last_nfse_response.xml` - Resposta do GISS
- `/tmp/lote_rps_canonicalizado.xml` - LoteRps canonicalizado (após rodar diagnóstico)

## Comando rápido

Execute tudo de uma vez:
```bash
scp diagnostico_assinatura.py root@137.184.152.149:/root/api_nfe/ && \
ssh root@137.184.152.149 "cd /root/api_nfe && python3 diagnostico_assinatura.py"
```
