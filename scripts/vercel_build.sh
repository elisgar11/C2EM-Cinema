#!/usr/bin/env sh
set -eu

if [ -z "${SECRET_KEY:-}" ]; then
  echo "WARNING: SECRET_KEY not set — using dev fallback. Set SECRET_KEY in Vercel env for production."
fi

python manage.py migrate --noinput
python manage.py ensure_default_admin
