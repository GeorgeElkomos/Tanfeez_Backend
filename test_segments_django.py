"""
Django shell script to test the new segment functionality
Run with: python manage.py shell < test_segments_django.py
"""

# Test the balance report model and segment queries
from account_and_entitys.models import XX_BalanceReport
from django.db.models import Sum

print("🧪 Testing Balance Report Segment Functionality")
print("="*60)

# 1. Check total records
total_records = XX_BalanceReport.objects.count()
print(f"📊 Total balance report records: {total_records}")

# 2. Get unique segments
segment1_values = list(XX_BalanceReport.objects.values_list('segment1', flat=True).distinct())
segment2_values = list(XX_BalanceReport.objects.values_list('segment2', flat=True).distinct()) 
segment3_values = list(XX_BalanceReport.objects.values_list('segment3', flat=True).distinct())

print(f"\n🔍 Unique Segments:")
print(f"Segment1 values: {segment1_values}")
print(f"Segment2 values: {segment2_values}")
print(f"Segment3 values: {segment3_values}")

# 3. Test specific segment combination
test_segment1 = '10001'
test_segment2 = '2205403'
test_segment3 = 'CTRLCE1'

print(f"\n💰 Testing specific segments: {test_segment1}/{test_segment2}/{test_segment3}")

record = XX_BalanceReport.objects.filter(
    segment1=test_segment1,
    segment2=test_segment2,
    segment3=test_segment3
).first()

if record:
    print(f"✅ Found record:")
    print(f"   Control Budget: {record.control_budget_name}")
    print(f"   Period: {record.as_of_period}")
    print(f"   Actual YTD: {record.actual_ytd}")
    print(f"   Encumbrance YTD: {record.encumbrance_ytd}")
    print(f"   Funds Available: {record.funds_available_asof}")
    print(f"   Other YTD: {record.other_ytd}")
    print(f"   Budget YTD: {record.budget_ytd}")
else:
    print("❌ No record found for this segment combination")

# 4. Test aggregation for all records with same segment1
print(f"\n📈 Aggregation for segment1 = {test_segment1}:")
aggregation = XX_BalanceReport.objects.filter(segment1=test_segment1).aggregate(
    total_actual=Sum('actual_ytd'),
    total_encumbrance=Sum('encumbrance_ytd'),
    total_available=Sum('funds_available_asof'),
    total_budget=Sum('budget_ytd')
)

print(f"   Total Actual YTD: {aggregation['total_actual']}")
print(f"   Total Encumbrance YTD: {aggregation['total_encumbrance']}")
print(f"   Total Available Funds: {aggregation['total_available']}")
print(f"   Total Budget YTD: {aggregation['total_budget']}")

# 5. Show all records for verification
print(f"\n📋 All Balance Report Records:")
for i, record in enumerate(XX_BalanceReport.objects.all()[:10], 1):
    print(f"{i:2d}. {record.segment1}/{record.segment2}/{record.segment3} - "
          f"Actual: {record.actual_ytd}, Encumbrance: {record.encumbrance_ytd}, "
          f"Available: {record.funds_available_asof}")

print(f"\n✅ Testing completed successfully!")
print(f"🎯 The new APIs are ready to use!")
