from flask import Flask
from flask_restful import Resource, Api
from models import report
from peewee import *
import json
import datetime
import os, sys
import MySQLdb
import _mysql



def abort_if_todo_doesnt_exist(request_id):
    if request_id not in TODOS:
        abort(404, message="Doesn't exist".format(request_id))

parser = reqparse.RequestParser()

class Request(Resource):
  def get(self, request_id):
    abort_if_todo_doesnt_exist(request_id)
    reports = list(report.select().filter(report.release==0))
