FROM python:3.14-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential tree curl git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/laike9m/Python-Type-Challenges && \
    cd Python-Type-Challenges &&  \
    pip3 install -r requirements.txt && \
    pip3 install poetry==2.4.1 gunicorn

WORKDIR /Python-Type-Challenges

RUN sed -i '/^venvPath = /d; /^venv = /d' pyproject.toml

RUN python -m pip install "pyright[nodejs]" && pyright --version

CMD ["gunicorn", "-b 0.0.0.0:8001", "app:app"]
