from django.conf.urls import patterns, url

from lily.google.views import SetupEmailAuth, OAuth2Callback

urlpatterns = patterns(
    '',
    url(r'^setup/$', SetupEmailAuth.as_view(), name='google_setup'),
    url(r'^oauth2callback/$', OAuth2Callback.as_view(), name='google_oauth2callback'),
)
