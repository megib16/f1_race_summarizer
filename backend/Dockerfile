FROM python:3.11-slim

WORKDIR /app/backend
ENV APP_ENV=production

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

RUN groupadd --system app && useradd --system --gid app app \
    && mkdir -p /app/cache /app/data && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
