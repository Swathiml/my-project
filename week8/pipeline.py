import pandas as pd
import json
from analyzer import ChangeDetector, EventPrioritizer
from typing import Optional


class BehavioralAnalysisPipeline:
    """
    End-to-end execution from data loading to event prioritization
    """

    def __init__(self, data_path: str, goals_path: Optional[str] = None):
        self.data_path = data_path
        self.df = None
        self.goals = None
        self.detector = None
        self.results = None
        self.prioritizer = None

        if goals_path:
            with open(goals_path, 'r') as f:
                ground_truth = json.load(f)
                self.goals = ground_truth.get('user_goals', {})

    def load_data(self) -> pd.DataFrame:
        """Load transaction data"""
        self.df = pd.read_csv(self.data_path)
        self.df['date'] = pd.to_datetime(self.df['date'])
        print(f"Loaded {len(self.df)} transactions from {self.data_path}")
        return self.df

    def run_analysis(self) -> dict:
        """Execute full detection pipeline"""
        if self.df is None:
            self.load_data()

        self.detector = ChangeDetector(self.df)
        self.results = self.detector.detect_all(goals=self.goals)

        self.prioritizer = EventPrioritizer(self.results)

        return self.results

    def get_summary(self) -> dict:
        """Generate analysis summary"""
        if not self.results:
            return {}

        return {
            'dataset_summary': {
                'total_transactions': len(self.df),
                'date_range': {
                    'start': self.df['date'].min().strftime('%Y-%m-%d'),
                    'end': self.df['date'].max().strftime('%Y-%m-%d')
                },
                'categories': self.df['category'].unique().tolist()
            },
            'detection_summary': {
                'spending_spikes': len(self.results['spikes']),
                'category_drifts': len(self.results['drifts']),
                'anomalies': len(self.results['anomalies']),
                'savings_drops': len(self.results['savings_drops']),
                'goal_statuses': len(self.results['goals'])
            },
            'top_events': self.prioritizer.prioritize(top_n=5) if self.prioritizer else []
        }

    def export_results(self, output_path: str = 'output/final_report.json'):
        """Export complete analysis results"""
        if not self.results:
            raise ValueError("Run analysis before exporting results.")

        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        report = {
            'summary': self.get_summary(),
            'detailed_results': self.results,
            'all_events': self.prioritizer.all_events if self.prioritizer else []
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        return output_path


def main():
    pipeline = BehavioralAnalysisPipeline(
        data_path='output/synthetic_transactions_6mo.csv',
        goals_path='output/ground_truth_events.json'
    )

    pipeline.run_analysis()
    summary = pipeline.get_summary()

    print("\nFINAL SUMMARY\n")

    print(f"Dataset: {summary['dataset_summary']['total_transactions']} transactions")
    print(f"Period: {summary['dataset_summary']['date_range']['start']} "
          f"to {summary['dataset_summary']['date_range']['end']}")

    print("\nDetections:")
    for key, count in summary['detection_summary'].items():
        print(f"  - {key}: {count}")

    print("\nTop 5 Priority Events:")
    for i, event in enumerate(summary['top_events'], 1):
        print(f"  {i}. [{event['type']}] "
              f"{event.get('category', event.get('goal_name', ''))} "
              f"(Score: {event['priority_score']}, Month: {event.get('month', '')})")

    pipeline.export_results()


if __name__ == "__main__":
    main()