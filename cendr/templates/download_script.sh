#!/usr/bin/bash

# Files will be named appropriately upon download.
#
# Use the following line to run this script:
# curl  http://www.elegansvariation.org{{ request.path
}} | bash
#

{% for isotype, strains in strain_listing|groupby('isotype') -%}
{% if filetype == "bam" -%}
{% if strains[0].bam_file -%}
wget -O {{ strains[0].isotype + ".bam" }}         {{ strains[0].bam_file }}
wget -O {{ strains[0].isotype }}.bam.bai     {{ strains[0].bam_index }}
{% endif -%}
{% elif filetype == "cram" -%}
{% if strains[0].cram_file -%}
wget -O {{ strains[0].isotype }}.cram {{ strains[0].cram_file }}
wget -O {{ strains[0].isotype }}.crai {{ strains[0].cram_index }}
{% endif -%}
{% endif -%}
{% endfor -%}