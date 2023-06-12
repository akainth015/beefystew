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

from py4web import action, request, abort, redirect, URL, HTTP
from yatl.helpers import A

from . import settings
from .common import db, session, T, cache, auth, logger, authenticated, unauthenticated, flash, model
import subprocess
import tempfile
import shutil
import tensorflow as tf


@action("index")
@action.uses("index.html", auth)
def index():
    user = auth.get_user()
    message = T("Hello {first_name}".format(**user) if user else "Hello")
    actions = {"allowed_actions": auth.param.allowed_actions}

    # get all streams
    streams = db(db.stream).select()
    return dict(message=message, actions=actions, streams=streams)


@action("stream/<stream_id:int>")
@action.uses("s.html", auth, T)
def stream(stream_id=None):
    assert stream_id is not None
    posts = db(db.post_stream_mapping.stream_id == stream_id).select(
        db.post.ALL, db.auth_user.ALL,
        join=[
            db.post.on(db.post.id == db.post_stream_mapping.post_id),
            db.auth_user.on(db.post.created_by == db.auth_user.id)
        ]
    ).as_list()

    return dict(stream=db.stream[stream_id], posts=json.dumps(posts))


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
