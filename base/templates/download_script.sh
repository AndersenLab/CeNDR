#!/usr/bin/bash

# Files will be named appropriately upon download.
#
# Use the following line to run this script:
# curl  http://www.elegansvariation.org{{ request.path }} | bash
#

{% for isotype, strains in strain_listing|groupby('isotype') -%}
wget https://elegansvariation.org.s3.amazonaws.com/bam/{{ strains[0].isotype }}.bam
wget https://elegansvariation.org.s3.amazonaws.com/bam/{{ strains[0].isotype }}.bam.bai
{% endfor -%}