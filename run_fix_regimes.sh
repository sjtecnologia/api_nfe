#!/bin/bash
export PGPASSWORD='gMGM!#)NW$nH1w(wrVIdcmn5'
psql -U nfeuser -h localhost -d sjtnfe -f /tmp/fix_regimes_tributarios.sql
