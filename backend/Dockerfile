FROM python:3.12.10-slim AS lock

RUN pip install --no-cache-dir poetry==2.3.2 poetry-plugin-export==1.10.1
COPY pyproject.toml poetry.lock ./
RUN poetry export --only main -o /requirements.txt


FROM python:3.12.10-slim

WORKDIR /app

COPY --from=lock /requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD uvicorn lender_match.api:app --host 0.0.0.0 --port ${PORT:-8000}
