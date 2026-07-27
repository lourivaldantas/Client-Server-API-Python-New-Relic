FROM python:3.9.14-alpine3.16

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir newrelic

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY apps ./apps
COPY config ./config

ENV NEW_RELIC_CONFIG_FILE=/app/config/newrelic.ini

EXPOSE 8000 8001

ENTRYPOINT ["newrelic-admin", "run-program"]
CMD ["uvicorn", "apps.server.main:app", "--host", "0.0.0.0", "--port", "8000"]
