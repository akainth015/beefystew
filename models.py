"""
This file defines the database models
"""
import random
from py4web.utils.populate import FIRST_NAMES, LAST_NAMES, IUP

from .common import db, Field
from pydal.validators import *
from .common import db, Field, auth



def get_user_email():
    return auth.current_user.get('email') if auth.current_user else None

# Define your table below
#
# db.define_table('thing', Field('name'))
#
# always commit your models to avoid problems later
#
# post table
# 1. id
# 2. created_by
# 3. image_ref (link to blob storage)

db.define_table('post',
                Field('created_by', 'reference auth_user'),
                Field('created_at', type='datetime'),
                Field('image_ref', type='string'),
                Field('caption', 'text'),
                Field('file_path'),
                Field('confirmed', 'boolean', default=False),
                Field('draft', type='boolean')
                )

db.define_table('neural_network',
                Field('created_by', type='reference auth_user', required=True, notnull=True),
                Field('is_trained', type='boolean', default=False),
                # store a reference to file that contains the weights
                Field('weights', type='string', default=None)
                )

db.define_table('stream',
                Field('created_by', 'reference auth_user'),
                Field('name', 'string', required=True, requires=IS_NOT_EMPTY()),
                Field('custom_question', 'string'),
                Field('nn_id', 'reference neural_network'),
                )

db.define_table('post_stream_mapping',
                Field('post_id', 'reference post'),
                # Field('post_id', 'reference upload'),
                Field('stream_id', 'reference stream'),
                )

db.commit()

