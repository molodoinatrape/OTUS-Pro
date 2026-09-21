FROM python:3.14-slim
WORKDIR /app

RUN pip install --no-cache-dir poetry==2.4.3

ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root

COPY log_analyzer.py ./
COPY templates ./templates

ENTRYPOINT ["python", "/app/log_analyzer.py"]
CMD ["--help"]
