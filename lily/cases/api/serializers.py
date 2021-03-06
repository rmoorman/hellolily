from rest_framework import serializers

from lily.accounts.api.serializers import AccountSerializer
from lily.api.fields import LilyPrimaryKeyRelatedField
from lily.api.serializers import ContentTypeSerializer
from lily.contacts.api.serializers import ContactSerializer
from lily.users.models import LilyUser

from ..models import Case, CaseStatus


class CasePriorityField(serializers.RelatedField):
    """
    Field that shows the priority name and id.
    """
    def to_representation(self, value):
        return Case.PRIORITY_CHOICES[value]


class CaseSerializer(serializers.ModelSerializer):
    """
    Serializer for the case model
    """
    # Uses account and contact serializers
    account = AccountSerializer(read_only=True)
    contact = ContactSerializer(read_only=True)

    # Show string versions of fields
    type = serializers.StringRelatedField(read_only=True)
    priority = CasePriorityField(read_only=True)
    status = serializers.StringRelatedField(read_only=True)
    assigned_to = LilyPrimaryKeyRelatedField(queryset=LilyUser.objects)
    assigned_to_groups = serializers.StringRelatedField(many=True, read_only=True)
    content_type = ContentTypeSerializer(read_only=True)

    class Meta:
        model = Case
        fields = (
            'id',
            'account',
            'contact',
            'subject',
            'description',
            'type',
            'assigned_to',
            'assigned_to_groups',
            'priority',
            'status',
            'expires',
            'created',
            'is_archived',
            'content_type',
        )


class CaseStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for case status model
    """
    class Meta:
        model = CaseStatus
        fields = (
            'id',
            'status',
        )
