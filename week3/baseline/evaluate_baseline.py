import pandas as pd
import json

def convert_to_serializable(obj):
    """
    Convert pandas/numpy types to Python native types for JSON serialization
    """
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (pd.Int64Dtype, pd.Series, pd.DataFrame)):
        return obj.astype(str).to_dict() if hasattr(obj, 'to_dict') else str(obj)
    elif hasattr(obj, 'item'):  # numpy scalar
        return obj.item()
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(i) for i in obj]
    else:
        return str(obj)

def evaluate_baseline():
    """
    Evaluate Week 2 baseline performance
    """
    df = pd.read_csv('week2/week2_deliverable.csv')
    
    # Get value counts and convert to regular Python dict with int values
    cat_dist = df['category'].value_counts()
    conf_dist = df['confidence_level'].value_counts()
    type_dist = df['transaction_type'].value_counts()
    
    report = {
        'total_transactions': int(len(df)),
        'category_distribution': {str(k): int(v) for k, v in cat_dist.items()},
        'confidence_distribution': {str(k): int(v) for k, v in conf_dist.items()},
        'avg_confidence': float(df['category_confidence'].mean()),
        'transaction_types': {str(k): int(v) for k, v in type_dist.items()}
    }
    
    # Calculate accuracy vs ground truth if available
    if 'category_hint' in df.columns:
        correct = int((df['category'] == df['category_hint']).sum())
        report['accuracy'] = round(correct / len(df), 3)
        report['misclassifications'] = int(len(df) - correct)
    
    # Identify problematic categories
    low_conf = df[df['confidence_level'] == 'low']
    report['low_confidence_count'] = int(len(low_conf))
    low_conf_by_cat = low_conf['category'].value_counts().head(5)
    report['low_confidence_by_category'] = {str(k): int(v) for k, v in low_conf_by_cat.items()}
    
    # Save report
    with open('week3/baseline/baseline_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("=" * 60)
    print("WEEK 2 BASELINE EVALUATION")
    print("=" * 60)
    print(f"Total transactions: {report['total_transactions']}")
    print(f"Average confidence: {report['avg_confidence']:.3f}")
    print(f"\nCategory distribution:")
    for cat, count in report['category_distribution'].items():
        pct = count / report['total_transactions'] * 100
        print(f"  {cat}: {count} ({pct:.1f}%)")
    
    print(f"\nConfidence levels:")
    for level, count in report['confidence_distribution'].items():
        pct = count / report['total_transactions'] * 100
        print(f"  {level}: {count} ({pct:.1f}%)")
    
    if 'accuracy' in report:
        print(f"\nAccuracy vs ground truth: {report['accuracy']:.1%}")
    
    print(f"\nLow confidence predictions: {report['low_confidence_count']}")
    
    return report

if __name__ == "__main__":
    evaluate_baseline()