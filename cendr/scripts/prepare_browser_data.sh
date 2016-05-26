
build=20160408

# Prepare tajima D data
tb tajima 100000 10000 ${andersen_vcf} > WI_${build}.tajima.tsv

# SEtup gene file
wget ftp://ftp.wormbase.org/pub/wormbase/releases/WS253/MULTI_SPECIES/hub/elegans/elegans_genes_WS245.bb
BigBedToBed elegans_genes_WS245.bb elegans_transcripts_WS245.bed

# brew install igvtools
igvtools index elegans_transcripts_WS245.bed

# get gff
gff=~/Dropbox/Andersenlab/Reagents/WormReagents/Variation/N2_GFF_WS245/c_elegans.WS245.annotations.gff3

# Gene Track
sortBed -i ${gff} | gff2bed gff - | grep 'locus'  |\
gawk '{ match($0, "locus=([^;\t]+)", f); print $1 "\t" $2 "\t" $3 "\t" f[1] "\t" 100 "\t" $6 "\t" $2 "\t" $3  "\t0\t1\t" $3 - $2 - 1 "\t0"  }' > elegans_gene.WS245.bed
# Don't index to improve searching.

# Generate HIGH MED LOW tracks

# LOW
for i in LOW MODERATE HIGH; do
	bcftools view --apply-filters PASS ${andersen_vcf} | grep ${i} | awk '$0 !~ "^#" { print $1 "\t" ($2 - 1) "\t" ($2)  "\t" $1 ":" $2 "\t0\t+"  "\t" $2 - 1 "\t" $2 "\t0\t1\t1\t0" }'  > ${build}.${i}.bed && sleep 3 && igvtools index ${build}.${i}.bed &
done;

# Finish this part later.
gsutil cp gs://andersen_dist/vcf/all/${build}/browser/