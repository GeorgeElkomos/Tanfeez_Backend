from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import ApprovalWorkflowTemplateViewSet, ApprovalWorkflowStageTemplateViewSet

router = DefaultRouter()
router.register(r'workflow-templates', ApprovalWorkflowTemplateViewSet, basename='workflowtemplate')
router.register(r'stage-templates', ApprovalWorkflowStageTemplateViewSet, basename='stagetemplate')

urlpatterns = [
    path('', include(router.urls)),
]
