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
import pathlib
import requests
import zipfile
import tempfile
import ombott

from py4web import action, request, abort, redirect, URL, HTTP
from yatl.helpers import A

from . import settings
from .common import db, session, T, cache, auth, logger, authenticated, unauthenticated, flash, model
import os
import tempfile
import shutil
import tensorflow as tf


import datetime
import os
import traceback
import uuid
from nqgcs import NQGCS
from .models import get_user_email
from .settings import APP_FOLDER, bucket, GCS_KEY_PATH, GCS_KEYS
from .gcs_url import gcs_url

@action("index")
@action.uses("index.html", auth)
def index():
    user = auth.get_user()
    message = T("Hello {first_name}".format(**user) if user else "Hello")
    actions = {"allowed_actions": auth.param.allowed_actions}

    # get all streams
    streams = db(db.stream).select()
    return dict(message=message, actions=actions, streams=streams)

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


@action('file_info')
@action.uses(db)
def file_info():
    row = db(db.post.created_by == db.auth_user.id).select().first()
    if row is None:
        row = {}
    file_path = row.get('file_path')
    two_weeks = 3600 * 24 * 7 * 2
    return dict(
        file_path=file_path,
        download_url=None if file_path is None else gcs_url(GCS_KEYS, file_path, expiration_secs=two_weeks),
        # These two could be controlled to get other things done.
        upload_enabled=True,
        download_enabled=True,
    )


@action('obtain_gcs', method="POST")
@action.uses(db, session)
def obtain_gcs():
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
    db.post.insert(
        created_by=auth.current_user.get("id"),
        created_at=datetime.datetime.now(),
        file_path=file_path,
        confirmed=False,
    )


@action('stream/<stream_id:int>/notify_upload', method="POST")
@action.uses(db, session)
def notify_upload(stream_id=None):
    file_path = request.json.get("file_path")
    download_url=gcs_url(GCS_KEYS, file_path, verb='GET')
    db.post.update_or_insert(
        ((db.post.created_by == auth.current_user.get("id")) &
         (db.post.file_path == file_path)),
        created_by=auth.current_user.get("id"),
        created_at=datetime.datetime.now(),
        file_path=file_path,
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
    )


@action('stream/<stream_id:int>/post')
@action.uses('post.html', auth.user, db)
def post_image(stream_id):
    return dict(stream_id=stream_id)


@action('stream/<stream_id:int>/classify', method='POST')
@action.uses(auth.user, db)
def classify(stream_id):
    post = request.files.get("image")
    stream = db.stream[stream_id]
    weights_file = str(pathlib.Path("apps", settings.APP_NAME, "weights", f"{stream.name}.h5"))
    model.load_weights(weights_file)

    path = pathlib.Path("apps", settings.APP_NAME, "posts", post.filename)
    post.save(str(path), overwrite=True)

    image = tf.io.read_file(str(path))
    image = tf.image.decode_image(image, channels=3)

    image = tf.image.resize(image, [224, 224])
    image = tf.expand_dims(image, 0)

    confidence = model(image).numpy().item()
    return dict(result="Accepted" if confidence > .9 else "Rejected")


@action('create_stream', method='GET')
@action.uses('create_stream.html', auth.user)
def create_stream():
    return dict()


@action('create_stream', method='POST')
@action.uses(db, session, auth.user)
def create_stream_post():
    stream_name = request.POST.get('streamName')
    file = request.files.get('file')

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
        nn_id=nn_id
    )

    train_dir = tempfile.mkdtemp()

    import zipfile
    zipfile.ZipFile(file.file, mode='r').extractall(train_dir)

    train_ds = tf.keras.utils.image_dataset_from_directory(
        train_dir,
        class_names=["no", "yes"],
        label_mode="binary",
        validation_split=0.2,
        subset="training",
        seed=123,
        image_size=(224, 224),
        batch_size=32
    )

    val_ds = tf.keras.utils.image_dataset_from_directory(
        train_dir,
        class_names=["no", "yes"],
        label_mode="binary",
        validation_split=0.2,
        subset="validation",
        seed=123,
        image_size=(224, 224),
        batch_size=32
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.1),
        loss=tf.keras.losses.BinaryCrossentropy(),
        metrics=['accuracy']
    )
    model.fit(train_ds, epochs=1, validation_data=val_ds)

    weights_file = str(pathlib.Path("apps", settings.APP_NAME, "weights", f"{stream_name}.h5"))
    model.save_weights(weights_file)

    shutil.rmtree(train_dir)

    return dict(stream_id=stream_id)


def download_images(urls):
    output_directory = tempfile.mkdtemp()
    for i, url in enumerate(urls):
        response = requests.get(url)

        if response.status_code == 200:
            filename = f"image_{i}.jpg"
            filepath = pathlib.Path(output_directory, filename)

            with open(filepath, "wb") as file:
                file.write(response.content)
        else:
            print(f"Failed to download {url}")
    return output_directory


def compress_directory(directory):
    _, zipfile_name = tempfile.mkstemp(suffix=".zip")
    with zipfile.ZipFile(zipfile_name, "w") as zip_file:
        for folder_name, _, filenames in os.walk(directory):
            for filename in filenames:
                file_path = pathlib.Path(folder_name, filename)
                zip_file.write(file_path, filename)
    return zipfile_name


@action("zip_posts", method="POST")
@action.uses(db)
def create_posts_zip():
    posts = json.loads(request.forms.get("posts", "[]"))
    urls = [gcs_url(GCS_KEYS, post) for post in posts]

    dl_f = download_images(urls)
    zf = compress_directory(dl_f)

    zf_path = pathlib.Path(zf)

    return ombott.static_file(
        str(zf_path.relative_to(tempfile.gettempdir())),
        root=tempfile.gettempdir(),
        mimetype="application/zip",
        download=True
    )
