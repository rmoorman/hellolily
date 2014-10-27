import logging
from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.utils.translation import ugettext as _
from django.views.generic import View
from oauth2client import xsrfutil
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.django_orm import Storage

from lily.google.models import CredentialsModel
from lily.utils.views import LoginRequiredMixin


log = logging.getLogger('django.request')

FLOW = OAuth2WebServerFlow(
    client_id=settings.GA_CLIENT_ID,
    client_secret=settings.GA_CLIENT_SECRET,
    redirect_uri='http://localhost:8000/gmailapi/oauth2callback/',
    scope='https://mail.google.com/',
    user_agent='my-sample/1.0',
)


def set_credentials(request, success_url):
    storage = Storage(CredentialsModel, 'id', request.user, 'credential')
    credential = storage.get()
    if credential is None or credential.invalid is True:
        # No valid credential for user, need to ask for one
        FLOW.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY, request.user)
        authorize_url = FLOW.step1_get_authorize_url()
        return HttpResponseRedirect(authorize_url)
    else:
        messages.info(request, _("You're authorized"), _('Gmail integration is working (again)!'))
        return HttpResponseRedirect(success_url)


class SetupEmailAuth(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return set_credentials(request, reverse('dashboard'))


class OAuth2Callback(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        if not xsrfutil.validate_token(settings.SECRET_KEY, request.GET.get('state'), request.user):
            return HttpResponseBadRequest()
        credential = FLOW.step2_exchange(code=request.GET.get('code'))
        storage = Storage(CredentialsModel, 'id', request.user, 'credential')
        storage.put(credential)
        return HttpResponseRedirect('/')
