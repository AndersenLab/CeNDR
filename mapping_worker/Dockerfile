FROM continuumio/miniconda3
RUN conda config --add channels defaults && \
    conda config --add channels bioconda && \
    conda config --add channels conda-forge && \
    conda config --add channels danielecook
COPY env.yml .
RUN conda env create --file env.yml && conda clean -a
ENV PATH /opt/conda/envs/worker/bin:$PATH
RUN conda env export --name worker > worker.yml

RUN pip install gcloud

COPY genes.db .
COPY pipeline.R .
COPY run.py .
COPY app.py .

ENV PORT=8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 1 app:app
