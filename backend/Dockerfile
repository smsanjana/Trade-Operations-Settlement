FROM python:3.12-slim

WORKDIR /app

RUN groupadd -r appgroup && useradd -r -g appgroup -u 10001 appuser

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

USER appuser

EXPOSE 8000
CMD ["uvicorn", "trade_operations_settlement.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
