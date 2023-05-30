"""
This file defines the database models
"""
import random
from py4web.utils.populate import FIRST_NAMES, LAST_NAMES, IUP

from .common import db, Field
from pydal.validators import *
from .common import db, Field, auth


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
                Field('image_ref', 'blob'),
                Field('caption', 'text'),
                )

db.define_table('stream',
                Field('created_by', 'reference auth_user'),
                Field('name', 'string'),
                Field('nn_id', 'string'),
                )

db.define_table('post_stream_mapping',
                Field('post_id', 'reference post'),
                Field('stream_id', 'reference stream'),
                )

db.commit()


def add_users_for_testing(num_users):
    # Test user names begin with "_".
    # Counts how many users we need to add.
    db(db.auth_user.username.startswith("_")).delete()
    num_test_users = db(db.auth_user.username.startswith("_")).count()
    num_new_users = num_users - num_test_users
    print("Adding", num_new_users, "users.")
    for k in range(num_test_users, num_users):
        first_name = random.choice(FIRST_NAMES)
        last_name = first_name = random.choice(LAST_NAMES)
        username = "_%s%.2i" % (first_name.lower(), k)
        user = dict(
            username=username,
            email=username + "@ucsc.edu",
            first_name=first_name,
            last_name=last_name,
            password=username,  # To facilitate testing.
        )
        auth.register(user, send=False)
    db.commit()


def add_streams_for_testing():

    cb = random.choice(
        db(db.auth_user.username.startswith("_")).select()).id
    s = dict(
        created_by=cb,
        name="Banana",
        nn_id="1234",
    )
    cb = random.choice(
        db(db.auth_user.username.startswith("_")).select()).id
    db.stream.insert(**s)
    s = dict(
        created_by=cb,
        name="Apple",
        nn_id="12345",
    )
    db.stream.insert(**s)

    db.commit()


def add_posts_for_testing(num_posts=15):
    # Test post names begin with "_".
    # Counts how many posts we need to add.
    db(db.post.caption.startswith("_")).delete()
    num_test_posts = db(db.post.caption.startswith("_")).count()
    num_new_posts = num_posts - num_test_posts
    print("Adding", num_new_posts, "posts.")
    banana_image = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Banana-Single.jpg/2324px-Banana-Single.jpg"
    for k in range(num_test_posts, num_posts):

        caption = random.choice(f"test caption {k}")
        created_b = random.choice(
            db(db.auth_user.username.startswith("_")).select().as_list())['id']
        post = dict(
            caption=caption,
            created_by=created_b,
            image_ref=banana_image,
        )
        p = db.post.insert(**post)

        # Add post to a random stream
        stream = random.choice(db(db.stream).select())
        db.post_stream_mapping.insert(
            post_id=p, stream_id=stream['id'])

    db.commit()


add_users_for_testing(5)
add_streams_for_testing()
add_posts_for_testing()
