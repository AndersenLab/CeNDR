#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook



"""
import datetime
import decimal
import hashlib
import os
import uuid
import zipfile
import pytz
import yaml

from collections import Counter
from datetime import datetime as dt
from flask import g, json
from gcloud import storage
from logzero import logger
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable
from urllib.request import urlretrieve
from rich.progress import (
    BarColumn,
    DownloadColumn,
    TextColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
    Progress,
    TaskID,
)

from base.constants import GOOGLE_CLOUD_BUCKET, GOOGLE_CLOUD_PROJECT_ID

def flatten_dict(d, max_depth=1):
    def expand(key, value):
        if hasattr(value, "__dict__"):
            value = value.__dict__
            print(value)
        if isinstance(value, dict) and max_depth > 0:
            return [(key + '.' + k, v) for k, v in flatten_dict(value, max_depth - 1).items()]
        else:
            return [(key, value)]

    items = [item for k, v in d.items() for item in expand(k, v)]

    return dict(items)


def load_yaml(yaml_file):
    return yaml.load(open(f"base/static/yaml/{yaml_file}", 'r'))


def get_gs():
    """
        Gets the google storage bucket which
        stores static assets and report data.
    """
    if not hasattr(g, 'gs'):
        g.gs = storage.Client(project=GOOGLE_CLOUD_PROJECT_ID).get_bucket(GOOGLE_CLOUD_BUCKET)
    return g.gs

class json_encoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, "to_json"):
            return o.to_json()
        if hasattr(o, "__dict__"):
            return {k: v for k, v in o.__dict__.items() if k != "id" and not k.startswith("_")}
        if type(o) == decimal.Decimal:
            return float(o)
        elif isinstance(o, datetime.date):
            return str(o.isoformat())
        try:
            iterable = iter(o)
            return tuple(iterable)
        except TypeError:
            pass
        return json.JSONEncoder.default(self, o)


def dump_json(data):
    """
        Use to dump json on internal requests.
    """
    return json.dumps(data, cls=json_encoder)


def sorted_files(path):
    """
        Sorts files
    """
    return sorted([x for x in os.listdir(path) if not x.startswith(".")], reverse=True)


def hash_it(object, length=10):
    logger.debug(object)
    return hashlib.sha1(str(object).encode('utf-8')).hexdigest()[0:length]


def hash_file_upload(file, length=10):
  ''' Computes the sha1 hash of a file upload (FileStorage object) '''
  logger.debug(file)
  return hashlib.sha1(file.read()).hexdigest() [0:length]


def hash_password(password):
    h = hashlib.md5(password.encode())
    return h.hexdigest()


def chicago_date():
    return dt.now(pytz.timezone("America/Chicago")).date().isoformat()


def unique_id():
    return uuid.uuid4().hex


def is_number(s):
    if not s:
        return None
    try:
        complex(s)  # for int, long, float and complex
    except (ValueError, TypeError):
        return False

    return True


def list_duplicates(input_list):
    """
        Return the set of duplicates in a list
    """
    counts = Counter(input_list)
    return [x for x, v in counts.items() if v > 1]


def zipdir(directory, fname):
    """
    Zips a directory

    Args:
        path - The directory to zip
        fname - The output filename

    """
    with zipfile.ZipFile(fname, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(directory):
            for file in files:
                zipf.write(os.path.join(root, file))


progress = Progress(
    TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.1f}%",
    "•",
    DownloadColumn(),
    "•",
    TransferSpeedColumn(),
    "•",
    TimeRemainingColumn(),
)


class progress_bar():
    def __init__(self, task_id):
        self.task_id = task_id

    def __call__(self, block_num, block_size, total_size):
        progress.update(self.task_id, advance=1 * block_size, total=total_size)


def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)


def copy_url(task_id: TaskID, url: str, path: str) -> None:
    """Copy data from a url to a local file."""
    urlretrieve(url, path, progress_bar(task_id))
    touch(path + ".done")


def download(urls: Iterable[str], dest_dir: str):
    """Download multuple files to the given directory."""
    with progress:
        with ThreadPoolExecutor(max_workers=4) as pool:
            for url in urls:
                filename = url.split("/")[-1]
                dest_path = os.path.join(dest_dir, filename)
                done_path = dest_path + ".done"
                if os.path.exists(done_path) is False:
                    task_id = progress.add_task("download", filename=filename)
                    pool.submit(copy_url, task_id, url, dest_path)
