from rest_framework import serializers

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate_email(self, value):
        return value.lower()

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True, min_length=12)
    confirm_password = serializers.CharField(required=True, write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate_email(self, value):
        return value.lower()

    def validate(self, data):
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Passwords must match."})
        return data

class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=True)

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        return value.lower()

class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True, min_length=12)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Passwords must match."})
        return data

class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)

class MFASerializer(serializers.Serializer):
    otp = serializers.CharField(required=True, min_length=6, max_length=6)
    
    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP must contain only numbers.")
        return value
