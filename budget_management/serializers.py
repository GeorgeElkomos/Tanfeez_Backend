from rest_framework import serializers
from .models import xx_BudgetTransfer

class BudgetTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = xx_BudgetTransfer
        fields = '__all__'
        # Make certain fields optional or read-only
        extra_kwargs = {
            'amount': {'required': False},  # Make amount optional during creation
            'status': {'read_only': True},  # Set by the server, not client
            'requested_by': {'read_only': True},  # Set from the authenticated user
            'user_id': {'read_only': True},  # Set from the authenticated user
            # Other fields that should be read-only
        }
    
    def create(self, validated_data):
        # Set a default value for amount if not provided
        if 'amount' not in validated_data:
            validated_data['amount'] = 0  # Default value, will be updated later
        return super().create(validated_data)


