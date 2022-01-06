# syntax=docker/dockerfile:1
FROM python:3.8.12-slim-buster
ENV url=192.168.15.129
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
ENV TZ Asia/Singapore
CMD ["python3", "-u", "main.py ${env}"]