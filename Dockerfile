FROM gcr.io/google-appengine/python

RUN apt-get update && apt-get install -y --no-install-recommends \
build-essential \
ca-certificates \
curl \
git \
libncursesw5-dev \
libncurses5-dev \
make \
zlib1g-dev \
libbz2-dev \
liblzma-dev \
fuse \
&& rm -rf /var/lib/apt/lists/*

ENV BCFTOOLS_BIN="bcftools-1.4.tar.bz2" \
BCFTOOLS_PLUGINS="/usr/local/libexec/bcftools" \
BCFTOOLS_VERSION="1.4"

# Install BCFTools
RUN curl -fsSL https://github.com/samtools/bcftools/releases/download/$BCFTOOLS_VERSION/$BCFTOOLS_BIN -o /opt/$BCFTOOLS_BIN \
&& tar xvjf /opt/$BCFTOOLS_BIN -C /opt/ \
&& cd /opt/bcftools-$BCFTOOLS_VERSION \
&& make \
&& make install 

# Create a virtualenv for dependencies. This isolates these packages from
# system-level packages.
RUN virtualenv /env

# Setting these environment variables are the same as running
# source /env/bin/activate.
ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH

# Copy the application's requirements.txt and run pip to install all
# dependencies into the virtualenv.
ADD requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# Add the application source code.
ADD . /app

# Setup MySQL Socket
RUN wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 && mv cloud_sql_proxy.linux.amd64 cloud_sql_proxy && chmod +x cloud_sql_proxy
RUN sudo mkdir /cloudsql; sudo chmod 777 /cloudsql
RUN ./cloud_sql_proxy -dir=/cloudsql -instances=andersen-lab:us-central1:cendr-db=tcp:3306  -credential_file client-secret.json &

# Run a WSGI server to serve the application. gunicorn must be declared as
# a dependency in requirements.txt.
CMD gunicorn -b :$PORT main:app
