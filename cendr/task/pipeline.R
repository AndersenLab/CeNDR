.libPaths( c( "/home/danielcook/R/x86_64-pc-linux-gnu-library/3.2", .libPaths()) )
library(cegwas)
library(dplyr)
library(ggplot2)
library(jsonlite)
library(RMySQL)
library(tidyr)
library(readr)
library(xmemoise)
library(grid)

# Get Payload
if (length(commandArgs(trailingOnly=TRUE)) == 0) {
  args <- fromJSON('{ "trait_slug": "telomere-length", "report_slug": "telomere-length", "trait_name" : "telomere-length"}')
} else {
  args <- fromJSON(commandArgs(trailingOnly=TRUE))
}

mysql_credentials <- fromJSON(readLines("credentials.json"))

# To connect to a database first create a src:
db <- src_mysql(dbname = "cegwas_v2", host = mysql_credentials$host, user = mysql_credentials$user, password= mysql_credentials$password)

update_status <- function(status) {
  # Update the status of the job.
  db <- src_mysql(dbname = "cegwas_v2", host = mysql_credentials$host, user = mysql_credentials$user, password= mysql_credentials$password)
  # Function for updating status of currently running job.
  comm <- sprintf("UPDATE report_trait SET status='%s' WHERE report_slug = '%s' AND trait_slug = '%s'",
                  status, args$report_slug, args$trait_slug)
  dbSendQuery(db$con, comm)
  try(invisible(dbDisconnect(db$con)), silent = T)
}

report_trait_strain_tbl <- tbl(db, "report_trait_strain_value_20170531")

# Then reference a tbl within that src
input_trait <- collect(report_trait_strain_tbl %>%
             dplyr::select(strain, report_slug, trait_slug, value) %>%
             dplyr::filter(trait_slug == args$trait_slug, report_slug == args$report_slug) %>%
             dplyr::select(strain, value))

try(invisible(dbDisconnect(db$con)), silent = T)

colnames(input_trait) <- c("strain", args$trait_slug)
pub_theme <- ggplot2::theme_bw() +
  ggplot2::theme(axis.text.x = ggplot2::element_text(size=14, color="black"),
                 axis.text.y = ggplot2::element_text(size=14, color="black"),
                 axis.title.x = ggplot2::element_text(size=14, face="bold", color="black", vjust=-.3),
                 axis.title.y = ggplot2::element_text(size=14, face="bold", color="black", vjust=2),
                 strip.text.x = ggplot2::element_text(size=16, face="bold", color="black"),
                 strip.text.y = ggplot2::element_text(size=16, face="bold", color="black"),
                 axis.ticks= element_line( color = "black", size = 0.25),
                 legend.position="none",
                 plot.margin = unit(c(1.0,0.5,0.5,1.0),"cm"),
                 plot.title = ggplot2::element_text(size=24, face="bold", vjust = 1),
                 panel.background = ggplot2::element_rect(color = "black", size= 0.75),
                 strip.background = ggplot2::element_rect(color = "black", size = 0.75))

#=================#
# Perform Mapping #
#=================#
update_status("Processing Phenotype Data")
trait  <- process_pheno(input_trait)


# Save phenotype data
as.data.frame(t(trait[[2]])) %>%
tibble::rownames_to_column("isotype") %>%
plyr::rename(c("V1"=paste0("processed_",args$trait_name))) %>%
dplyr::full_join(input_trait %>%
  dplyr::rowwise() %>%
   dplyr::mutate(isotype = cegwas::resolve_isotype(strain)[[1]])
  , by = "isotype") %>%
dplyr::select(1,3,4,2) %>%
readr::write_tsv("tables/phenotype.tsv")

update_status("Performing Mapping")


# CUSTOM CEGWAS GWAS MAPPINGS FUNCTION
gwas_mappings <- function (data, kin_matrix = kinship, 
    snpset = snps, min.MAF = 0.05, mapping_snp_set = FALSE) 
{
    x <- data.frame(trait = data[[1]], data[[2]]) %>% tidyr::gather(strain, 
        value, -trait) %>% tidyr::spread(trait, value)
    y <- snpset %>% dplyr::mutate(marker = paste0(CHROM, "_", 
        POS)) %>% dplyr::select(marker, dplyr::everything(), -REF, -ALT) %>% 
        as.data.frame()
    if (mapping_snp_set == TRUE) {
        y <- y %>% dplyr::filter(marker %in% data.frame(mapping_snps)$CHROM_POS)
    }
    kin <- as.matrix(kin_matrix)
    strains <- data.frame(strain = x[, 1])
    x <- data.frame(x[, 2:ncol(x)])
    colnames(x) <- data[[1]]
    ph = data.frame(strains, x)
    colnames(ph) <- c("strain", data[[1]])
    pmap <- rrBLUP::GWAS(pheno = ph, geno = y, K = kin, min.MAF = min.MAF, 
        n.core = 1, P3D = FALSE, plot = FALSE)
    return(pmap)
}


mgwas_mappings <- memoise(gwas_mappings, cache = cache_datastore(project = "andersen-lab", cache = "rcache"))

mapping <- mgwas_mappings(trait, mapping_snp_set = F)
colnames(mapping) <- c("marker", "CHROM", "POS", "log10p")
mapping <- mapping %>% dplyr::mutate(trait = gsub("-", "\\.", trait[[1]])) %>% tbl_df()

mapping <- mapping %>% dplyr::filter(!is.na(log10p), log10p > 0)
# Fix trait names
mapping$trait <- gsub("^X","",mapping$trait)
max_sig <- max(mapping$log10p)
BF <- -log10(.05/nrow(mapping))

# Save mapping file
save(mapping, file = "tables/mapping.Rdata")

update_status("Processing Mapping")

if(max_sig < BF) {
  # If no significant peaks found, write mapping.tsv and plot Manhattan
  readr::write_tsv(mapping, "tables/mapping.tsv", na = "")

  #==================================#
  # Manhattan Plot - Not significant #
  #==================================#
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
        panel.margin = unit(0.75, "lines"),
        strip.background = element_blank(),
        axis.title.x = ggplot2::element_text(margin=margin(15,0,0,0), size=18, color="black"),
        axis.title.y = ggplot2::element_text(margin=margin(0,15,0,5), size=18, color="black"),
        panel.border = element_rect(size=1, color = "black")) +
  ggplot2::labs(x = "Genomic Position (Mb)",
                y = expression(-log[10](p)))

  ggsave("figures/Manhattan.png", width = 10, height = 5)

} else {

  proc_mappings <- process_mappings(mapping, trait) %>%
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
}
update_status("Transferring Data")