FROM andersenlab/wi-nf

RUN brew install python3 \
    && pip3 install gcloud arrow logzero pandas numpy

# Install custom memoization function (temporary)
RUN Rscript -e 'devtools::install_github("Andersenlab/cegwas")'
RUN Rscript -e 'install.packages(c("memoise", "aws.s3", "genetics"))'

RUN pip3 install cython
RUN pip3 install cyvcf2

ADD . ${HOME}

CMD python3 run.py