# Week 3 – Error Analysis Report

## Overview

This report analyzes the performance of the transaction categorization pipeline
using zero-shot classification (facebook/bart-large-mnli) with confidence thresholds
and fallback rules.

Dataset:
- Total transactions: 50
- Evaluation method: comparison with category_hint ground truth

---

## Baseline Performance

- Accuracy: 64% (32/50 correct)
- Confidence Distribution:
  - High: 13
  - Medium: 17
  - Low: 20

- Status Distribution:
  - auto-accepted: 13
  - suggested: 28
  - fallback: 6
  - uncategorized: 3

Observation:
High confidence predictions were generally reliable, while low confidence
predictions indicate ambiguous merchant descriptions.

---

## Category Distribution

| Category | Count |
|----------|------|
| subscriptions | 14 |
| food and dining | 7 |
| fees | 7 |
| transportation | 6 |
| income | 6 |
| groceries | 3 |
| shopping | 3 |
| travel | 2 |
| healthcare | 2 |

Observation:
The "subscriptions" category appears overrepresented, likely due to recurring
payment descriptions influencing zero-shot predictions.

---

## Error Patterns Identified

Based on low-confidence inspection:

- Some merchants were misclassified despite clear names:
  - SHELL → predicted fees instead of transportation
  - TARGET → predicted fees instead of shopping
  - UBER EATS → predicted transportation instead of food and dining

- Travel merchants such as HILTON and UNITED AIRLINES received lower
  confidence scores even when correctly categorized.

Possible causes:
- Ambiguous merchant text after normalization
- Zero-shot model bias toward certain categories
- Conservative fallback trigger threshold

---

## Fallback Rule Behavior

Fallback classification triggered 6 times.

Impact:
- Reduced "fees" misclassification compared to earlier versions.
- Helped correct obvious merchant names where zero-shot confidence was low.

However:
- Some low-confidence predictions remained unresolved,
  which suggests potential areas for future tuning.

---

## Confidence Threshold Observations

Thresholds used:
- Auto-accept: > 0.7
- Suggested: 0.5 – 0.7
- Weak prediction: < 0.5

Findings:
- Many predictions fell into the low-confidence range.
- The strict fallback trigger helped maintain stability but limited
  automatic correction.

---

## Evidence Integration

Each prediction includes an evidence record containing:
- Input text used for classification
- Hypothesis template
- Full category score distribution
- Top category alternatives

This supports transparency and allows later explanation of model decisions.

---

## Conclusion

The Week 3 pipeline demonstrates a stable baseline with interpretable results:

Strengths:
- Clear preprocessing and clustering workflow
- Structured evidence tracking
- Balanced category distribution
- Functional fallback rules

Limitations:
- Moderate accuracy (64%)
- Overrepresentation of "subscriptions"
- Some ambiguous merchants remain low confidence

The pipeline is suitable as a baseline system and provides a foundation
for future iteration and refinement.
