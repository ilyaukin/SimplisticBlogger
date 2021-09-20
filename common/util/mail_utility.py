import traceback
from os import environ
from flask_mail import Message
from common import mail

# Here mail templates are defined, each template is rendered
# using a dict which contains it's own params
NEW_COMMENT = \
    "<h4> Hello,%(name)s! There has been a new comment to your post " + \
    "<i>%(title)s</i>.</h4><br/><div style='width: 30%%;display: flex;flex-direction: " \
    "column;border: 1px red solid;'><div><p>Comment: %(comment)s</p>" + \
    "<p>Author: %(commenter_name)s</p></div></div>"
COMMENT_REPLY = \
    "<h4> Hello,%(name)s! There has been a reply to your comment to " + \
    "<i>%(title)s</i>.</h4><br/><div style='width: 30%%;display: flex;flex-direction: " \
    "column;border: 1px red solid;'><div><p>Comment: %(comment)s</p>" + \
    "<p>Author: %(commenter_name)s</p></div></div>"


def sendmail(recipient, template, params):
    try:
        msg = Message(
            'New message from Blog',
            sender=environ.get("MAIL_USERNAME"),
            recipients=[recipient],
        )
        msg.html = template % params
        mail.send(msg)
        return True
    except (UnicodeError, TypeError, AttributeError):
        traceback.print_exc()
        return False
