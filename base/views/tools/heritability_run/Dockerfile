# docker build --file alignment.Dockerfile -t swantonlab/alignment .
FROM continuumio/miniconda3
RUN apt-get update && apt-get install -y procps && \
    apt-get clean
RUN conda config --add channels defaults && \
    conda config --add channels bioconda && \
    conda config --add channels conda-forge
RUN conda create -n heritability \
				 conda-forge::go=1.13.15 \
				 r=3.6.0 \
				 r-lme4 \
				 r-dplyr \
				 r-boot \
				 r-data.table \
				 r-futile.logger \
				 && conda clean -a
ENV PATH /opt/conda/envs/heritability/bin:$PATH
LABEL Name="heritability" Author="Daniel Cook"

# Create and change to the app directory.
WORKDIR /app

# Copy local code to the container image.
COPY invoke.go ./

# Install google cloud storage
RUN CGO_ENABLED=0 GOOS=linux go get cloud.google.com/go/storage

# Build the binary.
# -mod=readonly ensures immutable go.mod and go.sum in container builds.
RUN CGO_ENABLED=0 GOOS=linux go build -v -o server

COPY ./H2_script.R ./

# Run the web service on container startup.
CMD ["/app/server"]