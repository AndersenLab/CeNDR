FROM andersenlab/wi-nf

RUN brew install python3 \
    && pip3 install gcloud arrow logzero pandas numpy

# Install custom memoization function (temporary)
RUN Rscript -e 'install.packages("memoise", "aws.s3')'


ADD . ${HOME}

CMD python3 run.py