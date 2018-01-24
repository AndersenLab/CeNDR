#!/usr/env/R
library(devtools)
library(memoise)
library(cegwas)
library(tidyverse)
library(jsonlite)
library(rdatastore)

# Setup RDatastore
rdatastore::authenticate_datastore_service("gcloud_fargate.json", 'andersen-lab')
credentials <- rdatastore::lookup("credential", 'aws_fargate')

Sys.setenv("AWS_ACCESS_KEY_ID" = credentials$aws_access_key_id,
           "AWS_SECRET_ACCESS_KEY" = credentials$aws_secret_access_key)

# Output session info
session <- devtools::session_info()
session

# Get variables
REPORT_NAME <- Sys.getenv('REPORT_NAME')
TRAIT_NAME <- Sys.getenv('TRAIT_NAME')
GOOGLE_APPLICATION_CREDENTIALS <- Sys.getenv('GOOGLE_APPLICATION_CREDENTIALS')

# Define Constants
source("constants.R")

df <- readr::read_tsv("df.tsv")
# Make trait name just 'TRAIT'
names(df) <- c("STRAIN", 'TRAIT')

# Cache the function to increase speed
gwas <- function(df,
                 session_packages=session$packages,
                 r_version=session$platform$version,
                 r_system=session$platform$system) {
  mapping <- cegwas::cegwas_map(df, mapping_snp_set = FALSE)
}
mgwas <- memoise::memoise(gwas, cache=cache_s3("cendr-cache"))

# Perform the mapping
mapping <- mgwas(df)

readr::write_tsv(mapping, "data/mapping.tsv", na = "")

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

ggsave("data/Manhattan.png", width = 10, height = 5)

if (!is_significant) {
    quit(save = "no", status = 0)
}

#===============#
# Process Peaks #
#===============#

# Remove MtDNA
mapping <- mapping %>% dplyr::filter(CHROM != "MtDNA")
mapping <- mapping %>% dplyr::mutate(marker = gsub("_", ":", marker))

peaks <- na.omit(mapping) %>%
    dplyr::distinct(peak_id, .keep_all = TRUE) %>%
    dplyr::select(marker, CHROM, POS, startPOS, endPOS, log10p, trait, var.exp) %>%
    dplyr::mutate(marker = gsub("_", ":", marker)) %>%
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

# Generate a summary for each interval
interval_summary <- cegwas::interval_summary("II:12825015-15276626")

#============================#
# Generate data for PxG Plot #
#============================#

# Save mapping Intervals
mapping_intervals <- mapping %>% 
            dplyr::mutate(report = args$report_slug, BF = BF, version = 0.1, reference = "WS245") %>%
            dplyr::group_by(peak_id) %>%
            dplyr::filter(!is.na(peak_id), log10p == max(log10p)) %>%
            dplyr::select(marker, CHROM, POS, report, trait, var.exp, log10p, BF, startPOS, endPOS, version, reference) %>%
            dplyr::distinct(.keep_all = T)

readr::write_tsv(mapping_intervals, "data/mapping_intervals.tsv")

# Fetch peak marker genotypes for generation of box plots
peak_markers <- snpeff(peaks$peak_pos, severity="ALL", elements="ALL") %>%
                  
  peak_markers %>% dplyr::mutate(TRAIT = TRAIT_NAME) %>%
                  dplyr::rowwise() %>%
                  dplyr::mutate(TGT = .data[[.data$GT]]) %>%
                  dplyr::mutate(MARKER = glue::glue("{CHROM}:{POS}")) %>%
                  dplyr::select(MARKER, CHROM, POS, STRAIN=strain, REF, ALT, GT, TGT, FT, FILTER) %>%
                  dplyr::mutate(GT = glue::glue("{GT} ({TGT})")) %>%
                  dplyr::inner_join(df) %>%
                  dplyr::distinct()

readr::write_tsv(peak_markers, "data/peak_markers.tsv")

# PxG Plot
pg_plot <- cegwas::pxg_plot(mapping, color_strains = NA)[[1]] +
                   labs(y=TRAIT_NAME) +
                   PUB_THEME +
theme(plot.margin = unit(c(0.0,0.5,0.5,0),"cm"),
    strip.background = element_blank(),
    axis.title.y = element_text(vjust=2.5),
    panel.border = element_rect(size=1, color = "black"))  +
theme(legend.position = "none",
                  plot.title = ggplot2::element_blank())
ggsave("figures/PxG.png", width = 10, height = 5)
# Plot Peak LD if more than one peak.
if(nrow(peaks) > 1){
plot_peak_ld(proc_mappings)
ggsave("figures/LD.png", width = 14, height = 11)
}
# Get interval variants
update_status("Fine Mapping")
proc_variants <- function(proc_mappings) {
process_correlations(variant_correlation(proc_mappings, quantile_cutoff_high = 0.75, quantile_cutoff_low = 0.25, condition_trait = F))
}
mproc_variants <- memoise(proc_variants, cache = cache_datastore(project = "andersen-lab", cache = "rcache"))
interval_variants <- mproc_variants(proc_mappings)
# Don't write huge interval variant file anymore.
# readr::write_tsv(interval_variants, "tables/interval_variants.tsv")
# Condense Interval Variants File
interval_variants %>%
dplyr::select(CHROM, POS, gene_id, num_alt_allele, num_strains, corrected_spearman_cor) %>%
dplyr::mutate(num_alt_allele = as.integer(num_alt_allele)) %>%
dplyr::distinct(.keep_all = T) %>%
readr::write_tsv("tables/interval_variants_db.tsv")



