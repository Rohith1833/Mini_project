# LocalLens: Local Business Review Sentiment and Aspect Analyzer

## Abstract
LocalLens is a restaurant-review analysis tool that identifies customer opinions about food, service, price, cleanliness and waiting time. It combines keyword-based aspect tagging with VADER sentiment scoring at clause level. Users can analyze an individual review or upload a CSV and explore per-aspect scores. The prototype uses Python, pandas and Streamlit and includes a public restaurant-review sentence dataset.

## Problem and objectives
A single positive/negative label hides mixed experiences. A review can praise food while criticizing service. The objectives are to identify explicit aspects, estimate sentiment for each aspect, show supporting text, aggregate feedback and help businesses decide which comments deserve investigation.

## Architecture
User input or CSV → input validation → clause splitting → aspect keyword matching → VADER scoring → review-level aspect aggregation → dataset summary → Streamlit charts and CSV export.

## Implementation
VADER provides a sentiment lexicon and contextual rules. A small restaurant-specific vocabulary extension handles terms such as slow and overpriced. Whole-word keyword rules identify aspects. Sentences and contrast words separate opinions; some conjunctions split when each side has an explicit aspect. Negation, case and punctuation remain intact.

Each review receives one score for each aspect it mentions. The dashboard averages those scores across mentioning reviews, giving each review equal weight within an aspect. Aspects with no mentions have no score. Both mention counts and scores are shown because an average based on one review carries limited evidence.

## Dataset
The public dataset consists of 1,000 Yelp restaurant-review sentences from UCI Sentiment Labelled Sentences: 500 positive and 500 negative. It is attributed and distributed under CC BY 4.0. Thirty synthetic reviews are included separately for demonstrations. Neither dataset contains aspect-level ground truth.

## Results
The supplied evaluation script measured 74.5% whole-sentence forced-binary accuracy on the 1,000 UCI Yelp sentences. Positive-class F1 was approximately 79.15%. Compound scores of zero were mapped to positive, and the UI's neutral and mixed rules were not part of this binary evaluation. This metric must not be presented as aspect sentiment accuracy.

## Limitations and future work
The baseline is English-only and may miss implicit aspects or misread sarcasm, negation scope and complex multi-aspect clauses. Keywords can overlap, and all aspects in an unsplit clause share a score. Future work includes an independently annotated aspect test set, better clause parsing, domain-specific keyword dictionaries, and a supervised aspect model compared fairly against this baseline.

## Two-minute demonstration
1. Open Review explorer and analyze “The food was delicious, but the service was slow.”
2. Point out positive food, negative service, and the matched clauses.
3. Open Dataset dashboard and switch to Public Yelp dataset.
4. Explain the five aspect averages and mention counts. Missing aspects do not count as neutral.
5. Filter negative reviews, inspect comments and download the results.
6. Explain that this is a rule-based baseline, not a newly trained model.

## Common viva questions
**Why aspect-based analysis?** It connects opinions to specific business attributes instead of assigning only one overall label.

**Did you train a model?** No. The implementation uses VADER's existing sentiment lexicon and rules plus an explicit keyword dictionary and small vocabulary extension.

**What is the score?** A sentiment compound between −1 and +1, not a probability or customer rating.

**Why not remove stop words?** Removing words such as “not” can reverse meaning. Punctuation and case also carry sentiment cues.

**How was accuracy measured?** By comparing a forced-binary whole-sentence prediction to the provided UCI labels. There are no aspect labels, so aspect accuracy is not measured.

**How does a small business use this?** It can inspect repeated negative feedback for an aspect and prioritize investigation, while checking the original text before acting.

## References
Kotzias, D. (2015). Sentiment Labelled Sentences. UCI. https://doi.org/10.24432/C57604.

Hutto, C.J. & Gilbert, E.E. (2014). VADER: A Parsimonious Rule-based Model for Sentiment Analysis of Social Media Text. ICWSM. https://github.com/cjhutto/vaderSentiment.
