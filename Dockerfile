FROM partlab/ubuntu-postgresql		
MAINTAINER Andersonlab <joshuapr1@gmail.com>		
RUN apt-get update		
RUN apt-get install --fix-missing -y -q libpq-dev python-dev python-all python-pip
ADD ./cegwas_app/requirements.txt /tmp/requirements.txt		
RUN pip install Cython
RUN pip install -qr /tmp/requirements.txt		
ADD ./cegwas_app /opt/cegwas_app/		
WORKDIR /opt/cegwas_app		
EXPOSE 5000		
ENTRYPOINT ["python"]
CMD ["cegwas.py"]		