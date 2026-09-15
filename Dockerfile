FROM alpine:3.24

RUN apk update && apk add --no-cache \
    libreoffice \
    fontconfig \
    ttf-dejavu \
    bash \
    python3 \
    py3-flask

WORKDIR /app

COPY app.py /app/app.py

CMD ["sh", "-c", "mkdir -p /data/input /data/output /data/processed && chmod -R 777 /data/input /data/output /data/processed && python3 -u /app/app.py"]
