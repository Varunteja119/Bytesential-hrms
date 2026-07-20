FROM python:3.12-slim

WORKDIR /app

# System deps for psycopg2 (Postgres driver) and WeasyPrint (PDF gen, added in a later phase)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# In production, run migrations as a separate release step (see docker-compose.yml),
# not baked into the image start command — keeps "deploy code" and "migrate schema"
# as two auditable actions instead of one implicit one.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
