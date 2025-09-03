from account_and_entitys.models import XX_PivotFund
from decimal import Decimal  # Add this import

def update_pivot_fund(cost_center_code, account_code, project_code, from_center, to_center, decide):
    """
    Update the pivot fund for a given cost center and account with the from_center amount.
    Returns a dict with update status and information.
    """
    try:
        # Convert values to Decimal to ensure type compatibility
        from_center_dec = Decimal(str(from_center)) if from_center is not None else Decimal('0')
        to_center_dec = Decimal(str(to_center)) if to_center is not None else Decimal('0')

        print(f"cost_center_code: {cost_center_code}")
        print(f"account_code: {account_code}")
        print(f"project_code: {project_code}")
        print(f"from_center: {from_center}")
        print(f"to_center: {to_center}")

        pivot_fund = XX_PivotFund.objects.get(entity=cost_center_code, account=account_code, project=project_code)
        pivot_fund.encumbrance = Decimal(str(pivot_fund.encumbrance).strip()) if pivot_fund.encumbrance not in [None, '', ' '] else Decimal('0')
        pivot_fund.actual = Decimal(str(pivot_fund.actual).strip()) if pivot_fund.actual not in [None, '', ' '] else Decimal('0')

        print(f"Pivot fund found: ////////////")
        print(f"Pivot fund found: {pivot_fund}")
        print(f"Pivot fund found: ////////////")

        # Store old value before changes for reporting
        old_encumbrance = pivot_fund.encumbrance

        # decide =1 when sent for approvel
        print(f"decide: {decide}")
        if decide == 1:
            print(f"from_center_dec: {from_center_dec}")
            print(f"encumbrance: {pivot_fund.encumbrance}")
            pivot_fund.encumbrance += from_center_dec
        # decide = 2 when approved
        elif decide == 2:
            if from_center_dec > 0:
                print(f"from_center_dec: {from_center_dec}")
                print(f"encumbrance: {pivot_fund.encumbrance}")
                pivot_fund.encumbrance -= from_center_dec
            elif to_center_dec > 0:
                pivot_fund.actual += to_center_dec
        # decide = 3 when rejcted
        elif decide == 3:  # Changed to elif to avoid multiple executions
            if from_center_dec > 0:
                pivot_fund.encumbrance += from_center_dec

        print(f"Pivot fund updated: {pivot_fund}")

        pivot_fund.save()
        print("finish")

        return {
            "cost_center_code": cost_center_code,
            "account_code": account_code,
            "project_code": project_code,
            "from_center": from_center,
            "status": "updated seccessfully",
            "encumbrance_old_value": old_encumbrance,
            "encumbrance_new_value": pivot_fund.encumbrance,
        }

    except XX_PivotFund.DoesNotExist:
        # Handle the case where the pivot fund does not exist
        return {
            "cost_center_code": cost_center_code,
            "account_code": account_code,
            "project_code": project_code,
            "from_center": from_center,
            "status": "failed",
            "error": "Pivot fund not found",
        }
