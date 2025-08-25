import numpy as np
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from budget_management.models import get_entities_with_children, get_level_zero_children, get_zero_level_accounts
from .models import XX_Account, XX_Entity, XX_PivotFund, XX_TransactionAudit, XX_ACCOUNT_ENTITY_LIMIT
from .serializers import AccountSerializer, EntitySerializer, PivotFundSerializer, TransactionAuditSerializer, AccountEntityLimitSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
from django.db import transaction
from .models import XX_ACCOUNT_ENTITY_LIMIT
from .serializers import AccountEntityLimitSerializer
from django.db.models import CharField
from django.db.models.functions import Cast
from django.db.models import Q
class EntityPagination(PageNumberPagination):
    """Pagination class for entities and accounts"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

# Account views
class AccountListView(APIView):
    """List all accounts with optional search"""
    permission_classes = [IsAuthenticated]
    pagination_class = EntityPagination

    def get(self, request):
        search_query = request.query_params.get("search", None)

        accounts = XX_Account.objects.all().order_by("account")
        
        accounts = get_zero_level_accounts(accounts)

        if search_query:
            # Cast account (int) to string for filtering
            accounts = accounts.filter(
                Q(account__icontains=search_query)  # works because Django auto casts to text in SQL
            )

        serializer = AccountSerializer(accounts, many=True)

        return Response({
            "message": "Accounts retrieved successfully.",
            "data": serializer.data
        })

class AccountCreateView(APIView):
    """Create a new account"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = AccountSerializer(data=request.data)
        if serializer.is_valid():
            account = serializer.save()
            return Response({
                'message': 'Account created successfully.',
                'data': AccountSerializer(account).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'message': 'Failed to create account.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class AccountDetailView(APIView):
    """Retrieve a specific account"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return XX_Account.objects.get(pk=pk)
        except XX_Account.DoesNotExist:
            return None
    
    def get(self, request, pk):
        account = self.get_object(pk)
        if account is None:
            return Response({
                'message': 'Account not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        serializer = AccountSerializer(account)
        return Response({
            'message': 'Account details retrieved successfully.',
            'data': serializer.data
        })

class AccountUpdateView(APIView):
    """Update a specific account"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return XX_Account.objects.get(pk=pk)
        except XX_Account.DoesNotExist:
            return None
    
    def put(self, request, pk):
        account = self.get_object(pk)
        if account is None:
            return Response({
                'message': 'Account not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        serializer = AccountSerializer(account, data=request.data)
        if serializer.is_valid():
            updated_account = serializer.save()
            return Response({
                'message': 'Account updated successfully.',
                'data': AccountSerializer(updated_account).data
            })
        return Response({
            'message': 'Failed to update account.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class AccountDeleteView(APIView):
    """Delete a specific account"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return XX_Account.objects.get(pk=pk)
        except XX_Account.DoesNotExist:
            return None
    
    def delete(self, request, pk):
        account = self.get_object(pk)
        if account is None:
            return Response({
                'message': 'Account not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        account.delete()
        return Response({
            'message': 'Account deleted successfully.'
        }, status=status.HTTP_200_OK)

# Entity views
class EntityListView(APIView):
    """List all entities"""
    permission_classes = [IsAuthenticated]
    pagination_class = EntityPagination
    
    def get(self, request):
        # 🔹 Apply permissions filter
        if request.user.abilities.count() > 0:
            entity_ids = [ability.Entity.id for ability in request.user.abilities.all() if ability.Entity]
            # Get all accessible entities including their children
            entities = get_entities_with_children(entity_ids)
        else:
            # If no permissions filter, get all entities
            entities = list(XX_Entity.objects.all().order_by('entity'))
        
        # 🔹 Get only level zero children from the accessible entities
        level_zero_entities = get_level_zero_children([e.id for e in entities])
        
        # 🔹 Apply search filter
        search_query = request.query_params.get("search")
        if search_query:
            search_lower = search_query.lower()
            level_zero_entities = [e for e in level_zero_entities if search_lower in str(e.entity).lower()]
        
        # 🔹 Sort the final results
        level_zero_entities.sort(key=lambda x: x.entity)
        
        serializer = EntitySerializer(level_zero_entities, many=True)
        return Response({
            'message': 'Accounts retrieved successfully.',
            'data': serializer.data
        })

class EntityCreateView(APIView):
    """Create a new entity"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = EntitySerializer(data=request.data)
        if serializer.is_valid():
            entity = serializer.save()
            return Response({
                'message': 'Entity created successfully.',
                'data': EntitySerializer(entity).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'message': 'Failed to create entity.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class EntityDetailView(APIView):
    """Retrieve a specific entity"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return XX_Entity.objects.get(pk=pk)
        except XX_Entity.DoesNotExist:
            return None
    
    def get(self, request, pk):
        entity = self.get_object(pk)
        if entity is None:
            return Response({
                'message': 'Entity not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        serializer = EntitySerializer(entity)
        return Response({
            'message': 'Entity details retrieved successfully.',
            'data': serializer.data
        })

class EntityUpdateView(APIView):
    """Update a specific entity"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return XX_Entity.objects.get(pk=pk)
        except XX_Entity.DoesNotExist:
            return None
    
    def put(self, request, pk):
        entity = self.get_object(pk)
        if entity is None:
            return Response({
                'message': 'Entity not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        serializer = EntitySerializer(entity, data=request.data)
        if serializer.is_valid():
            updated_entity = serializer.save()
            return Response({
                'message': 'Entity updated successfully.',
                'data': EntitySerializer(updated_entity).data
            })
        return Response({
            'message': 'Failed to update entity.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class EntityDeleteView(APIView):
    """Delete a specific entity"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return XX_Entity.objects.get(pk=pk)
        except XX_Entity.DoesNotExist:
            return None
    
    def delete(self, request, pk):
        entity = self.get_object(pk)
        if entity is None:
            return Response({
                'message': 'Entity not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        entity.delete()
        return Response({
            'message': 'Entity deleted successfully.'
        }, status=status.HTTP_200_OK)

# PivotFund views
class PivotFundListView(APIView):
    """List all pivot funds"""
    permission_classes = [IsAuthenticated]
    pagination_class = EntityPagination
    
    def get(self, request):
        # Allow filtering by entity, account, and year
        entity_id = request.query_params.get('entity')
        account_id = request.query_params.get('account')
        year = request.query_params.get('year')
        
        pivot_funds = XX_PivotFund.objects.all()
        
        if entity_id:
            pivot_funds = pivot_funds.filter(entity=entity_id)
        if account_id:
            pivot_funds = pivot_funds.filter(account=account_id)
        if year:
            pivot_funds = pivot_funds.filter(year=year)
        
        # Order by year, entity, account
        pivot_funds = pivot_funds.order_by('-year', 'entity__entity', 'account__account')
        
        # Handle pagination
        paginator = self.pagination_class()
        paginated_funds = paginator.paginate_queryset(pivot_funds, request)
        serializer = PivotFundSerializer(paginated_funds, many=True)
        
        return paginator.get_paginated_response(serializer.data)

class PivotFundCreateView(APIView):
    """Create a new pivot fund"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Handle batch creation
        if isinstance(request.data, list):
            created_funds = []
            errors = []
            
            for index, fund_data in enumerate(request.data):
                serializer = PivotFundSerializer(data=fund_data)
                if serializer.is_valid():
                    fund = serializer.save()
                    created_funds.append(PivotFundSerializer(fund).data)
                else:
                    errors.append({
                        'index': index,
                        'errors': serializer.errors,
                        'data': fund_data
                    })
            
            response_data = {
                'message': f'Created {len(created_funds)} pivot funds, with {len(errors)} errors.',
                'created': created_funds,
                'errors': errors
            }
            
            if errors and not created_funds:
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
            elif errors:
                return Response(response_data, status=status.HTTP_207_MULTI_STATUS)
            else:
                return Response(response_data, status=status.HTTP_201_CREATED)
        
        # Handle single creation
        else:
            serializer = PivotFundSerializer(data=request.data)
            if serializer.is_valid():
                fund = serializer.save()
                return Response({
                    'message': 'Pivot fund created successfully.',
                    'data': PivotFundSerializer(fund).data
                }, status=status.HTTP_201_CREATED)
            return Response({
                'message': 'Failed to create pivot fund.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

class PivotFundDetailView(APIView):
    """Retrieve a specific pivot fund"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, entity,account):
        try:
           
            return XX_PivotFund.objects.get(entity=entity,account=account)
        
        except XX_PivotFund.DoesNotExist:
            

            return None
    
    def get(self, request):

        entity=request.query_params.get('entity_id')
        account=request.query_params.get('account_id')
        print(entity,account)
        pivot_fund = self.get_object(entity,account)

        if pivot_fund is None:
            return Response({
                'message': 'Pivot fund not found.'
            }, status=status.HTTP_200_OK)
        serializer = PivotFundSerializer(pivot_fund)
        return Response({
            'message': 'Pivot fund details retrieved successfully.',
            'data': serializer.data
        })

class PivotFundUpdateView(APIView):
    """Update a specific pivot fund"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return XX_PivotFund.objects.get(pk=pk)
        except XX_PivotFund.DoesNotExist:
            return None
    
    def put(self, request, pk):
        pivot_fund = self.get_object(pk)
        if pivot_fund is None:
            return Response({
                'message': 'Pivot fund not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        serializer = PivotFundSerializer(pivot_fund, data=request.data)
        if serializer.is_valid():
            updated_fund = serializer.save()
            return Response({
                'message': 'Pivot fund updated successfully.',
                'data': PivotFundSerializer(updated_fund).data
            })
        return Response({
            'message': 'Failed to update pivot fund.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class PivotFundDeleteView(APIView):
    """Delete a specific pivot fund"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return XX_PivotFund.objects.get(pk=pk)
        except XX_PivotFund.DoesNotExist:
            return None
    
    def delete(self, request, pk):
        pivot_fund = self.get_object(pk)
        if pivot_fund is None:
            return Response({
                'message': 'Pivot fund not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        pivot_fund.delete()
        return Response({
            'message': 'Pivot fund deleted successfully.'
        }, status=status.HTTP_200_OK)
    
# ADJD Transaction Audit views 

class AdjdTransactionAuditListView(APIView):
    """List all ADJD transaction audit records"""
    permission_classes = [IsAuthenticated]
    pagination_class = EntityPagination
    
    def get(self, request):
        audit_records = XX_TransactionAudit.objects.all().order_by('-id')
        
        # Handle pagination
        paginator = self.pagination_class()
        paginated_records = paginator.paginate_queryset(audit_records, request)
        serializer = TransactionAuditSerializer(paginated_records, many=True)
        
        return paginator.get_paginated_response(serializer.data)

class AdjdTransactionAuditCreateView(APIView):
    """Create a new ADJD transaction audit record"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = TransactionAuditSerializer(data=request.data)
        if serializer.is_valid():
            audit_record = serializer.save()
            return Response({
                'message': 'Audit record created successfully.',
                'data': TransactionAuditSerializer(audit_record).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'message': 'Failed to create audit record.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class AdjdTransactionAuditDetailView(APIView):
    """Retrieve a specific ADJD transaction audit record"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return XX_TransactionAudit.objects.get(pk=pk)
        except XX_TransactionAudit.DoesNotExist:
            return None
    
    def get(self, request, pk):
        audit_record = self.get_object(pk)
        if audit_record is None:
            return Response({
                'message': 'Audit record not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        serializer = TransactionAuditSerializer(audit_record)
        return Response({
            'message': 'Audit record details retrieved successfully.',
            'data': serializer.data
        })

class AdjdTransactionAuditUpdateView(APIView):
    """Update a specific ADJD transaction audit record"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return XX_TransactionAudit.objects.get(pk=pk)
        except XX_TransactionAudit.DoesNotExist:
            return None
    
    def put(self, request, pk):
        audit_record = self.get_object(pk)
        if audit_record is None:
            return Response({
                'message': 'Audit record not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        serializer = TransactionAuditSerializer(audit_record, data=request.data)
        if serializer.is_valid():
            updated_record = serializer.save()
            return Response({
                'message': 'Audit record updated successfully.',
                'data': TransactionAuditSerializer(updated_record).data
            })
        return Response({
            'message': 'Failed to update audit record.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class AdjdTransactionAuditDeleteView(APIView):
    """Delete a specific ADJD transaction audit record"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return XX_TransactionAudit.objects.get(pk=pk)
        except XX_TransactionAudit.DoesNotExist:
            return None
    
    def delete(self, request, pk):
        audit_record = self.get_object(pk)
        if audit_record is None:
            return Response({
                'message': 'Audit record not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        audit_record.delete()
        return Response({
            'message': 'Audit record deleted successfully.'
        }, status=status.HTTP_200_OK)



class list_ACCOUNT_ENTITY_LIMIT(APIView):
    """List all ADJD transaction audit records"""
    permission_classes = [IsAuthenticated]
    pagination_class = EntityPagination
    
    def get(self, request):
        # Change "enity_id" to "entity_id"
        entity_id = request.query_params.get('cost_center')
        account_id = request.query_params.get('account_id')

        audit_records = XX_ACCOUNT_ENTITY_LIMIT.objects.filter(
            entity_id=entity_id
        ).order_by('-id')
        audit_records = audit_records.annotate(account_id_str=Cast('account_id', CharField()))

        if account_id:
            audit_records = audit_records.filter(account_id_str__icontains=str(account_id))
        
        # Handle pagination
        paginator = self.pagination_class()
        paginated_records = paginator.paginate_queryset(audit_records, request)
        serializer = AccountEntityLimitSerializer(paginated_records, many=True)

        data = [
            
            {
                'id': record["id"],
                'account': record["account_id"],
                'is_transer_allowed_for_source': record["is_transer_allowed_for_source"],
                'is_transer_allowed_for_target': record["is_transer_allowed_for_target"],
                'is_transer_allowed': record["is_transer_allowed"],
                'source_count': record["source_count"],
                'target_count': record["target_count"],
            }
            for record in serializer.data
        ]
        
        return paginator.get_paginated_response(data)



class AccountEntityLimitAPI(APIView):
    """Handle both listing and creation of ACCOUNT_ENTITY_LIMIT records"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]  # For file upload support

    def get(self, request):
        """List all records with optional filtering by cost_center"""
        entity_id = request.query_params.get('cost_center')

        audit_records = XX_ACCOUNT_ENTITY_LIMIT.objects.filter(
            entity_id=entity_id
        ).order_by('-id')
        
        paginator = self.pagination_class()
        paginated_records = paginator.paginate_queryset(audit_records, request)
        serializer = AccountEntityLimitSerializer(paginated_records, many=True)

        data = [
            {
                'id': record["id"],
                'account': record["account_id"],
                'is_transfer_allowed_for_source': record["is_transfer_allowed_for_source"],
                'is_transfer_allowed_for_target': record["is_transfer_allowed_for_target"],
                'is_transfer_allowed': record["is_transfer_allowed"],
                'source_count': record["source_count"],
                'target_count': record["target_count"],
            }
            for record in serializer.data
        ]
        
        return paginator.get_paginated_response(data)

    def post(self, request):
        """Handle both single record creation and bulk upload via file"""
        # Check if file is present for bulk upload
        uploaded_file = request.FILES.get('file')
        
        if uploaded_file:
            return self._handle_file_upload(uploaded_file)
        else:
            return self._handle_single_record(request.data)

    def _handle_file_upload(self, file):
        """Process Excel file for bulk creation"""
        try:
            # Read Excel file
            df = pd.read_excel(file)
            
            # Clean column names (convert to lowercase and strip whitespace)
            df.columns = df.columns.str.strip().str.lower()
            df = df.replace([np.nan, pd.NA, pd.NaT, '', 'NULL', 'null'], None)


            # Convert to list of dictionaries
            records = df.to_dict('records')
            
            created_count = 0
            errors = []
            
            with transaction.atomic():
                for idx, record in enumerate(records, start=1):
                    try:
                        serializer = AccountEntityLimitSerializer(data=record)
                        if serializer.is_valid():
                            serializer.save()
                            created_count += 1
                        else:
                            errors.append({
                                'row': idx,
                                'errors': serializer.errors,
                                'data': record
                            })
                    except Exception as e:
                        errors.append({
                            'row': idx,
                            'error': str(e),
                            'data': record
                        })
            
            response = {
                'status': 'success',
                'created_count': created_count,
                'error_count': len(errors),
                'errors': errors if errors else None
            }
            
            return Response(response, status=status.HTTP_201_CREATED if created_count else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _handle_single_record(self, data):
        """Handle single record creation"""
        serializer = AccountEntityLimitSerializer(data=data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)







class UpdateAccountEntityLimit(APIView):
    """Update a specific account entity limit."""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return XX_ACCOUNT_ENTITY_LIMIT.objects.get(pk=pk)
        except XX_ACCOUNT_ENTITY_LIMIT.DoesNotExist:
            return None

    def put(self, request):

        pk=request.query_params.get('pk')
        limit_record = self.get_object(pk)
        if limit_record is None:
            return Response({'message': 'Limit record not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = AccountEntityLimitSerializer(limit_record, data=request.data)
        if serializer.is_valid():
            updated_record = serializer.save()
            return Response({
                'message': 'Limit record updated successfully.',
                'data': AccountEntityLimitSerializer(updated_record).data
            })
        return Response({'message': 'Failed to update limit record.', 'errors': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)


class DeleteAccountEntityLimit(APIView):
    """Delete a specific account entity limit."""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return XX_ACCOUNT_ENTITY_LIMIT.objects.get(pk=pk)
        except XX_ACCOUNT_ENTITY_LIMIT.DoesNotExist:
            return None

    def delete(self, request, pk):
        limit_record = self.get_object(pk)
        if limit_record is None:
            return Response({'message': 'Limit record not found.'}, status=status.HTTP_404_NOT_FOUND)
        limit_record.delete()
        return Response({'message': 'Limit record deleted successfully.'}, status=status.HTTP_200_OK)

# MainCurrency views
