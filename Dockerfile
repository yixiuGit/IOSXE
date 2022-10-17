FROM python:3.10-slim-buster
ENV PYTHONUNBUFFERED=1
RUN mkdir /iosxe
WORKDIR /iosxe
COPY requirements.txt /iosxe/
RUN pip install -r requirements.txt
COPY . /iosxe/
#if image already being built, this copy does not work
#one way is to delete existing image and re-create