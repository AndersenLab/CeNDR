#!/usr/env/R
library(devtools)
library(memoise)
library(cegwas)
library(tidyverse)
library(jsonlite)
library(aws.s3)

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

# Make trait name just 'TRAIT'
names(df) <- c("STRAIN", 'TRAIT')

# Cache the function to increase speed
gwas <- function(df,
                 session_packages=session$packages,
                 r_version=session$platform$version,
                 r_system=session$platform$system) {
  mapping <- cegwas::cegwas_map(df, mapping_snp_set = FALSE)
}


# Perform the mapping
if(!file.exists("mapping.Rdata")) {
  mapping <- gwas(df)
  save(mapping, file='mapping.Rdata')
} else {
  load("mapping.Rdata")
}

mapping %>% 
    dplyr::mutate(trait = TRAIT_NAME) %>%
    dplyr::mutate(marker = gsub("_", ":", marker)) %>%
readr::write_tsv(.,
                 "data/mapping.tsv.gz", na = "")

is_significant = any(mapping$aboveBF == 1)

#
# Manhattan plot
#

# Filter MtDNA for plotting purposes
cegwas::manplot(mapping %>% dplyr::filter(CHROM != "MtDNA"))[[1]] +
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
                  interval_length)

n_peaks <- nrow(peaks)

readr::write_tsv(peaks, "data/peak_summary.tsv.gz")

# Generate phenotype/genotype data for PxG Boxplots.
snpeff(peaks$peak_pos, severity="ALL", elements="ALL") %>%             
  dplyr::mutate(TRAIT = TRAIT_NAME) %>%
  dplyr::rowwise() %>%
  dplyr::mutate(TGT = .data[[.data$GT]]) %>%
  dplyr::mutate(MARKER = glue::glue("{CHROM}:{POS}")) %>%
  dplyr::select(MARKER, CHROM, POS, STRAIN=strain, REF, ALT, GT, TGT, FT, FILTER) %>%
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
peak_markers <- snpeff(peaks$peak_pos, severity="ALL", elements="ALL") %>%
                dplyr::mutate(TRAIT = TRAIT_NAME) %>%
                dplyr::rowwise() %>%
                dplyr::mutate(TGT = .data[[.data$GT]]) %>%
                dplyr::mutate(MARKER = glue::glue("{CHROM}:{POS}")) %>%
                dplyr::select(MARKER, CHROM, POS, STRAIN=strain, REF, ALT, GT, TGT, FT, FILTER) %>%
                dplyr::mutate(GT = glue::glue("{GT} ({TGT})")) %>%
                dplyr::inner_join(df) %>%
                dplyr::distinct()

readr::write_tsv(peak_markers, "data/peak_markers.tsv.gz")

#============================#
# Generate data for PxG Plot #
#============================#
if(nrow(peaks) > 1){
    plot_peak_ld(mapping)
    ggsave("data/LD.png", width = 14, height = 11)
}

# Get interval correlations
if (!file.exists('interval.Rdata')) {
interval_variants <- process_correlations(variant_correlation(mapping,
                                                              condition_trait = F))
  save(interval_variants, file='interval.Rdata')
} else {
  load('interval.Rdata')
}
# Don't write huge interval variant file anymore.
# Condense Interval Variants File
interval_variants %>%
    dplyr::select(CHROM, POS, gene_id, num_alt_allele, num_strains, spearman_cor_p, corrected_spearman_cor_p) %>%
    dplyr::mutate(num_alt_allele = as.integer(num_alt_allele)) %>%
    dplyr::distinct(.keep_all = T) %>%
    readr::write_tsv("data/interval_variants.tsv.gz")



