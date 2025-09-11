from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import xx_User as User, xx_UserLevel, xx_notification as Notification
import re
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate_new_password(self, value):
        # Reuse your strong password validation
        array_of_errors=[]
        if len(value) < 8:
            array_of_errors.append("Password must be at least 8 characters long.")
        if not re.search(r'[A-Z]', value):
            array_of_errors.append("Must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', value):
            array_of_errors.append("Must contain at least one lowercase letter.")
        if not re.search(r'[0-9]', value):
            array_of_errors.append("Must contain at least one digit.")
        if not re.search(r'[!@_#$%^&*(),.?":{}|<>]', value):
            array_of_errors.append("Must contain at least one special character.")

        if array_of_errors:
            raise serializers.ValidationError(array_of_errors)

        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        self.validated_data['old_password']
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'role', 'can_transfer_budget']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_password(self, value):
        """
        Enforce strong password:
        - At least 8 characters
        - Contains uppercase, lowercase, digit, and special character
        """
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")

        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")

        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter.")

        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError("Password must contain at least one digit.")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError("Password must contain at least one special character.")

        return value

    def create(self, validated_data):
        validated_data['username'] = validated_data['username'].lower()
        return User.objects.create_user(**validated_data)

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
 
    def validate(self, data):
        data['username'] = data['username'].lower()
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Invalid credentials")

class UserLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = xx_UserLevel
        fields = ['id', 'name', 'description', 'level_order']

class NotificationSerializer(serializers.Serializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'is_read','is_shown','is_system_read', 'created_at']