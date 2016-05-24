
build=20160408

# Prepare tajima D data
tb tajima 100000 10000 ${andersen_vcf} > WI_${build}.tajima.tsv

#
wget ftp://ftp.wormbase.org/pub/wormbase/releases/WS253/MULTI_SPECIES/hub/elegans/elegans_genes_WS245.bb
BigBedToBed elegans_genes_WS245.bb elegans_genes_WS245.bed

# brew install igvtools
igvtools index elegans_genes_WS245.bed
