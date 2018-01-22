FROM andersenlab/wi-nf

RUN brew install python3 \
    && pip3 install gcloud arrow logzero pandas numpy

ADD . ${HOME}

CMD python3 run.py