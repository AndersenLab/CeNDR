from peewee import *
import json
credentials = json.loads(open("../credentials.json",'r').read())

db = PostgresqlDatabase(
  'andersen',
  **credentials
  )

db.connect()

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