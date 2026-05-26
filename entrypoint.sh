#!/bin/sh

[ -f /.env ] && export $(cat /.env | xargs)

exec "$@"
