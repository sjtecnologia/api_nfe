#!/bin/bash
export PGPASSWORD='***SENHA_RDS_ROTACIONADA***'
psql -U nfeuser -h localhost -d sjtnfe -f /tmp/fix_regimes_tributarios.sql
