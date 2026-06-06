FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir -e .

EXPOSE 7860

CMD ["uvicorn", "agent.server:app", "--host", "0.0.0.0", "--port", "7860"]
