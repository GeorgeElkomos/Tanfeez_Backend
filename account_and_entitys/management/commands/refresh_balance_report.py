"""
Django management command to refresh balance report data
"""
from django.core.management.base import BaseCommand, CommandError
from account_and_entitys.utils import refresh_balance_report_data


class Command(BaseCommand):
    help = 'Download balance report from Oracle and load into XX_BalanceReport table'

    def add_arguments(self, parser):
        parser.add_argument(
            '--budget-name',
            type=str,
            default='MIC_HQ_MONTHLY',
            help='Control budget name for the report (default: MIC_HQ_MONTHLY)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )

    def handle(self, *args, **options):
        budget_name = options['budget_name']
        verbose = options['verbose']
        
        if verbose:
            self.stdout.write(
                self.style.SUCCESS(f'Starting balance report refresh for: {budget_name}')
            )
        
        try:
            result = refresh_balance_report_data(budget_name)
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ {result["message"]}')
                )
                
                if verbose and 'details' in result:
                    details = result['details']
                    self.stdout.write(f"📊 Created: {details.get('created_count', 0)} records")
                    self.stdout.write(f"🗑️  Deleted: {details.get('deleted_count', 0)} old records")
                    if details.get('error_count', 0) > 0:
                        self.stdout.write(
                            self.style.WARNING(f"⚠️  Errors: {details['error_count']} rows skipped")
                        )
                        
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ {result["message"]}')
                )
                raise CommandError(f'Failed to refresh balance report: {result["message"]}')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Unexpected error: {str(e)}')
            )
            raise CommandError(f'Command failed: {str(e)}')
