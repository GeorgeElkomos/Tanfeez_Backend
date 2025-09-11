# approval/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import ApprovalWorkflowStageInstance
from .managers import ApprovalManager


@shared_task
def check_sla_breaches():
    """
    Find all active stage instances that have SLA exceeded and call on_sla_breached.
    """
    now = timezone.now()
    for stage in ApprovalWorkflowStageInstance.objects.filter(status="active"):
        sla_hours = stage.stage_template.sla_hours
        if sla_hours:
            deadline = stage.activated_at + timedelta(hours=sla_hours)
            if now > deadline:
                ApprovalManager.on_sla_breached(stage)


@shared_task
def cleanup_delegations():
    """
    Deactivate stale delegations where the stage is no longer active.
    """
    now = timezone.now()
    qs = ApprovalWorkflowStageInstance.objects.exclude(status="active")
    for stage in qs:
        stage.delegations.filter(active=True).update(active=False, deactivated_at=now)
