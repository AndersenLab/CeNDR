#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook



"""
import os
import time
import arrow
from logzero import logger
from utils.gcloud import get_item, report_m, trait_m

# Define variables
report_name = os.environ['REPORT_NAME']
trait_name = os.environ['TRAIT_NAME']
logger.info(f"Fetching Task: {report_name} - {trait_name}")

report = report_m(os.environ['REPORT_NAME'])
trait = trait_m(report.trait_task_ids[trait_name])

# Update report start time
trait.started_on = arrow.utcnow().datetime
trait.run_status = "Running"
trait.save()

time.sleep(25)



trait.completed_on = arrow.utcnow().datetime
trait.run_status = "Complete"
trait.save()