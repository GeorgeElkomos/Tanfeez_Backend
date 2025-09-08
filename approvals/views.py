from rest_framework import viewsets

from user_management.permissions import IsSuperAdmin
from .models import ApprovalWorkflowTemplate, ApprovalWorkflowStageTemplate
from .serializers import (
    ApprovalWorkflowTemplateSerializer,
    ApprovalWorkflowStageTemplateSerializer,
)
from rest_framework.decorators import action
from rest_framework.response import Response

class ApprovalWorkflowTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    queryset = ApprovalWorkflowTemplate.objects.all()
    serializer_class = ApprovalWorkflowTemplateSerializer

    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        template = self.get_object()
        serializer = self.get_serializer(template)
        return Response(serializer.data)

class ApprovalWorkflowStageTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    queryset = ApprovalWorkflowStageTemplate.objects.all()
    serializer_class = ApprovalWorkflowStageTemplateSerializer

