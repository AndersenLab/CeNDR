FROM andersenlab/wi-nf

RUN brew unlink python && brew install python
RUN pip3 install gcloud arrow logzero pandas numpy
RUN pip3 install cython
RUN pip3 install cyvcf2 logzero sqlalchemy

# Install custom memoization function (temporary)
RUN Rscript -e 'install.packages(c("memoise", "aws.s3", "genetics"))'
RUN Rscript -e 'devtools::install_github("Andersenlab/cegwas") #2' 
RUN Rscript -e 'install.packages(c("RSQLite"))'
RUN Rscript -e 'devtools::install_github("aryoda/tryCatchLog")'
RUN Rscript -e 'install.packages("futile.logger")'

ADD . ${HOME}
RUN pip3 install requests

CMD python3 run.py