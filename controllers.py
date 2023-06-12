"""
This file defines actions, i.e. functions the URLs are mapped into
The @action(path) decorator exposed the function at URL:

    http://127.0.0.1:8000/{app_name}/{path}

If app_name == '_default' then simply

    http://127.0.0.1:8000/{path}

If path == 'index' it can be omitted:

    http://127.0.0.1:8000/

The path follows the bottlepy syntax.

@action.uses('generic.html')  indicates that the action uses the generic.html template
@action.uses(session)         indicates that the action uses the session
@action.uses(db)              indicates that the action uses the db
@action.uses(T)               indicates that the action uses the i18n & pluralization
@action.uses(auth.user)       indicates that the action requires a logged in user
@action.uses(auth)            indicates that the action requires the auth object

session, db, T, auth, and templates are examples of Fixtures.
Warning: Fixtures MUST be declared with @action.uses({fixtures}) else your app will result in undefined behavior
"""
import json

from py4web import action, request, abort, redirect, URL
from yatl.helpers import A
from .common import db, session, T, cache, auth, logger, authenticated, unauthenticated, flash

import datetime
import os 
import traceback 
import uuid 
from nqgcs import NQGCS 
from .models import get_user_email 
from .settings import APP_FOLDER 
from .gcs_url import gcs_url

bucket = "/beefystew-cse-183"
GCS_KEY_PATH = os.path.join(APP_FOLDER, 'private/gcs_keys.json')
with open(GCS_KEY_PATH) as gcs_key_f:
    GCS_KEYS = json.load(gcs_key_f)

gcs = NQGCS(json_key_path=GCS_KEY_PATH)


@action("index")
@action.uses("index.html", auth)
def index():
    user = auth.get_user()
    message = T("Hello {first_name}".format(**user) if user else "Hello")
    actions = {"allowed_actions": auth.param.allowed_actions}

    # get all streams
    streams = db(db.stream).select()
    return dict(message=message, actions=actions, streams=streams)


# @action("stream/<stream_id:int>")
# @action.uses("s.html", auth, T)
# def stream(stream_id=None):
#     assert stream_id is not None
#     posts = db(db.post_stream_mapping.stream_id == stream_id).select(
#         db.post.ALL, db.auth_user.ALL,
#         join=[
#             db.post.on(db.post.id == db.post_stream_mapping.post_id),
#             db.auth_user.on(db.post.created_by == db.auth_user.id)
#         ]
#     ).as_list()

#     return dict(stream=db.stream[stream_id], posts=json.dumps(posts))


@action('stream/<stream_id:int>/posts')
def get_stream_posts(stream_id=None):
    assert stream_id is not None
    stream = db.stream[stream_id]
    assert stream is not None
    posts = db(db.post_stream_mapping.stream_id == stream_id).select(
        db.post.ALL, db.auth_user.ALL,
        join=[
            db.post.on(db.post.id == db.post_stream_mapping.post_id),
            db.auth_user.on(db.post.created_by == db.auth_user.id)
        ],
        orderby=~db.post.created_at
    ).as_list()
    for post in posts:
        post['post']['image_ref'] = gcs_url(GCS_KEYS, post['post']['file_path'])
    return posts


@action("stream/<stream_id:int>")
@action.uses("s.html", auth, T)
def stream(stream_id = None):
    print('\nloading s.html\n')
    assert stream_id is not None, "stream: stream_id is None"
    stream = db.stream[stream_id]
    assert stream is not None, "stream: stream is None object"
    posts = db(db.post_stream_mapping.stream_id == stream_id).select(
        db.post.ALL, db.auth_user.ALL,
        join=[
            db.post.on(db.post.id == db.post_stream_mapping.post_id),
            db.auth_user.on(db.post.created_by == db.auth_user.id)
        ]
    ).as_list()
    return dict(
        stream = stream,
        file_info_url = URL('file_info'),
        obtain_gcs_url = URL('obtain_gcs'),
        notify_url = URL('stream', stream_id, 'notify_upload'),
        delete_url = URL('notify_delete'),
        posts = posts
        )

# upload happens as a form 
# submitting form goes to url that checks whether image is accepted by stream
# if yes, create post entry in database after uploading to gcs
# create post stream mapping to associate post with stream

@action('file_info')
@action.uses(db)
def file_info():
    print("\nFILE_INFO\n")
    row = db(db.post.created_by == db.auth_user.id).select().first()
    print(row)
    # if row is not None and not row.confirmed:
    #     # delete_path(row.file_path)
    #     row.delete_record() 
    #     row = {}
    if row is None:
        row = {}
    file_path = row.get('file_path')
    two_weeks = 3600 * 24 * 7 * 2
    return dict(
        file_name=row.get('file_name'),
        file_type=row.get('file_type'),
        file_date=row.get('file_date'),
        file_size=row.get('file_size'),
        file_path=file_path,
        download_url=None if file_path is None else gcs_url(GCS_KEYS, file_path, expiration_secs=two_weeks),
        # These two could be controlled to get other things done.
        upload_enabled=True,
        download_enabled=True,
    )


@action('stream/<stream_id:int>/post', method='POST')
def post_to_stream(stream_id):
    pass

@action('obtain_gcs', method="POST")
@action.uses(db, session)
def obtain_gcs():
    print("\nOBTAIN_GCS\n")
    verb = request.json.get("action")
    if verb == "PUT":
        mimetype = request.json.get("mimetype", "")
        file_name = request.json.get("file_name")
        extension = os.path.splitext(file_name)[1]
        file_path = bucket + "/" + str(uuid.uuid1()) + extension 
        mark_possible_upload(file_path) ## 
        upload_url = gcs_url(GCS_KEYS, file_path, verb='PUT',
                             content_type=mimetype)
        return dict(signed_url=upload_url, file_path=file_path)
    elif verb in ["GET", "DELETE"]:
        file_path = request.json.get("file_path")
        if file_path is not None:
            r = db(db.post.file_path == file_path).select().first()
            if r is not None and r.created_by == auth.current_user.get("id"):
                signed_url = gcs_url(GCS_KEYS, file_path, verb=verb)
                return dict(signed_url=signed_url)
        return dict(signer_url=None)
    

def mark_possible_upload(file_path):
    # delete_previous_uploads()

    db.post.insert(
        created_by=auth.current_user.get("id"),
        created_at=datetime.datetime.now(),
        file_path=file_path,
        confirmed=False,
    )

@action('stream/<stream_id:int>/notify_upload', method="POST")
@action.uses(db, session)
def notify_upload(stream_id=None):
    print("\nNOTIFY_UPLOAD\n")
    file_type = request.json.get("file_type")
    file_name = request.json.get("file_name")
    file_path = request.json.get("file_path")
    file_size = request.json.get("file_size")
    # Deletes any previous file.
    # rows = db(db.post.created_by == db.auth_user.id).select()
    # for r in rows:
    #     if r.file_path != file_path:
    #         delete_path(r.file_path)
    # Marks the upload as confirmed.
    d = datetime.datetime.utcnow()
    download_url=gcs_url(GCS_KEYS, file_path, verb='GET')
    db.post.update_or_insert(
        ((db.post.created_by == auth.current_user.get("id")) &
         (db.post.file_path == file_path)),
        created_by=auth.current_user.get("id"),
        created_at=datetime.datetime.now(),
        file_path=file_path,
        file_name=file_name,
        file_type=file_type,
        file_date=d,
        file_size=file_size,
        confirmed=True,
        image_ref=download_url
    )
    db.post_stream_mapping.insert(
        post_id=db(db.post.file_path == file_path).select().first().id,
        stream_id=stream_id,
    )
    # Returns the file information.
    return dict(
        download_url=download_url,
        file_date=d,
    )


# def delete_path(file_path):
#     print("\nDELETE_PATH\n")
#     try: 
#         bucket, id = os.path.split(file_path)
#         gcs.delete(bucket[1:], id)
#     except: 
#         pass



######################
@action('create_stream', method='GET')
@action.uses('create_stream.html', auth.user)
def create_stream():
    return dict()


@action('create_stream', method='POST')
@action.uses(db, session, auth.user)
def create_stream_post():
    print("THIS IS CREATING STREAM")
    stream_name = request.POST.get('streamName')
    file = request.files.get('file')
    custom_question = request.POST.get('customQuestion')
    user = auth.get_user()

    existing_stream = db(db.stream.name == stream_name).select().first()
    if existing_stream:
        return {'error': 'Stream name already exists'}

    nn_id = db.neural_network.insert(
        created_by=user.get('id'),
    )

    stream_id = db.stream.insert(
        created_by=auth.current_user.get('id'),
        name=stream_name,
        custom_question=custom_question,
        nn_id=nn_id
    )

    # Use file data to train stream

    return dict(stream_id=stream_id)
