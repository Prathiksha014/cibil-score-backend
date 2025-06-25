# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for viewsets
router = DefaultRouter()

urlpatterns = [
    # Main CIBIL score checking endpoint
    path('check-cibil-score/', views.check_cibil_score, name='check_cibil_score'),
    path('check-dynamic-cibil-score/', views.check_dynamic_cibil_score, name='check_dynamic_cibil_score'),
    
    # Customer management
    path('customers/', views.CustomerViewSet.as_view(), name='customer_list_create'),
    path('customers/<str:pan_card_number>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/<str:pan_card_number>/dashboard/', views.customer_dashboard, name='customer_dashboard'),
    
    # CIBIL score history
    path('customers/<str:pan_card_number>/cibil-history/', views.get_cibil_history, name='cibil_history'),
    
    # Financial data management
    path('customers/<str:pan_card_number>/bank-accounts/', views.BankAccountViewSet.as_view(), name='bank_accounts'),
    path('customers/<str:pan_card_number>/credit-cards/', views.CreditCardViewSet.as_view(), name='credit_cards'),
    path('customers/<str:pan_card_number>/loans/', views.LoanViewSet.as_view(), name='loans'),
    path('customers/<str:pan_card_number>/payment-history/', views.PaymentHistoryViewSet.as_view(), name='payment_history'),
    
    # Bulk data operations
    path('add-customer-data/', views.add_customer_data, name='add_customer_data'),
    
    # Generic endpoints
    path('bank-accounts/', views.BankAccountViewSet.as_view(), name='all_bank_accounts'),
    path('credit-cards/', views.CreditCardViewSet.as_view(), name='all_credit_cards'),
    path('loans/', views.LoanViewSet.as_view(), name='all_loans'),
    path('payment-history/', views.PaymentHistoryViewSet.as_view(), name='all_payment_history'),
]