FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN mkdir -p /app/data /app/backups && useradd -r -u 10001 ragham && chown -R ragham:ragham /app
USER ragham
ENV RAGHAM_HOST=0.0.0.0 RAGHAM_PORT=8080 RAGHAM_DATA_DIR=/app/data
EXPOSE 8080
VOLUME ["/app/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3).read()"
CMD ["python", "server.py"]
