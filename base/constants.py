# -*- coding: utf-8 -*-
"""

This page is intended to store application constants that change
very infrequently (if ever). 

Author: Daniel E. Cook (danielecook@gmail.com)
"""

# PRICES
class PRICES:
    DIVERGENT_SET = 160
    STRAIN_SET = 640
    STRAIN = 15
    SHIPPING = 65

# BUILDS AND RELEASES
WORMBASE_BUILD = "WS261"
RELEASES = ["20170531",
            "20160408"]
CURRENT_RELEASE = RELEASES[0]


# URLS
BAM_URL_PREFIX = "https://elegansvariation.org.s3.amazonaws.com/bam"

# Maps chromosome in roman numerals to integer
CHROM_NUMERIC = {"I": 1,
                 "II": 2,
                 "III": 3,
                 "IV": 4,
                 "V": 5,
                 "X": 6,
                 "MtDNA": 7}