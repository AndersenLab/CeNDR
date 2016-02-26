for i in `bcftools query -l $andersen_vcf`; do
    echo ${i}
    bcftools query --print-header --samples ${i} -f '%CHROM\t%POS\t%FILTER\t[%FT\t%GT\t%TGT\t%ANN]\n' ${andersen_vcf}
done;
