from rest_framework import serializers
from .models import XX_Account, XX_Entity, XX_PivotFund, XX_TransactionAudit, XX_ACCOUNT_ENTITY_LIMIT, XX_Project

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = XX_Account
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = XX_Project
        fields = "__all__"


class EntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = XX_Entity
        fields = '__all__'

class PivotFundSerializer(serializers.ModelSerializer):
    class Meta:
        model = XX_PivotFund
        fields = '__all__'

class TransactionAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = XX_TransactionAudit
        fields = '__all__'

class AccountEntityLimitSerializer(serializers.ModelSerializer):
    class Meta:
        model = XX_ACCOUNT_ENTITY_LIMIT
        fields = '__all__'
