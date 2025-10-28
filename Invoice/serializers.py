from .models import xx_Invoice
from rest_framework import serializers



class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = xx_Invoice
        fields = ['Invoice_ID', 'Invoice_Number', 'Invoice_Data', 'uploaded_by', 'base64_file', 'file_name','status']


    def create(self, validated_data):
        return xx_Invoice.objects.create(**validated_data)