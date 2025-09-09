from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from approvals.pagination import LargeResultsSetPagination, SmallResultsSetPagination
from user_management.permissions import IsSuperAdmin
from .models import ApprovalWorkflowStageTemplate, ApprovalWorkflowTemplate
from .serializers import (
    ApprovalWorkflowStageTemplateSerializer,
    ApprovalWorkflowTemplateSerializer,
    ApprovalWorkflowTemplateDetailSerializer,
)


class ApprovalWorkflowTemplateViewSet(viewsets.ModelViewSet):
    queryset = ApprovalWorkflowTemplate.objects.all()
    serializer_class = ApprovalWorkflowTemplateSerializer
    pagination_class = SmallResultsSetPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["is_active", "transfer_type", "version"]
    search_fields = ["name", "description", "code", "transfer_type"]
    ordering_fields = ["created_at", "updated_at", "version"]

    def get_serializer_class(self):
        if self.action in ["retrieve", "create", "update", "partial_update"]:
            return ApprovalWorkflowTemplateDetailSerializer
        return ApprovalWorkflowTemplateSerializer



class ApprovalWorkflowStageTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    queryset = ApprovalWorkflowStageTemplate.objects.all()
    serializer_class = ApprovalWorkflowStageTemplateSerializer
    pagination_class = LargeResultsSetPagination
