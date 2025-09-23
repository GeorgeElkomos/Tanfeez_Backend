from django.db import models
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.utils import timezone

"""Dynamic approval workflow models.

These models implement the flexible, data‑driven approval engine described in
`DYNAMIC_APPROVAL_DESIGN.md` allowing variable length workflows, per‑stage
assignment, and auditable approval history.

Phase 1: Models only (engine / services to be added separately).
"""

# Avoid top-level imports of other app models to prevent circular import problems;
# use string references in ForeignKey/OneToOne declarations instead.

class ApprovalWorkflowTemplate(models.Model):
	"""Defines a reusable workflow template for a given transfer type.

	Only one active template per (transfer_type, version) should normally be used
	at runtime; older versions can remain for audit / legacy instances.
	"""

	TRANSFER_TYPE_CHOICES = [
		("FAR", "FAR"),
		("AFR", "AFR"),
		("FAD", "FAD"),
		("GEN", "Generic"),  # fallback / future
	]

	code = models.CharField(max_length=60, unique=True)
	transfer_type = models.CharField(max_length=10, choices=TRANSFER_TYPE_CHOICES)
	name = models.CharField(max_length=120)
	description = models.TextField(blank=True, null=True)
	is_active = models.BooleanField(default=True)
	version = models.PositiveIntegerField(default=1)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "APPROVAL_WORKFLOW_TEMPLATE"
		ordering = ["transfer_type", "-version", "code"]
		indexes = [
			models.Index(fields=["transfer_type", "is_active"]),
		]

	def __str__(self):
		return f"WorkflowTemplate {self.code} v{self.version} ({'active' if self.is_active else 'inactive'})"

class ApprovalWorkflowStageTemplate(models.Model):
	"""Stage template belonging to a workflow template."""

	POLICY_ALL = "ALL"
	POLICY_ANY = "ANY"
	POLICY_QUORUM = "QUORUM"
	DECISION_POLICY_CHOICES = [
		(POLICY_ALL, "All must approve"),
		(POLICY_ANY, "Any one can approve"),
		(POLICY_QUORUM, "Quorum of approvals"),
	]

	workflow_template = models.ForeignKey(
		ApprovalWorkflowTemplate, related_name="stages", on_delete=models.CASCADE
	)
	order_index = models.PositiveIntegerField(help_text="1-based ordering of stages")
	name = models.CharField(max_length=120)
	decision_policy = models.CharField(
		max_length=10, choices=DECISION_POLICY_CHOICES, default=POLICY_ALL
	)
	quorum_count = models.PositiveIntegerField(null=True, blank=True)
	required_user_level = models.ForeignKey(
		"user_management.xx_UserLevel",
		on_delete=models.PROTECT,
		related_name="stage_templates",
		help_text="If set, assignments will include users with this level",
	)
	required_role = models.CharField(
		max_length=50, null=True, blank=True, help_text="Optional user.role filter"
	)
	dynamic_filter_json = models.TextField(
		null=True,
		blank=True,
		help_text="Reserved for future dynamic filtering (store JSON string)",
	)
	allow_reject = models.BooleanField(default=True)
	allow_delegate = models.BooleanField(default=False)
	sla_hours = models.PositiveIntegerField(null=True, blank=True)
	parallel_group = models.PositiveIntegerField(
		null=True,
		blank=True,
		help_text="Future use: stages in same group run in parallel",
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "APPROVAL_WORKFLOW_STAGE_TEMPLATE"
		ordering = ["workflow_template", "order_index"]
		unique_together = ("workflow_template", "order_index")

	def __str__(self):
		return f"StageTemplate {self.workflow_template.code}#{self.order_index} {self.name}"

class ApprovalWorkflowInstance(models.Model):
	"""Runtime instance of a workflow for a specific budget transfer."""

	STATUS_PENDING = "pending"
	STATUS_IN_PROGRESS = "in_progress"
	STATUS_APPROVED = "approved"
	STATUS_REJECTED = "rejected"
	STATUS_CANCELLED = "cancelled"
	STATUS_CHOICES = [
		(STATUS_PENDING, "Pending"),
		(STATUS_IN_PROGRESS, "In Progress"),
		(STATUS_APPROVED, "Approved"),
		(STATUS_REJECTED, "Rejected"),
		(STATUS_CANCELLED, "Cancelled"),
	]

	budget_transfer = models.OneToOneField(
		"budget_management.xx_BudgetTransfer",
		on_delete=models.CASCADE,
		related_name="workflow_instance",
		db_column="transaction_id",
	)
	template = models.ForeignKey(
		ApprovalWorkflowTemplate, on_delete=models.PROTECT, related_name="instances"
	)
	current_stage_template = models.ForeignKey(
		ApprovalWorkflowStageTemplate,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="active_instances",
	)
	status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING)
	started_at = models.DateTimeField(auto_now_add=True)
	finished_at = models.DateTimeField(null=True, blank=True)
	completed_stage_count = models.PositiveIntegerField(default=0)

	class Meta:
		db_table = "APPROVAL_WORKFLOW_INSTANCE"
		indexes = [
			models.Index(fields=["status", "current_stage_template"]),
		]

	def __str__(self):
		return f"WorkflowInstance for Transfer {self.budget_transfer_id} ({self.status})"

class ApprovalWorkflowStageInstance(models.Model):
	"""Concrete runtime stage tied to its template and parent instance."""

	STATUS_PENDING = "pending"
	STATUS_ACTIVE = "active"
	STATUS_COMPLETED = "completed"
	STATUS_SKIPPED = "skipped"
	STATUS_CANCELLED = "cancelled"
	STATUS_CHOICES = [
		(STATUS_PENDING, "Pending"),
		(STATUS_ACTIVE, "Active"),
		(STATUS_COMPLETED, "Completed"),
		(STATUS_SKIPPED, "Skipped"),
		(STATUS_CANCELLED, "Cancelled"),
	]

	workflow_instance = models.ForeignKey(
		ApprovalWorkflowInstance, related_name="stage_instances", on_delete=models.CASCADE
	)
	stage_template = models.ForeignKey(
		ApprovalWorkflowStageTemplate,
		related_name="stage_instances",
		on_delete=models.PROTECT,
	)
	status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING)
	activated_at = models.DateTimeField(null=True, blank=True)
	completed_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		db_table = "APPROVAL_WORKFLOW_STAGE_INSTANCE"
		ordering = ["workflow_instance", "stage_template__order_index"]
		indexes = [
			models.Index(fields=["workflow_instance", "status"]),
		]

	def __str__(self):
		return (
			f"StageInstance {self.stage_template.name} for Transfer {self.workflow_instance.budget_transfer_id}"
		)

	@property
	def is_terminal(self):
		return self.status in {self.STATUS_COMPLETED, self.STATUS_SKIPPED, self.STATUS_CANCELLED}

class ApprovalAssignment(models.Model):
    """Materialized eligible approvers for a given stage instance."""
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_DELEGATED = "delegated"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_DELEGATED, "Delegated"),
    ]
    stage_instance = models.ForeignKey(
        ApprovalWorkflowStageInstance, related_name="assignments", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
		"user_management.xx_User", related_name="approval_assignments", on_delete=models.CASCADE
    )
    role_snapshot = models.CharField(max_length=50, null=True, blank=True)
    level_snapshot = models.CharField(max_length=50, null=True, blank=True)
    is_mandatory = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "APPROVAL_ASSIGNMENT"
        unique_together = ("stage_instance", "user")
        indexes = [
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"Assignment {self.user_id} -> StageInstance {self.stage_instance_id}"

class ApprovalAction(models.Model):
    """Audit log of user actions within a stage instance."""

    ACTION_APPROVE = "approve"
    ACTION_REJECT = "reject"
    ACTION_DELEGATE = "delegate"
    ACTION_CHOICES = [
        (ACTION_APPROVE, "Approve"),
        (ACTION_REJECT, "Reject"),
        (ACTION_DELEGATE, "Delegate"),
    ]

    stage_instance = models.ForeignKey(
        ApprovalWorkflowStageInstance, related_name="actions", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
		"user_management.xx_User",
		related_name="approval_actions",
		on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Null for system actions (auto-cancel, auto-skip, etc.)",
    )

    assignment = models.OneToOneField(ApprovalAssignment, null=True, blank=True, on_delete=models.SET_NULL, related_name="action")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    triggers_stage_completion = models.BooleanField(default=False)

    class Meta:
        db_table = "APPROVAL_ACTION"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["stage_instance", "action"]),
        ]

    def __str__(self):
        return f"Action {self.action} by {self.user_id or 'SYSTEM'} on StageInstance {self.stage_instance_id}"

class ApprovalDelegation(models.Model):
	"""Optional delegation record (future extension)."""

	from_user = models.ForeignKey(
		"user_management.xx_User", related_name="delegations_given", on_delete=models.CASCADE
	)
	to_user = models.ForeignKey(
		"user_management.xx_User", related_name="delegations_received", on_delete=models.CASCADE
	)
	stage_instance = models.ForeignKey(
		ApprovalWorkflowStageInstance, related_name="delegations", on_delete=models.CASCADE
	)
	active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	deactivated_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		db_table = "APPROVAL_DELEGATION"
		indexes = [
			models.Index(fields=["active"]),
		]

	def __str__(self):
		return f"Delegation {self.from_user_id}->{self.to_user_id} (StageInstance {self.stage_instance_id})"

	def deactivate(self):
		if self.active:
			self.active = False
			self.deactivated_at = timezone.now()
			self.save(update_fields=["active", "deactivated_at"])
