#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook



"""
import os
import time
import arrow
from utils.gcloud import get_item, report_m, trait_m
from subprocess import Popen, STDOUT, PIPE


# Define variables
try:
    report_name = os.environ['REPORT_NAME']
    trait_name = os.environ['TRAIT_NAME']
    print(f"Fetching Task: {report_name} - {trait_name}")
    report = report_m(os.environ['REPORT_NAME'])
    trait = report.fetch_traits(trait_name=trait_name, latest=True)

    # Update report start time
    trait.started_on = arrow.utcnow().datetime
    trait.run_status = "Running"
    trait.save()

    # Get cegwas version
    comm = ['Rscript', 'library(tidyverse);(devtools::session_info()$packages %>% dplyr::filter(package == "cegwas") %>% dplyr::select(version, source) %>% dplyr::mutate(v = glue::glue("{version}:{source}")))$v']
    out, err = Popen(comm, stdout=PIPE, stderr=PIPE).communicate()
    trait.cegwas_version = out

    comm = ['Rscript', 'pipeline.R']
    process = Popen(comm, stdout=PIPE, stderr=STDOUT)
    with process.stdout as proc:
        for line in proc:
            print(str(line, 'utf-8').strip())
    exitcode = process.wait()
    print(f"R exited with code {exitcode}")
except Exception as e:
    trait.error = e
    trait.run_status = "Error"
else:
    trait.run_status = "Complete"
finally:
    trait.completed_on = arrow.utcnow().datetime
    trait.save()