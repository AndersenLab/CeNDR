#!/usr/bin/bash

# Use the following line to run this script:
# curl  http://www.elegansvariation.org{{ request.path }} | bash
#
# Requirements:
#    wget is required for downloading files. 
#    We recommend using Homebrew (brew.sh) for Unix/Mac OS or Cygwin (cygwin.com) on windows.
#

{% for isotype, strains in strain_listing|groupby('isotype') -%}
{% if v2 %}
# {{ isotype }} strains
{% for strain in strains -%}
wget https://elegansvariation.org.s3.amazonaws.com/bam/strain/{{ strain }}.bam
wget https://elegansvariation.org.s3.amazonaws.com/bam/strain/{{ strain }}.bam.bai
{% endfor -%}

{%- else %}
wget https://elegansvariation.org.s3.amazonaws.com/bam/{{ strains[0].isotype }}.bam
wget https://elegansvariation.org.s3.amazonaws.com/bam/{{ strains[0].isotype }}.bam.bai
{% endif %}
{%- endfor -%}