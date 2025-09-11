from datetime import time
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db.models import Q, Sum, Count, Case, When, Value, F
from django.db.models.functions import Cast, Substr, Upper
from django.db.models import CharField, DecimalField
from user_management.models import xx_notification
from budget_management.models import (
    xx_BudgetTransfer,
    xx_BudgetTransferAttachment,
    xx_BudgetTransferRejectReason,
    xx_DashboardBudgetTransfer,
)
from adjd_transaction.models import xx_TransactionTransfer
import time
import multiprocessing
from collections import defaultdict
from decimal import Decimal




def dashboard_smart(filter_cost_center=None, filter_account_code=None):
    """
    Optimized smart dashboard using database-level aggregations
    
    Args:
        filter_cost_center (int, optional): Filter by specific cost center code
        filter_account_code (int, optional): Filter by specific account code
    
    Returns:
        dict: Dashboard data with optional filters applied
    """
    try:
        start_time = time.time()

        print("Starting optimized smart dashboard calculation...")
        if filter_cost_center or filter_account_code:
            print(f"Filters applied: cost_center={filter_cost_center}, account_code={filter_account_code}")

        # PHASE 1: Database-level aggregations for approved transfers
        aggregation_start = time.time()
        
        # Build base queryset with optimized filtering
        base_queryset = xx_TransactionTransfer.objects.select_related('transaction').filter(
            transaction__status="approved"
        )
        
        # Apply additional filters if provided
        if filter_cost_center:
            base_queryset = base_queryset.filter(cost_center_code=filter_cost_center)
        if filter_account_code:
            base_queryset = base_queryset.filter(account_code=filter_account_code)

        # Aggregate by cost center code (single database query)
        cost_center_totals = list(base_queryset.values('cost_center_code').annotate(
            total_from_center=Sum('from_center'),
            total_to_center=Sum('to_center')
        ).order_by('cost_center_code'))

        # Aggregate by account code (single database query)
        account_code_totals = list(base_queryset.values('account_code').annotate(
            total_from_center=Sum('from_center'),
            total_to_center=Sum('to_center')
        ).order_by('account_code'))

        # Aggregate by combination of cost center and account code (single database query)
        all_combinations = list(base_queryset.values('cost_center_code', 'account_code').annotate(
            total_from_center=Sum('from_center'),
            total_to_center=Sum('to_center')
        ).order_by('cost_center_code', 'account_code'))

        # Get filtered individual records if filters are applied
        if filter_cost_center or filter_account_code:
            filtered_combinations = list(base_queryset.values(
                'cost_center_code', 'account_code', 'from_center', 'to_center'
            ))
        else:
            # If no filters, use aggregated data to avoid large result sets
            filtered_combinations = all_combinations

        print(f"Database aggregations completed in {time.time() - aggregation_start:.2f}s")

        # PHASE 2: Format response data
        format_start = time.time()
        
        # Convert Decimal to float for JSON serialization
        for item in cost_center_totals:
            item['total_from_center'] = float(item['total_from_center'] or 0)
            item['total_to_center'] = float(item['total_to_center'] or 0)

        for item in account_code_totals:
            item['total_from_center'] = float(item['total_from_center'] or 0)
            item['total_to_center'] = float(item['total_to_center'] or 0)

        for item in all_combinations:
            item['total_from_center'] = float(item['total_from_center'] or 0)
            item['total_to_center'] = float(item['total_to_center'] or 0)

        # Convert filtered combinations
        for item in filtered_combinations:
            if 'from_center' in item:  # Individual records
                item['from_center'] = float(item['from_center'] or 0)
                item['to_center'] = float(item['to_center'] or 0)

        print(f"Data formatting completed in {time.time() - format_start:.2f}s")

        # Prepare final response
        data = {
            "filtered_combinations": filtered_combinations,
            "cost_center_totals": cost_center_totals,
            "account_code_totals": account_code_totals,
            "all_combinations": all_combinations,
            "applied_filters": {
                "cost_center_code": filter_cost_center,
                "account_code": filter_account_code,
            },
            "performance_metrics": {
                "total_processing_time": round(time.time() - start_time, 2),
                "aggregation_time": round(time.time() - aggregation_start, 2),
                "cost_center_groups": len(cost_center_totals),
                "account_code_groups": len(account_code_totals),
                "total_combinations": len(all_combinations)
            }
        }

        print(f"Total optimized processing time: {time.time() - start_time:.2f}s")
        print(f"Found {len(cost_center_totals)} cost centers, {len(account_code_totals)} account codes")

        # Save dashboard data
        save_start = time.time()
        try:
            dashboard, created = xx_DashboardBudgetTransfer.objects.get_or_create(
                Dashboard_id=1,
                defaults={'data': '{}'}
            )
            
            existing_data = dashboard.get_data() or {}
            existing_data['smart'] = data
            
            dashboard.set_data(existing_data)
            dashboard.save()
            
            print(f"Dashboard data saved in {time.time() - save_start:.2f}s")
            print(f"Smart dashboard data {'created' if created else 'updated'} successfully")
            return data
            
        except Exception as save_error:
            print(f"Error saving dashboard data: {save_error}")
            return data

    except Exception as e:
        print(f"Error in optimized dashboard_smart: {e}")
        import traceback
        traceback.print_exc()
        return False

def dashboard_normal():
    """
    Optimized normal dashboard using database-level aggregations and counting
    """
    try:
        start_time = time.time()
        print("Starting optimized normal dashboard calculation...")

        # PHASE 1: Database-level counting and aggregations
        count_start = time.time()

        # Get all transfers with minimal data loading
        transfers_queryset = xx_BudgetTransfer.objects.only(
            'code', 'status', 'status_level', 'request_date'
        )

        # Use database aggregations for counting
        total_count = transfers_queryset.count()
        
        # Count by status using database aggregation
        status_counts = transfers_queryset.aggregate(
            approved=Count('transaction_id', filter=Q(status='approved')),
            rejected=Count('transaction_id', filter=Q(status='rejected')),
            pending=Count('transaction_id', filter=Q(status='pending'))
        )

        # Count by status level using database aggregation
        level_counts = transfers_queryset.aggregate(
            level1=Count('transaction_id', filter=Q(status_level=1)),
            level2=Count('transaction_id', filter=Q(status_level=2)),
            level3=Count('transaction_id', filter=Q(status_level=3)),
            level4=Count('transaction_id', filter=Q(status_level=4))
        )

        # Count by code prefix using database functions
        code_counts = transfers_queryset.aggregate(
            far=Count('transaction_id', filter=Q(code__istartswith='FAR')),
            afr=Count('transaction_id', filter=Q(code__istartswith='AFR')),
            fad=Count('transaction_id', filter=Q(code__istartswith='FAD'))
        )

        # Get request dates efficiently (only non-null dates)
        request_dates = list(
            transfers_queryset.filter(request_date__isnull=False)
            .values_list('request_date', flat=True)
            .order_by('-request_date')[:1000]  # Limit to recent 1000 for performance
        )

        # Convert datetime objects to ISO format strings for JSON serialization
        request_dates_iso = [date.isoformat() for date in request_dates]

        print(f"Database counting completed in {time.time() - count_start:.2f}s")

        # PHASE 2: Format response data
        data = {
            "total_transfers": total_count,
            "total_transfers_far": code_counts['far'],
            "total_transfers_afr": code_counts['afr'],
            "total_transfers_fad": code_counts['fad'],
            "approved_transfers": status_counts['approved'],
            "rejected_transfers": status_counts['rejected'],
            "pending_transfers": status_counts['pending'],
            "pending_transfers_by_level": {
                "Level1": level_counts['level1'],
                "Level2": level_counts['level2'],
                "Level3": level_counts['level3'],
                "Level4": level_counts['level4'],
            },
            "request_dates": request_dates_iso,
            "performance_metrics": {
                "total_processing_time": round(time.time() - start_time, 2),
                "counting_time": round(time.time() - count_start, 2),
                "total_records_processed": total_count,
                "request_dates_retrieved": len(request_dates_iso)
            }
        }

        print(f"Total optimized processing time: {time.time() - start_time:.2f}s")
        print(f"Processed {total_count} transfers")

        # Save dashboard data
        save_start = time.time()
        try:
            dashboard, created = xx_DashboardBudgetTransfer.objects.get_or_create(
                Dashboard_id=1,
                defaults={'data': '{}'}
            )
            
            existing_data = dashboard.get_data() or {}
            existing_data['normal'] = data
            
            dashboard.set_data(existing_data)
            dashboard.save()
            
            print(f"Dashboard data saved in {time.time() - save_start:.2f}s")
            print(f"Normal dashboard data {'created' if created else 'updated'} successfully")
            return data
            
        except Exception as save_error:
            print(f"Error saving normal dashboard data: {save_error}")
            return data

    except Exception as e:
        print(f"Error in optimized dashboard_normal: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_saved_dashboard_data(dashboard_type='smart'):
    """
    Retrieve saved dashboard data from database
    
    Args:
        dashboard_type (str): 'smart' or 'normal'
    
    Returns:
        dict: Dashboard data or None if not found
    """
    try:
        dashboard = xx_DashboardBudgetTransfer.objects.get(Dashboard_id=1)
        all_data = dashboard.get_data() or {}
        return all_data.get(dashboard_type)
    except xx_DashboardBudgetTransfer.DoesNotExist:
        print(f"No saved dashboard data found")
        return None
    except Exception as e:
        print(f"Error retrieving {dashboard_type} dashboard data: {e}")
        return None


def get_all_dashboard_data():
    """
    Retrieve all dashboard data (both smart and normal) from database
    
    Returns:
        dict: All dashboard data or None if not found
    """
    try:
        dashboard = xx_DashboardBudgetTransfer.objects.get(Dashboard_id=1)
        print("Retrieved dashboard data successfully")
        return dashboard.get_data() or {}
    except xx_DashboardBudgetTransfer.DoesNotExist:
        print("No saved dashboard data found")
        return {}
    except Exception as e:
        print(f"Error retrieving dashboard data: {e}")
        return {}


def refresh_dashboard_data(dashboard_type='smart'):
    """
    Refresh dashboard data by running the appropriate function and saving to database
    
    Args:
        dashboard_type (str): 'smart' or 'normal'
    
    Returns:
        dict: Updated dashboard data or False if error
    """
    if dashboard_type == 'smart':
        return dashboard_smart()
    elif dashboard_type == 'normal':
        return dashboard_normal()
    else:
        print(f"Invalid dashboard type: {dashboard_type}")
        return False


