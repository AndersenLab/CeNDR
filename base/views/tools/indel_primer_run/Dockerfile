FROM andersenlab/vcf-kit

ENV PATH /opt/conda/envs/vcfkit/bin:$PATH
LABEL Name="vcf-kit" Author="Daniel Cook"

RUN vk genome wormbase --ref=WS276

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
