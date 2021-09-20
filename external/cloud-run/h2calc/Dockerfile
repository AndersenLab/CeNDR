# Use the offical golang image to create a binary.
# This is based on Debian and sets the GOPATH to /go.
# https://hub.docker.com/_/golang
FROM golang:1.16-buster as builder

# Create and change to the app directory.
WORKDIR /app

# Retrieve application dependencies.
# This allows the container build to reuse cached dependencies.
# Expecting to copy go.mod and if present go.sum.
COPY H2_script.R ./
COPY strain_data.tsv ./
COPY go.* ./
RUN go mod download

# Copy local code to the container image.
COPY . ./

# Build the binary.
RUN go build -v -o server


# build the deployed image
FROM continuumio/miniconda3

RUN apt-get update && apt-get install -y procps && \
    apt-get clean
RUN conda config --add channels defaults && \
    conda config --add channels bioconda && \
    conda config --add channels conda-forge
RUN conda create -n heritability \
    conda-forge::go=1.16.3 \
    r=3.6.0 \
    r-lme4 \
    r-dplyr \
    r-tidyr \
    r-glue \
    r-boot \
    r-data.table \
    r-futile.logger \
    && conda clean -a

LABEL Name="heritability" Author="Daniel Cook"
ENV PATH /opt/conda/envs/heritability/bin:$PATH
WORKDIR /app

# Copy local code to the container image.
COPY --from=builder /app/H2_script.R /app/H2_script.R
COPY --from=builder /app/strain_data.tsv /app/strain_data.tsv
COPY --from=builder /app/server /app/server

# Run the web service on container startup.
CMD ["/app/server"]
