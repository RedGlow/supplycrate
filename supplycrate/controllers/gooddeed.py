from sqlalchemy import Table, cast, Integer, func, insert
from sqlalchemy.orm import aliased
from sqlalchemy.sql import functions, literal_column, or_, and_
import transaction
from supplycrate import models, DBSession
from supplycrate.models import RTLPMemoryTable
import supplycrate.tablerenderer.model as tmodels


__author__ = 'Mattia'




class GoodDeedTable(tmodels.Table):
    name = "gooddeed"

    default_sorting_column = 5

    default_sorting_asc = False

