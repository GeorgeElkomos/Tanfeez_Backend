from decimal import Decimal
from rest_framework import serializers

from account_and_entitys.models import XX_ACCOUNT_ENTITY_LIMIT
from .models import xx_TransactionTransfer

class AdjdTransactionTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = xx_TransactionTransfer
        fields = '__all__'

    
   

    