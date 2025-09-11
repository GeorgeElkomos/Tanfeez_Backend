
from rest_framework import serializers
from .models import   MainCurrency, MainRoutesName

class MainCurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = MainCurrency
        fields = '__all__'


class MainRoutesNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainRoutesName
        fields = '__all__'