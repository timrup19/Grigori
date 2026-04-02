"""
Risk Scoring Engine

Calculates composite risk scores for tenders and contractors based on:
- Price anomalies (30%)
- Bid patterns (25%)
- Single bidder flags (20%)
- Network risk (15%)
- High value contracts (10%)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from scipy import stats
from loguru import logger

from app.config import settings


@dataclass
class RiskFactors:
    """Container for individual risk factors."""
    price_anomaly_score: float = 0.0
    bid_pattern_score: float = 0.0
    single_bidder_score: float = 0.0
    network_risk_score: float = 0.0
    high_value_score: float = 0.0
    
    # Flags
    is_price_anomaly: bool = False
    is_bid_pattern_anomaly: bool = False
    is_single_bidder: bool = False
    is_high_value: bool = False
    
    # Details
    price_deviation_pct: Optional[float] = None
    bid_cv: Optional[float] = None
    reasons: List[str] = None
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "price_anomaly_score": self.price_anomaly_score,
            "bid_pattern_score": self.bid_pattern_score,
            "single_bidder_score": self.single_bidder_score,
            "network_risk_score": self.network_risk_score,
            "high_value_score": self.high_value_score,
            "is_price_anomaly": self.is_price_anomaly,
            "is_bid_pattern_anomaly": self.is_bid_pattern_anomaly,
            "is_single_bidder": self.is_single_bidder,
            "is_high_value": self.is_high_value,
            "price_deviation_pct": self.price_deviation_pct,
            "bid_cv": self.bid_cv,
            "reasons": self.reasons,
        }


class RiskScoringEngine:
    """
    Main risk scoring engine.
    
    Combines multiple signals to produce a composite risk score (0-100).
    """
    
    def __init__(self):
        self.weights = {
            "price_anomaly": settings.RISK_WEIGHT_PRICE,
            "bid_pattern": settings.RISK_WEIGHT_BID_PATTERN,
            "single_bidder": settings.RISK_WEIGHT_SINGLE_BIDDER,
            "network_risk": settings.RISK_WEIGHT_NETWORK,
            "high_value": settings.RISK_WEIGHT_HIGH_VALUE,
        }
        
        self.isolation_forest = None
        self.scaler = StandardScaler()
        self.category_benchmarks: Dict[str, Dict] = {}
        self.value_threshold_p90: float = 0.0
    
    # ========================================================================
    # Category Benchmarks
    # ========================================================================
    
    def calculate_category_benchmarks(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """Calculate price benchmarks for each CPV category."""
        benchmarks = {}
        
        for cpv in df['cpv_code'].dropna().unique():
            subset = df[df['cpv_code'] == cpv]['expected_value'].dropna()
            
            if len(subset) >= 3:
                benchmarks[cpv] = {
                    'count': len(subset),
                    'mean': float(subset.mean()),
                    'median': float(subset.median()),
                    'std': float(subset.std()),
                    'p25': float(subset.quantile(0.25)),
                    'p75': float(subset.quantile(0.75)),
                }
        
        self.category_benchmarks = benchmarks
        return benchmarks
    
    # ========================================================================
    # Price Anomaly Detection
    # ========================================================================
    
    def detect_price_anomalies(
        self,
        df: pd.DataFrame,
        z_threshold: float = 2.5
    ) -> pd.DataFrame:
        """Detect price anomalies using Z-score and Isolation Forest."""
        df = df.copy()
        
        # Initialize columns
        df['price_z_score'] = 0.0
        df['is_price_outlier_zscore'] = False
        df['price_deviation_pct'] = 0.0
        
        # Z-score within each CPV category
        for cpv in df['cpv_code'].dropna().unique():
            mask = df['cpv_code'] == cpv
            values = df.loc[mask, 'expected_value'].dropna()
            
            if len(values) > 2 and values.std() > 0:
                z_scores = stats.zscore(values)
                df.loc[mask, 'price_z_score'] = z_scores
                df.loc[mask, 'is_price_outlier_zscore'] = np.abs(z_scores) > z_threshold
                
                # Price deviation from median
                median = values.median()
                if median > 0:
                    df.loc[mask, 'price_deviation_pct'] = (
                        (df.loc[mask, 'expected_value'] - median) / median * 100
                    )
        
        # Isolation Forest for multivariate anomalies
        features_df = df[['expected_value', 'num_bids']].copy()
        features_df['log_value'] = np.log1p(features_df['expected_value'])
        features_df = features_df.fillna(0)
        
        if len(features_df) > 10:
            X = self.scaler.fit_transform(features_df)
            
            self.isolation_forest = IsolationForest(
                contamination=0.1,
                random_state=42,
                n_estimators=100
            )
            
            predictions = self.isolation_forest.fit_predict(X)
            anomaly_scores = self.isolation_forest.decision_function(X)
            
            df['is_price_outlier_if'] = predictions == -1
            df['isolation_forest_score'] = -anomaly_scores  # Higher = more anomalous
        else:
            df['is_price_outlier_if'] = False
            df['isolation_forest_score'] = 0.0
        
        # Combined price anomaly flag
        df['is_price_anomaly'] = df['is_price_outlier_zscore'] | df['is_price_outlier_if']
        
        return df
    
    # ========================================================================
    # Bid Pattern Analysis
    # ========================================================================
    
    def analyze_bid_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Analyze bidding patterns for collusion indicators."""
        df = df.copy()
        
        def calculate_bid_cv(bid_amounts):
            """Calculate coefficient of variation for bids."""
            if not isinstance(bid_amounts, list) or len(bid_amounts) < 2:
                return None
            bids = np.array([b for b in bid_amounts if b and b > 0])
            if len(bids) < 2 or bids.mean() == 0:
                return None
            return (bids.std() / bids.mean()) * 100
        
        # Bid coefficient of variation
        df['bid_cv'] = df['bid_amounts'].apply(calculate_bid_cv)
        
        # Suspicious bid spread (CV < 3% suggests possible coordination)
        df['suspicious_bid_spread'] = df['bid_cv'].apply(
            lambda x: x is not None and x < 3
        )
        
        # Single bidder flag
        df['is_single_bidder'] = df['num_bids'] <= 1
        
        # Combined bid pattern flag
        df['is_bid_pattern_anomaly'] = df['suspicious_bid_spread']
        
        return df
    
    # ========================================================================
    # Network Risk
    # ========================================================================
    
    def calculate_network_risk(
        self,
        contractor_id: str,
        network_metrics: Dict[str, Dict]
    ) -> float:
        """Get network risk score for a contractor."""
        if contractor_id in network_metrics:
            metrics = network_metrics[contractor_id]
            # Normalize degree centrality to 0-1 score
            return min(1.0, metrics.get('degree_centrality', 0) * 5)
        return 0.0
    
    # ========================================================================
    # Composite Risk Score
    # ========================================================================
    
    def calculate_risk_score(
        self,
        row: pd.Series,
        network_metrics: Optional[Dict[str, Dict]] = None
    ) -> Tuple[float, str, RiskFactors]:
        """Calculate composite risk score for a single tender."""
        factors = RiskFactors()
        
        # Price anomaly score (0-1)
        if row.get('is_price_anomaly', False):
            factors.is_price_anomaly = True
            # Normalize isolation forest score to 0-1
            if_score = row.get('isolation_forest_score', 0)
            if_min, if_max = -0.5, 0.5
            factors.price_anomaly_score = np.clip((if_score - if_min) / (if_max - if_min), 0, 1)
            factors.price_deviation_pct = row.get('price_deviation_pct')
            factors.reasons.append(
                f"Price anomaly detected ({factors.price_deviation_pct:+.0f}% from median)"
            )
        
        # Bid pattern score (0-1)
        if row.get('is_bid_pattern_anomaly', False):
            factors.is_bid_pattern_anomaly = True
            factors.bid_pattern_score = 1.0
            factors.bid_cv = row.get('bid_cv')
            factors.reasons.append(
                f"Suspicious bid spread (CV={factors.bid_cv:.1f}%)"
            )
        
        # Single bidder score (0-1)
        if row.get('is_single_bidder', False):
            factors.is_single_bidder = True
            factors.single_bidder_score = 1.0
            factors.reasons.append("Single bidder (no competition)")
        
        # Network risk score (0-1)
        if network_metrics and row.get('winner_id'):
            factors.network_risk_score = self.calculate_network_risk(
                str(row['winner_id']), network_metrics
            )
            if factors.network_risk_score > 0.5:
                factors.reasons.append("Winner has high network connectivity")
        
        # High value score (0-1)
        expected_value = row.get('expected_value', 0) or 0
        if self.value_threshold_p90 > 0 and expected_value > self.value_threshold_p90:
            factors.is_high_value = True
            factors.high_value_score = 1.0
            factors.reasons.append("High-value contract (top 10%)")
        
        # Calculate weighted composite score (0-100)
        risk_score = (
            factors.price_anomaly_score * self.weights['price_anomaly'] +
            factors.bid_pattern_score * self.weights['bid_pattern'] +
            factors.single_bidder_score * self.weights['single_bidder'] +
            factors.network_risk_score * self.weights['network_risk'] +
            factors.high_value_score * self.weights['high_value']
        ) * 100
        
        # Determine category
        if risk_score >= settings.RISK_THRESHOLD_CRITICAL:
            category = "critical"
        elif risk_score >= settings.RISK_THRESHOLD_HIGH:
            category = "high"
        elif risk_score >= settings.RISK_THRESHOLD_MEDIUM:
            category = "medium"
        else:
            category = "low"
        
        return risk_score, category, factors
    
    # ========================================================================
    # Batch Processing
    # ========================================================================
    
    def score_tenders(
        self,
        df: pd.DataFrame,
        network_metrics: Optional[Dict[str, Dict]] = None
    ) -> pd.DataFrame:
        """Score all tenders in a DataFrame."""
        logger.info(f"Scoring {len(df)} tenders...")
        
        # Calculate value threshold
        self.value_threshold_p90 = df['expected_value'].quantile(0.9)
        
        # Calculate category benchmarks
        self.calculate_category_benchmarks(df)
        
        # Detect anomalies
        df = self.detect_price_anomalies(df)
        df = self.analyze_bid_patterns(df)
        
        # Calculate risk scores
        scores = []
        categories = []
        factors_list = []
        
        for _, row in df.iterrows():
            score, category, factors = self.calculate_risk_score(row, network_metrics)
            scores.append(score)
            categories.append(category)
            factors_list.append(factors.to_dict())
        
        df['risk_score'] = scores
        df['risk_category'] = categories
        df['risk_factors'] = factors_list
        
        # Summary
        logger.info(f"Scoring complete:")
        logger.info(f"  - Critical: {(df['risk_category'] == 'critical').sum()}")
        logger.info(f"  - High: {(df['risk_category'] == 'high').sum()}")
        logger.info(f"  - Medium: {(df['risk_category'] == 'medium').sum()}")
        logger.info(f"  - Low: {(df['risk_category'] == 'low').sum()}")
        
        return df
    
    def score_contractors(
        self,
        contractors_df: pd.DataFrame,
        tenders_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Score contractors based on their tender history."""
        contractors_df = contractors_df.copy()
        
        # Aggregate tender-level scores to contractor level
        contractor_scores = tenders_df.groupby('winner_id').agg({
            'risk_score': 'mean',
            'is_single_bidder': 'mean',
            'is_price_anomaly': 'mean',
        }).reset_index()
        
        contractor_scores.columns = [
            'contractor_id', 'avg_risk_score', 
            'single_bidder_rate', 'price_anomaly_rate'
        ]
        
        # Merge with contractors
        contractors_df = contractors_df.merge(
            contractor_scores,
            left_on='id',
            right_on='contractor_id',
            how='left'
        )
        
        # Fill NaN with 0 for contractors with no wins
        contractors_df['risk_score'] = contractors_df['avg_risk_score'].fillna(0)
        
        # Categorize
        def categorize(score):
            if score >= settings.RISK_THRESHOLD_CRITICAL:
                return "critical"
            elif score >= settings.RISK_THRESHOLD_HIGH:
                return "high"
            elif score >= settings.RISK_THRESHOLD_MEDIUM:
                return "medium"
            return "low"
        
        contractors_df['risk_category'] = contractors_df['risk_score'].apply(categorize)
        
        return contractors_df


# Singleton instance
risk_engine = RiskScoringEngine()
