from django.urls import path
from .views import (
    MainCurrencyListView, MainCurrencyCreateView, MainCurrencyDetailView, MainCurrencyUpdateView, MainCurrencyDeleteView,
    MainRoutesNameListView, MainRoutesNameCreateView, MainRoutesNameDetailView, MainRoutesNameUpdateView, MainRoutesNameDeleteView
)
 
urlpatterns = [
    
    path('main-currencies/', MainCurrencyListView.as_view(), name='main-currency-list'),
    path('main-currencies/create/', MainCurrencyCreateView.as_view(), name='main-currency-create'),
    path('main-currencies/<int:pk>/', MainCurrencyDetailView.as_view(), name='main-currency-detail'),
    path('main-currencies/<int:pk>/update/', MainCurrencyUpdateView.as_view(), name='main-currency-update'),
    path('main-currencies/<int:pk>/delete/', MainCurrencyDeleteView.as_view(), name='main-currency-delete'),
    
    # Main Routes Name URLs
    path('main-routes/', MainRoutesNameListView.as_view(), name='main-routes-list'),
    path('main-routes/create/', MainRoutesNameCreateView.as_view(), name='main-routes-create'),
    path('main-routes/<int:pk>/', MainRoutesNameDetailView.as_view(), name='main-routes-detail'),
    path('main-routes/<int:pk>/update/', MainRoutesNameUpdateView.as_view(), name='main-routes-update'),
    path('main-routes/<int:pk>/delete/', MainRoutesNameDeleteView.as_view(), name='main-routes-delete'),
]