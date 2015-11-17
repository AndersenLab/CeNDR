FROM ubuntu:14.04
MAINTAINER Andersonlab <joshuapr1@gmail.com>
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y -q python-all python-pip 
ADD ./cegwas_app/requirements.txt /tmp/requirements.txt
RUN pip install -qr /tmp/requirements.txt
ADD ./cegwas_app /opt/cegwas_app/
WORKDIR /opt/cegwas_app
EXPOSE 5000
CMD ["python", "cegwas.py"]