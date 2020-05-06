#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

These functions will concern genetic data.

"""

# chrom : left tip, left arm, center, right arm, right tip
# From Rockman Krugylak 2009
CHROM_ARM_CENTER = {'I': (527, 3331, 7182, 3835, 197),
                    'II': (306, 4573, 7141, 2589, 670),
                    'III': (494, 3228, 6618, 2877, 567),
                    'IV': (720, 3176, 9074, 3742, 782),
                    'V': (643, 5254, 10653, 3787, 583),
                    'X': (572, 5565, 6343, 3937, 1302)}


def arm_or_center(chrom, pos):
    """
        Determines whether a position is on the
        arm or center of a chromosome.
    """
    if chrom == 'MtDNA':
        return None
    ca = CHROM_ARM_CENTER[chrom]
    ca = [x * 1000 for x in ca]
    c = 'arm'
    if pos > ca[1]:
        c = 'center'
    if pos > ca[2]:
        c = 'arm'
    return c
