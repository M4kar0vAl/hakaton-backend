FROM public.ecr.aws/docker/library/python:3.11.9-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PATH="/app/.venv/bin:$PATH"


RUN addgroup --gid 1000 app &&\
    adduser --home /app --uid 1000 --gid 1000 app

WORKDIR /app

RUN apt-get update -y && \
    apt-get install -y gcc \
    musl-dev \
    libpq-dev

RUN python3 -m pip install --no-cache-dir --no-warn-script-location --upgrade pip &&\
    python3 -m pip install --no-cache-dir --no-warn-script-location poetry

COPY poetry.lock pyproject.toml ./

RUN python3 -m poetry config virtualenvs.in-project true &&\
    python3 -m poetry install --no-cache --no-root -n --without dev

COPY . .

RUN chown -R app:app /app

USER app

EXPOSE 8000

ENTRYPOINT [ "python3" ]
CMD [ "-m", "gunicorn", "-b", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-",  "core.config.asgi", "--reload", "-k", "uvicorn.workers.UvicornWorker", "--timeout", "90" ]