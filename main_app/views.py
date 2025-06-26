# views.py
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import JsonResponse
from datetime import datetime, timedelta
from .models import (
    Customer, BankAccount, CreditCard, Loan, 
    PaymentHistory, CibilScore, CibilReport
)
from .serializers import (
    CustomerSerializer, CibilScoreSerializer, CibilReportSerializer,
    CibilScoreRequestSerializer, BankAccountSerializer,
    CreditCardSerializer, LoanSerializer, PaymentHistorySerializer
)
from .cibil_calculator import UserInputCibilCalculator  # Import the new calculator
# from .cibil_calculator import  CibilScoreCalculator

class CustomerViewSet(generics.ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [AllowAny]

class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    lookup_field = 'pan_card_number'
    permission_classes = [AllowAny]

@api_view(['GET'])
@permission_classes([AllowAny])
def test_connection(request):
    print(f'Ping from: {request.method}')
    return JsonResponse({'message': 'Backend is working!'})

@api_view(['POST'])
@permission_classes([AllowAny])
def check_dynamic_cibil_score(request):
    pan_card_number = request.data.get('pan_card_number')
    custom_weights = request.data.get('custom_weights', {})
    return process_cibil_score(pan_card_number, custom_weights)

def process_cibil_score(pan_card_number, custom_weights):
    # Validate PAN
    if not pan_card_number:
        return Response({'error': 'PAN card number is required'}, status=status.HTTP_400_BAD_REQUEST)

    valid_factors = ['payment_history', 'credit_utilization', 'credit_history_length', 'credit_mix', 'new_credit']
    try:
        for factor, weight in custom_weights.items():
            if factor not in valid_factors:
                return Response(
                    {'error': f'Invalid factor: {factor}. Valid factors are: {valid_factors}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if float(weight) < 0 or float(weight) > 100:
                return Response(
                    {'error': f'Weight for {factor} must be between 0 and 100'},
                    status=status.HTTP_400_BAD_REQUEST
                )
    except Exception as e:
        return Response({'error': 'Invalid weight format', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    customer = get_object_or_404(Customer, pan_card_number=pan_card_number)

    try:
        calculator = UserInputCibilCalculator(customer, custom_weights)
        new_score, _ = calculator.calculate_dynamic_cibil_score(commit=False)
        new_score.customer = customer
        new_score.is_latest = True

        with transaction.atomic():
            CibilScore.objects.filter(customer=customer, is_latest=True).update(is_latest=False)
            new_score.save()

        breakdown = calculator.get_comprehensive_score_breakdown()

        return Response({
            'pan_card_number': pan_card_number,
            'customer': {
                'full_name': customer.full_name,
                'email': customer.email,
                'phone': customer.phone_number,
                'pan_card_number': customer.pan_card_number
            },
            'cibil_score_summary': {
                'final_score': breakdown['final_cibil_score'],
                'base_score': breakdown['base_cibil_score'],
                'score_range': {
                    'minimum_possible': breakdown['dynamic_range']['min_score'],
                    'maximum_possible': breakdown['dynamic_range']['max_score'],
                    'range_width': breakdown['dynamic_range']['range_width']
                },
                'score_grade': get_cibil_grade(breakdown['final_cibil_score']),
                'improvement_potential': breakdown['summary']['improvement_potential']
            },
            'weight_configuration': {
                'custom_weights_applied': bool(custom_weights),
                'weights_used': breakdown['custom_weights'],
                'weights_normalized': True
            },
            'detailed_breakdown': breakdown,
            'calculation_metadata': {
                'calculation_date': new_score.score_date.isoformat(),
                'dynamic_range_applied': True,
                'behavioral_adjustments_applied': True,
                'algorithm_version': '2.0_dynamic'
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': 'Failed to calculate dynamic CIBIL score', 'details': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_cibil_grade(score):
    """Convert CIBIL score to letter grade"""
    if score >= 800:
        return "A+"
    elif score >= 750:
        return "A"
    elif score >= 700:
        return "B+"
    elif score >= 650:
        return "B"
    elif score >= 600:
        return "C+"
    elif score >= 550:
        return "C"
    elif score >= 500:
        return "D+"
    elif score >= 450:
        return "D"
    else:
        return "F"

# Alternative endpoint for backward compatibility
@api_view(['POST'])
@permission_classes([AllowAny])
def check_cibil_score(request):
    pan_card_number = request.data.get('pan_card_number')
    return process_cibil_score(pan_card_number, custom_weights={})



@api_view(['GET'])
@permission_classes([AllowAny])
def get_cibil_history(request, pan_card_number):
    """
    Get CIBIL score history for a customer
    """
    try:
        customer = get_object_or_404(Customer, pan_card_number=pan_card_number)
        cibil_scores = CibilScore.objects.filter(customer=customer).order_by('-score_date')
        
        serializer = CibilScoreSerializer(cibil_scores, many=True)
        return Response({
            'customer': customer.full_name,
            'pan_card_number': pan_card_number,
            'score_history': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )

class BankAccountViewSet(generics.ListCreateAPIView):
    serializer_class = BankAccountSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        pan_card_number = self.kwargs.get('pan_card_number')
        if pan_card_number:
            customer = get_object_or_404(Customer, pan_card_number=pan_card_number)
            return BankAccount.objects.filter(customer=customer)
        return BankAccount.objects.all()

class CreditCardViewSet(generics.ListCreateAPIView):
    serializer_class = CreditCardSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        pan_card_number = self.kwargs.get('pan_card_number')
        if pan_card_number:
            customer = get_object_or_404(Customer, pan_card_number=pan_card_number)
            return CreditCard.objects.filter(customer=customer)
        return CreditCard.objects.all()

class LoanViewSet(generics.ListCreateAPIView):
    serializer_class = LoanSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        pan_card_number = self.kwargs.get('pan_card_number')
        if pan_card_number:
            customer = get_object_or_404(Customer, pan_card_number=pan_card_number)
            return Loan.objects.filter(customer=customer)
        return Loan.objects.all()

class PaymentHistoryViewSet(generics.ListCreateAPIView):
    serializer_class = PaymentHistorySerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        pan_card_number = self.kwargs.get('pan_card_number')
        if pan_card_number:
            customer = get_object_or_404(Customer, pan_card_number=pan_card_number)
            return PaymentHistory.objects.filter(customer=customer).order_by('-due_date')
        return PaymentHistory.objects.all()


@api_view(['POST'])
@permission_classes([AllowAny])
def add_customer_data(request):
    """
    Bulk add customer financial data
    """
    try:
        with transaction.atomic():
            # Extract customer data
            customer_data = request.data.get('customer')
            bank_accounts = request.data.get('bank_accounts', [])
            credit_cards = request.data.get('credit_cards', [])
            loans = request.data.get('loans', [])
            payment_history = request.data.get('payment_history', [])
            
            # Create or get customer
            customer, created = Customer.objects.get_or_create(
                pan_card_number=customer_data['pan_card_number'],
                defaults=customer_data
            )
            
            # Add bank accounts
            for account_data in bank_accounts:
                account_data['customer'] = customer.id
                BankAccount.objects.create(**account_data)
            
            # Add credit cards
            for card_data in credit_cards:
                card_data['customer'] = customer.id
                CreditCard.objects.create(**card_data)
            
            # Add loans
            for loan_data in loans:
                loan_data['customer'] = customer.id
                Loan.objects.create(**loan_data)
            
            # Add payment history
            for payment_data in payment_history:
                payment_data['customer'] = customer.id
                PaymentHistory.objects.create(**payment_data)
            
            return Response({
                'message': 'Customer data added successfully',
                'customer': CustomerSerializer(customer).data
            }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        return Response({
            'error': 'Failed to add customer data',
            'details': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def customer_dashboard(request, pan_card_number):
    """
    Get complete customer dashboard with all financial information
    """
    try:
        customer = get_object_or_404(Customer, pan_card_number=pan_card_number)
        
        # Get all related data
        bank_accounts = BankAccount.objects.filter(customer=customer)
        credit_cards = CreditCard.objects.filter(customer=customer)
        loans = Loan.objects.filter(customer=customer)
        payment_history = PaymentHistory.objects.filter(customer=customer).order_by('-due_date')[:10]
        latest_cibil_score = CibilScore.objects.filter(customer=customer, is_latest=True).first()
        
        # Calculate summary statistics
        total_credit_limit = sum(card.credit_limit for card in credit_cards if card.is_active)
        total_credit_used = sum(card.current_balance for card in credit_cards if card.is_active)
        total_loan_outstanding = sum(loan.outstanding_amount for loan in loans if loan.status == 'ACTIVE')
        
        utilization_ratio = 0
        if total_credit_limit > 0:
            utilization_ratio = (total_credit_used / total_credit_limit) * 100
        
        dashboard_data = {
            'customer': CustomerSerializer(customer).data,
            'summary': {
                'total_bank_accounts': bank_accounts.count(),
                'active_credit_cards': credit_cards.filter(is_active=True).count(),
                'active_loans': loans.filter(status='ACTIVE').count(),
                'total_credit_limit': float(total_credit_limit),
                'total_credit_used': float(total_credit_used),
                'credit_utilization_ratio': round(utilization_ratio, 2),
                'total_loan_outstanding': float(total_loan_outstanding),
            },
            'bank_accounts': BankAccountSerializer(bank_accounts, many=True).data,
            'credit_cards': CreditCardSerializer(credit_cards, many=True).data,
            'loans': LoanSerializer(loans, many=True).data,
            'recent_payments': PaymentHistorySerializer(payment_history, many=True).data,
            'latest_cibil_score': CibilScoreSerializer(latest_cibil_score).data if latest_cibil_score else None
        }
        
        return Response(dashboard_data, status=status.HTTP_200_OK)
        
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )

def generate_cibil_report(cibil_score):
    """
    Generate detailed CIBIL report based on score
    """
    customer = cibil_score.customer
    score = cibil_score.score
    
    # Generate report summary
    summary = f"""
    CIBIL Score Report for {customer.full_name}
    PAN: {customer.pan_card_number}
    Score: {score} ({cibil_score.get_score_category()})
    Report Date: {cibil_score.score_date.strftime('%Y-%m-%d')}
    
    Score Breakdown:
    - Payment History: {cibil_score.payment_history_score}% (Weight: 35%)
    - Credit Utilization: {cibil_score.credit_utilization_score}% (Weight: 30%)
    - Credit History Length: {cibil_score.credit_history_length_score}% (Weight: 15%)
    - Credit Mix: {cibil_score.credit_mix_score}% (Weight: 10%)
    - New Credit: {cibil_score.new_credit_score}% (Weight: 10%)
    
    Account Summary:
    - Total Accounts: {cibil_score.total_accounts}
    - Active Accounts: {cibil_score.active_accounts}
    - Total Credit Limit: ₹{cibil_score.total_credit_limit:,.2f}
    - Total Outstanding: ₹{cibil_score.total_outstanding:,.2f}
    - Credit Utilization: {cibil_score.credit_utilization_ratio}%
    """
    
    # Generate recommendations
    recommendations = []
    risk_factors = []
    positive_factors = []
    
    if cibil_score.payment_history_score < 70:
        risk_factors.append("Payment history needs improvement")
        recommendations.append("Make all payments on time to improve payment history")
    else:
        positive_factors.append("Good payment history")
    
    if cibil_score.credit_utilization_ratio > 30:
        risk_factors.append("High credit utilization")
        recommendations.append("Reduce credit card balances to below 30% of limit")
    else:
        positive_factors.append("Good credit utilization")
    
    if cibil_score.credit_history_length_score < 50:
        risk_factors.append("Short credit history")
        recommendations.append("Maintain old accounts to build credit history")
    
    if cibil_score.credit_mix_score < 50:
        recommendations.append("Consider diversifying credit types")
    
    report = CibilReport.objects.create(
        customer=customer,
        cibil_score=cibil_score,
        report_summary=summary.strip(),
        recommendations="; ".join(recommendations),
        risk_factors="; ".join(risk_factors),
        positive_factors="; ".join(positive_factors)
    )
    
    return report