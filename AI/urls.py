from django.urls import path

from .views import (
    AnalyzeView
)


urlpatterns = [
    path("Tnfeez_Analyzer/", AnalyzeView.as_view(), name="analyze"),
]
