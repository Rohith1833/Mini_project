"""Reproducible whole-sentence sentiment check; NOT aspect accuracy."""
import json
from pathlib import Path
import pandas as pd
from analyzer import engine

def evaluate():
    frame = pd.read_csv(Path(__file__).parent / 'data' / 'uci_yelp_reviews.csv')
    scores = frame.review.map(lambda text: engine().polarity_scores(text)['compound'])
    # Explicit forced-binary protocol; zero (ties) maps to positive.
    predictions = (scores >= 0).astype(int)
    truth = frame.label.astype(int)
    tp = int(((predictions == 1) & (truth == 1)).sum())
    fp = int(((predictions == 1) & (truth == 0)).sum())
    fn = int(((predictions == 0) & (truth == 1)).sum())
    tn = int(((predictions == 0) & (truth == 0)).sum())
    return {'dataset': 'UCI Yelp subset; 1000 labelled sentences', 'rows': len(frame),
            'method': 'VADER plus documented restaurant lexicon; no training or tuning on these labels',
            'protocol': 'Forced binary whole-sentence compound >= 0 is positive; otherwise negative. Differs from UI neutral/mixed handling.',
            'accuracy': float((predictions == truth).mean()), 'positive_precision': tp/(tp+fp),
            'positive_recall': tp/(tp+fn), 'positive_f1': 2*tp/(2*tp+fp+fn),
            'confusion_matrix': {'true_negative': tn, 'false_positive': fp, 'false_negative': fn, 'true_positive': tp},
            'neutral_band_sentences': int(((scores > -.05) & (scores < .05)).sum()),
            'limitations': 'One public dataset, no aspect labels. Not an estimate of aspect detection accuracy, UI four-class accuracy, or performance on unseen local businesses.'}

if __name__ == '__main__':
    result = evaluate()
    dest = Path(__file__).parent / 'evaluation_results.json'
    dest.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
