
# Loading VCFs

New VCFs should be loaded with:


### Loading Tajima Data

```
tb tajima 100000 10000 ${andersen_vcf} > WI_${build}.tajima.tsv
```




### Loading VCF Data

#### Generating a tsv

```
	tb vcftb mysql --simple --print --ANN ${andersen_vcf}
```

The transcript biotypes that Snpeff uses are not very thorough. They only classify genes as being `protein coding` or `noncoding. The transcript biotypes provided by wormbase are much better and include many classes of RNAs. To update the biotypes in a loaded VCF Use the following SQL Command.

```
UPDATE 
	WI_20160408
INNER JOIN
	wb_gene
	ON
		WI_20160408.gene_id = wb_gene.Name
	SET
WI_20160408.transcript_biotype = wb_gene.biotype;
```

SNPeff assigns gene names as gene ids rather than locus names. So the following addresses that also.

```
UPDATE
	WI_20160408
INNER JOIN
	wb_gene
	ON
		WI_20160408.gene_id = wb_gene.Name
	SET
WI_20160408.gene_name = wb_gene.locus
```