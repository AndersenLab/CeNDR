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
          panel.spacing = unit(0.50, "lines"),
          strip.background = element_blank(),
          axis.title.x = ggplot2::element_text(margin=margin(15,0,0,0), size=18, color="black"),
          axis.title.y = ggplot2::element_text(margin=margin(0,15,0,5), size=18, color="black"),
          panel.background = ggplot2::element_rect(color = "black", size= 0.50),
          axis.ticks= element_line(color = "black", size = 0.25),
          panel.border = element_rect(size=1, color = "black")) +
    ggplot2::labs(x = "Genomic Position (Mb)",
                  y = expression(-log[10](p)))

ggsave("figures/Manhattan.png", width = 10, height = 5)

}


PUB_THEME <- ggplot2::theme_bw() +
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
