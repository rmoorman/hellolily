import base64
import email
from django.conf import settings
import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client import xsrfutil
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.django_orm import Storage

from lily.google.models import CredentialsModel


FLOW = OAuth2WebServerFlow(
    client_id=settings.GA_CLIENT_ID,
    client_secret=settings.GA_CLIENT_SECRET,
    redirect_uri='http://localhost:8000/gmailapi/oauth2callback/',
    scope='https://mail.google.com/',
    user_agent='my-sample/1.0',
)


def get_credentials(user):
    storage = Storage(CredentialsModel, 'id', user, 'credential')
    credential = storage.get()
    if credential is not None and credential.invalid is False:
        return credential
    else:
        #TODO: flag that user has invalid credential
        return None


def get_credentials_link(user):
    storage = Storage(CredentialsModel, 'id', user, 'credential')
    credential = storage.get()
    if credential is None or credential.invalid is True:
        # No valid credential for user, need to ask for one
        FLOW.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY, user)
        authorize_url = FLOW.step1_get_authorize_url()
        return authorize_url
    else:
        return None
