"""
Django signals package for budget_management app
This file registers all signal modules when the app starts
"""

# Import all signal modules to register them with Django
try:
    from . import budget_trasnfer
    print("✓ Budget transfer signals imported successfully")
except ImportError as e:
    print(f"✗ Error importing budget transfer signals: {e}")
except Exception as e:
    print(f"✗ Unexpected error loading budget transfer signals: {e}")

# You can add more signal imports here in the future
# from . import other_signals_file