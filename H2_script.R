#!/usr/bin/env Rscript H2_script.R
library(boot)
library(lme4)
library(dplyr)
library(futile.logger)
library(tidyr)
library(glue)
library(data.table)

########################
### define functions ###
########################
# Heritability
# data is data frame that contains strain and Value column
# indicies are used by the boot function to sample from the 'data' data.frame
H2.test.boot <- function(data, indicies){
    
    d <- data[indicies,]
    
    pheno <- as.data.frame(dplyr::select(d, Value))[,1]
    
    Strain <- as.factor(d$Strain)
    
    reffMod <- lme4::lmer(pheno ~ 1 + (1|Strain))
    
    Variances <- as.data.frame(lme4::VarCorr(reffMod, comp = "Variance"))
    
    Vg <- Variances$vcov[1]
    Ve <- Variances$vcov[2]
    H2 <- Vg/(Vg+Ve)
    
    # errors <- sqrt(diag(lme4::VarCorr(reffMod, comp = "Variance")$strain))
    
    return(H2)
}

# data is data frame that contains strain and Value column
H2.test <- function(data){
    
    pheno <- as.data.frame(dplyr::select(data, Value))[,1]
    Strain <- as.factor(data$Strain)
    
    reffMod <- lme4::lmer(pheno ~ 1 + (1|Strain))
    
    Variances <- as.data.frame(lme4::VarCorr(reffMod, comp = "Variance"))
    
    Vg <- Variances$vcov[1]
    Ve <- Variances$vcov[2]
    H2 <- Vg/(Vg+Ve)
    
    # errors <- sqrt(diag(lme4::VarCorr(reffMod, comp = "Variance")$strain))
    
    return(H2)
}

# df is data frame that contains strain and Value column
H2.calc <- function(data, boot = TRUE, type = "broad", reps = 10000){
    df <- dplyr::select(data, Strain, Value)
    
    flog.info("Running bootstrapping")
    if(boot == TRUE){
        # bootstrapping with 10000 replications
        # can reduce value to save time (500 is reasonable most of the time).
        # if you Error in bca.ci(boot.out, conf, index[1L], L = L, t = t.o, t0 = t0.o,  : estimated adjustment 'a' is NA, then you need to increase R value.
        if(type == "broad") {
            results <- boot(data = df, statistic = H2.test.boot, R = reps) 
        } else {
            results <- boot(data = df, statistic = narrowh2.boot, R = reps) 
        }
        
        # get 95% confidence interval
        ci <- boot.ci(results, type="bca")
        
        H2_errors <- data.frame(H2 = ci$t0,
                                ci_l = ci$bca[4],
                                ci_r = ci$bca[5])
        
        return(H2_errors)
        
    } else {
        if(type == "broad") {
            H2 <- data.frame(H2 = H2.test(data = df), ci_l = NA, ci_r = NA)
        } else {
            H2 <- data.frame(H2 = narrowh2(df_h = df), ci_l = NA, ci_r = NA)
        }
        return(H2)
    }
    
}

# extract strain, isotype dataframe from database
generate_isotype_lookup <- function(species = "ce") {
    
    if ( species == "ce" ) {
        isotype_lookup <- strain_data %>%
            dplyr::mutate(strain_names = ifelse(!is.na( previous_names ),
                                                paste( strain, previous_names, sep = "|" ),
                                                strain )) %>%
            tidyr::separate_rows(strain_names, sep = "\\|") %>%
            dplyr::select(strain, previous_name = strain_names, isotype) %>%
            dplyr::distinct()
    }
    
    return( isotype_lookup )
}

# Resolve strain names to isotypes
resolve_isotypes <- function(...) {
    
    isotype_lookup = generate_isotype_lookup()
    strains <- unlist(list(...))
    
    purrr::map_chr(strains, function(x) {
        isotype <- isotype_lookup %>%
            dplyr::filter(
                (x == strain) |
                    (x == isotype) |
                    (x == previous_name)
            ) %>%
            dplyr::pull(isotype) %>%
            unique()
        
        if (length(isotype) == 0) {
            message(glue::glue("{x} is not a known strain. Isotype set to NA; Please check CeNDR"))
        } else if (length(isotype) > 1) {
            message(glue::glue("{x} resolves to multiple isotypes. Isotype set to NA; Please check CeNDR"))
        }
        if (length(isotype) != 1) {
            isotype <- NA
        }
        isotype
    })
    
}

# prune outliers
# data = strain, trait, phenotype
BAMF_prune <- function(data, remove_outliers = TRUE ){
    
    categorize1 <- function(data) {
        with(data,
             ( (sixhs >= 1 & ( (s6h + s5h + s4h ) / numst) <= .05))
             | ( (sixls >= 1 & ( (s6l + s5l + s4l) / numst) <= .05))
        )
    }
    # If the 5 innermost bins are discontinuous by more than a 1 bin gap, the
    # observation is in the fifth bin (between 7 and 10x IQR outside the
    # distribution), and the four outermost bins make up less than 5% of the
    # population, mark the observation an outlier
    categorize2 <- function(data) {
        with(data,
             ( (fivehs >= 1 & ( (s6h + s5h + s4h + s3h) / numst) <= .05))
             | ( (fivels >= 1 & ( (s6l + s5l + s4l + s3l) / numst) <= .05))
        )
    }
    # If the 4 innermost bins are discontinuous by more than a 1 bin gap, the
    # observation is in the fourth bin (between 5 and 7x IQR outside the
    # distribution), and the four outermost bins make up less than 5% of the
    # population, mark the observation an outlier
    categorize3 <- function(data) {
        with(data,
             ( (fourhs >= 1 & (s5h + s4h + s3h + s2h) / numst <= .05))
             | ( (fourls >= 1 & (s5l + s4l + s3l + s2l) / numst <= .05))
        )
    }
    napheno <- data[is.na(data$phenotype), ] %>%
        dplyr::mutate(bamfoutlier1 = NA, bamfoutlier2 = NA, bamfoutlier3 = NA)
    
    datawithoutliers <- data %>%
        # Filter out all of the wash and/or empty wells
        dplyr::filter(!is.na(strain)) %>%
        # Group by trait, the, calculate the first and third
        # quartiles for each of the traits
        dplyr::group_by(trait) %>%
        dplyr::summarise(iqr = IQR(phenotype, na.rm = TRUE),
                         q1 = quantile(phenotype, probs = .25, na.rm = TRUE),
                         q3 = quantile(phenotype, probs = .75,
                                       na.rm = TRUE)) %>%
        # Add a column for the boundaries of each of the bins
        dplyr::mutate(cut1h = q3 + (iqr * 2),
                      cut1l = q1 - (iqr * 2),
                      cut2h = q3 + (iqr * 3),
                      cut2l = q1 - (iqr * 3),
                      cut3h = q3 + (iqr * 4),
                      cut3l = q1 - (iqr * 4),
                      cut4h = q3 + (iqr * 5),
                      cut4l = q1 - (iqr * 5),
                      cut5l = q1 - (iqr * 7),
                      cut5h = q3 + (iqr * 7),
                      cut6l = q1 - (iqr * 10),
                      cut6h = q3 + (iqr * 10)) %>%
        # Join the bin boundaries back to the original data frame
        dplyr::left_join(data, ., by = c("trait")) %>%
        dplyr::ungroup() %>%
        dplyr::rowwise() %>%
        # Add columns tallying the total number of points in each of the bins
        dplyr::mutate(onehs = ifelse(cut2h > phenotype & phenotype >= cut1h,
                                     1, 0),
                      onels = ifelse(cut2l < phenotype & phenotype <= cut1l,
                                     1, 0),
                      twohs = ifelse(cut3h > phenotype & phenotype >= cut2h,
                                     1, 0),
                      twols = ifelse(cut3l < phenotype & phenotype <= cut2l,
                                     1, 0),
                      threehs = ifelse(cut4h > phenotype & phenotype >= cut3h,
                                       1, 0),
                      threels = ifelse(cut4l < phenotype & phenotype <= cut3l,
                                       1, 0),
                      fourhs = ifelse(cut5h > phenotype &  phenotype >= cut4h,
                                      1, 0),
                      fourls = ifelse(cut5l < phenotype &  phenotype <= cut4l,
                                      1, 0),
                      fivehs = ifelse(cut6h > phenotype & phenotype >= cut5h,
                                      1, 0),
                      fivels = ifelse(cut6l < phenotype & phenotype <= cut5l,
                                      1, 0),
                      sixhs = ifelse(phenotype >= cut6h, 1, 0),
                      sixls = ifelse(phenotype <= cut6l, 1, 0)) %>%
        # Group on condition and trait, then sum the total number of data points
        # in each of the IQR multiple bins
        dplyr::group_by(trait) %>%
        dplyr::mutate(s1h = sum(onehs, na.rm = TRUE),
                      s2h = sum(twohs, na.rm = TRUE),
                      s3h = sum(threehs, na.rm = TRUE),
                      s4h = sum(fourhs, na.rm = TRUE),
                      s5h = sum(fivehs, na.rm = TRUE),
                      s1l = sum(onels, na.rm = TRUE),
                      s2l = sum(twols, na.rm = TRUE),
                      s3l = sum(threels, na.rm = TRUE),
                      s4l = sum(fourls, na.rm = TRUE),
                      s5l = sum(fivels, na.rm = TRUE),
                      s6h = sum(sixhs, na.rm = TRUE),
                      s6l = sum(sixls, na.rm = TRUE)) %>%
        # Group on condition and trait, then check to see if the number of
        # points in each bin is more than 5% of the total number of data points
        dplyr::group_by(trait) %>%
        dplyr::mutate(p1h = ifelse(sum(onehs, na.rm = TRUE) / n() >= .05, 1, 0),
                      p2h = ifelse(sum(twohs, na.rm = TRUE) / n() >= .05, 1, 0),
                      p3h = ifelse(sum(threehs, na.rm = TRUE) / n() >= .05, 1, 0),
                      p4h = ifelse(sum(fourhs, na.rm = TRUE) / n() >= .05 ,1, 0),
                      p5h = ifelse(sum(fivehs, na.rm = TRUE) / n() >= .05 ,1 ,0),
                      p6h = ifelse(sum(sixhs, na.rm = TRUE) / n() >= .05 ,1, 0),
                      p1l = ifelse(sum(onels, na.rm = TRUE) / n() >= .05 ,1, 0),
                      p2l = ifelse(sum(twols, na.rm = TRUE) / n() >= .05 ,1, 0),
                      p3l = ifelse(sum(threels, na.rm = TRUE) / n() >= .05 ,1,0),
                      p4l = ifelse(sum(fourls, na.rm = TRUE) / n() >= .05 , 1, 0),
                      p5l = ifelse(sum(fivels, na.rm = TRUE) / n() >= .05, 1, 0),
                      p6l = ifelse(sum(sixls,
                                       na.rm = TRUE) / n() >= .05, 1, 0)) %>%
        # Count the number of observations in each condition/trait combination
        dplyr::mutate(numst = n()) %>%
        # Group on trait, then filter out NAs in any of the added
        # columns
        dplyr::group_by(trait) %>%
        dplyr::filter(!is.na(trait), !is.na(phenotype), !is.na(iqr), !is.na(q1),
                      !is.na(q3), !is.na(cut1h), !is.na(cut1l), !is.na(cut2h),
                      !is.na(cut2l), !is.na(cut3h), !is.na(cut3l),
                      !is.na(cut4h), !is.na(cut4l), !is.na(cut5l),
                      !is.na(cut5h), !is.na(cut6l), !is.na(cut6h),
                      !is.na(onehs), !is.na(onels), !is.na(twohs),
                      !is.na(twols), !is.na(threehs), !is.na(threels),
                      !is.na(fourhs), !is.na(fourls), !is.na(fivehs),
                      !is.na(fivels), !is.na(sixhs), !is.na(sixls),
                      !is.na(s1h), !is.na(s2h), !is.na(s3h), !is.na(s4h),
                      !is.na(s5h), !is.na(s1l), !is.na(s2l), !is.na(s3l),
                      !is.na(s4l), !is.na(s5l), !is.na(s6h), !is.na(s6l),
                      !is.na(p1h), !is.na(p2h), !is.na(p3h), !is.na(p4h),
                      !is.na(p5h), !is.na(p6h), !is.na(p1l), !is.na(p2l),
                      !is.na(p3l), !is.na(p4l), !is.na(p5l), !is.na(p6l),
                      !is.na(numst)) %>%
        # Add three columns stating whether the observation is an outlier
        # based the three outlier detection functions below
        dplyr::ungroup() %>%
        dplyr::mutate(cuts = categorize1(.),
                      cuts1 = categorize2(.),
                      cuts2 = categorize3(.))
    
    if ( remove_outliers == T){
        outliers_removed <- datawithoutliers %>%
            dplyr::rename(bamfoutlier1 = cuts,
                          bamfoutlier2 = cuts1,
                          bamfoutlier3 = cuts2) %>%
            dplyr::filter(!bamfoutlier1 & !bamfoutlier2 & !bamfoutlier3) %>%
            dplyr::select(trait, strain, phenotype)
        
        return(outliers_removed)
    } else {
        with_outliers <- datawithoutliers %>%
            dplyr::rename(bamfoutlier1 = cuts,
                          bamfoutlier2 = cuts1,
                          bamfoutlier3 = cuts2) %>%
            dplyr::select(trait, strain, phenotype, bamfoutlier1, bamfoutlier2, bamfoutlier3) %>%
            dplyr::mutate(outlier = ifelse( bamfoutlier1 | bamfoutlier2 | bamfoutlier3, TRUE, FALSE)) %>%
            dplyr::select(strain, trait, phenotype, outlier)
        
        return(with_outliers)
    }
}

# Process phenotypes for mapping and heritability
process_phenotypes <- function(df,
                               summarize_replicates = "mean",
                               prune_method = "BAMF",
                               remove_outliers = TRUE,
                               threshold = 2){
    
    if ( sum(grepl(colnames(df)[1], "Strain", ignore.case = T)) == 0 ) {
        message(glue::glue("Check input data format, strain should be the first column."))
    }
    
    # ~ ~ ~ # resolve strain isotypes # ~ ~ ~ #
    # get strain isotypes
    strain_isotypes_db <- generate_isotype_lookup()
    # identify strains that were phenotyped, but are not part of an isotype
    non_isotype_strains <- dplyr::filter(df,
                                         !(strain %in% strain_isotypes_db$strain),
                                         !(strain %in% strain_isotypes_db$isotype))
    # remove any strains identified to not fall into an isotype
    if ( nrow(non_isotype_strains) > 0 ) {
        
        strains_to_remove <- unique(non_isotype_strains$strain)
        
        message(glue::glue("Removing strain(s) {strains_to_remove} because they do not fall into a defined isotype."))
        
        df_non_isotypes_removed <- dplyr::filter( df, !( strain %in% strains_to_remove) )
    } else {
        df_non_isotypes_removed <- df
    }
    
    # ~ ~ ~ ## ~ ~ ~ ## ~ ~ ~ ## ~ ~ ~ # Resolve Isotypes # ~ ~ ~ ## ~ ~ ~ ## ~ ~ ~ ## ~ ~ ~ #
    df_isotypes_resolved <- df_non_isotypes_removed %>%
        dplyr::group_by(strain) %>%
        dplyr::mutate(isotype = resolve_isotypes(strain)) %>%
        dplyr::ungroup() %>%
        tidyr::gather(trait, phenotype, -strain, -isotype) %>%
        dplyr::filter(!is.na(phenotype))
    
    # deal with multiple strains per isotype group
    test <- df_isotypes_resolved %>%
        dplyr::group_by(isotype) %>%
        dplyr::mutate(num = length(unique(strain))) %>% 
        dplyr::mutate(ref_strain = strain == isotype)
    no_issues <- test %>%
        dplyr::filter(num == 1 & ref_strain == T)
    issues <- test %>%
        dplyr::filter(num > 1 | ref_strain == F) 
    
    fixed_issues <- no_issues %>%
        dplyr::select(-num, -ref_strain)
    
    # go through each isotype issue and resolve it
    for(i in unique(issues$isotype)) {
        df <- issues %>%
            dplyr::filter(isotype == i)
        
        # if only one strain is phenotyped, just rename strain to isotype ref strain and flag
        if(nrow(df) == 1) {
            fix <- df %>%
                dplyr::mutate(strain = isotype)
            message(glue::glue("Non-isotype reference strain {df$strain[1]} renamed to isotype {i}."))
        } else {
            # remove non-isotype strains
            fix <- df %>%
                dplyr::filter(ref_strain) %>%
                dplyr::select(-ref_strain, -num)
            
            # warn the user
            if(sum(df$ref_strain) > 0) {
                message(glue::glue("Non-isotype reference strain(s) {paste(df %>% dplyr::filter(!ref_strain) %>% dplyr::pull(strain), collapse = ', ')} from isotype group {i} removed."))
            } 
            else {
                message(glue::glue("Non-isotype reference strain(s) {paste(df %>% dplyr::filter(!ref_strain) %>% dplyr::pull(strain), collapse = ', ')} from isotype group {i} removed.
                                   To include this isotype in the analysis, you can (1) phenotype {i} or (2) evaluate the similarity of these strains and choose one representative for the group."))
            }
            }
        # add to data
        fixed_issues <- rbind(fixed_issues, fix)
        }
    
    # ~ ~ ~ ## ~ ~ ~ ## ~ ~ ~ ## ~ ~ ~ # Summarize Replicate Data # ~ ~ ~ ## ~ ~ ~ ## ~ ~ ~ ## ~ ~ ~ #
    df_replicates_summarized <- fixed_issues %>%
        dplyr::group_by(isotype, trait) %>% {
            if (summarize_replicates == "mean") dplyr::summarise(., phenotype = mean( phenotype, na.rm = T ) )
            else if (summarize_replicates == "median") dplyr::summarise(., phenotype = median( phenotype, na.rm = T ) )
            else if (summarize_replicates == "none") dplyr::mutate(., phenotype = phenotype)
            else  message(glue::glue("Please choose mean, median, or none as options for summarizeing replicate data.")) } %>%
        dplyr::select(strain = isotype, trait, phenotype) %>%
        dplyr::ungroup()
    
    # ~ ~ ~ ## ~ ~ ~ ## ~ ~ ~ ## ~ ~ ~ # Outlier Functions # ~ ~ ~ ## ~ ~ ~ ## ~ ~ ~ ## ~ ~ ~ #
    is_out_tukey <- function(x, k = threshold, na.rm = TRUE) {
        quar <- quantile(x, probs = c(0.25, 0.75), na.rm = na.rm)
        iqr <- diff(quar)
        
        ( !(quar[1] - k * iqr <= x) ) | ( !(x <= quar[2] + k * iqr) )
    }
    is_out_z <- function(x, thres = threshold, na.rm = TRUE) {
        ( !abs(x - mean(x, na.rm = na.rm)) <= thres * sd(x, na.rm = na.rm) )
    }
    is_out_mad <- function(x, thres = threshold, na.rm = TRUE) {
        ( !abs(x - median(x, na.rm = na.rm)) <= thres * mad(x, na.rm = na.rm) )
    }
    
    # ~ ~ ~ ## ~ ~ ~ ## ~ ~ ~ ## ~ ~ ~ # Perform outlier removal # ~ ~ ~ ## ~ ~ ~ ## ~ ~ ~ ## ~ ~ ~ #
    if ( prune_method == "BAMF" ) {
        df_outliers <- BAMF_prune(df_replicates_summarized, remove_outliers = FALSE)
    } else {
        df_outliers <-  dplyr::ungroup(df_replicates_summarized) %>%
            dplyr::group_by(trait) %>% {
                if (prune_method == "MAD") dplyr::transmute_if(., is.numeric, dplyr::funs( outlier = is_out_mad ) )
                else if (prune_method == "TUKEY") dplyr::transmute_if(., is.numeric, dplyr::funs( outlier = is_out_tukey ) )
                else if (prune_method == "Z") dplyr::transmute_if(., is.numeric, dplyr::funs( outlier = is_out_z ) )
                else  message(glue::glue("Please choose BAMF, MAD, TUKEY, or Z as options for summarizeing replicate data.")) } %>%
            dplyr::ungroup() %>%
            dplyr::bind_cols(., dplyr::ungroup(df_replicates_summarized)) %>%
            dplyr::select(strain, trait, phenotype, outlier)
    }
    
    if (remove_outliers == TRUE ) {
        processed_phenotypes_output <- df_outliers %>%
            dplyr::filter( !outlier ) %>%
            dplyr::select( -outlier )
        # tidyr::spread( trait, phenotype)
    } else {
        processed_phenotypes_output <- df_outliers 
        # tidyr::spread( trait, phenotype)
    }
    
    return(processed_phenotypes_output)
}



# RUN
args = commandArgs(trailingOnly=TRUE)

# update to include geno matrix
usage_cmd = "USAGE: Rscript H2_script.R input_file output_file"

if (length(args) < 3){
    print(usage_cmd)
}

### ARGS ###
# 1 - input_file
# 2 - output_file
# 3 - hash_file
# 4 - version
# 5 - strain_data


# Read in data
data <- data.table::fread(args[1]) %>%
    tidyr::spread(TraitName, Value) %>%
    dplyr::select(-Replicate, -AssayNumber) %>%
    dplyr::rename(strain = Strain)
output_fname = args[2]
heritability_version = args[4]
hash <- readLines(args[3])
strain_data <- data.table::fread(args[5])

# process phenotypes
processed_data <- process_phenotypes(data, summarize_replicates = "none") %>%
    dplyr::rename(Strain = strain, Value = phenotype, TraitName = trait)

# Run H2 calculation
result <- NULL
result <- H2.calc(processed_data, boot = T, type = "broad", reps = 500) 

# if result doesn't converge, just give point estimate...
if(is.null(result)) {
    result <- H2.calc(processed_data, boot = F, type = "broad")
}

# add timepoint data
result$hash <- hash
result$trait_name <- data$TraitName[1]
result$date <- Sys.time()
result$heritability_version <- heritability_version

# Write the result
data.table::fwrite(result, output_fname, sep = '\t')
