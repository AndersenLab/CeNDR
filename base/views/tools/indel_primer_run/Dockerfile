# docker build --file alignment.Dockerfile -t swantonlab/alignment .
FROM continuumio/miniconda3
RUN apt-get update && apt-get install -y procps && \
    apt-get clean
RUN conda config --add channels defaults && \
    conda config --add channels bioconda && \
    conda config --add channels conda-forge
RUN conda create -n vcfkit \
                 python=3.7 \
                 numpy \
                 scipy \
                 biopython \
                 bwa \
                 samtools \
                 bcftools \
                 vcftools \
                 blast \
                 primer3=2.5.0 \
				 && conda clean -a

ENV PATH /opt/conda/envs/vcfkit/bin:$PATH
LABEL Name="vcf-kit" Author="Daniel Cook"

# Now install VCF-Kit
RUN git clone https://www.github.com/andersenlab/vcf-kit && \
    cd vcf-kit && \
    git checkout --track origin/python3 && \
    python setup.py install

# Create and change to the app directory.
WORKDIR /app

# # Copy local code to the container image.
# COPY invoke.go ./

# # Install google cloud storage
# RUN CGO_ENABLED=0 GOOS=linux go get cloud.google.com/go/storage

# # Build the binary.
# # -mod=readonly ensures immutable go.mod and go.sum in container builds.
# RUN CGO_ENABLED=0 GOOS=linux go build -v -o server

# COPY ./H2_script.R ./
