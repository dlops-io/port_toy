FROM python:3.14-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
CMD ["python", "-u", "processor.py"]
