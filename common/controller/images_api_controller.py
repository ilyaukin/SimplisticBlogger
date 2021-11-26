import datetime
import os
import traceback

from flask import (Blueprint, request)
from flask_login import login_required
from sqlalchemy import exc
from werkzeug.utils import secure_filename

from common import db
from common.models.images_model import Images

image_bp = Blueprint("image_api", __name__)

# Relative path so implying cwd == root of the app
PATH = "static/upload"
if not os.path.exists(PATH):
    os.symlink(os.environ.get('UPLOAD_FOLDER'), PATH)


@image_bp.route("/image_upload", methods=["POST"])
@login_required
def upload_image():
    file = request.files["image"]

    try:
        filename = _make_unique_filename(file)
        file_path = os.path.join(PATH, filename)
        file.save(file_path)
        return _get_image_url(file_path)
    except Exception:
        traceback.print_exc()
        return "Internal Error, check logs", 500


@image_bp.route("/image_delete", methods=["POST"])
@login_required
def delete_image():
    try:
        payload = request.get_json()
        filename = payload["image_file"].split("/")[-1]

        # file location removal
        file_path = os.path.join(PATH, filename)
        os.remove(file_path)

        image = Images.query.filter_by(image_url=_get_image_url(file_path))\
            .first()
        if image:
            # Remove from database
            # database
            db.session.delete(image)
            db.session.commit()

        return "Successfully removed the image file"

    except (FileNotFoundError, exc.SQLAlchemyError):
        traceback.print_exc()
        return "File cannot be delete, check logs !!!", 500


def _make_unique_filename(file):
    file_name = secure_filename(file.filename)
    try:
        i = file_name.rindex('.')
        file_ext = file_name[i:]  # with '.'
        file_name = file_name[:i]
    except ValueError:
        file_ext = '.' + file.content_type.split('/')[
            -1]  # process 'image/jpeg' etc...

    path = os.path.join(PATH, file_name + file_ext)
    if not os.path.exists(path):
        return file_name + file_ext
    for i in range(100):
        file_name_mod = file_name + "-" + \
                        datetime.datetime.now().strftime('%Y%m%d%H%M%S%f') \
                        + '_' + str(i)
        path = os.path.join(PATH, file_name_mod + file_ext)
        if not os.path.exists(path):
            return file_name_mod + file_ext
    raise Exception("Desperately failed to make a unique file name")


def _get_image_url(file_path):
    return "/" + file_path
