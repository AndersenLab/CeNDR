from collections import OrderedDict
from peewee import *
import re
import requests

db = PostgresqlDatabase(
  'andersen',
  user = 'andersen',
  password = 'kniB3duE4drYil6hinD2yeD8juth8coUn2ef7Ayb',
  host = 'andersen-db.cu9qvcawtap6.us-east-1.rds.amazonaws.com'
  )

db.connect()



class strain(Model):
  """C Elegans strain complete info database"""
  strain = CharField()
  isotype = CharField(null=True)
  longitude = FloatField(null = True)
  latitude = FloatField(null = True)
  isolation = CharField(null=True)
  location = CharField(null=True)
  prev_names = CharField(null=True)
  warning_msg =  CharField(null=True)
  sequenced = BooleanField()

  class Meta:
    database = db


db.drop_tables([strain], safe=True)
db.create_tables([strain])

r = requests.get("https://raw.githubusercontent.com/AndersenLab/Andersen-Lab-Strains/master/processed/strain_info_join.tsv")

lines = r.text.splitlines()


header = ["strain", "isotype", "longitude", "latitude", "isolation", "location", "prev_names", 
"warning_msg", "sequenced"]

for line in lines[1:]:
  strain_info = re.split('\t',line)
  data = OrderedDict(zip(header,strain_info))
  data = {k:v for k,v in data.items()}
  for k in data.keys():
    if data[k] == "NA":
      data[k] = None
  strain(**data).save()
 