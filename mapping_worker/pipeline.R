#!/usr/env/R
library(devtools)
library(memoise)
library(cegwas)
library(tidyverse)
library(jsonlite)
library(aws.s3)
library(future)

# In batch R process ----
dump_and_quit <- function() {
  # Save debugging info to file last.dump.rda
  traceback()
  dump.frames(to.file = FALSE)
  # Quit R with error status
  q(status = 1)
}
options(error = dump_and_quit)


# Output session info
session <- devtools::session_info()
session

# Get variables
REPORT_NAME <- Sys.getenv('REPORT_NAME')
TRAIT_NAME <- Sys.getenv('TRAIT_NAME')
GOOGLE_APPLICATION_CREDENTIALS <- Sys.getenv('GOOGLE_APPLICATION_CREDENTIALS')

# Define Constants
source("constants.R")

df <- readr::read_tsv("df.tsv") %>%
      dplyr::select(1,3)

readr::read_tsv("df.tsv") %>% readr::write_tsv("data/phenotype_data.tsv.gz")

# Make trait name just 'TRAIT'
names(df) <- c("STRAIN", 'TRAIT')

# Perform the mapping
if(!file.exists("data/mapping.Rdata")) {
  mapping <- cegwas::cegwas_map(df, mapping_snp_set = FALSE)
  save(mapping, file='mapping.Rdata')
  save(mapping, file='data/mapping.Rdata')
} else {
  load("data/mapping.Rdata")
}

mapping %>%
    dplyr::ungroup() %>%
    dplyr::mutate(trait = TRAIT_NAME) %>%
    dplyr::mutate(marker = gsub("_", ":", marker)) %>%
readr::write_tsv(.,
                 "data/mapping.tsv.gz", na = "")

is_significant = any(mapping$aboveBF == 1)

#
# Manhattan plot
#

# Filter MtDNA for plotting purposes
cegwas::manplot(mapping %>% dplyr::filter(CHROM != "MtDNA"), bf_line_color='red')[[1]] +
  theme_bw() +
  PUB_THEME +
  theme(plot.margin = unit(c(0.0,0.5,0.5,0),"cm"),
        panel.spacing = unit(0.8, "lines"),
        strip.background = element_blank(),
        axis.title.x = ggplot2::element_text(margin=margin(15,0,0,0), size=18, color="black"),
        axis.title.y = ggplot2::element_text(margin=margin(0,15,0,5), size=18, color="black"),
        panel.background = ggplot2::element_rect(color = "black", size= 0.50),
        axis.ticks= element_line(color = "black", size = 0.25),
        panel.border = element_rect(size=1, color = "black")) +
  ggplot2::labs(x = "Genomic Position (Mb)",
                y = expression(-log[10](p)),
                title = "")

ggsave("data/Manhattan.png", width = 10, height = 5, dpi=175)

if (!is_significant) {
    quit(save = "no", status = 0)
}

#===============#
# Process Peaks #
#===============#

# Remove MtDNA
mapping <- mapping %>% dplyr::filter(CHROM != "MtDNA") %>%
                       dplyr::mutate(marker = gsub("_", ":", marker)) %>%
                       dplyr::mutate(trait = TRAIT_NAME)

CHROM_INT = list("I"=1,
                 "II"=2,
                 "III"=3,
                 "IV"=4,
                 "V"=5,
                 "X"=6,
                 "MtDNA"=7)

peaks <- na.omit(mapping) %>%
    dplyr::distinct(peak_id, .keep_all = TRUE) %>%
    dplyr::select(marker, CHROM, POS, startPOS, endPOS, log10p, trait, var.exp) %>%
    dplyr::mutate(query = paste0(CHROM, ":",startPOS, "-",endPOS)) %>%
    dplyr::mutate(interval_length=endPOS - startPOS) %>%
    dplyr::arrange(desc(log10p)) %>%
    dplyr::mutate(top3peaks = seq(1:n())) %>%
    dplyr::filter(top3peaks < 4) %>%
    dplyr::select(trait,
                  peak_pos = marker,
                  interval = query,
                  peak_log10p = log10p,
                  variance_explained = var.exp,
                  interval_length) %>%
    tidyr::separate(peak_pos,
                    sep=":",
                    into=c("CHROM", "POS"),
                    remove=FALSE) %>%
    dplyr::rowwise() %>%
    dplyr::mutate(CHROM_INT=CHROM_INT[CHROM][[1]]) %>%
    dplyr::arrange(CHROM_INT, POS) %>%
    dplyr::select(-CHROM_INT)

n_peaks <- nrow(peaks)

readr::write_tsv(peaks, "data/peak_summary.tsv.gz")

# Generate phenotype/genotype data for PxG Boxplots.
query_vcf(peaks$peak_pos, impact="ALL", format=c("TGT", "GT", "FT")) %>%
  dplyr::mutate(TRAIT = TRAIT_NAME) %>%
  dplyr::rowwise() %>%
  dplyr::filter(genotype %in% c(0, 2)) %>%
  dplyr::mutate(GT=genotype, TGT = glue::glue("{a1}{a2}")) %>%
  dplyr::mutate(MARKER = glue::glue("{CHROM}:{POS}")) %>%
  dplyr::select(MARKER, CHROM, POS, ISOTYPE=SAMPLE, STRAIN=SAMPLE, REF, ALT, GT, TGT, FT, FILTER) %>%
  dplyr::mutate(GT = glue::glue("{GT} ({TGT})")) %>%
  dplyr::inner_join(df) %>%
  dplyr::distinct() %>% readr::write_tsv("data/peak_markers.tsv.gz")

#============================#
# Generate data for PxG Plot #
#============================#

# Save mapping Intervals
mapping_intervals <- mapping %>%
            dplyr::mutate(report = REPORT_NAME, BF = BF) %>%
            dplyr::group_by(peak_id) %>%
            dplyr::filter(!is.na(peak_id), log10p == max(log10p)) %>%
            dplyr::select(marker, CHROM, POS, report, trait, var.exp, log10p, BF, startPOS, endPOS) %>%
            dplyr::distinct(.keep_all = T)

readr::write_tsv(mapping_intervals, "data/mapping_intervals.tsv.gz")

# Fetch peak marker genotypes for generation of box plots
peak_markers <- query_vcf(peaks$peak_pos, impact="ALL", format=c("TGT", "GT", "FT")) %>%
                dplyr::mutate(TRAIT = TRAIT_NAME) %>%
                # Filter out hets
                dplyr::rowwise() %>%
                dplyr::filter(genotype %in% c(0, 2)) %>%
                dplyr::mutate(GT=genotype, TGT = glue::glue("{a1}{a2}")) %>%
                dplyr::mutate(MARKER = glue::glue("{CHROM}:{POS}")) %>%
                dplyr::select(MARKER, CHROM, POS, ISOTYPE=SAMPLE, STRAIN=SAMPLE, REF, ALT, GT, TGT, FT, FILTER) %>%
                dplyr::mutate(GT = glue::glue("{GT} ({TGT})")) %>%
                dplyr::inner_join(df) %>%
                dplyr::distinct()

readr::write_tsv(peak_markers, "data/peak_markers.tsv.gz")

#============================#
# Generate data for PxG Plot #
#============================#
if (n_peaks > 1) {
    plot_peak_ld(mapping)
    ggsave("data/LD.png", width = 14, height = 11)
}

split_interval <- function(startPOS, endPOS, size=25000) {
    last_interval <- rev(seq(from = startPOS, to = endPOS, by = size))[1]
    intervals <- lapply(seq(from = startPOS, to = endPOS, by = size), function(x) {
        end = x + size
        if (end >= endPOS) {
            end = endPOS
        }
        if (x != end) {
            glue::glue("{x}:{end}")
        }
    })
    paste(unlist(intervals), collapse=",")
}

# Partition variant correlation
mapping_chunked <- mapping %>%
    dplyr::filter(aboveBF>0) %>%
    dplyr::distinct() %>%
    dplyr::filter(complete.cases(.)) %>%
    dplyr::ungroup() %>%
    dplyr::rowwise() %>%
    dplyr::mutate(interval_set = strsplit(split_interval(startPOS, endPOS), ",")) %>%
    tidyr::unnest(interval_set) %>%
    dplyr::rename(intervalStart=startPOS, intervalEnd=endPOS) %>%
    tidyr::separate(interval_set, into=c("startPOS", "endPOS"), convert=TRUE) %>%
    dplyr::mutate(split_interval=glue::glue("{CHROM}:{startPOS}-{endPOS}"))

plan(multiprocess)
print(availableCores())
# Get interval correlations
interval_variants <- data.frame()
print("Performing variant correlation")
if (!file.exists('data/interval.Rdata')) {
        tryCatch({
        vc <- sapply(split(mapping_chunked, mapping_chunked$split_interval), function(x) {
            future({variant_correlation(x,
                                condition_trait = F,
                                variant_severity = c("MODERATE", "SEVERE"),
                                gene_types = "ALL")})
        })

        vc <- dplyr::bind_rows(sapply(vc, value)) %>%
              dplyr::left_join(mapping_chunked) %>%
              dplyr::select(-startPOS, -endPOS) %>%
              dplyr::rename(startPOS=intervalStart, endPOS=intervalEnd)

        interval_variants <- vc %>% dplyr::distinct(CHROM,
                                             POS,
                                             REF,
                                             ALT,
                                             gene_id,
                                             trait,
                                             effect,
                                             impact,
                                             nt_change,
                                             aa_change, .keep_all = TRUE) %>%
                             dplyr::mutate(peak = glue::glue("{CHROM}:{startPOS}-{endPOS}")) %>%
                             dplyr::group_by(peak, gene_id) %>%
                             dplyr::mutate(n_variants = n()) %>%
                             dplyr::mutate(max_gene_corr_p = max(-log10(corrected_spearman_cor_p)),
                                           corrected_spearman_cor_p = -log10(corrected_spearman_cor_p)) %>%
                             dplyr::arrange(dplyr::desc(max_gene_corr_p),
                                            gene_id) %>%
                             dplyr::mutate(n = dplyr::row_number(gene_id)) %>%
                             dplyr::select(-n,
                                           -strain,
                                           -GT,
                                           -FILTER,
                                           -FT,
                                           -pheno_value,
                                           -corrected_pheno,
                                           -startPOS,
                                           -endPOS)
        }, error = function(e) {
                print(e)
                traceback()
                stop("VC Error")
            })
        # For user
    save(interval_variants, file='data/interval.Rdata')
} else {
    load('data/interval.Rdata')
}

# Don't write huge interval variant file anymore.
# Condense Interval Variants File
interval_variants %>%
    readr::write_tsv("data/interval_variants.tsv.gz")

quit(save="no", status=0)

