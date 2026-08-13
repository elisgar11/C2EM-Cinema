#!/usr/bin/env sh
set -eu

if [ -z "${SECRET_KEY:-}" ]; then
  echo "ERROR: Set SECRET_KEY in Vercel → Settings → Environment Variables."
  exit 1
fi

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: Set DATABASE_URL by adding Vercel Postgres (Storage tab) or Neon."
  exit 1
fi

python manage.py migrate --noinput
python manage.py ensure_default_admin
