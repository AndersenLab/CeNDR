#!

library(devtools)
library(memoise)
library(cegwas)
library(tidyverse)
library(jsonlite)

# Output session info
devtools::session_info()

# Get variables
REPORT_NAME <- Sys.getenv('REPORT_NAME')
TRAIT_NAME <- Sys.getenv('TRAIT_NAME')
GOOGLE_APPLICATION_CREDENTIALS <- Sys.getenv('GOOGLE_APPLICATION_CREDENTIALS')

# Define Constants
source("constants.R")

df <- readr::read_tsv("df.tsv")

# Perform mapping
mapping <- cegwas::cegwas_map(df, mapping_snp_set = FALSE)

is_significant = any(results$aboveBF == 1)

if (!is_significant) {
  
  readr::write_tsv(mapping, "tables/mapping.tsv", na = "")
  
  #==================================#
  # Manhattan Plot - Not significant #
  #==================================#
  
  # Store mapping.tsv results
  readr::write_tsv(mapping, "tables/mapping.tsv", na = "")
  
  # Remove MtDNA
  mapping <- mapping %>% dplyr::filter(CHROM != "MtDNA")
  
  ggplot(mapping) +
    ggplot2::aes(x = POS/1e6, y = log10p) +
    ggplot2::geom_point() +
    ggplot2::facet_grid(.~CHROM, scales = "free_x", space = "free_x") +
    ggplot2::theme_bw() +
    ggplot2::geom_hline(aes(yintercept = BF), color = "#FF0000", size = 1)+
    theme_bw() +
    pub_theme +
    theme(plot.margin = unit(c(0.0,0.5,0.5,0),"cm"),
          panel.spacing = unit(0.8, "lines"),
          strip.background = element_blank(),
          axis.title.x = ggplot2::element_text(margin=margin(15,0,0,0), size=18, color="black"),
          axis.title.y = ggplot2::element_text(margin=margin(0,15,0,5), size=18, color="black"),
          panel.background = ggplot2::element_rect(color = "black", size= 0.50),
          axis.ticks= element_line(color = "black", size = 0.25),
          panel.border = element_rect(size=1, color = "black")) +
    ggplot2::labs(x = "Genomic Position (Mb)",
                  y = expression(-log[10](p)))

ggsave("figures/Manhattan.png", width = 10, height = 5)
quit(save = "no", status = 0)
}

# All code below is processed for significant mappings

proc_mappings <- cegwas::process_mappings(mapping, trait) %>%
               dplyr::mutate(marker = gsub("_", ":", marker)) 

readr::write_tsv(proc_mappings, "tables/mapping.tsv", na = "")

# Remove MtDNA
proc_mappings <- proc_mappings %>% dplyr::filter(CHROM != "MtDNA")
#================================================#
# Process Peaks and Manhattan Plot - Significant #
#================================================#

peaks <- na.omit(proc_mappings) %>%
dplyr::distinct(peak_id, .keep_all = TRUE) %>%
dplyr::select(marker, CHROM, startPOS, endPOS, log10p, trait) %>%
dplyr::mutate(query = paste0(CHROM, ":",startPOS, "-",endPOS)) %>%
dplyr::arrange(desc(log10p)) %>%
dplyr::mutate(top3peaks = seq(1:n())) %>%
dplyr::filter(top3peaks < 4) %>%
dplyr::select(trait,peak_pos = marker, interval = query, peak_log10p = log10p)
# Save mapping Intervals
mapping_intervals <- proc_mappings %>% 
            dplyr::mutate(report = args$report_slug, BF = BF, version = 0.1, reference = "WS245") %>%
            dplyr::group_by(peak_id) %>%
            dplyr::filter(!is.na(peak_id), log10p == max(log10p)) %>%
            dplyr::select(marker, CHROM, POS, report, trait, var.exp, log10p, BF, startPOS, endPOS, version, reference) %>%
            dplyr::distinct(.keep_all = T)
readr::write_tsv(mapping_intervals, "tables/mapping_intervals.tsv")
# Manhattan Plot
mplot <- cegwas::manplot(proc_mappings, "#666666")
mplot[[1]] +
theme_bw() +
pub_theme +
theme(plot.margin = unit(c(0.0,0.5,0.5,0),"cm"),
    panel.margin = unit(0.75, "lines"),
    strip.background = element_blank(),
    axis.title.x = ggplot2::element_text(margin=margin(15,0,0,0), size=18, color="black"),
    axis.title.y = ggplot2::element_text(margin=margin(0,15,0,5), size=18, color="black"),
    panel.border = element_rect(size=1, color = "black")) +
ggplot2::labs(x = "Genomic Position (Mb)",
            y = expression(-log[10](p))) +
theme(plot.title = ggplot2::element_blank())
ggsave("figures/Manhattan.png", width = 10, height = 5)
# PxG Plot
pg_plot <- pxg_plot(proc_mappings, color_strains = NA)
pg_plot[[1]] +
labs(y= args$trait_slug) +
pub_theme +
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

