FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HYPERFIT_RUNS=/data
WORKDIR /app
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt \
    && groupadd --gid 10001 hyperfit \
    && useradd --uid 10001 --gid hyperfit --no-create-home hyperfit \
    && mkdir /data && chown hyperfit:hyperfit /data
COPY hyperfit ./hyperfit
USER hyperfit
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/models', timeout=3)"
CMD ["python", "-m", "uvicorn", "hyperfit.api:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "1"]
