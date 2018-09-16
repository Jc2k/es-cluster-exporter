FROM alpine:3.8 AS builder

RUN apk --no-cache add python3-dev gcc
RUN python3 -m venv /app

COPY requirements.txt /requirements.txt
RUN /app/bin/pip install -r requirements.txt


FROM alpine:3.8

ENV PYTHONUNBUFFERED 1

COPY requirements.txt /requirements.txt
COPY --from=builder /app /app
COPY exporter.py /app/bin/es-cluster-exporter
COPY units.txt /app/share/units.txt

STOPSIGNAL SIGINT

CMD ["/app/bin/python", "/app/bin/es-cluster-exporter"]
