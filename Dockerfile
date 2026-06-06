FROM python:3.11-slim

WORKDIR /app

# Copy dependency files first for better Docker layer caching
COPY pyproject.toml ./

# Copy source code
COPY src/ ./src/

# Debug: verify files are present
RUN ls -la /app/ && ls -la /app/src/

# Install dependencies (non-editable for Docker)
RUN pip install --no-cache-dir .

EXPOSE 7860

CMD ["uvicorn", "agent.server:app", "--host", "0.0.0.0", "--port", "7860"]
