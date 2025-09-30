from django.db import models

from approvals.models import ApprovalWorkflowInstance

# Removed encrypted fields import - using standard Django fields now


class XX_Account(models.Model):
    """Model representing ADJD accounts"""

    account = models.CharField(max_length=50, unique=False)
    parent = models.CharField(
        max_length=50, null=True, blank=True
    )  # Changed from EncryptedCharField
    alias_default = models.CharField(
        max_length=255, null=True, blank=True
    )  # Changed from EncryptedCharField

    def __str__(self):
        return str(self.account)

    class Meta:
        db_table = "XX_ACCOUNT_XX"


class XX_Entity(models.Model):
    """Model representing ADJD entities"""

    entity = models.CharField(max_length=50, unique=False)
    parent = models.CharField(
        max_length=50, null=True, blank=True
    )  # Changed from EncryptedCharField
    alias_default = models.CharField(
        max_length=255, null=True, blank=True
    )  # Changed from EncryptedCharField

    def __str__(self):
        return str(self.entity)

    class Meta:
        db_table = "XX_ENTITY_XX"


class XX_Project(models.Model):
    """Model representing ADJD entities"""

    project = models.CharField(max_length=50, unique=False)
    parent = models.CharField(
        max_length=50, null=True, blank=True
    )  # Changed from EncryptedCharField
    alias_default = models.CharField(
        max_length=255, null=True, blank=True
    )  # Changed from EncryptedCharField

    def __str__(self):
        return str(self.project)

    class Meta:
        db_table = "XX_PROJECT_XX"


class Project_Envelope(models.Model):
    """Model representing ADJD entities"""

    project = models.CharField(max_length=50, unique=False)
    envelope = models.DecimalField(
        max_digits=30, decimal_places=2
    )  # Changed from EncryptedCharField

    def __str__(self):
        return str(self.project)

    class Meta:
        db_table = "XX_PROJECT_ENVELOPE_XX"


class Account_Mapping(models.Model):
    """Model representing ADJD account mappings"""

    source_account = models.CharField(max_length=50, unique=False)
    target_account = models.CharField(max_length=50, unique=False)

    def __str__(self):
        return f"{self.source_account} -> {self.target_account}"

    class Meta:
        db_table = "XX_ACCOUNT_MAPPING_LEGACY_XX"
        unique_together = ("source_account", "target_account")


class Budget_data(models.Model):
    project = models.CharField(max_length=50, unique=False)
    account = models.CharField(max_length=50, unique=False)
    FY24_budget = models.DecimalField(max_digits=30, decimal_places=2)
    FY25_budget = models.DecimalField(max_digits=30, decimal_places=2)

    class Meta:
        db_table = "BUDGET_DATA_XX"
        unique_together = ("project", "account")


class EnvelopeManager:
    @staticmethod
    def Has_Envelope(project_code):
        try:
            envelope_record = Project_Envelope.objects.get(project=project_code)
            return True
        except Project_Envelope.DoesNotExist:
            return False

    @staticmethod
    def Get_Envelope(project_code):
        try:
            envelope_record = Project_Envelope.objects.get(project=project_code)
            return envelope_record.envelope
        except Project_Envelope.DoesNotExist:
            return 0

    @staticmethod
    def __get_project_parent_code(project_code):
        try:
            parent_project = XX_Project.objects.get(project=project_code)
            return parent_project.parent
        except XX_Project.DoesNotExist:
            return None

    @staticmethod
    def get_all_children(all_projects, curr_code, visited=None):
        """Recursively get all descendants of a project code with cycle protection."""
        if visited is None:
            visited = set()
        if curr_code in visited:
            return []
        visited.add(curr_code)

        direct_children = list(
            all_projects.filter(parent=curr_code).values_list("project", flat=True)
        )

        descendants = []
        for child in direct_children:
            if child in visited:
                continue
            descendants.append(child)
            descendants.extend(
                EnvelopeManager.get_all_children(all_projects, child, visited)
            )
        return descendants

    @staticmethod
    def get_all_children_for_accounts(all_accounts, curr_code, visited=None):
        """Recursively get all descendants of an account code with cycle protection."""
        if visited is None:
            visited = set()
        if curr_code in visited:
            return []
        visited.add(curr_code)

        direct_children = list(
            all_accounts.filter(parent=curr_code).values_list("account", flat=True)
        )

        descendants = []
        for child in direct_children:
            if child in visited:
                continue
            descendants.append(child)
            descendants.extend(
                EnvelopeManager.get_all_children_for_accounts(
                    all_accounts, child, visited
                )
            )
        return descendants

    @staticmethod
    def __get_all_level_zero_children_code(project_code):
        """
        Get all leaf node project codes that are descendants of the given project_code.
        A leaf node is a project that has no children (no other projects have it as their parent).

        Args:
            project_code (str): The project code to find leaf descendants for

        Returns:
            list: List of project codes that are leaf nodes under the given project_code
        """
        try:
            # First verify the parent project exists
            XX_Project.objects.get(project=project_code)

            # Get all projects
            all_projects = XX_Project.objects.all()

            # Get all parent codes to identify which projects are not parents
            parent_codes = set(
                all_projects.exclude(parent__isnull=True)
                .values_list("parent", flat=True)
                .distinct()
            )

            # Get all descendants of the given project_code
            all_descendants = EnvelopeManager.get_all_children(
                all_projects, project_code
            )

            # Filter to only include descendants that are not parents themselves
            leaf_nodes = [code for code in all_descendants if code not in parent_codes]

            return leaf_nodes

        except XX_Project.DoesNotExist:
            return []

    @staticmethod
    def __get_all_children_codes(project_code):
        try:
            XX_Project.objects.only("project").get(project=project_code)

            pairs = XX_Project.objects.values_list("project", "parent")
            children_map = {}
            for proj, parent in pairs:
                children_map.setdefault(parent, []).append(proj)

            result = []
            stack = list(children_map.get(project_code, []))
            while stack:
                node = stack.pop()
                result.append(node)
                stack.extend(children_map.get(node, []))
            return result
        except XX_Project.DoesNotExist:
            return []

    @staticmethod
    def Get_First_Parent_Envelope(project_code):
        while project_code:
            try:
                if EnvelopeManager.Has_Envelope(project_code):
                    return project_code, EnvelopeManager.Get_Envelope(project_code)
                else:
                    project_code = EnvelopeManager.__get_project_parent_code(
                        project_code
                    )
            except XX_Project.DoesNotExist:
                project_code = None
        return None, None

    @staticmethod
    def Get_Envelope_Amount(project_code):
        envelope_amount = EnvelopeManager.Get_Envelope(project_code)
        if envelope_amount:
            return envelope_amount
        return 0

    @staticmethod
    def Get_Total_Amount_for_Project(
        project_code, year=None, month=None, FilterAccounts=True
    ):
        try:
            from django.db.models import Sum, F, Value, Q
            from django.db.models.functions import Coalesce
            import calendar

            # Import here to avoid circular import at module import time
            from transaction.models import xx_TransactionTransfer

            if FilterAccounts:
                accounts = [
                    "TC11100T",  # Men Power
                    "TC11200T",  # Non Men Power
                    "TC13000T",  # Copex
                ]
                all_accounts = []
                for account in accounts:
                    all_accounts.append(account)
                    all_accounts.extend(
                        EnvelopeManager.get_all_children_for_accounts(
                            XX_Account.objects.all(), account
                        )
                    )
                for account in all_accounts:
                    if Account_Mapping.objects.filter(target_account=account).exists():
                        mapped_accounts = Account_Mapping.objects.filter(
                            target_account=account
                        ).values_list("source_account", flat=True)
                        all_accounts.extend(list(mapped_accounts))
                base_transactions = xx_TransactionTransfer.objects.filter(
                    project_code=project_code, account_code__in=all_accounts
                )
                # Start with base filter for project code
            else:
                base_transactions = xx_TransactionTransfer.objects.filter(
                    project_code=project_code
                )

            print(
                f"Base transactions count for project {project_code}: {base_transactions.count()}"
            )
            # Apply date filtering based on provided parameters
            if year is not None:
                base_transactions = base_transactions.filter(transaction__fy=year)

            if month is not None:
                month_abbr = calendar.month_abbr[
                    month
                ]  # Convert month number to abbreviation
                base_transactions = base_transactions.filter(
                    transaction__transaction_date=month_abbr
                )

            # Get approved transactions
            approved_transactions = base_transactions.filter(
                transaction__workflow_instance__status=ApprovalWorkflowInstance.STATUS_APPROVED
            )
            print(
                f"Approved transactions count for project {project_code}: {approved_transactions.count()}"
            )
            # Get submitted (in progress) transactions
            submitted_transactions = base_transactions.filter(
                transaction__workflow_instance__status=ApprovalWorkflowInstance.STATUS_IN_PROGRESS
            )
            print(
                f"Submitted transactions count for project {project_code}: {submitted_transactions.count()}"
            )
            # Calculate totals for approved transactions
            approved_result = approved_transactions.aggregate(
                total_from=Coalesce(
                    Sum("from_center"), Value(0, output_field=models.DecimalField())
                ),
                total_to=Coalesce(
                    Sum("to_center"), Value(0, output_field=models.DecimalField())
                ),
            )
            approved = {}
            approved["total_from"] = approved_result["total_from"] * -1
            approved["total_to"] = approved_result["total_to"]
            approved["total"] = approved["total_from"] + approved["total_to"]

            # Calculate totals for submitted transactions
            submitted_result = submitted_transactions.aggregate(
                total_from=Coalesce(
                    Sum("from_center"), Value(0, output_field=models.DecimalField())
                ),
                total_to=Coalesce(
                    Sum("to_center"), Value(0, output_field=models.DecimalField())
                ),
            )
            submitted = {}
            submitted["total_from"] = submitted_result["total_from"] * -1
            submitted["total_to"] = submitted_result["total_to"]
            submitted["total"] = submitted["total_from"] + submitted["total_to"]

            return approved, submitted

        except Exception as e:
            print(f"Error calculating total amount for project {project_code}: {e}")
            return None, None

    @staticmethod
    def Get_Active_Projects(project_codes=None, year=None, month=None):
        """Return a list of distinct project codes used by transactions.

        Params:
            project_codes: optional list of project codes to filter by. If provided, only projects
                         from this list that have transactions will be returned.
            year: optional fiscal year (int or numeric string) — filters on transaction__fy
            month: optional month (int 1-12 or 3-letter abbreviation like 'Jan') — filters on transaction__transaction_date
            IsApproved: if True only include transactions whose parent budget transfer's workflow instance status is APPROVED,
                        otherwise include those in IN_PROGRESS.

        Returns:
            list of project_code strings (empty list on error)
        """
        try:
            import calendar

            # Import here to avoid circular import at module import time
            from transaction.models import xx_TransactionTransfer

            # desired_status = (
            #     ApprovalWorkflowInstance.STATUS_APPROVED
            #     if IsApproved
            #     else ApprovalWorkflowInstance.STATUS_IN_PROGRESS
            # )

            # transactions = xx_TransactionTransfer.objects.filter(
            #     transaction__workflow_instance__status=desired_status
            # )
            transactions = xx_TransactionTransfer.objects.all()
            # Filter by provided project codes if any
            if project_codes:
                transactions = transactions.filter(project_code__in=project_codes)

            # Apply year filter if provided
            if year is not None and year != "":
                try:
                    year_int = int(year)
                    transactions = transactions.filter(transaction__fy=year_int)
                except Exception:
                    # invalid year value; ignore filter but log
                    print(
                        f"Get_Active_Projects: invalid year value '{year}', skipping year filter"
                    )

            # Apply month filter if provided; accept month as int or 3-letter name
            if month is not None and month != "":
                month_abbr = None
                try:
                    if isinstance(month, str):
                        m = month.strip()
                        if len(m) == 3:
                            month_abbr = m[:3]
                        else:
                            month_int = int(m)
                            if 1 <= month_int <= 12:
                                month_abbr = calendar.month_abbr[month_int]
                    else:
                        month_int = int(month)
                        if 1 <= month_int <= 12:
                            month_abbr = calendar.month_abbr[month_int]
                except Exception:
                    print(
                        f"Get_Active_Projects: invalid month value '{month}', skipping month filter"
                    )

                if month_abbr:
                    transactions = transactions.filter(
                        transaction__transaction_date=month_abbr
                    )

            # Return plain list of distinct project codes
            project_qs = transactions.values_list("project_code", flat=True).distinct()
            return list(project_qs)

        except Exception as e:
            # Don't raise to avoid breaking import-time usage; log and return empty list
            print(f"Error in Get_Active_Projects: {e}")
            return []

    @staticmethod
    def Get_Current_Envelope_For_Project(project_code, year=None, month=None):
        try:
            parent_project, envelope = EnvelopeManager.Get_First_Parent_Envelope(
                project_code
            )
            if envelope is None:
                return None
            Children_projects = EnvelopeManager.__get_all_level_zero_children_code(
                parent_project
            )
            active_projects = EnvelopeManager.Get_Active_Projects(
                project_codes=Children_projects, year=year, month=month
            )

            # Initialize dictionary to store results for all projects
            projects_totals = {}

            # Get totals for each active project
            for proj in active_projects:
                approved, submitted = EnvelopeManager.Get_Total_Amount_for_Project(
                    proj, year=year, month=month
                )
                projects_totals[proj] = {
                    "approved": (
                        approved
                        if approved
                        else {"total": 0, "total_from": 0, "total_to": 0}
                    ),
                    "submitted": (
                        submitted
                        if submitted
                        else {"total": 0, "total_from": 0, "total_to": 0}
                    ),
                }

            current_envelope = envelope
            estimated_envelope = envelope
            for proj, totals in projects_totals.items():
                current_envelope += totals["approved"]["total"]
                estimated_envelope += totals["approved"]["total"]
                estimated_envelope += totals["submitted"]["total"]
            return {
                "initial_envelope": envelope,
                "current_envelope": current_envelope,
                "estimated_envelope": estimated_envelope,
                "project_totals": projects_totals,
            }
        except Project_Envelope.DoesNotExist:
            return None

    @staticmethod
    def Get_Budget_for_Project(project_code):
        from django.db.models import Sum

        budget_totals = Budget_data.objects.filter(project=project_code).aggregate(
            FY24_total=Sum("FY24_budget"), FY25_total=Sum("FY25_budget")
        )
        return {
            "FY24_budget": budget_totals["FY24_total"] or 0,
            "FY25_budget_initial": budget_totals["FY25_total"] or 0,
        }

    @staticmethod
    def Get_Total_Amount_for_Entity(entity_code):
        try:
            from django.db.models import Sum, F, Value, Q
            from django.db.models.functions import Coalesce
            import calendar

            # Import here to avoid circular import at module import time
            from transaction.models import xx_TransactionTransfer

            base_transactions = xx_TransactionTransfer.objects.filter(
                cost_center_code=entity_code,
            )
            project_codes = list(
                base_transactions.values_list("project_code", flat=True).distinct()
            )

            data = {}
            for proj in project_codes:
                # Get transaction totals
                approved, submitted = EnvelopeManager.Get_Total_Amount_for_Project(
                    proj, FilterAccounts=False
                )
                if approved is None or submitted is None:
                    continue

                # Get budget data
                budget_data = EnvelopeManager.Get_Budget_for_Project(proj)

                data[proj] = {
                    # FY24 data
                    "FY24_budget": budget_data.get("FY24_budget", 0),
                    # FY25 data
                    "FY25_budget_current": budget_data.get("FY25_budget_initial", 0)
                    + approved["total"],
                    "variances": budget_data.get("FY24_budget", 0)
                    - (budget_data.get("FY25_budget_initial", 0)
                     + approved["total"]),
                }
            return data

        except Exception as e:
            print(f"Error calculating total amount for entity {entity_code}: {e}")
            return None, None

    @staticmethod
    def Get_Dashboard_Data_For_Entity(entity_code):
        result = EnvelopeManager.Get_Total_Amount_for_Entity(entity_code)
        if not result:
            return []

        dashboard_data = []
        for project_code, project_data in result.items():
            dashboard_data.append(
                {
                    "project_code": project_code,
                    "project_name": XX_Project.objects.get(
                        project=project_code
                    ).alias_default
                    or project_code,
                    "FY24_budget": project_data["FY24_budget"],
                    "FY25_budget_current": project_data["FY25_budget_current"],
                    "variances": project_data["variances"],
                }
            )

        return dashboard_data


class XX_PivotFund(models.Model):
    """Model representing ADJD pivot funds"""

    entity = models.CharField(max_length=50)
    account = models.CharField(max_length=50)
    project = models.CharField(max_length=50, null=True, blank=True)
    year = models.IntegerField()
    actual = models.DecimalField(
        max_digits=30, decimal_places=2, null=True, blank=True
    )  # Changed from EncryptedCharField to DecimalField
    fund = models.DecimalField(
        max_digits=30, decimal_places=2, null=True, blank=True
    )  # Changed from EncryptedCharField to DecimalField
    budget = models.DecimalField(
        max_digits=30, decimal_places=2, null=True, blank=True
    )  # Changed from EncryptedCharField to DecimalField
    encumbrance = models.DecimalField(
        max_digits=30, decimal_places=2, null=True, blank=True
    )  # Changed from EncryptedCharField to DecimalField

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["entity", "account", "project", "year"],
                name="unique_entity_account_year",
            )
        ]
        db_table = "XX_PIVOTFUND_XX"


class XX_TransactionAudit(models.Model):
    """Model representing ADJD transaction audit records"""

    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=50, null=True, blank=True)
    transfer_id = models.IntegerField(null=True, blank=True)
    transcation_code = models.CharField(max_length=50, null=True, blank=True)
    cost_center_code = models.CharField(max_length=50, null=True, blank=True)
    account_code = models.CharField(max_length=50, null=True, blank=True)
    project_code = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"Audit {self.id}: {self.transcation_code}"

    class Meta:
        db_table = "XX_TRANSACTION_AUDIT_XX"


class XX_ACCOUNT_ENTITY_LIMIT(models.Model):
    """Model representing ADJD account entity limits"""

    id = models.AutoField(primary_key=True)
    account_id = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=50)
    project_id = models.CharField(max_length=50, null=True, blank=True)
    is_transer_allowed_for_source = models.CharField(
        max_length=255, null=True, blank=True
    )  # Changed from EncryptedBooleanField
    is_transer_allowed_for_target = models.CharField(
        max_length=255, null=True, blank=True
    )  # Changed from EncryptedBooleanField
    is_transer_allowed = models.CharField(
        max_length=255, null=True, blank=True
    )  # Changed from EncryptedBooleanField
    source_count = models.IntegerField(
        null=True, blank=True
    )  # Changed from EncryptedIntegerField
    target_count = models.IntegerField(
        null=True, blank=True
    )  # Changed from EncryptedIntegerField

    def __str__(self):
        return f"Account Entity Limit {self.id}"

    class Meta:
        db_table = "XX_ACCOUNT_ENTITY_LIMIT_XX"
        unique_together = ("account_id", "entity_id")


class XX_BalanceReport(models.Model):
    """Model representing balance report data from report.xlsx"""

    id = models.AutoField(primary_key=True)
    control_budget_name = models.CharField(
        max_length=100, null=True, blank=True, help_text="Control Budget Name"
    )
    ledger_name = models.CharField(
        max_length=100, null=True, blank=True, help_text="Ledger Name"
    )
    as_of_period = models.CharField(
        max_length=20, null=True, blank=True, help_text="As of Period (e.g., Sep-25)"
    )
    segment1 = models.CharField(
        max_length=50, null=True, blank=True, help_text="Segment 1 (Cost Center)"
    )
    segment2 = models.CharField(
        max_length=50, null=True, blank=True, help_text="Segment 2 (Account)"
    )
    segment3 = models.CharField(
        max_length=50, null=True, blank=True, help_text="Segment 3 (Project)"
    )
    encumbrance_ytd = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Encumbrance Year to Date",
    )
    other_ytd = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Other Year to Date",
    )
    actual_ytd = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual Year to Date",
    )
    funds_available_asof = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Funds Available As Of",
    )
    budget_ytd = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Budget Year to Date",
    )

    # Additional metadata fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Balance Report: {self.control_budget_name} - {self.segment1}/{self.segment2}/{self.segment3}"

    class Meta:
        db_table = "XX_BALANCE_REPORT_XX"
        verbose_name = "Balance Report"
        verbose_name_plural = "Balance Reports"
        indexes = [
            models.Index(fields=["control_budget_name", "as_of_period"]),
            models.Index(fields=["segment1", "segment2", "segment3"]),
            models.Index(fields=["as_of_period"]),
        ]


class XX_ACCOUNT_mapping(models.Model):
    """Model representing ADJD account mappings"""
    id = models.AutoField(primary_key=True)
    source_account = models.CharField(max_length=50)
    target_account = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Account Mapping {self.id}: {self.source_account} -> {self.target_account}"

    class Meta:
        db_table = 'XX_ACCOUNT_MAPPING__elies_XX'
        unique_together = ('source_account', 'target_account')


class XX_Entity_mapping(models.Model):
    """Model representing ADJD entity mappings"""
    id = models.AutoField(primary_key=True)
    source_entity = models.CharField(max_length=50)
    target_entity = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Entity Mapping {self.id}: {self.source_entity} -> {self.target_entity}"

    class Meta:
        db_table = 'XX_ENTITY_MAPPING__elies_XX'
        unique_together = ('source_entity', 'target_entity')
