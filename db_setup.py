from collections import OrderedDict
from peewee import *
import re
import requests
import json

credentials = json.loads(open("credentials.json",'r').read())

db = PostgresqlDatabase(
  'andersen',
  **credentials
  )

db.connect()


booldict = {"TRUE": True, "FALSE": False}

#=======================#
# Generate strain table #
#=======================#

class strain(Model):
  """C Elegans strain complete info database"""
  strain = CharField(index = True)
  isotype = CharField(null=True, index = True)
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

header = ["strain", "isotype", "longitude", "latitude", "isolation", "location", "prev_names", 
"warning_msg", "sequenced"]

strain_info_join = requests.get("https://raw.githubusercontent.com/AndersenLab/Andersen-Lab-Strains/master/processed/strain_info_join.tsv")

lines = strain_info_join.text.splitlines()

strain_data = []
with db.atomic():
  for line in lines[1:]:
    strain_info = re.split('\t',line)
    l = OrderedDict(zip(header,strain_info))
    l = {k:v for k,v in l.items()}
    l["sequenced"] = booldict[l["sequenced"]]
    for k in l.keys():
      if l[k] == "NA":
        l[k] = None
    strain_data.append(l)

with db.atomic():
  strain.insert_many(strain_data).execute()
   