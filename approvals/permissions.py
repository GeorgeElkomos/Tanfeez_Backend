# approval/permissions.py
from rest_framework.permissions import BasePermission
from .models import ApprovalWorkflowStageInstance


class IsAssignedApprover(BasePermission):
    """
    Permission: user must have a pending assignment
    in the active stage to act.
    """

    def has_permission(self, request, view):
        user = request.user
        stage_id = view.kwargs.get("stage_id")
        try:
            stage = ApprovalWorkflowStageInstance.objects.get(
                pk=stage_id, status="active"
            )
        except ApprovalWorkflowStageInstance.DoesNotExist:
            return False
        return stage.assignments.filter(user=user, status="pending").exists()
