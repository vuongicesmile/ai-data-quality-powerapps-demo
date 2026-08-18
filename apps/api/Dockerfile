FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY apps/api ./apps/api
COPY packages/data-quality-core ./packages/data-quality-core
RUN pip install --no-cache-dir .
COPY sample-data ./sample-data

ENV PYTHONPATH=/app/apps/api/src:/app/packages/data-quality-core/src
CMD ["uvicorn", "ai_data_quality_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
