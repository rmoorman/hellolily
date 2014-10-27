from django.db import models
from lily.users.models import CustomUser


class GmailAccount(models.Model):
    user = models.ForeignKey(CustomUser)
    is_authorized = models.BooleanField(default=False)
    history_id = models.BigIntegerField(null=True)


class GmailLabel(models.Model):
    account = models.ForeignKey(GmailAccount, related_name='labels')
    type = models.CharField(max_length=10)
    label_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)


class GmailMessage(models.Model):
    account = models.ForeignKey(GmailAccount, related_name='messages')
    labels = models.ManyToManyField(GmailLabel, related_name='messages')
    message_id = models.CharField(max_length=50)
    thread_id = models.CharField(max_length=50)
    sent_date = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    subject = models.CharField(max_length=255, null=True)
    snippet = models.CharField(max_length=255, null=True)
    body_html = models.TextField(null=True)
    body_text = models.TextField(null=True)

    class Meta:
        unique_together = ('account', 'message_id')


class GmailHeader(models.Model):
    message = models.ForeignKey(GmailMessage, related_name='headers')
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=1000)


