# main_app/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

def generate_id():
    return uuid.uuid4().hex  # This gives a 32-character hex string without hyphens

class Customer(models.Model):
    id = models.CharField(primary_key=True, max_length=32, editable=False, default=generate_id)
    pan_card_number = models.CharField(max_length=10, unique=True, db_index=True)
    full_name = models.CharField(max_length=255)
    date_of_birth = models.DateField()
    phone_number = models.CharField(max_length=15)
    email = models.EmailField()
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customers'
        indexes = [
            models.Index(fields=['pan_card_number']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.full_name} - {self.pan_card_number}"

class BankAccount(models.Model):
    ACCOUNT_TYPES = [
        ('SAVINGS', 'Savings Account'),
        ('CURRENT', 'Current Account'),
        ('SALARY', 'Salary Account'),
        ('FIXED_DEPOSIT', 'Fixed Deposit'),
        ('RECURRING_DEPOSIT', 'Recurring Deposit'),
    ]
    
    id = models.CharField(primary_key=True, max_length=32, editable=False, default=generate_id)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='bank_accounts')
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    ifsc_code = models.CharField(max_length=11)
    account_opened_date = models.DateField()
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'bank_accounts'
        unique_together = ['account_number', 'ifsc_code']
        indexes = [
            models.Index(fields=['customer', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"

class CreditCard(models.Model):
    CARD_TYPES = [
        ('VISA', 'Visa'),
        ('MASTERCARD', 'Mastercard'),
        ('RUPAY', 'RuPay'),
        ('AMEX', 'American Express'),
    ]
    
    id = models.CharField(primary_key=True, max_length=32, editable=False, default=generate_id)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='credit_cards')
    bank_name = models.CharField(max_length=100)
    card_number_last_four = models.CharField(max_length=4)
    card_type = models.CharField(max_length=20, choices=CARD_TYPES)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2)
    current_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    available_credit = models.DecimalField(max_digits=10, decimal_places=2)
    card_issued_date = models.DateField()
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'credit_cards'
        indexes = [
            models.Index(fields=['customer', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.bank_name} - **** {self.card_number_last_four}"

class Loan(models.Model):
    LOAN_TYPES = [
        ('HOME_LOAN', 'Home Loan'),
        ('PERSONAL_LOAN', 'Personal Loan'),
        ('CAR_LOAN', 'Car Loan'),
        ('EDUCATION_LOAN', 'Education Loan'),
        ('BUSINESS_LOAN', 'Business Loan'),
        ('GOLD_LOAN', 'Gold Loan'),
    ]
    
    LOAN_STATUS = [
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
        ('OVERDUE', 'Overdue'),
        ('DEFAULTED', 'Defaulted'),
    ]
    
    id = models.CharField(primary_key=True, max_length=32, editable=False, default=generate_id)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    bank_name = models.CharField(max_length=100)
    loan_account_number = models.CharField(max_length=50)
    loan_type = models.CharField(max_length=20, choices=LOAN_TYPES)
    principal_amount = models.DecimalField(max_digits=15, decimal_places=2)
    outstanding_amount = models.DecimalField(max_digits=15, decimal_places=2)
    emi_amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tenure_months = models.IntegerField()
    remaining_tenure = models.IntegerField()
    loan_start_date = models.DateField()
    loan_end_date = models.DateField()
    status = models.CharField(max_length=20, choices=LOAN_STATUS, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'loans'
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['loan_account_number']),
        ]
    
    def __str__(self):
        return f"{self.loan_type} - {self.loan_account_number}"

class PaymentHistory(models.Model):
    PAYMENT_STATUS = [
        ('ON_TIME', 'On Time'),
        ('LATE_1_30', 'Late (1-30 days)'),
        ('LATE_31_60', 'Late (31-60 days)'),
        ('LATE_61_90', 'Late (61-90 days)'),
        ('LATE_90_PLUS', 'Late (90+ days)'),
        ('MISSED', 'Missed Payment'),
        ('DEFAULTED', 'Defaulted'),
    ]
    
    PAYMENT_TYPE = [
        ('LOAN_EMI', 'Loan EMI'),
        ('CREDIT_CARD', 'Credit Card Bill'),
        ('UTILITY_BILL', 'Utility Bill'),
        ('OTHER', 'Other'),
    ]
    
    id = models.CharField(primary_key=True, max_length=32, editable=False, default=generate_id)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payment_history')
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, null=True, blank=True)
    credit_card = models.ForeignKey(CreditCard, on_delete=models.CASCADE, null=True, blank=True)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE)
    due_date = models.DateField()
    payment_date = models.DateField(null=True, blank=True)
    due_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS)
    days_late = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payment_history'
        indexes = [
            models.Index(fields=['customer', 'due_date']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.customer.full_name} - {self.payment_type} - {self.due_date}"

class CibilScore(models.Model):
    id = models.CharField(primary_key=True, max_length=32, editable=False, default=generate_id)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='cibil_scores')
    score = models.IntegerField(
        validators=[MinValueValidator(300), MaxValueValidator(900)]
    )
    
    # Score breakdown factors
    payment_history_score = models.DecimalField(max_digits=5, decimal_places=2)  # 35%
    credit_utilization_score = models.DecimalField(max_digits=5, decimal_places=2)  # 30%
    credit_history_length_score = models.DecimalField(max_digits=5, decimal_places=2)  # 15%
    credit_mix_score = models.DecimalField(max_digits=5, decimal_places=2)  # 10%
    new_credit_score = models.DecimalField(max_digits=5, decimal_places=2)  # 10%
    
    # Additional metrics
    total_accounts = models.IntegerField(default=0)
    active_accounts = models.IntegerField(default=0)
    total_credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_outstanding = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit_utilization_ratio = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Status and timestamps
    score_date = models.DateTimeField(auto_now_add=True)
    is_latest = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'cibil_scores'
        indexes = [
            models.Index(fields=['customer', 'is_latest']),
            models.Index(fields=['score_date']),
        ]
    
    def save(self, *args, **kwargs):
        if self.is_latest:
            # Set all other scores for this customer to not latest
            CibilScore.objects.filter(customer=self.customer, is_latest=True).update(is_latest=False)
        super().save(*args, **kwargs)
    
    def get_score_category(self):
        if self.score >= 750:
            return "Excellent"
        elif self.score >= 700:
            return "Good"
        elif self.score >= 650:
            return "Fair"
        elif self.score >= 600:
            return "Poor"
        else:
            return "Very Poor"
    
    def __str__(self):
        return f"{self.customer.full_name} - Score: {self.score} ({self.get_score_category()})"

class CibilReport(models.Model):
    id = models.CharField(primary_key=True, max_length=32, editable=False, default=generate_id)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='cibil_reports')
    cibil_score = models.ForeignKey(CibilScore, on_delete=models.CASCADE)
    
    # Report details
    report_summary = models.TextField()
    recommendations = models.TextField(blank=True)
    risk_factors = models.TextField(blank=True)
    positive_factors = models.TextField(blank=True)
    
    # Report metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    report_version = models.CharField(max_length=10, default='1.0')
    
    class Meta:
        db_table = 'cibil_reports'
        indexes = [
            models.Index(fields=['customer', 'generated_at']),
        ]
    
    def __str__(self):
        return f"CIBIL Report - {self.customer.full_name} - {self.generated_at.date()}"