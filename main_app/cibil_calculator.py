from datetime import datetime, timedelta
from decimal import Decimal
import math
from typing import Dict, Any, Optional, Tuple

class UserInputCibilCalculator:
    """
    Dynamic CIBIL Score Calculator based purely on user inputs
    No default values - all calculations based on provided data
    """
    
    def __init__(self, user_financial_data: Dict[str, Any], custom_weights: Dict[str, float]):
        """
        Initialize calculator with user financial data and custom weights
        
        Args:
            user_financial_data: Dictionary containing all financial information
            custom_weights: Dictionary with custom weight percentages for each factor
        """
        self.financial_data = user_financial_data
        self.weights = self._normalize_weights(custom_weights)
        
        # Validate required data
        self._validate_input_data()
    
    def _validate_input_data(self) -> None:
        """Validate that all required input data is provided"""
        required_fields = [
            'total_payments', 'on_time_payments', 'late_payments', 'missed_payments',
            'total_credit_limit', 'current_balance', 'credit_history_years',
            'has_credit_cards', 'has_home_loan', 'has_car_loan', 'has_personal_loan',
            'has_bank_accounts', 'recent_accounts_last_6_months'
        ]
        
        for field in required_fields:
            if field not in self.financial_data:
                raise ValueError(f"Required field '{field}' missing from financial data")
    
    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Normalize weights to ensure they sum to 100%
        
        Args:
            weights: Dictionary with weight percentages
            
        Returns:
            Normalized weights dictionary
        """
        required_factors = [
            'payment_history', 'credit_utilization', 'credit_history_length',
            'credit_mix', 'new_credit'
        ]
        
        # Validate all factors are present
        for factor in required_factors:
            if factor not in weights:
                raise ValueError(f"Weight for '{factor}' not provided")
        
        # Convert to decimal values and normalize
        total_weight = sum(weights.values())
        if total_weight == 0:
            raise ValueError("Total weights cannot be zero")
        
        normalized_weights = {}
        for factor, weight in weights.items():
            normalized_weights[factor] = weight / total_weight
        
        return normalized_weights
    
    def calculate_payment_history_score(self) -> float:
        """
        Calculate payment history score based on payment patterns
        
        Returns:
            Payment history score (0-100)
        """
        total_payments = self.financial_data['total_payments']
        on_time_payments = self.financial_data['on_time_payments']
        late_payments = self.financial_data['late_payments']
        missed_payments = self.financial_data['missed_payments']
        
        if total_payments == 0:
            return 0.0  # No payment history
        
        # Validate payment consistency
        if (on_time_payments + late_payments + missed_payments) != total_payments:
            raise ValueError("Payment counts don't match total payments")
        
        # Calculate ratios
        on_time_ratio = on_time_payments / total_payments
        late_ratio = late_payments / total_payments
        missed_ratio = missed_payments / total_payments
        
        # Score calculation with penalties
        base_score = on_time_ratio * 100
        late_penalty = late_ratio * 30
        missed_penalty = missed_ratio * 60  # Higher penalty for missed payments
        
        score = max(0, base_score - late_penalty - missed_penalty)
        return round(score, 2)
    
    def calculate_credit_utilization_score(self) -> float:
        """
        Calculate credit utilization score
        
        Returns:
            Credit utilization score (0-100)
        """
        total_limit = self.financial_data['total_credit_limit']
        current_balance = self.financial_data['current_balance']
        
        if total_limit == 0:
            return 0.0  # No credit available
        
        if current_balance < 0:
            raise ValueError("Current balance cannot be negative")
        
        utilization_ratio = current_balance / total_limit
        
        # Enhanced scoring based on utilization levels
        if utilization_ratio <= 0.01:
            return 90.0  # Very low usage
        elif utilization_ratio <= 0.10:
            return 100.0  # Optimal usage
        elif utilization_ratio <= 0.30:
            return 85.0  # Good usage
        elif utilization_ratio <= 0.50:
            return 65.0  # Moderate usage
        elif utilization_ratio <= 0.70:
            return 40.0  # High usage
        elif utilization_ratio <= 0.90:
            return 20.0  # Very high usage
        else:
            return 5.0   # Maxed out
    
    def calculate_credit_history_length_score(self) -> float:
        """
        Calculate credit history length score
        
        Returns:
            Credit history length score (0-100)
        """
        years_of_history = self.financial_data['credit_history_years']
        
        if years_of_history < 0:
            raise ValueError("Credit history years cannot be negative")
        
        # Score based on years of credit history
        if years_of_history >= 15:
            return 100.0
        elif years_of_history >= 10:
            return 90.0
        elif years_of_history >= 7:
            return 80.0
        elif years_of_history >= 5:
            return 65.0
        elif years_of_history >= 3:
            return 50.0
        elif years_of_history >= 1:
            return 35.0
        elif years_of_history >= 0.5:
            return 20.0
        else:
            return 5.0
    
    def calculate_credit_mix_score(self) -> float:
        """
        Calculate credit mix score based on variety of credit types
        
        Returns:
            Credit mix score (0-100)
        """
        has_credit_cards = self.financial_data['has_credit_cards']
        has_home_loan = self.financial_data['has_home_loan']
        has_car_loan = self.financial_data['has_car_loan']
        has_personal_loan = self.financial_data['has_personal_loan']
        has_bank_accounts = self.financial_data['has_bank_accounts']
        
        score = 0
        
        # Points for different credit types
        if has_credit_cards:
            score += 25
        if has_bank_accounts:
            score += 20
        if has_home_loan:
            score += 30  # Higher weight for secured loans
        if has_car_loan:
            score += 15
        if has_personal_loan:
            score += 10
        
        return min(100.0, score)
    
    def calculate_new_credit_score(self) -> float:
        """
        Calculate new credit score based on recent credit activity
        
        Returns:
            New credit score (0-100)
        """
        recent_accounts = self.financial_data['recent_accounts_last_6_months']
        
        if recent_accounts < 0:
            raise ValueError("Recent accounts count cannot be negative")
        
        # Score based on recent credit activity
        if recent_accounts == 0:
            return 100.0  # No recent activity is good
        elif recent_accounts == 1:
            return 80.0   # One new account is acceptable
        elif recent_accounts == 2:
            return 60.0   # Two accounts show some activity
        elif recent_accounts <= 4:
            return 35.0   # Multiple accounts raise concerns
        else:
            return 10.0   # Too many new accounts
    
    def calculate_behavioral_adjustments(self) -> float:
        """
        Calculate behavioral adjustments based on financial patterns
        
        Returns:
            Behavioral multiplier (0.8 - 1.2)
        """
        multiplier = 1.0
        
        # Credit utilization behavior
        utilization_ratio = self.financial_data['current_balance'] / max(1, self.financial_data['total_credit_limit'])
        
        # Penalty for extreme underutilization (dormant accounts)
        if utilization_ratio < 0.01 and self.financial_data['total_credit_limit'] > 50000:
            multiplier *= 0.95  # 5% penalty
        
        # Bonus for optimal utilization
        elif 0.05 <= utilization_ratio <= 0.15:
            multiplier *= 1.03  # 3% bonus
        
        # Payment consistency bonus
        if self.financial_data['total_payments'] > 0:
            consistency_ratio = self.financial_data['on_time_payments'] / self.financial_data['total_payments']
            if consistency_ratio >= 0.95:
                multiplier *= 1.05  # 5% bonus for excellent payment history
            elif consistency_ratio >= 0.85:
                multiplier *= 1.02  # 2% bonus for good payment history
        
        # Credit mix diversity bonus
        credit_types = sum([
            self.financial_data['has_credit_cards'],
            self.financial_data['has_home_loan'],
            self.financial_data['has_car_loan'],
            self.financial_data['has_personal_loan'],
            self.financial_data['has_bank_accounts']
        ])
        
        if credit_types >= 4:
            multiplier *= 1.04  # 4% bonus for excellent diversity
        elif credit_types >= 3:
            multiplier *= 1.02  # 2% bonus for good diversity
        elif credit_types <= 1:
            multiplier *= 0.96  # 4% penalty for poor diversity
        
        return round(max(0.8, min(1.2, multiplier)), 4)
    
    def calculate_dynamic_score_range(self) -> Dict[str, Any]:
        """
        Calculate dynamic score range based on user's credit profile
        
        Returns:
            Dictionary with dynamic score range information
        """
        base_min = 300
        base_max = 900
        
        # Factors affecting score range
        credit_years = self.financial_data['credit_history_years']
        credit_limit = self.financial_data['total_credit_limit']
        
        range_multiplier = 1.0
        
        # Adjust based on credit maturity
        if credit_years >= 10:
            range_multiplier += 0.15
        elif credit_years >= 5:
            range_multiplier += 0.08
        elif credit_years < 1:
            range_multiplier -= 0.10
        
        # Adjust based on credit exposure
        if credit_limit > 500000:
            range_multiplier += 0.12
        elif credit_limit > 100000:
            range_multiplier += 0.06
        elif credit_limit < 25000:
            range_multiplier -= 0.08
        
        # Calculate dynamic range
        range_expansion = (base_max - base_min) * (range_multiplier - 1)
        
        dynamic_min = max(250, int(base_min - range_expansion/2))
        dynamic_max = min(950, int(base_max + range_expansion/2))
        
        return {
            'min_score': dynamic_min,
            'max_score': dynamic_max,
            'range_multiplier': round(range_multiplier, 3),
            'range_width': dynamic_max - dynamic_min
        }
    
    def convert_to_cibil_scale(self, score_0_100: float, dynamic_range: Dict[str, Any]) -> int:
        """
        Convert 0-100 score to CIBIL scale using sigmoid transformation
        
        Args:
            score_0_100: Score in 0-100 range
            dynamic_range: Dynamic range information
            
        Returns:
            CIBIL score in dynamic range
        """
        # Normalize to 0-1
        normalized = max(0, min(100, score_0_100)) / 100.0
        
        # Apply sigmoid transformation for realistic distribution
        sigmoid_factor = 6
        sigmoid_score = 1 / (1 + math.exp(-sigmoid_factor * (normalized - 0.5)))
        
        # Apply power transformation
        if normalized < 0.5:
            power_score = math.pow(sigmoid_score, 1.1)
        else:
            power_score = math.pow(sigmoid_score, 0.95)
        
        # Map to dynamic range
        score_range = dynamic_range['max_score'] - dynamic_range['min_score']
        final_score = dynamic_range['min_score'] + (power_score * score_range)
        
        return max(dynamic_range['min_score'], min(dynamic_range['max_score'], int(final_score)))
    
    def calculate_cibil_score(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Calculate complete CIBIL score with detailed breakdown
        
        Returns:
            Tuple of (score_result, detailed_breakdown)
        """
        # Calculate individual factor scores
        payment_history_score = self.calculate_payment_history_score()
        credit_utilization_score = self.calculate_credit_utilization_score()
        credit_history_length_score = self.calculate_credit_history_length_score()
        credit_mix_score = self.calculate_credit_mix_score()
        new_credit_score = self.calculate_new_credit_score()
        
        # Calculate weighted contributions
        weighted_contributions = {
            'payment_history': payment_history_score * self.weights['payment_history'],
            'credit_utilization': credit_utilization_score * self.weights['credit_utilization'],
            'credit_history_length': credit_history_length_score * self.weights['credit_history_length'],
            'credit_mix': credit_mix_score * self.weights['credit_mix'],
            'new_credit': new_credit_score * self.weights['new_credit']
        }
        
        # Calculate base score (0-100)
        base_score = sum(weighted_contributions.values())
        
        # Apply behavioral adjustments
        behavioral_multiplier = self.calculate_behavioral_adjustments()
        adjusted_score = base_score * behavioral_multiplier
        
        # Calculate dynamic range
        dynamic_range = self.calculate_dynamic_score_range()
        
        # Convert to CIBIL scale
        base_cibil_score = self.convert_to_cibil_scale(base_score, dynamic_range)
        final_cibil_score = self.convert_to_cibil_scale(adjusted_score, dynamic_range)
        
        # Score result
        score_result = {
            'final_cibil_score': final_cibil_score,
            'base_cibil_score': base_cibil_score,
            'score_grade': self._get_score_grade(final_cibil_score),
            'improvement_points': max(0, 100 - base_score)
        }
        
        # Detailed breakdown
        detailed_breakdown = {
            'factor_scores': {
                'payment_history': {
                    'raw_score': round(payment_history_score, 2),
                    'weight_percentage': round(self.weights['payment_history'] * 100, 1),
                    'weighted_contribution': round(weighted_contributions['payment_history'], 2),
                    'rating': self._get_score_rating(payment_history_score)
                },
                'credit_utilization': {
                    'raw_score': round(credit_utilization_score, 2),
                    'weight_percentage': round(self.weights['credit_utilization'] * 100, 1),
                    'weighted_contribution': round(weighted_contributions['credit_utilization'], 2),
                    'rating': self._get_score_rating(credit_utilization_score)
                },
                'credit_history_length': {
                    'raw_score': round(credit_history_length_score, 2),
                    'weight_percentage': round(self.weights['credit_history_length'] * 100, 1),
                    'weighted_contribution': round(weighted_contributions['credit_history_length'], 2),
                    'rating': self._get_score_rating(credit_history_length_score)
                },
                'credit_mix': {
                    'raw_score': round(credit_mix_score, 2),
                    'weight_percentage': round(self.weights['credit_mix'] * 100, 1),
                    'weighted_contribution': round(weighted_contributions['credit_mix'], 2),
                    'rating': self._get_score_rating(credit_mix_score)
                },
                'new_credit': {
                    'raw_score': round(new_credit_score, 2),
                    'weight_percentage': round(self.weights['new_credit'] * 100, 1),
                    'weighted_contribution': round(weighted_contributions['new_credit'], 2),
                    'rating': self._get_score_rating(new_credit_score)
                }
            },
            'calculations': {
                'base_score_0_100': round(base_score, 2),
                'behavioral_multiplier': behavioral_multiplier,
                'adjusted_score_0_100': round(adjusted_score, 2),
                'dynamic_range': dynamic_range
            },
            'financial_metrics': {
                'credit_utilization_ratio': round((self.financial_data['current_balance'] / max(1, self.financial_data['total_credit_limit'])) * 100, 2),
                'payment_success_rate': round((self.financial_data['on_time_payments'] / max(1, self.financial_data['total_payments'])) * 100, 2),
                'credit_diversity_count': sum([
                    self.financial_data['has_credit_cards'],
                    self.financial_data['has_home_loan'],
                    self.financial_data['has_car_loan'],
                    self.financial_data['has_personal_loan'],
                    self.financial_data['has_bank_accounts']
                ])
            }
        }
        
        return score_result, detailed_breakdown
    
    def _get_score_rating(self, score: float) -> str:
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
    
    def _get_score_grade(self, cibil_score: int) -> str:
        """Get grade based on CIBIL score"""
        if cibil_score >= 800:
            return "Excellent"
        elif cibil_score >= 750:
            return "Very Good"
        elif cibil_score >= 700:
            return "Good"
        elif cibil_score >= 650:
            return "Fair"
        elif cibil_score >= 600:
            return "Average"
        else:
            return "Poor"
