FROM debian:testing
MAINTAINER {{ cookiecutter.email }}

RUN apt-get update -qq && apt-get install -y git python3 python3-setuptools python3-pip
RUN pip3 install qi-irida-uploader

WORKDIR /data
