from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    """Permission check for admin users"""
    def has_permission(self, request, view):
        return request.user.role == 'admin' or request.user.role == 'superadmin'
    
class IsSuperAdmin(BasePermission):
    """Permission check for admin users"""
    def has_permission(self, request, view):
        return request.user.role == 'superadmin'
 
class IsRegularUser(BasePermission):
    """Permission check for regular users"""
    def has_permission(self, request, view):
        return request.user.role == 'user'

class CanTransferBudget(BasePermission):
    """Permission check for users with budget transfer rights"""
    def has_permission(self, request, view):
        return request.user.can_transfer_budget or request.user.role == 'admin'
