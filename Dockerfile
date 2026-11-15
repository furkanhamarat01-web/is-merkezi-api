FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

ENV POSTGRES_HOST=185.184.210.52
ENV POSTGRES_PORT=5433
ENV POSTGRES_DB=stage_vkvdb
ENV POSTGRES_USER=postgres
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
