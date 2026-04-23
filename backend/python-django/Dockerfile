FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN pip wheel -r requirements.txt

# stage 2 

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app /app/

RUN pip install --no-index --no-cache-dir --find-links=/app -r requirements.txt && rm -rf /app/*.whl

COPY . .

EXPOSE 8001

CMD [ "gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8001" ]
