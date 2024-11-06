# syntax=docker/dockerfile:1

FROM python:3.13-slim

ARG PIP_DISABLE_PIP_VERSION_CHECK=1
ARG PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt requirements.txt


RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "main.py"]
