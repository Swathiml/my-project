import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional


class ChangeDetector:
    """
    Week 8: Behavioral & Change Detection
    Detects spending spikes, category drift, anomalies, and savings changes
    """
    
    def __init__(self, transactions_df: pd.DataFrame):
        self.df = transactions_df.copy()
        self.df['date'] = pd.to_datetime(self.df['date'])
        self.df['month'] = self.df['date'].dt.to_period('M')
        self.events = []
        
    # ============================================
    # 1. MONTH-OVER-MONTH COMPARISON
    # ============================================
    
    def calculate_monthly_totals(self) -> pd.DataFrame:
        """Calculate total spending per category per month"""
        monthly = self.df.groupby(['month', 'category'])['amount'].sum().unstack(fill_value=0)
        return monthly
    
    def calculate_mom_changes(self) -> pd.DataFrame:
        """Calculate month-over-month percentage changes"""
        monthly = self.calculate_monthly_totals()
        # For expenses (negative), we compare absolute values
        mom_changes = monthly.apply(lambda x: x.abs()).pct_change() * 100
        return mom_changes.fillna(0)
    
    # ============================================
    # 2. SPENDING SPIKE DETECTION (Z-Score)
    # ============================================
    
    def detect_spikes(self, z_threshold: float = 2.0, lookback_months: int = 3) -> List[Dict]:
        """
        Detect spending spikes using Z-score vs rolling average
        Z = (current - mean) / std
        """
        monthly = self.calculate_monthly_totals()
        spikes = []
        
        for category in monthly.columns:
            if category == 'income':
                continue  # Skip income for spending spikes
                
            spending = monthly[category].abs()  # Convert to positive for comparison
            
            # Calculate rolling statistics
            rolling_mean = spending.rolling(window=lookback_months, min_periods=1).mean()
            rolling_std = spending.rolling(window=lookback_months, min_periods=1).std()
            
            # Avoid division by zero
            rolling_std = rolling_std.replace(0, np.nan)
            
            # Calculate Z-scores
            z_scores = (spending - rolling_mean) / rolling_std
            
            # Find spikes
            for month, z_score in z_scores.items():
                if pd.notna(z_score) and abs(z_score) > z_threshold:
                    current_amount = spending[month]
                    previous_mean = rolling_mean[month]
                    
                    spikes.append({
                        'type': 'spending_spike',
                        'category': category,
                        'month': str(month),
                        'current_amount': round(current_amount, 2),
                        'baseline_amount': round(previous_mean, 2),
                        'change_pct': round(((current_amount - previous_mean) / previous_mean * 100), 1) if previous_mean > 0 else 0,
                        'z_score': round(z_score, 2),
                        'severity': 'high' if abs(z_score) > 3 else 'medium',
                        'confidence': min(0.95, 0.7 + abs(z_score) * 0.05)  # Higher confidence for extreme Z
                    })
        
        return spikes
    
    # ============================================
    # 3. CATEGORY DRIFT DETECTION (Rolling Average)
    # ============================================
    
    def detect_drift(self, drift_threshold_pct: float = 30.0, window_months: int = 3) -> List[Dict]:
        """
        Detect gradual spending increases using rolling averages
        Flag if 3-month rolling average increases by >30%
        """
        monthly = self.calculate_monthly_totals()
        drifts = []
        
        for category in monthly.columns:
            if category == 'income':
                continue
                
            spending = monthly[category].abs()
            
            # Calculate 3-month rolling average
            rolling_avg = spending.rolling(window=window_months, min_periods=2).mean()
            
            # Calculate change in rolling average (month-over-month of the rolling avg)
            rolling_change = rolling_avg.pct_change() * 100
            
            for month, change in rolling_change.items():
                if pd.notna(change) and change > drift_threshold_pct:
                    # Check if this is part of a sustained trend (at least 2 consecutive increases)
                    month_idx = rolling_change.index.get_loc(month)
                    if month_idx >= 1:
                        prev_change = rolling_change.iloc[month_idx - 1]
                        if pd.notna(prev_change) and prev_change > 0:
                            drifts.append({
                                'type': 'category_drift',
                                'category': category,
                                'month': str(month),
                                'rolling_avg_current': round(rolling_avg[month], 2),
                                'rolling_avg_previous': round(rolling_avg.shift(1)[month], 2),
                                'change_pct': round(change, 1),
                                'trend_months': window_months,
                                'severity': 'high' if change > 50 else 'medium',
                                'confidence': min(0.9, 0.6 + change/100)
                            })
        
        return drifts
    
    # ============================================
    # 4. ANOMALY DETECTION (IQR Method)
    # ============================================
    
    def detect_anomalies(self, multiplier: float = 1.5) -> List[Dict]:
        """
        Detect anomalous individual transactions using IQR method
        Outlier if: amount > Q3 + 1.5*IQR or amount < Q1 - 1.5*IQR
        """
        anomalies = []
        
        for category in self.df['category'].unique():
            if category == 'income':
                continue
                
            cat_data = self.df[self.df['category'] == category].copy()
            amounts = cat_data['amount'].abs()
            
            if len(amounts) < 4:  # Need minimum data for IQR
                continue
                
            q1 = amounts.quantile(0.25)
            q3 = amounts.quantile(0.75)
            iqr = q3 - q1
            
            upper_bound = q3 + (multiplier * iqr)
            lower_bound = q1 - (multiplier * iqr)  # Usually not relevant for spending
            
            # Find outliers
            outliers = cat_data[amounts > upper_bound]
            
            for _, txn in outliers.iterrows():
                anomalies.append({
                    'type': 'anomaly',
                    'category': category,
                    'transaction_id': txn['transaction_id'],
                    'date': txn['date'].strftime('%Y-%m-%d'),
                    'amount': round(abs(txn['amount']), 2),
                    'merchant': txn['merchant_raw'],
                    'upper_bound': round(upper_bound, 2),
                    'exceeds_by_pct': round((abs(txn['amount']) - upper_bound) / upper_bound * 100, 1) if upper_bound > 0 else 0,
                    'severity': 'high' if abs(txn['amount']) > q3 + 3*iqr else 'medium',
                    'confidence': 0.85 if abs(txn['amount']) > q3 + 3*iqr else 0.75
                })
        
        return anomalies
    
    # ============================================
    # 5. SAVINGS RATE TRACKING
    # ============================================
    
    def calculate_savings_rate(self) -> pd.DataFrame:
        """Calculate savings rate per month (income - spending) / income"""
        monthly = self.calculate_monthly_totals()
        
        if 'income' not in monthly.columns:
            return pd.DataFrame()
        
        income = monthly['income']
        # Sum all expense categories (negative values)
        expenses = monthly.drop('income', axis=1).sum(axis=1).abs()
        
        savings = income - expenses
        savings_rate = (savings / income).replace([np.inf, -np.inf], 0)
        
        return pd.DataFrame({
            'income': income,
            'expenses': expenses,
            'savings': savings,
            'savings_rate': savings_rate,
            'savings_rate_pct': (savings_rate * 100).round(1)
        })
    
    def detect_savings_drops(self, threshold_pct: float = 20.0) -> List[Dict]:
        """
        Detect significant drops in savings rate month-over-month
        """
        savings_df = self.calculate_savings_rate()
        if savings_df.empty:
            return []
        
        drops = []
        prev_rate = None
        
        for month, row in savings_df.iterrows():
            current_rate = row['savings_rate']
            
            if prev_rate is not None and prev_rate > 0:
                rate_change_pct = ((current_rate - prev_rate) / prev_rate) * 100
                
                if rate_change_pct < -threshold_pct:  # Drop > 20%
                    drops.append({
                        'type': 'savings_drop',
                        'month': str(month),
                        'savings_rate_previous': round(prev_rate * 100, 1),
                        'savings_rate_current': round(current_rate * 100, 1),
                        'drop_pct': round(abs(rate_change_pct), 1),
                        'income': round(row['income'], 2),
                        'expenses': round(row['expenses'], 2),
                        'severity': 'high' if rate_change_pct < -40 else 'medium',
                        'confidence': min(0.95, 0.7 + abs(rate_change_pct)/100)
                    })
            
            prev_rate = current_rate
        
        return drops
    
    # ============================================
    # 6. GOAL TRACKING
    # ============================================
    
    def track_goals(self, goals: Dict[str, Any]) -> List[Dict]:
        """
        Track progress against user-defined goals
        goals format: {'category_budget': {'limit': 400, 'period': 'monthly'}}
        """
        monthly = self.calculate_monthly_totals()
        goal_status = []
        
        for goal_name, goal_config in goals.items():
            if 'category' in goal_name or '_budget' in goal_name:
                # Extract category from goal name (e.g., 'dining_budget' -> 'dining')
                category = goal_name.replace('_budget', '').replace('_', ' ')
                
                if category in monthly.columns:
                    limit = goal_config['limit']
                    
                    for month, amount in monthly[category].items():
                        spent = abs(amount)
                        remaining = limit - spent
                        pct_used = (spent / limit) * 100 if limit > 0 else 0
                        
                        status = 'on_track' if spent <= limit else 'exceeded'
                        
                        goal_status.append({
                            'type': 'goal_status',
                            'goal_name': goal_name,
                            'category': category,
                            'month': str(month),
                            'budget_limit': limit,
                            'amount_spent': round(spent, 2),
                            'remaining': round(remaining, 2),
                            'pct_used': round(pct_used, 1),
                            'status': status,
                            'severity': 'warning' if pct_used > 100 else ('caution' if pct_used > 80 else 'good'),
                            'confidence': 0.9
                        })
            
            elif 'savings_rate' in goal_name:
                # Savings rate goal
                target_rate = goal_config.get('target', 0.20)
                savings_df = self.calculate_savings_rate()
                
                for month, row in savings_df.iterrows():
                    actual_rate = row['savings_rate']
                    gap = (target_rate - actual_rate) * 100  # percentage points
                    
                    goal_status.append({
                        'type': 'goal_status',
                        'goal_name': goal_name,
                        'month': str(month),
                        'target_rate_pct': round(target_rate * 100, 1),
                        'actual_rate_pct': round(actual_rate * 100, 1),
                        'gap_pct': round(gap, 1),
                        'status': 'on_track' if actual_rate >= target_rate else 'below_target',
                        'severity': 'warning' if actual_rate < target_rate * 0.5 else ('caution' if actual_rate < target_rate else 'good'),
                        'confidence': 0.9
                    })
        
        return goal_status
    
    # ============================================
    # 7. RUN ALL DETECTIONS
    # ============================================
    
    def detect_all(self, goals: Optional[Dict] = None) -> Dict[str, List[Dict]]:
        """Run all detection algorithms and return combined results"""
        print("=" * 60)
        print("RUNNING CHANGE DETECTION ALGORITHMS")
        print("=" * 60)
        
        results = {
            'spikes': self.detect_spikes(),
            'drifts': self.detect_drift(),
            'anomalies': self.detect_anomalies(),
            'savings_drops': self.detect_savings_drops(),
            'goals': self.track_goals(goals) if goals else []
        }
        
        # Print summary
        print(f"\nDETECTION SUMMARY:")
        print(f"  - Spending spikes detected: {len(results['spikes'])}")
        print(f"  - Category drifts detected: {len(results['drifts'])}")
        print(f"  - Anomalies detected: {len(results['anomalies'])}")
        print(f"  - Savings drops detected: {len(results['savings_drops'])}")
        print(f"  - Goal statuses tracked: {len(results['goals'])}")
        
        return results


# ============================================
# EVENT PRIORITIZATION
# ============================================

class EventPrioritizer:
    """Rank detected events by importance and user relevance"""
    
    def __init__(self, events: Dict[str, List[Dict]]):
        self.events = events
        self.all_events = []
        self._flatten_events()
    
    def _flatten_events(self):
        """Combine all event types into single list with scores"""
        for event_type, event_list in self.events.items():
            for event in event_list:
                event['event_type'] = event_type
                self.all_events.append(event)
    
    def calculate_priority_score(self, event: Dict) -> float:
        """
        Calculate priority score based on:
        - Magnitude of change (40%)
        - Confidence (30%)
        - Severity (20%)
        - Recency (10%) - higher for recent months
        """
        score = 0.0
        
        # Magnitude component (40%)
        if 'change_pct' in event:
            magnitude = min(abs(event['change_pct']) / 100, 2.0)  # Cap at 2x
        elif 'drop_pct' in event:
            magnitude = min(event['drop_pct'] / 50, 2.0)
        elif 'amount' in event:
            magnitude = min(event['amount'] / 500, 2.0)
        else:
            magnitude = 0.5
        score += magnitude * 0.4
        
        # Confidence component (30%)
        confidence = event.get('confidence', 0.7)
        score += confidence * 0.3
        
        # Severity component (20%)
        severity_map = {'high': 1.0, 'medium': 0.6, 'low': 0.3, 'warning': 0.8, 'caution': 0.5, 'good': 0.2}
        severity = severity_map.get(event.get('severity', 'medium'), 0.5)
        score += severity * 0.2
        
        # Recency component (10%) - assume later months are more recent
        month_str = event.get('month', '2026-01')
        try:
            month_num = int(str(month_str).split('-')[1])
            recency = month_num / 6.0  # Normalize to 6 months
        except:
            recency = 0.5
        score += recency * 0.1
        
        return round(score, 3)
    
    def prioritize(self, top_n: int = 10) -> List[Dict]:
        """Sort events by priority score and return top N"""
        for event in self.all_events:
            event['priority_score'] = self.calculate_priority_score(event)
        
        # Sort by priority score descending
        sorted_events = sorted(self.all_events, key=lambda x: x['priority_score'], reverse=True)
        
        return sorted_events[:top_n]
    
    def get_events_by_category(self, category: str) -> List[Dict]:
        """Get all events for a specific spending category"""
        return [e for e in self.all_events if e.get('category') == category]
    
    def get_events_by_month(self, month: str) -> List[Dict]:
        """Get all events for a specific month (format: '2026-04')"""
        return [e for e in self.all_events if e.get('month') == month]


# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    # Load data
    df = pd.read_csv('output/synthetic_transactions_6mo.csv')
    
    # Initialize detector
    detector = ChangeDetector(df)
    
    # Define goals (from ground truth)
    goals = {
        'dining_budget': {'limit': 400, 'period': 'monthly'},
        'grocery_budget': {'limit': 600, 'period': 'monthly'},
        'savings_rate': {'target': 0.20, 'period': 'monthly'}
    }
    
    # Run detection
    results = detector.detect_all(goals=goals)
    
    # Prioritize events
    prioritizer = EventPrioritizer(results)
    top_events = prioritizer.prioritize(top_n=10)
    
    print(f"\n{'='*60}")
    print("TOP 10 PRIORITY EVENTS")
    print(f"{'='*60}")
    for i, event in enumerate(top_events, 1):
        print(f"{i}. [{event['type'].upper()}] {event.get('category', event.get('goal_name', 'N/A'))}")
        print(f"   Month: {event.get('month', 'N/A')}, Score: {event['priority_score']}")
        print(f"   Severity: {event.get('severity', 'N/A')}, Confidence: {event.get('confidence', 'N/A')}")
        print()
    
    # Save results
    import json
    with open('output/detected_events.json', 'w') as f:
        json.dump({
            'all_events': results,
            'top_priorities': top_events,
            'summary': {
                'total_events': sum(len(v) for v in results.values()),
                'categories_affected': list(set(e.get('category') for e in prioritizer.all_events if e.get('category')))
            }
        }, f, indent=2, default=str)
    
    print("Results saved to: output/detected_events.json")