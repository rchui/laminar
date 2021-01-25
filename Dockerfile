FROM tiangolo/uvicorn-gunicorn-fastapi:python3.6

ENV PYTHONPATH ${PYTHONPATH}:/app
ENV PY_COLORS 1
ENV PIP_NO_CACHE_DIR off

#  setting env vars that will be used by gunicorn startup script
ENV WORKERS_PER_CORE 2

EXPOSE 8081

WORKDIR /app

COPY requirements.txt.lock ./
RUN pip install --upgrade pip && \
    pip install --requirement requirements.txt.lock

COPY . ./

CMD ["uvicorn", "laminar.api:app", "--host", "0.0.0.0", "--port", "8081"]
