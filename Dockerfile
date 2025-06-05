FROM python:3.11

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-tk \
        libx11-6 \
        libxext-dev \
        libxrender-dev \
        libxinerama-dev \
        libxi-dev \
        libxrandr-dev \
        libxcursor-dev \
        libxtst-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install requests
RUN mkdir -p /app/valid_files /app/error_logs

ENV DISPLAY=192.168.1.7:0.0

COPY . .

CMD ["python", "Testfile10.py"]
