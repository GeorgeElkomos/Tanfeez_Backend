from django.db import models

# Create your models here.
class MainCurrency(models.Model):
    """Model representing main currencies with icons"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=255, null=True, blank=True, help_text='Icon URL or class name for the currency')
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Main Currency'
        verbose_name_plural = 'Main Currencies'
        db_table = 'MAIN_CURRENCY'


class MainRoutesName(models.Model):
    """Model representing main route names in English and Arabic"""
    id = models.AutoField(primary_key=True)
    english_name = models.CharField(max_length=255)
    arabic_name = models.CharField(max_length=255)
    
    def __str__(self):
        return f"{self.english_name} - {self.arabic_name}"
    
    class Meta:
        verbose_name = 'Main Route Name'
        verbose_name_plural = 'Main Routes Names'
        db_table = 'MAIN_ROUTES_NAME'
