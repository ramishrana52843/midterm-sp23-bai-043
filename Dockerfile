FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS trained
ARG GIT_COMMIT
COPY config.json train.py ./
COPY dataset/train.csv dataset/train.csv
RUN test -n "$GIT_COMMIT" && python train.py

FROM base AS runtime
COPY app.py smoke_test.py ./
COPY --from=trained /app/artifacts/ artifacts/
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
