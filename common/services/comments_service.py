import datetime
import os
import traceback
import uuid

from libgravatar import Gravatar
from sqlalchemy import exc

from common import db
from common.models import comments_model
from common.services.comment_state_enums import States
from common.util import mail_utility
from common.util.mail_utility import sendmail


class CommentService():
    def __init__(self):
        pass

    @classmethod
    def serialize_comments(cls, comments_db_obj, is_admin=False):
        comments_list = list()
        for comment_db_obj in comments_db_obj:
            if is_admin:
                comments_list.append({
                    "author_name": comment_db_obj.author_name,
                    "author_email": comment_db_obj.author_email,
                    "comment_ref_id": comment_db_obj.comment_uuid,
                    "content": comment_db_obj.author_comment,
                    "posted_date": comment_db_obj.posted_date.strftime(
                        '%B %d, %Y'),
                    "post_link": "http://" + os.environ.get(
                        "FLASK_HOST") + ":" + os.environ.get(
                        "FLASK_BLOG_PORT") + "/blog/" +
                                 comment_db_obj.posts.title
                })
            else:
                comments_list.append({
                    "author_name": comment_db_obj.author_name,
                    "author_email": comment_db_obj.author_email,
                    "comment_ref_id": comment_db_obj.comment_uuid,
                    "content": comment_db_obj.author_comment,
                    "image_url": Gravatar(
                        comment_db_obj.author_email).get_image(
                        default="robohash"),
                    "posted_date": comment_db_obj.posted_date.strftime(
                        '%B %d, %Y'),
                })

        return comments_list

    def add_comment(self, author_name, author_email, author_comment,
                    post_db_obj, is_admin=False):
        try:
            if is_admin:
                comment_state = States.APPROVED.value
            else:
                comment_state = States.UNDER_MODERATION.value

            comment_db_obj = comments_model.Comments(author_name=author_name,
                                                     author_email=author_email,
                                                     author_comment=author_comment,
                                                     comment_uuid=str(
                                                         uuid.uuid4()).split(
                                                         "-")[0],
                                                     posted_date=datetime.datetime.now(),
                                                     comment_state=comment_state,
                                                     post_id=post_db_obj.p_id)
            db.session.add(comment_db_obj)
            db.session.commit()
            return True
        except exc.SQLAlchemyError:
            traceback.print_exc()
            return False

    @classmethod
    def get_comment_count(cls, is_admin=False):
        try:
            if is_admin:
                count = comments_model.Comments.query.filter_by(
                    comment_state=States.UNDER_MODERATION.value).count()
            else:
                count = comments_model.Comments.query.filter_by(
                    comment_state=States.APPROVED.value).count()
            return count
        except exc.SQLAlchemyError:
            traceback.print_exc()
            return 0

    @classmethod
    def get_comments(cls, post_db_obj=None, is_admin=False):
        if not post_db_obj and is_admin:
            comments = comments_model.Comments.query.filter_by(
                comment_state=States.UNDER_MODERATION.value).all()
        elif post_db_obj and is_admin:
            comments = comments_model.Comments.query.filter_by(
                posts=post_db_obj).filter_by(
                comment_state=States.UNDER_MODERATION.value).all()
        elif post_db_obj and not is_admin:
            comments = comments_model.Comments.query.filter_by(
                posts=post_db_obj).filter_by(
                comment_state=States.APPROVED.value).all()

        serialized_comments = cls.serialize_comments(comments, is_admin)
        return serialized_comments

    def get_comment(self):
        pass

    def edit_comment(self, comment_ref_id, comment_status):
        try:
            # If the status is reject delete from db
            comment = comments_model.Comments.query.filter_by(
                comment_uuid=comment_ref_id).first()
            if comment:
                if int(comment_status) == States.REJECTED.value:
                    db.session.delete(comment)
                    db.session.commit()
                    return {"resp": True, "message": "Deleted Comment"}
                elif int(comment_status) == States.APPROVED.value:
                    # Edit the comment to be accept for posting
                    comment.comment_state = States.APPROVED.value
                    db.session.add(comment)
                    db.session.commit()
                    return {"resp": True, "message": "Approved Comment"}
            else:
                return {"resp": False,
                        "message": "Comment does not exist in DB"}
        except (exc.SQLAlchemyError, AttributeError):
            traceback.print_exc()
            return {"resp": False,
                    "message": "Internal System Error has occurred"}

    def delete_comment(self):
        pass

    @classmethod
    def notify_on_new_comment(cls, author_comment, author_name, post):
        """
        notify the admin on new comment submitted
        @param author_comment comment text
        @param author_name commenter name
        @param post post DB object
        @return if notification is successful or not
        """
        return sendmail(os.environ.get('EMAIL'), mail_utility.NEW_COMMENT,
                        {
                            'name': os.environ.get('F_NAME'),
                            'comment': author_comment,
                            'commenter_name': author_name,
                            'title': post.title,
                        })

    @classmethod
    def check_reply(cls, comment, post):
        """
        check if the comment contains replies to
        some other comments (by mentions in format of @name:)
        @param comment comment text
        @param post post DB object
        @return tuple of comment author, comment email of the comments
        referred to.
        """
        refer_names = list()
        words_list = comment.split(" ")
        for word in words_list:
            if len(word) >= 3 and "@" in word[0] and ":" in word[len(word) - 1]:
                refer_names.append(word.replace("@", "").replace(":", ""))
        for name in refer_names:
            comment_data = comments_model.Comments.query.filter(
                comments_model.Comments.author_name.like("%" + name + "%"),
                comments_model.Comments.post_id == post.p_id).first()
            if comment_data.author_name:
                yield comment_data.author_name, comment_data.author_email

    @classmethod
    def notify_on_reply(cls, author_comment, author_name, post):
        for name, email in cls.check_reply(author_comment, post):
            e_status = sendmail(email, mail_utility.COMMENT_REPLY,
                                {
                                    'name': name,
                                    'comment': author_comment,
                                    'commenter_name': author_name,
                                    'title': post.title,
                                })
            if e_status:
                print("The reply email is sent to -- ", email)
                return True
            else:
                print("error while sending the email reply")
                return False
