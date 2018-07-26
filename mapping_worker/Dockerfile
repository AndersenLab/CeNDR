FROM andersenlab/wi-nf

RUN brew unlink python && brew install python
RUN pip3 install gcloud arrow logzero pandas numpy
RUN pip3 install cython
RUN pip3 install cyvcf2 logzero sqlalchemy

# Install custom memoization function (temporary)
RUN Rscript -e 'install.packages(c("memoise", "aws.s3", "genetics"))'
RUN Rscript -e 'devtools::install_github("Andersenlab/cegwas") #3'
RUN Rscript -e 'install.packages(c("RSQLite"))'

ADD . ${HOME}
RUN pip3 install requests
RUN pip3 install ipython

RUN Rscript -e 'devtools::install_github("DavisVaughan/furrr")'

CMD python3 run.py
