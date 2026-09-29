# Data sources

## uci_yelp_reviews.csv
1,000 sentences from restaurant reviews, with 500 positive and 500 negative labels.
Source: UCI Sentiment Labelled Sentences, Yelp subset.
https://archive.ics.uci.edu/dataset/331/sentiment+labelled+sentences

Citation: Kotzias, D. (2015). Sentiment Labelled Sentences [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C57604.

License: Creative Commons Attribution 4.0 International.
https://creativecommons.org/licenses/by/4.0/

Modification: Converted original yelp_labelled.txt tab-separated rows into UTF-8 CSV with review,label headers. Review text and binary labels retained. These are extracted sentences, not necessarily complete reviews. No aspect labels are provided.

Related paper: Dimitrios Kotzias, Misha Denil, Nando de Freitas, Padhraic Smyth. From Group to Individual Labels Using Deep Features, KDD 2015.

## demo_reviews.csv
30 synthetic examples authored for this project. Not scraped, not real customer feedback, and not used as an accuracy benchmark.
