library(data.table)
library(seqinr)
library(Rsamtools)

try(setwd(dirname(rstudioapi::getActiveDocumentContext()$path)))
COLNAMES <- c("CHROM",
              "START",
              "END",
              "SUPPORT",
              "SVTYPE",
              "STRAND",	
              "SV_TYPE_CALLER",	
              "SV_POS_CALLER",	
              "STRAIN",	
              "CALLER",	
              "GT",	
              "SNPEFF_TYPE",	
              "SNPEFF_PRED",	
              "SNPEFF_EFF",	
              "SVTYPE_CLEAN",
              "TRANSCRIPT",
              "SIZE",
              "HIGH_EFF",
              "WBGeneID")
df <- data.table::fread("sv_data.bed", col.names = COLNAMES)

STRAIN_ORDER <- sort(unique(df$STRAIN))

# Subset columns to only those that are needed.
vcf <- df[, c("CHROM", "START", "END", "SVTYPE", "SIZE", "STRAIN", "GT")]
vcf <- unique(vcf)
vcf <- dcast(vcf, CHROM + START + END + SVTYPE + SIZE ~ STRAIN, value.var="GT")

# Get reference sequences for ranges
REFERENCE <- "/Users/dec/.genome/WS276/c_elegans.PRJNA13758.WS276.genome.fa.gz"
ref <- Rsamtools::scanFa(REFERENCE)
idx <- scanFaIndex(REFERENCE)
seq_lengths <- width(ranges(idx))
names(seq_lengths) <- seqnames(idx)
range_set <- IRanges(start = vcf$START, end = vcf$END)
ranges <- GRanges(seqnames = as.character(vcf$CHROM), ranges = range_set, seqlengths = seq_lengths)
ranges <- trim(ranges)
seqs <- scanFa(REFERENCE, ranges)

# Integrate sequences
vcf[, sequence := as.character(seqs)]

# Setup VCF columns
vcf[, POS := START + 1]
vcf[, ID := "."]

vcf[, REF := dplyr::case_when(SVTYPE == "INS" ~ sequence[1],
                              SVTYPE == "DEL" ~ sequence), by=1:nrow(vcf)]
# insert size is - 1 of size for ref.
vcf[, ALT := dplyr::case_when(SVTYPE == "DEL" ~ sequence[1],
                              SVTYPE == "INS" ~ paste0(rep("N", SIZE), collapse="")), by=1:nrow(vcf)]
vcf[, QUAL := 1]
vcf[, INFO := paste0("INDEL=1;", "END=", vcf$END, "TYPE=", SVTYPE)]
vcf[, FILTER := "PASS"]
vcf[, FORMAT := "GT"]

vcf[, SVTYPE := NULL]
vcf[, SIZE := NULL]
vcf[, START := NULL]
vcf[, END := NULL]


setcolorder(vcf, c("CHROM",
                   "POS",
                   "ID",
                   "REF",
                   "ALT",
                   "QUAL",
                   "FILTER",
                   "INFO",
                   "FORMAT",
                   STRAIN_ORDER))
setnames(vcf, "CHROM", "#CHROM")


# Fix Genotypes; Set NA to 0/0; Infer reference
vcf[, (STRAIN_ORDER) := lapply(.SD, function(x) ifelse(is.na(x), "0/0", x)), .SDcols=STRAIN_ORDER]


HEADER_LINES <- c("##fileformat=VCFv4.2",
                  '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
                  '##INFO=<ID=INDEL,Number=1,Type=Flag,Description="1 if indel">',
                  '##INFO=<ID=END,Number=1,Type=Integer,Description="end position">')

writeLines(HEADER_LINES, file("sv.vcf"))
data.table::fwrite(vcf, "sv.vcf", col.names=TRUE, append=TRUE, sep="\t")
err = system("bgzip -f sv.vcf && bcftools index sv.vcf.gz")
if (err != 0) {
  Error("Something went wrong!")
}
