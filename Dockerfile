FROM python:3.11

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-tk

WORKDIR /app

RUN pip install requests
RUN mkdir -p /app/valid_files /app/error_logs

COPY . .

CMD ["python", "Testfile10.py"]
# TEST
