# dynamic_cibil_calculator.py - Complete Implementation

from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Avg, Count, Sum, Q
from django.utils import timezone
import math
from .models import Customer, PaymentHistory, CreditCard, Loan, BankAccount, CibilScore

class DynamicCibilScoreCalculator:
    
    def __init__(self, customer, custom_weights=None):
        self.customer = customer
        
        # Default weights (can be overridden by user)
        self.default_score_factors = {
            'payment_history': 0.35,
            'credit_utilization': 0.30,
            'credit_history_length': 0.15,
            'credit_mix': 0.10,
            'new_credit': 0.10
        }
        
        # Use custom weights if provided, otherwise use defaults
        if custom_weights:
            self.score_factors = self._validate_and_normalize_weights(custom_weights)
        else:
            self.score_factors = self.default_score_factors.copy()
        
        # Dynamic score range - adapts based on credit profile
        self.base_min_score = 200
        self.base_max_score = 1000
    
    def _validate_and_normalize_weights(self, custom_weights):
        """
        Validate and normalize user-provided weights to ensure they sum to 100%
        """
        # Convert percentage to decimal if needed
        normalized_weights = {}
        for key, value in custom_weights.items():
            if key in self.default_score_factors:
                # Convert percentage to decimal (e.g., 30 -> 0.30)
                normalized_value = float(value) / 100 if float(value) > 1 else float(value)
                normalized_weights[key] = normalized_value
        
        # Fill missing weights with defaults
        for key in self.default_score_factors:
            if key not in normalized_weights:
                normalized_weights[key] = self.default_score_factors[key]
        
        # Normalize to ensure sum equals 1.0
        total_weight = sum(normalized_weights.values())
        if total_weight != 1.0:
            for key in normalized_weights:
                normalized_weights[key] = normalized_weights[key] / total_weight
        
        return normalized_weights
    
    def calculate_dynamic_cibil_score(self, commit=True):
        """
        Calculate CIBIL score with dynamic scaling and user-defined weights
        """
        # Calculate individual factor scores
        payment_history_score = self._calculate_payment_history_score()
        credit_utilization_score = self._calculate_credit_utilization_score()
        credit_history_length_score = self._calculate_credit_history_length_score()
        credit_mix_score = self._calculate_credit_mix_score()
        new_credit_score = self._calculate_new_credit_score()
        
        # Calculate weighted contributions using custom weights
        payment_history_contribution = payment_history_score * self.score_factors['payment_history']
        credit_utilization_contribution = credit_utilization_score * self.score_factors['credit_utilization']
        credit_history_length_contribution = credit_history_length_score * self.score_factors['credit_history_length']
        credit_mix_contribution = credit_mix_score * self.score_factors['credit_mix']
        new_credit_contribution = new_credit_score * self.score_factors['new_credit']
        
        # Calculate base weighted score (0-100 scale)
        base_final_score = (
            payment_history_contribution +
            credit_utilization_contribution +
            credit_history_length_contribution +
            credit_mix_contribution +
            new_credit_contribution
        )
        
        # Apply behavioral adjustments
        behavioral_multiplier = self._get_behavioral_adjustments()
        adjusted_final_score = base_final_score * behavioral_multiplier
        
        # Dynamic score range calculation
        dynamic_range = self._calculate_dynamic_score_range()
        
        # Convert to dynamic CIBIL scale
        base_cibil_score = self._convert_to_dynamic_scale(base_final_score, dynamic_range)
        final_cibil_score = self._convert_to_dynamic_scale(adjusted_final_score, dynamic_range)
        
        # Get additional metrics
        metrics = self._get_additional_metrics()
        
        # Create enhanced CibilScore object
        cibil_score_obj = CibilScore(
            customer=self.customer,
            score=final_cibil_score,
            payment_history_score=payment_history_score,
            credit_utilization_score=credit_utilization_score,
            credit_history_length_score=credit_history_length_score,
            credit_mix_score=credit_mix_score,
            new_credit_score=new_credit_score,
            **metrics
        )

        if commit:
            CibilScore.objects.filter(customer=self.customer, is_latest=True).update(is_latest=False)
            cibil_score_obj.save()
        
        return cibil_score_obj, {
            'base_score': base_cibil_score,
            'final_score': final_cibil_score,
            'behavioral_multiplier': behavioral_multiplier,
            'dynamic_range': dynamic_range,
            'custom_weights_used': self.score_factors
        }

    # CORE CALCULATION METHODS - These were missing!

    def _calculate_payment_history_score(self):
        """
        Calculate payment history score based on payment patterns
        """
        payments = PaymentHistory.objects.filter(customer=self.customer)
        
        if not payments.exists():
            return 50.0  # Neutral score if no history
        
        total_payments = payments.count()
        on_time_payments = payments.filter(payment_status='ON_TIME').count()
        late_payments = payments.filter(
            payment_status__in=['LATE_1_30', 'LATE_31_60', 'LATE_61_90', 'LATE_90_PLUS']
        ).count()
        missed_payments = payments.filter(
            payment_status__in=['MISSED', 'DEFAULTED']
        ).count()
        
        # Calculate score based on payment patterns
        on_time_ratio = on_time_payments / total_payments
        late_ratio = late_payments / total_payments
        missed_ratio = missed_payments / total_payments
        
        # Score calculation
        base_score = on_time_ratio * 100
        late_penalty = late_ratio * 30
        missed_penalty = missed_ratio * 50
        
        score = max(0, base_score - late_penalty - missed_penalty)
        return round(score, 2)
    
    def _calculate_credit_utilization_score(self):
        """
        Calculate credit utilization score based on credit card usage
        """
        credit_cards = CreditCard.objects.filter(customer=self.customer, is_active=True)
        
        if not credit_cards.exists():
            return 70.0  # Neutral-positive score if no credit cards
        
        total_limit = credit_cards.aggregate(
            total=Sum('credit_limit'))['total'] or Decimal('0')
        total_balance = credit_cards.aggregate(
            total=Sum('current_balance'))['total'] or Decimal('0')
        
        if total_limit == 0:
            return 70.0
        
        utilization_ratio = float(total_balance / total_limit)
        
        # Enhanced scoring with more granular levels
        if utilization_ratio <= 0.05:
            return 95.0  # Very low usage
        elif utilization_ratio <= 0.10:
            return 100.0  # Sweet spot
        elif utilization_ratio <= 0.30:
            return 85.0
        elif utilization_ratio <= 0.50:
            return 65.0
        elif utilization_ratio <= 0.70:
            return 45.0
        elif utilization_ratio <= 0.90:
            return 25.0
        else:
            return 10.0
    
    def _calculate_credit_history_length_score(self):
        """
        Calculate credit history length score based on account age
        """
        # Get oldest credit account
        oldest_loan = Loan.objects.filter(customer=self.customer).order_by('loan_start_date').first()
        oldest_card = CreditCard.objects.filter(customer=self.customer).order_by('card_issued_date').first()
        oldest_account = BankAccount.objects.filter(customer=self.customer).order_by('account_opened_date').first()
        
        oldest_dates = []
        if oldest_loan:
            oldest_dates.append(oldest_loan.loan_start_date)
        if oldest_card:
            oldest_dates.append(oldest_card.card_issued_date)
        if oldest_account:
            oldest_dates.append(oldest_account.account_opened_date)
        
        if not oldest_dates:
            return 30.0  # Low score if no credit history
        
        oldest_date = min(oldest_dates)
        years_of_history = (datetime.now().date() - oldest_date).days / 365.25
        
        # Score based on years of history
        if years_of_history >= 10:
            return 100.0
        elif years_of_history >= 7:
            return 85.0
        elif years_of_history >= 5:
            return 70.0
        elif years_of_history >= 3:
            return 55.0
        elif years_of_history >= 1:
            return 40.0
        else:
            return 25.0
    
    def _calculate_credit_mix_score(self):
        """
        Calculate credit mix score based on variety of credit types
        """
        loan_types = set(Loan.objects.filter(
            customer=self.customer, status='ACTIVE'
        ).values_list('loan_type', flat=True))
        
        has_credit_cards = CreditCard.objects.filter(
            customer=self.customer, is_active=True
        ).exists()
        
        has_bank_accounts = BankAccount.objects.filter(
            customer=self.customer, is_active=True
        ).exists()
        
        credit_mix_score = 0
        
        # Points for different credit types
        if has_credit_cards:
            credit_mix_score += 30
        if has_bank_accounts:
            credit_mix_score += 20
        if 'HOME_LOAN' in loan_types:
            credit_mix_score += 25
        if 'CAR_LOAN' in loan_types:
            credit_mix_score += 15
        if 'PERSONAL_LOAN' in loan_types:
            credit_mix_score += 10
        
        return min(100.0, credit_mix_score)
    
    def _calculate_new_credit_score(self):
        """
        Calculate new credit score based on recent credit activity
        """
        # Recent accounts (last 6 months)
        six_months_ago = timezone.now() - timedelta(days=180)
        
        recent_loans = Loan.objects.filter(
            customer=self.customer,
            created_at__gte=six_months_ago
        ).count()
        
        recent_cards = CreditCard.objects.filter(
            customer=self.customer,
            created_at__gte=six_months_ago
        ).count()
        
        total_recent_accounts = recent_loans + recent_cards
        
        # Score based on recent credit activity
        if total_recent_accounts == 0:
            return 100.0
        elif total_recent_accounts == 1:
            return 80.0
        elif total_recent_accounts == 2:
            return 60.0
        elif total_recent_accounts <= 4:
            return 40.0
        else:
            return 20.0

    # DYNAMIC SCORING METHODS

    def _calculate_dynamic_score_range(self):
        """
        Calculate dynamic score range based on customer's credit profile
        """
        # Factors that influence score range
        credit_history_years = self._get_credit_age_years()
        total_credit_limit = self._get_total_credit_limit()
        account_diversity = self._get_account_diversity_score()
        payment_consistency = self._get_payment_consistency_score()
        
        # Base range adjustment factors
        range_multiplier = 1.0
        
        # Adjust range based on credit maturity
        if credit_history_years >= 10:
            range_multiplier += 0.2  # Mature credit history gets wider range
        elif credit_history_years >= 5:
            range_multiplier += 0.1
        elif credit_history_years < 1:
            range_multiplier -= 0.1  # New credit gets narrower range
        
        # Adjust range based on credit exposure
        if total_credit_limit > 500000:  # High credit limits
            range_multiplier += 0.15
        elif total_credit_limit > 100000:
            range_multiplier += 0.05
        elif total_credit_limit < 25000:
            range_multiplier -= 0.05
        
        # Adjust range based on account diversity
        if account_diversity >= 80:
            range_multiplier += 0.1
        elif account_diversity < 40:
            range_multiplier -= 0.05
        
        # Calculate dynamic min and max
        range_expansion = (self.base_max_score - self.base_min_score) * (range_multiplier - 1)
        
        dynamic_min = max(150, int(self.base_min_score - range_expansion/2))
        dynamic_max = min(1200, int(self.base_max_score + range_expansion/2))
        
        return {
            'min_score': dynamic_min,
            'max_score': dynamic_max,
            'range_multiplier': round(range_multiplier, 3),
            'range_width': dynamic_max - dynamic_min
        }
    
    def _convert_to_dynamic_scale(self, score_0_100, dynamic_range):
        """
        Convert 0-100 score to dynamic CIBIL scale using advanced algorithms
        """
        # Normalize score to 0-1 range
        normalized_score = max(0, min(100, score_0_100)) / 100.0
        
        # Apply sigmoid transformation for more realistic distribution
        sigmoid_factor = 8  # Controls steepness of the curve
        sigmoid_score = 1 / (1 + math.exp(-sigmoid_factor * (normalized_score - 0.5)))
        
        # Apply power transformation for fine-tuning
        if normalized_score < 0.5:
            power_score = math.pow(sigmoid_score, 1.2)  # Slightly compress lower scores
        else:
            power_score = math.pow(sigmoid_score, 0.9)   # Slightly expand higher scores
        
        # Map to dynamic range
        score_range = dynamic_range['max_score'] - dynamic_range['min_score']
        final_score = dynamic_range['min_score'] + (power_score * score_range)
        
        return max(dynamic_range['min_score'], min(dynamic_range['max_score'], int(final_score)))

    # BEHAVIORAL ADJUSTMENT METHODS

    def _get_behavioral_adjustments(self):
        """
        Enhanced behavioral adjustments based on multiple factors
        """
        multiplier = 1.0
        
        # Underutilization penalty
        utilization_multiplier = self._get_underutilization_penalty()
        multiplier *= utilization_multiplier
        
        # Credit diversity bonus/penalty
        diversity_multiplier = self._get_credit_diversity_adjustment()
        multiplier *= diversity_multiplier
        
        # Payment pattern consistency bonus
        consistency_multiplier = self._get_payment_consistency_adjustment()
        multiplier *= consistency_multiplier
        
        # Credit growth pattern adjustment
        growth_multiplier = self._get_credit_growth_adjustment()
        multiplier *= growth_multiplier
        
        return round(multiplier, 4)
    
    def _get_underutilization_penalty(self):
        """Apply penalty for severe underutilization of credit"""
        credit_cards = CreditCard.objects.filter(customer=self.customer, is_active=True)
        
        if not credit_cards.exists():
            return 1.0
        
        total_limit = credit_cards.aggregate(total=Sum('credit_limit'))['total'] or Decimal('0')
        total_balance = credit_cards.aggregate(total=Sum('current_balance'))['total'] or Decimal('0')
        
        if total_limit > 0:
            utilization = float(total_balance / total_limit)
            
            if utilization < 0.05 and total_limit > 100000:
                return 0.85  # 15% penalty
            elif utilization < 0.02 and total_limit > 50000:
                return 0.92  # 8% penalty
            elif utilization < 0.01 and total_limit > 25000:
                return 0.95  # 5% penalty
        
        return 1.0
    
    def _get_credit_diversity_adjustment(self):
        """Adjust score based on credit product diversity"""
        diversity_score = self._get_account_diversity_score()
        
        if diversity_score >= 80:
            return 1.05  # 5% bonus for excellent diversity
        elif diversity_score >= 60:
            return 1.02  # 2% bonus for good diversity
        elif diversity_score < 30:
            return 0.95  # 5% penalty for poor diversity
        
        return 1.0
    
    def _get_payment_consistency_adjustment(self):
        """Adjust score based on payment consistency"""
        consistency_score = self._get_payment_consistency_score()
        
        if consistency_score >= 90:
            return 1.03  # 3% bonus for excellent consistency
        elif consistency_score >= 75:
            return 1.01  # 1% bonus for good consistency
        elif consistency_score < 50:
            return 0.97  # 3% penalty for poor consistency
        
        return 1.0
    
    def _get_credit_growth_adjustment(self):
        """Adjust score based on credit growth pattern"""
        growth_score = self._get_credit_growth_score()
        
        if 70 <= growth_score <= 85:  # Optimal growth range
            return 1.02  # 2% bonus for optimal growth
        elif growth_score > 90 or growth_score < 30:  # Too fast or too slow growth
            return 0.98  # 2% penalty
        
        return 1.0

    # HELPER METHODS

    def _get_total_credit_limit(self):
        """Get total credit limit across all cards"""
        return float(CreditCard.objects.filter(
            customer=self.customer, is_active=True
        ).aggregate(total=Sum('credit_limit'))['total'] or Decimal('0'))
    
    def _get_account_diversity_score(self):
        """Calculate account diversity score"""
        score = 0
        
        # Credit cards
        if CreditCard.objects.filter(customer=self.customer, is_active=True).exists():
            score += 25
        
        # Different loan types
        loan_types = set(Loan.objects.filter(
            customer=self.customer, status='ACTIVE'
        ).values_list('loan_type', flat=True))
        
        score += len(loan_types) * 15  # 15 points per loan type
        
        # Bank accounts
        if BankAccount.objects.filter(customer=self.customer, is_active=True).exists():
            score += 20
        
        return min(100.0, score)
    
    def _get_payment_consistency_score(self):
        """Calculate payment consistency score"""
        six_months_ago = timezone.now() - timedelta(days=180)
        recent_payments = PaymentHistory.objects.filter(
            customer=self.customer,
            payment_date__gte=six_months_ago
        )
        
        if recent_payments.count() < 3:
            return 50.0
        
        on_time_payments = recent_payments.filter(payment_status='ON_TIME').count()
        total_payments = recent_payments.count()
        
        consistency_ratio = on_time_payments / total_payments
        return consistency_ratio * 100
    
    def _get_credit_growth_score(self):
        """Calculate credit growth score"""
        one_year_ago = timezone.now() - timedelta(days=365)
        
        current_limit = self._get_total_credit_limit()
        old_cards = CreditCard.objects.filter(
            customer=self.customer,
            created_at__lte=one_year_ago
        ).aggregate(total=Sum('credit_limit'))['total'] or Decimal('0')
        
        if old_cards > 0:
            growth_rate = (current_limit - float(old_cards)) / float(old_cards)
            # Optimal growth is 10-50% annually
            if 0.10 <= growth_rate <= 0.50:
                return 85.0
            elif 0.05 <= growth_rate < 0.10 or 0.50 < growth_rate <= 0.80:
                return 70.0
            else:
                return 50.0
        
        return 60.0  # Neutral for new customers
    
    def _get_credit_age_years(self):
        """Get credit history age in years"""
        oldest_loan = Loan.objects.filter(customer=self.customer).order_by('loan_start_date').first()
        oldest_card = CreditCard.objects.filter(customer=self.customer).order_by('card_issued_date').first()
        oldest_account = BankAccount.objects.filter(customer=self.customer).order_by('account_opened_date').first()
        
        oldest_dates = []
        if oldest_loan:
            oldest_dates.append(oldest_loan.loan_start_date)
        if oldest_card:
            oldest_dates.append(oldest_card.card_issued_date)
        if oldest_account:
            oldest_dates.append(oldest_account.account_opened_date)
        
        if oldest_dates:
            oldest_date = min(oldest_dates)
            return (datetime.now().date() - oldest_date).days / 365.25
        return 0
    
    def _get_additional_metrics(self):
        """Get additional metrics for the CIBIL score record"""
        # Count accounts
        total_accounts = (
            Loan.objects.filter(customer=self.customer).count() +
            CreditCard.objects.filter(customer=self.customer).count() +
            BankAccount.objects.filter(customer=self.customer).count()
        )
        
        active_accounts = (
            Loan.objects.filter(customer=self.customer, status='ACTIVE').count() +
            CreditCard.objects.filter(customer=self.customer, is_active=True).count() +
            BankAccount.objects.filter(customer=self.customer, is_active=True).count()
        )
        
        # Credit limits and outstanding
        credit_cards = CreditCard.objects.filter(customer=self.customer, is_active=True)
        total_credit_limit = credit_cards.aggregate(
            total=Sum('credit_limit'))['total'] or Decimal('0')
        total_outstanding = (
            credit_cards.aggregate(total=Sum('current_balance'))['total'] or Decimal('0')
        ) + (
            Loan.objects.filter(customer=self.customer, status='ACTIVE').aggregate(
                total=Sum('outstanding_amount'))['total'] or Decimal('0')
        )
        
        # Utilization ratio
        utilization_ratio = 0
        if total_credit_limit > 0:
            utilization_ratio = float(
                (credit_cards.aggregate(total=Sum('current_balance'))['total'] or Decimal('0')) 
                / total_credit_limit
            )
        
        return {
            'total_accounts': total_accounts,
            'active_accounts': active_accounts,
            'total_credit_limit': total_credit_limit,
            'total_outstanding': total_outstanding,
            'credit_utilization_ratio': round(utilization_ratio * 100, 2)
        }

    # COMPREHENSIVE BREAKDOWN METHOD

    def get_comprehensive_score_breakdown(self):
        """Get comprehensive breakdown with all dynamic factors"""
        # Calculate all individual scores
        payment_history_score = self._calculate_payment_history_score()
        credit_utilization_score = self._calculate_credit_utilization_score()
        credit_history_length_score = self._calculate_credit_history_length_score()
        credit_mix_score = self._calculate_credit_mix_score()
        new_credit_score = self._calculate_new_credit_score()
        
        # Calculate contributions with custom weights
        contributions = {}
        factor_scores = {
            'payment_history': payment_history_score,
            'credit_utilization': credit_utilization_score,
            'credit_history_length': credit_history_length_score,
            'credit_mix': credit_mix_score,
            'new_credit': new_credit_score
        }
        
        for factor in self.score_factors:
            raw_score = factor_scores[factor]
            weighted_contribution = raw_score * self.score_factors[factor]
            contributions[factor] = {
                'weight_percentage': round(self.score_factors[factor] * 100, 1),
                'raw_score': round(raw_score, 2),
                'weighted_contribution': round(weighted_contribution, 2),
                'score_rating': self._get_score_rating(raw_score)
            }
        
        # Calculate total scores
        base_total = sum(contrib['weighted_contribution'] for contrib in contributions.values())
        behavioral_multiplier = self._get_behavioral_adjustments()
        adjusted_total = base_total * behavioral_multiplier
        
        # Dynamic range calculation
        dynamic_range = self._calculate_dynamic_score_range()
        
        # Final scores
        base_cibil_score = self._convert_to_dynamic_scale(base_total, dynamic_range)
        final_cibil_score = self._convert_to_dynamic_scale(adjusted_total, dynamic_range)
        
        # Calculate contribution percentages
        for factor in contributions:
            if adjusted_total > 0:
                contributions[factor]['contribution_percentage'] = round(
                    (contributions[factor]['weighted_contribution'] / adjusted_total) * 100, 1
                )
            else:
                contributions[factor]['contribution_percentage'] = 0
        
        return {
            'final_cibil_score': final_cibil_score,
            'base_cibil_score': base_cibil_score,
            'dynamic_range': dynamic_range,
            'custom_weights': {k: round(v * 100, 1) for k, v in self.score_factors.items()},
            'behavioral_adjustments': {
                'total_multiplier': behavioral_multiplier,
                'underutilization_penalty': self._get_underutilization_penalty(),
                'diversity_adjustment': self._get_credit_diversity_adjustment(),
                'consistency_adjustment': self._get_payment_consistency_adjustment(),
                'growth_adjustment': self._get_credit_growth_adjustment()
            },
            'score_factors': contributions,
            'summary': {
                'base_total_score': round(base_total, 2),
                'adjusted_total_score': round(adjusted_total, 2),
                'improvement_potential': round(100 - base_total, 2),
                'score_range_width': dynamic_range['range_width']
            }
        }
    
    def _get_score_rating(self, score):
        """Get rating based on score"""
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "Very Good"
        elif score >= 70:
            return "Good"
        elif score >= 60:
            return "Fair"
        elif score >= 50:
            return "Average"
        else:
            return "Poor"