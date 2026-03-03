from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """
    Used for profile viewing and the 'Me' endpoint.
    Includes role-based logic for the Redux frontend.
    """
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    # Exposing the @property you created in the model
    is_teacher = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 
            'last_name', 'role', 'role_display', 
            'is_teacher', 'bio', 'date_joined'
        ]
        # Professional standard: Prevent role escalation via general profile updates
        read_only_fields = ['role', 'username', 'date_joined']

class RegisterSerializer(serializers.ModelSerializer):
    """
    Specifically for creating new accounts. 
    Handles secure password hashing.
    """
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'role', 'bio']

    def create(self, validated_data):
        # Professional Standard: Use create_user to hash the password
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=validated_data.get('role', User.Role.STUDENT),
            bio=validated_data.get('bio', '')
        )
        return user

