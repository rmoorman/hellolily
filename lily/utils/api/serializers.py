import re
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from lily.tags.models import Tag

from ..models.models import Address, EmailAddress, PhoneNumber


# TODO: Once we start our refactor sprint we should probably delete this serializer
class RelatedModelSerializer(serializers.ModelSerializer):

    def __init__(self, instance=None, data=empty, **kwargs):
        self.related_object = kwargs.pop('related_object', None)
        super(RelatedModelSerializer, self).__init__(instance, data, **kwargs)

    def create(self, validated_data):
        ModelClass = self.Meta.model
        instance = ModelClass.objects.create(**validated_data)
        return instance


class RelatedFieldSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        obj = super(RelatedFieldSerializer, self).to_internal_value(data)

        is_deleted = data.get('is_deleted', False)

        if 'id' not in data and is_deleted:
            # New object but removed, don't do anything
            return {}
        else:
            obj.update({
                'is_deleted': data.get('is_deleted', False)
            })

        return obj


class TagFieldSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        obj = super(TagFieldSerializer, self).to_internal_value(data)
        obj = dict(data)

        return obj


class PhoneNumberSerializer(RelatedFieldSerializer):
    id = serializers.IntegerField(required=False)
    status_name = serializers.CharField(source='get_status_display', read_only=True)
    number = serializers.CharField(read_only=True)

    def validate_raw_input(self, value):
        phone_number = value

        if phone_number:
            phone_number = re.sub('[\+\(\)]', '', phone_number)

            if not phone_number.isdigit():
                raise ValidationError('Phone number may not contain any letters.')
        else:
            raise ValidationError('Phone number must be filled in.')

        return value

    class Meta:
        model = PhoneNumber
        fields = ('id', 'status_name', 'number', 'raw_input', 'type', 'other_type', 'status',)


class AddressSerializer(RelatedFieldSerializer):
    id = serializers.IntegerField(required=False)
    street = serializers.CharField(required=True)
    street_number = serializers.IntegerField(required=True, error_messages={'invalid': 'Please enter a number.'})

    class Meta:
        model = Address
        fields = (
            'id',
            'street',
            'street_number',
            'complement',
            'postal_code',
            'city',
            'state_province',
            'country',
            'type',
        )


class EmailAddressSerializer(RelatedFieldSerializer):
    id = serializers.IntegerField(required=False)
    status_name = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = EmailAddress
        fields = ('id', 'status_name', 'email_address', 'status',)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name',)
