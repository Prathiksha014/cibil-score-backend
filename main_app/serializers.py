# serializers.py
from rest_framework import serializers
from .models import (
    Customer, BankAccount, CreditCard, Loan, 
    PaymentHistory, CibilScore, CibilReport
)

class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class CreditCardSerializer(serializers.ModelSerializer):
    utilization_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = CreditCard
        fields = '__all__'
        read_only_fields = ('id', 'created_at')
    
    def get_utilization_percentage(self, obj):
        if obj.credit_limit > 0:
            return round((obj.current_balance / obj.credit_limit) * 100, 2)
        return 0

class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class PaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentHistory
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class CibilScoreSerializer(serializers.ModelSerializer):
    score_category = serializers.CharField(source='get_score_category', read_only=True)
    
    class Meta:
        model = CibilScore
        fields = '__all__'
        read_only_fields = ('id', 'score_date')

class CibilReportSerializer(serializers.ModelSerializer):
    cibil_score_details = CibilScoreSerializer(source='cibil_score', read_only=True)
    
    class Meta:
        model = CibilReport
        fields = '__all__'
        read_only_fields = ('id', 'generated_at')

class CustomerSerializer(serializers.ModelSerializer):
    bank_accounts = BankAccountSerializer(many=True, read_only=True)
    credit_cards = CreditCardSerializer(many=True, read_only=True)
    loans = LoanSerializer(many=True, read_only=True)
    latest_cibil_score = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_latest_cibil_score(self, obj):
        latest_score = obj.cibil_scores.filter(is_latest=True).first()
        if latest_score:
            return CibilScoreSerializer(latest_score).data
        return None

class CibilScoreRequestSerializer(serializers.Serializer):
    pan_card_number = serializers.CharField(max_length=10, min_length=10)
    
    def validate_pan_card_number(self, value):
        # Basic PAN card validation
        import re
        pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
        if not re.match(pan_pattern, value.upper()):
            raise serializers.ValidationError("Invalid PAN card format")
        return value.upper()

class CibilScoreCalculationSerializer(serializers.Serializer):
    payment_history_weight = serializers.FloatField(default=0.35)
    credit_utilization_weight = serializers.FloatField(default=0.30)
    credit_history_length_weight = serializers.FloatField(default=0.15)
    credit_mix_weight = serializers.FloatField(default=0.10)
    new_credit_weight = serializers.FloatField(default=0.10)