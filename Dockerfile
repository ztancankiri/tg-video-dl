FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
COPY bot.py /app/

RUN pip install --no-cache-dir -r requirements.txt && mkdir -p downloads

ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]