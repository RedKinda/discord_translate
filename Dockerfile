FROM python:3.11 AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1

WORKDIR /src

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_NO_CACHE_DIR=1

RUN apt update
RUN apt install git -y
RUN apt-get install --yes --no-install-recommends gcc g++ libffi-dev && \
    apt-get install --yes tesseract-ocr

RUN pip install -U poetry
RUN pip install wheel
RUN poetry config virtualenvs.create false

WORKDIR /app
COPY poetry.lock pyproject.toml /app/
RUN poetry install
COPY . /app/

CMD ["python", "-m", "discord_translate.main"]
