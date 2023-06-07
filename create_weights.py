import tensorflow as tf
import tensorflow_hub as hub
import tensorflow.keras as keras

import sys

train_dir = sys.argv[1]
stream_name = sys.argv[2]

batch_size = 32
img_height = 224
img_width = 224

train_ds = tf.keras.utils.image_dataset_from_directory(
    train_dir,
    class_names=["no", "yes"],
    label_mode="binary",
    validation_split=0.2,
    subset="training",
    seed=123,
    image_size=(img_height, img_width),
    batch_size=batch_size
)

val_ds = tf.keras.utils.image_dataset_from_directory(
    train_dir,
    class_names=["no", "yes"],
    label_mode="binary",
    validation_split=0.2,
    subset="validation",
    seed=123,
    image_size=(img_height, img_width),
    batch_size=batch_size
)

normalization_layer = tf.keras.Sequential([
    tf.keras.layers.Resizing(img_height, img_width),
    tf.keras.layers.Rescaling(1./255),
])

data_augmentation = tf.keras.Sequential([
    tf.keras.layers.RandomFlip("horizontal_and_vertical"),
    tf.keras.layers.RandomRotation(0.2),
    tf.keras.layers.RandomZoom(0.1),
])

swin_transformers = "https://tfhub.dev/sayakpaul/swin_tiny_patch4_window7_224_fe/1"

feature_extractor_model = swin_transformers

feature_extractor_layer = hub.KerasLayer(
    feature_extractor_model,
    input_shape=(224, 224, 3),
    trainable=False
)

model = tf.keras.Sequential([
    normalization_layer,
    data_augmentation,
    feature_extractor_layer,
    tf.keras.layers.Dropout(0.7),
    tf.keras.layers.Dense(1, activation='sigmoid')
])

model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=0.1),
    loss=keras.losses.BinaryCrossentropy(),
    metrics=['acc']
)

model.fit(
    train_ds,
    epochs=2,
    validation_data=val_ds
)

model.save_weights(f"{stream_name}.h5")
