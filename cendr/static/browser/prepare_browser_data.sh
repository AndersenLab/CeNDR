
build=20160408

# Prepare tajima D data
tb tajima 100000 10000 ${andersen_vcf} > WI_${build}.tajima.tsv

# SEtup gene file
wget ftp://ftp.wormbase.org/pub/wormbase/releases/WS253/MULTI_SPECIES/hub/elegans/elegans_genes_WS245.bb
BigBedToBed elegans_genes_WS245.bb elegans_transcripts_WS245.bed

# brew install igvtools
igvtools index elegans_transcripts_WS245.bed


# Gene Track
sortBed -i ../../c_elegans.WS245.gff | gff2bed ../../c_elegans.WS245.gff | grep 'locus'  |\
gawk '{ match($0, "locus=([^;\t]+)", f); print $1 "\t" $2 "\t" $3 "\t" f[1] "\t" 100 "\t" $6 "\t" $2 "\t" $3  "\t0\t1\t" $3 - $2 - 1 "\t0"  }' > elegans_gene.WS245.bed
igvtools index elegans_gene.WS245.bed


# Generate HIGH MED LOW tracks
bcftools view ${andersen_vcf} | awk '$0 !~ "^#" { print $1 "\t" ($2 - 1) "\t" ($2)  "\t" $1 ":" $2 "\t0\t+"  "\t" $2 - 1 "\t" $2 "\t0\t1\t1\t0" }' | head -n 500 > test.bed && igvtools index test.bed