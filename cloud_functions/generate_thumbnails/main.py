import re
from wand.image import Image
from google.cloud import storage

client = storage.Client()

def generate_thumbnails(data, context):
  thumbnail_regex = "^photos\/isolation\/thumbnails\/.*\.(jpg|jpeg)$"
  image_regex = "^photos\/isolation\/.*\.(jpg|jpeg)$"

  # Only generate thumbnails for matching paths
  is_image = re.search(image_regex, data['name']) 
  is_thumbnail = re.search(thumbnail_regex, data['name']) 

  if (is_image and not is_thumbnail):
    # Download the image and resize it
    bucket = client.get_bucket(data['bucket'])
    thumbnail = Image(blob=bucket.get_blob(data['name']).download_as_string())
    thumbnail.transform(resize='x200')

    # Upload the thumbnail with modified name
    path = data['name'].rsplit('.', 1)
    blob_name = path[0] + ".thumb." + path[1]
    thumbnail_blob = bucket.blob(blob_name)
    thumbnail_blob.upload_from_string(thumbnail.make_blob())
    