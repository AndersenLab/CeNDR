import boto3
import codecs
import csv
from collections import OrderedDict
import os
import re
import requests


dynamodb = boto3.resource('dynamodb')

table = dynamodb.create_table(
    AttributeDefinitions = [
    {
      'AttributeName': 'Strain',
      'AttributeType': 'S'
    }
  ],
  TableName = 'strains',
  KeySchema = [
    {
      'AttributeName': 'Strain',
      'KeyType': 'HASH'
    }
  ],
    ProvisionedThroughput={
        'ReadCapacityUnits': 5,
        'WriteCapacityUnits': 5
    }
)

print table.does_table_exist()

# print table.meta.client.get_waiter('table_exists')

# r = requests.get("https://raw.githubusercontent.com/AndersenLab/Andersen-Lab-Strains/master/processed/strain_info.tsv")

# lines = r.text.splitlines()

# for line in lines:
#   print re.split('\t',line)
# # print re.split('\t', r.text.splitlines())
# # print r.text.decode("utf-8")