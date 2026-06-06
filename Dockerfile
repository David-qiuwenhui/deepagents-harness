FROM python:3.11-slim

WORKDIR /app

# Copy everything needed
COPY pyproject.toml ./
COPY src/ ./src/

# Debug: show what we have
RUN echo "=== Files in /app ===" && ls -la /app/ && echo "=== Files in /app/src ===" && ls -la /app/src/ && echo "=== pyproject.toml ===" && cat /app/pyproject.toml

# Install dependencies first, then the package itself
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir .

# Verify the package is installed
RUN python -c "import agent; print('agent package imported successfully')"

EXPOSE 7860

CMD ["uvicorn", "agent.server:app", "--host", "0.0.0.0", "--port", "7860"]
