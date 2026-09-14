FROM python:3.14-slim
# No curl here on purpose: the processor only answers requests, it never makes
# one. Only the gateway image gets curl, because that's where you run the
# "reach the processor by name" experiments from.
WORKDIR /app
COPY . .
CMD ["python", "-u", "processor.py"]
