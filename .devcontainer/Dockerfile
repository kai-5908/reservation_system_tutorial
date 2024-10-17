FROM python:3.11-bookworm

RUN apt update \
    && apt install default-mysql-client curl build-essential git -y \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt install -y nodejs

RUN curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.8.4 python3 -
ENV PATH /root/.local/bin:$PATH
RUN poetry config virtualenvs.create false

WORKDIR /workspace