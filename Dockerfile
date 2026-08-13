FROM node:22-alpine AS qr-assets

RUN npm install --prefix /vendor --omit=dev --no-audit --no-fund qr-scanner@1.4.2


FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/media /app/staticfiles /app/static/vendor/qr-scanner
COPY --from=qr-assets /vendor/node_modules/qr-scanner/qr-scanner.umd.min.js /app/static/vendor/qr-scanner/qr-scanner.umd.min.js
COPY --from=qr-assets /vendor/node_modules/qr-scanner/qr-scanner.umd.min.js.map /app/static/vendor/qr-scanner/qr-scanner.umd.min.js.map
COPY --from=qr-assets /vendor/node_modules/qr-scanner/qr-scanner-worker.min.js /app/static/vendor/qr-scanner/qr-scanner-worker.min.js
COPY --from=qr-assets /vendor/node_modules/qr-scanner/LICENSE /app/static/vendor/qr-scanner/LICENSE

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py ensure_default_admin && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1"]
