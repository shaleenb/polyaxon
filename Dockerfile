FROM python:3.7-bullseye

WORKDIR /code

COPY requirements.txt /code

RUN pip install --no-cache-dir -r /code/requirements.txt

# COPY keras /code/keras
COPY credentials.json /etc/secrets/credentials.json