from rest_framework import serializers

from ..models import LilyGroup, LilyUser


class UserInGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = LilyUser
        fields = (
            'id',
            'full_name',
            'first_name',
            'last_name',
            'preposition',
        )


class LilyGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for the contact model.
    """
    user_set = UserInGroupSerializer(many=True, read_only=True)

    class Meta:
        model = LilyGroup
        fields = (
            'id',
            'name',
            'user_set',
        )


class LilyUserSerializer(serializers.ModelSerializer):
    """
    Serializer for the LilyUser model.
    """
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = LilyUser
        fields = (
            'id',
            'first_name',
            'preposition',
            'last_name',
            'full_name',
            'primary_email_account',
        )


class LilyUserTokenSerializer(serializers.ModelSerializer):
    """
    Serializer for the LilyUser model.

    Only returns the user token
    """
    auth_token = serializers.CharField(read_only=True)

    class Meta:
        model = LilyUser
        fields = ('auth_token',)
