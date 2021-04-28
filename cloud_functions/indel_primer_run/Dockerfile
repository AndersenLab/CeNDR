FROM continuumio/miniconda3
RUN apt-get update && apt-get install -y procps && \
    apt-get clean
RUN conda config --add channels defaults && \
    conda config --add channels bioconda && \
    conda config --add channels conda-forge
RUN conda create -n vcf-kit \
			  conda-forge::go=1.13.15 \
              python=3.7 \
              pytest \
              pytest-cov \
              coveralls \
              logzero \
              curl \
              "biopython==1.77" \
              "matplotlib>=1.3.1" \
              "scipy>=0.13.3" \
              "numpy>=1.8.0" \
              "cython>=0.20.1" \
              "cyvcf2>=0.6.5" \
              "intervaltree>=2.1.0" \
              "networkx>=1.11" \
              "bwa>=0.7.12" \
              "samtools>=1.10" \
              "bcftools>=1.10" \
              "blast>=2.2.31" \
              "muscle>=3.8.31" \
              "primer3>=2.5.0"

ENV PATH /opt/conda/envs/vcf-kit/bin:$PATH

LABEL Name="vcf-kit" Author="Daniel Cook"

# Now install VCF-Kit 0.2.8
RUN git clone https://www.github.com/andersenlab/vcf-kit && \
    cd vcf-kit && \
    git checkout f433abb637fe59a370f8c654ef406cbabaa36e0a && \
    python setup.py install

RUN vk genome wormbase --ref=WS276

# Create and change to the app directory.
WORKDIR /app

# Copy local code to the container image.
COPY invoke.go ./

# Install google cloud storage
RUN CGO_ENABLED=0 GOOS=linux go get cloud.google.com/go/storage

# Build the binary.
# -mod=readonly ensures immutable go.mod and go.sum in container builds. .
RUN CGO_ENABLED=0 GOOS=linux go build -v -o server

# Run the web service on container startup.
CMD ["/app/server"]
