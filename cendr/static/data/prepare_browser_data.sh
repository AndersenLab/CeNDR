
build=20160408

# Prepare tajima D data
tb tajima 100000 10000 ${andersen_vcf} > WI_${build}.tajima.tsv

# Fetch track data
wget ftp://ftp.wormbase.org/pub/wormbase/releases/WS253/MULTI_SPECIES/hub/elegans/elegans.2bit
wget ftp://ftp.wormbase.org/pub/wormbase/releases/WS253/MULTI_SPECIES/hub/elegans/elegans_genes_WS245.bb

# Prepare variant data track - put into big bed format

bcftools view -H ${andersen_vcf} | cut -f 1,2 > variants.${build}.vcf