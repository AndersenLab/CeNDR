#!/bin/bash
# Author: Daniel E. Cook
# This script generates the transcript and gene track for the browser.

# Set directory to base.
cd "$(git rev-parse --show-toplevel)/.download"

function zip_index {
    bgzip -f ${1}
    tabix ${1}.gz
}
# Generate the transcripts track;
# Confusingly, this track is derived from 
# one called elegans_genes on wormbase.
# Add parenthetical gene name for transcripts.
mkdir -p browser
curl ftp://ftp.wormbase.org/pub/wormbase/releases/WS253/MULTI_SPECIES/hub/elegans/elegans_genes_WS253.bb > elegans_genes_WS253.bb
BigBedToBed elegans_genes_WS253.bb tmp.bed
sortBed -i tmp.bed > browser/elegans_transcripts_WS253.bed
bgzip -f browser/elegans_transcripts_WS253.bed
tabix browser/elegans_transcripts_WS253.bed.gz
rm tmp.bed

# Generate Gene Track BED File
tmp_gff=$(mktemp)
tmp_gff2=$(mktemp)
tmp_bed3=$(mktemp)
gzip -dc c_elegans.PRJNA13758.WS276.annotations.gff3.gz | \
grep 'locus' | \
awk '$2 == "WormBase" && $3 == "gene"' > "${tmp_gff}"
sortBed -i "${tmp_gff}" > "${tmp_gff2}"
# Install with conda install gawk
convert2bed -i gff < "${tmp_gff2}" > ${tmp_bed3}
gawk -v OFS='\t' '{ match($0, "locus=([^;\t]+)", f); $4=f[1]; print $1, $2, $3, $4, 100, $6  }' "${tmp_bed3}" | \
uniq > browser/elegans_gene.WS276.bed
zip_index browser/elegans_gene.WS276.bed

# Copy tracks to browser
gsutil cp browser/* gs://elegansvariation.org/browser_tracks

