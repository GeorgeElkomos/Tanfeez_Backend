from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken,TokenError
from datetime import timedelta, datetime, timezone as dt_timezone
from django.utils import timezone

from Admin_Panel import serializers
from .models import xx_User, xx_UserAbility, xx_UserLevel, xx_notification
from .serializers import ChangePasswordSerializer, NotificationSerializer, RegisterSerializer, LoginSerializer, UserLevelSerializer
from .permissions import IsAdmin, IsSuperAdmin
from .utils import send_notification

# Import all models from all apps
from budget_management.models import (
    xx_BudgetTransfer,
    xx_BudgetTransferAttachment, 
    xx_BudgetTransferRejectReason,
    xx_DashboardBudgetTransfer
)
from adjd_transaction.models import xx_TransactionTransfer
from account_and_entitys.models import (
    XX_Account,
    XX_Entity, 
    XX_PivotFund,
    XX_TransactionAudit,
    XX_ACCOUNT_ENTITY_LIMIT
)
from Admin_Panel.models import MainCurrency, MainRoutesName

# from test_querty import LLMQueryGenerator
# from django.db import connection
# Authentication Views
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status



class RefreshTokenView(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        user_id = request.data.get('user_id')
        if not refresh_token:
            return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Validate the old refresh token
            old_refresh = RefreshToken(refresh_token)
            
            # Get the user from the refresh token
            # user_id = old_refresh.payload.get('user_id')
            user = xx_User.objects.get(id=user_id)

            # Create a completely new refresh token for the user
            new_refresh = RefreshToken.for_user(user)
            
            # Optionally blacklist the old refresh token (if using token blacklisting)
            # old_refresh.blacklist()
            
            return Response({
                'access': str(new_refresh.access_token),
                'refresh': str(new_refresh)
            }, 
            status=status.HTTP_200_OK)
        except TokenError:
            return Response({'error': 'Invalid or expired refresh token'}, status=status.HTTP_401_UNAUTHORIZED)
        except xx_User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_401_UNAUTHORIZED)
        
        
class RegisterView(APIView):
    """Register a new user"""
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        print("Begin registration process")
        if serializer.is_valid():
            print("Serializer is valid, proceeding with registration")
            user = serializer.save()
            print("User registered successfully:", user.username)
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'data': RegisterSerializer(user).data,
                'message': 'User registered successfully.',
                'token': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        print("Serializer errors:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class LoginView(APIView):
    """Authenticate a user and return a token"""
    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        # XX_Account.objects.all().delete()
        # XX_Entity.objects.all().delete()
        # XX_PivotFund.objects.all().delete()
        # XX_ACCOUNT_ENTITY_LIMIT.objects.all().delete()

        if serializer.is_valid():
            user = serializer.validated_data
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'data': RegisterSerializer(user).data,
                'user_level': user.user_level.level_order if user.user_level else None,
                'message': 'Login successful.',
                'token': str(refresh.access_token),
                'refresh': str(refresh),
            })
            
        return Response({'message': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
class TokenExpiredView(APIView):
    """Check if the token is expired"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        token_created_at = request.auth.payload.get('iat', None)
        if token_created_at:
            expiration_minutes = 1440  # 24 hours
            created_time = datetime.fromtimestamp(token_created_at, tz=dt_timezone.utc)
            if timezone.now() > created_time + timedelta(minutes=expiration_minutes):
                return Response({
                    'data': [],
                    'message': 'Token expired.',
                    'token': None
                }, status=status.HTTP_401_UNAUTHORIZED)

        return Response({
            'data': RegisterSerializer(request.user).data,
            'message': 'Token valid.',
            'token': str(request.auth)
        })
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get("old_password", None)
        new_password = request.data.get("new_password", None)
        print("Old password:", old_password)
        print("New password:", new_password)
        try:
            serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
            
            if serializer.is_valid():
                serializer.save()
                return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)
        except serializers.ValidationError as e:
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# User Management Views
class ListUsersView(APIView):
    """List all users (admin only)"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        users = xx_User.objects.exclude(id=request.user.id)  # Exclude current admin
        data = []
        for user in users:
            data.append({
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'can_transfer_budget': user.can_transfer_budget,
                'user_level': user.user_level.name if user.user_level else 'None',
            })
        return Response(data)
class UpdateUserPermissionView(APIView):
    # """Update a user's permission to transfer budget (admin only)"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def put(self, request, user_id):
        try:
            user = xx_User.objects.get(id=user_id)
            can_transfer_budget = request.data.get('can_transfer_budget', False)
            
            # Update the permission
            user.can_transfer_budget = can_transfer_budget
            user.save()
            
            return Response({
                "message": f"Permissions updated for user {user.username}",
                "can_transfer_budget": user.can_transfer_budget
            })
        except xx_User.DoesNotExist:
            return Response({"message": "User not found."}, status=status.HTTP_404_NOT_FOUND)
class UserUpdateView(APIView):
    """Update user data (e.g., username, role)."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_object(self, pk):
        try:
            return xx_User.objects.get(pk=pk)
        except xx_User.DoesNotExist:
            return None

    def put(self, request):
        pk = request.query_params.get('pk')
        user = self.get_object(pk)
        if user is None:
            return Response({'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        for field in ['username', 'role', 'can_transfer_budget']:
            if field in request.data:
                setattr(user, field, request.data[field])

        user.save()
        return Response({
            'message': 'User updated successfully.',
            'data': {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'can_transfer_budget': user.can_transfer_budget,
            }
        })
class UserDeleteView(APIView):
    """Delete a specific user."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_object(self, pk):
        try:
            return xx_User.objects.get(pk=pk)
        except xx_User.DoesNotExist:
            return None

    def delete(self, request):
        pk = request.query_params.get('pk')
        user = self.get_object(pk)
        if user is None:
            return Response({'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        user.delete()
        return Response({'message': 'User deleted successfully.'}, status=status.HTTP_200_OK)


# User Level Views
class UpdateUserLevelView(APIView): # Update a user's level
    """Assign a specific user level to a user (admin only)"""
    permission_classes = [IsAuthenticated, IsAdmin]

    def put(self, request):
        try:
            # Get the user

            # Get the level ID from request data
            level_id = request.data.get('level_order')
            user_id = request.data.get('user_id')

            user = xx_User.objects.get(id=user_id)


            if level_id is None:
                return Response({
                    'error': 'Missing level_id',
                    'message': 'Please provide a level_id to assign'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if the level exists
            try:
                user_level = xx_UserLevel.objects.get(level_order=level_id)
            except xx_UserLevel.DoesNotExist:
                return Response({
                    'error': 'Invalid level_id',
                    'message': f'No user level found with ID: {level_id}'
                }, status=status.HTTP_404_NOT_FOUND)

            # Update the user's level
            old_level = user.user_level.name if user.user_level else 'None'
            user.user_level = user_level
            user.save()

            return Response({
                'message': f'User level updated successfully for {user.username}',
                'data': {
                    'user_id': user.id,
                    'username': user.username,
                    'previous_level': old_level,
                    'new_level': user_level.name,
                    'level_order': user_level.level_order
                }
            }, status=status.HTTP_200_OK)

        except xx_User.DoesNotExist:
            return Response({
                'error': 'User not found',
                'message': f'No user found with ID: {user_id}'
            }, status=status.HTTP_404_NOT_FOUND)

class UserLevelCreateView(APIView):
    """Create a new user level"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request):
        serializer = UserLevelSerializer(data=request.data)
        if serializer.is_valid():
            # Check if level_order already exists
            level_order = serializer.validated_data.get('level_order')
            if xx_UserLevel.objects.filter(level_order=level_order).exists():
                return Response({
                    'error': 'Level order already exists',
                    'message': f'A user level with order {level_order} already exists'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            serializer.save()
            return Response({
                'message': 'User level created successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  

class UserLevelUpdateView(APIView): # Update the data of the Level itself
    """Update an existing user level (name, level_order)."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_object(self, pk):
        try:
            return xx_UserLevel.objects.get(pk=pk)
        except xx_UserLevel.DoesNotExist:
            return None

    def put(self, request):
        pk = request.query_params.get('pk')
        level = self.get_object(pk)
        if level is None:
            return Response({'message': 'User level not found.'}, status=status.HTTP_404_NOT_FOUND)

        for field in ["name", "level_order", "description"]:
            if field in request.data:
                setattr(level, field, request.data[field])

        level.save()
        return Response({
            'message': 'User level updated successfully.',
            'data': {
                'id': level.id,
                'name': level.name,
                'level_order': level.level_order,
                'description': level.description
            }
        })

class UserLevelDeleteView(APIView):
    """Delete a specific user level."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_object(self, pk):
        try:
            return xx_UserLevel.objects.get(pk=pk)
        except xx_UserLevel.DoesNotExist:
            return None

    def delete(self, request):
        pk = request.query_params.get('pk')
        level = self.get_object(pk)
        if level is None:
            return Response({'message': 'User level not found.'}, status=status.HTTP_404_NOT_FOUND)
        level.delete()
        return Response({'message': 'User level deleted successfully.'}, status=status.HTTP_200_OK)
    
class UserLevelListView(APIView):
    """List all user levels"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        levels = xx_UserLevel.objects.all()
        serializer = UserLevelSerializer(levels, many=True)
        return Response(serializer.data)


# Notification Views
class UnRead_Notification(APIView):
    """Create and list notifications for a user"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        notifications = xx_notification.objects.filter(user=user, is_read=False, is_shown=True).order_by('created_at').reverse()
        count = notifications.count()
        data = [
            {
                'id': notification.id,
                'message': notification.message,
                'is_read': notification.is_read,
                'created_at': notification.created_at,
                'is_shown': notification.is_shown,
                'is_system_read': notification.is_system_read
            } for notification in notifications
        ]
        return Response({
            'notifications': data,
            'count': count
        })
    
class System_Notification(APIView):
    """Create and list system notifications for all users"""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        user = request.user
        notifications = xx_notification.objects.filter(user=user, is_system_read=False).order_by('created_at').reverse()
        count = notifications.count()
        for notification in notifications:
            notification.is_system_read = True
            notification.save()
        return Response({
            'Number_Of_Notifications': count,
        })
    
class Get_All_Notification(APIView):
    """Create and list system notifications for all users"""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        user = request.user
        notifications = xx_notification.objects.filter(user=user, is_shown=True).order_by('created_at').reverse()
        data = [
            {
                'id': notification.id,
                'message': notification.message,
                'is_read': notification.is_read,
                'created_at': notification.created_at,
                'is_shown': notification.is_shown,
                'is_system_read': notification.is_system_read
            } for notification in notifications
        ]
        return Response({
            'notifications': data
        })
    
class Read_Notification(APIView):
    """Mark a notification as read"""
    permission_classes = [IsAuthenticated]

    def put(self, request):
        try:
            notification_id = request.query_params.get('notification_id')
            notification = xx_notification.objects.get(id=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            return Response({'message': 'Notification marked as read.'})
        except xx_notification.DoesNotExist:
            return Response({'message': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)
        
class Read_All_Notification(APIView):
    """Mark a notification as read"""
    permission_classes = [IsAuthenticated]

    def put(self, request):
        try:
            notifications = xx_notification.objects.filter(user=request.user, is_read=False)
            for notification in notifications:
                notification.is_read = True
                notification.save()
            return Response({'message': 'Notification marked as read.'})
        except xx_notification.DoesNotExist:
            return Response({'message': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)
        
class Delete_Nnotification(APIView):
    """Delete a specific notification"""
    permission_classes = [IsAuthenticated]

    def put(self, request):
        try:
            notification_id = request.query_params.get('notification_id')
            notification = xx_notification.objects.get(id=notification_id, user=request.user)
            notification.is_shown = False
            notification.save()
            return Response({'message': 'Notification deleted successfully.'})
        except xx_notification.DoesNotExist:
            return Response({'message': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)






class UserAbilitiesView(APIView):
    """Manage user abilities"""
    permission_classes = [IsSuperAdmin, IsAuthenticated]

    def get(self, request):
        # start with all abilities for current user
        abilities = xx_UserAbility.objects.all()

        # optional filters
        user_id = request.query_params.get("user")
        entity_id = request.query_params.get("entity")
        ability_type = request.query_params.get("type")

        if user_id:
            abilities = abilities.filter(user_id=user_id)
        if entity_id:
            abilities = abilities.filter(Entity_id=entity_id)
        if ability_type:
            abilities = abilities.filter(Type=ability_type)

        data = [
            {
                'id': ability.id,
                'user': ability.user.username,
                'entity': ability.Entity.entity if ability.Entity else None,
                'type': ability.Type
            }
            for ability in abilities
        ]
        return Response(data)
    
    def post(self, request):
        user_id = request.data.get('user')
        entity_id = request.data.get('entity')
        ability_type = request.data.get('type')

        if not user_id or not entity_id or not ability_type:
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = xx_User.objects.get(id=user_id)
            entity = XX_Entity.objects.get(id=entity_id)
        except (xx_User.DoesNotExist, XX_Entity.DoesNotExist):
            return Response({'error': 'User or Entity not found'}, status=status.HTTP_404_NOT_FOUND)

        ability, created = xx_UserAbility.objects.get_or_create(
            user=user,
            Entity=entity,
            Type=ability_type
        )
        data = {
            "id": ability.id,
            "user": ability.user.username,
            "entity": ability.Entity.entity if ability.Entity else None,
            "type": ability.Type
        }

        if created:
            return Response({'message': 'Ability created successfully', 'ability':data}, status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'Ability already exists', 'ability':data}, status=status.HTTP_200_OK)
        
    def put(self, request):
        ability_id = request.data.get('id')
        user_id = request.data.get('user')
        entity_id = request.data.get('entity')
        ability_type = request.data.get('type')

        if not ability_id or not user_id or not entity_id or not ability_type:
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ability = xx_UserAbility.objects.get(id=ability_id)
            user = xx_User.objects.get(id=user_id)
            entity = XX_Entity.objects.get(id=entity_id)
        except (xx_UserAbility.DoesNotExist, xx_User.DoesNotExist, XX_Entity.DoesNotExist):
            return Response({'error': 'Ability, User or Entity not found'}, status=status.HTTP_404_NOT_FOUND)

        ability.user = user
        ability.Entity = entity
        ability.Type = ability_type
        ability.save()

        return Response({'message': 'Ability updated successfully'}, status=status.HTTP_200_OK)
    
    def delete(self, request):
        ability_id = request.data.get('id')
        if not ability_id:
            return Response({'error': 'Missing ability ID'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ability = xx_UserAbility.objects.get(id=ability_id)
            ability.delete()
            return Response({'message': 'Ability deleted successfully'}, status=status.HTTP_200_OK)
        except xx_UserAbility.DoesNotExist:
            return Response({'error': 'Ability not found'}, status=status.HTTP_404_NOT_FOUND)