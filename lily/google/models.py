from django.db import models
from oauth2client.django_orm import FlowField, CredentialsField
from south.modelsinspector import add_introspection_rules
from lily.users.models import CustomUser


class FlowModel(models.Model):
    id = models.ForeignKey(CustomUser, primary_key=True)
    flow = FlowField()


class CredentialsModel(models.Model):
    id = models.ForeignKey(CustomUser, primary_key=True)
    credential = CredentialsField()

add_introspection_rules([], ["^oauth2client\.django_orm\.FlowField"])
add_introspection_rules([], ["^oauth2client\.django_orm\.CredentialsField"])
