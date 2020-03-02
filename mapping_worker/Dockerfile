FROM andersenlab/wi-nf

RUN brew unlink python
RUN HOMEBREW_NO_AUTO_UPDATE=1 brew install python3
RUN pip3 install gcloud arrow logzero pandas numpy
RUN pip3 install cython
RUN pip3 install cyvcf2 logzero sqlalchemy requests ipython

# Install custom memoization function (temporary)
RUN Rscript -e 'install.packages(c("memoise", "aws.s3", "genetics"))'
RUN Rscript -e 'devtools::install_github("Andersenlab/cegwas") #3'
RUN Rscript -e 'install.packages(c("RSQLite"))'
RUN Rscript -e 'install.packages(c("future"))'

ADD . ${HOME}

CMD python3 run.py
