#! /bin/bash
export PATH="/home/danielcook/.linuxbrew/bin:$PATH"
export MANPATH="/home/danielcook/.linuxbrew/share/man:$MANPATH"
export INFOPATH="/home/danielcook/.linuxbrew/share/info:$INFOPATH"
export PYENV_ROOT=/home/danielcook/.pyenv
if which pyenv > /dev/null; then eval "$(pyenv init -)"; fi
curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/models" -H "Metadata-Flavor: Google" > models.py
curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/run_pipeline" -H "Metadata-Flavor: Google" > run_pipeline.py
cat models.py run_pipeline.py | python
gcloud -q compute instances delete --zone=us-central1-a `hostname`