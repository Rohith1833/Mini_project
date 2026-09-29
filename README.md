# LocalLens — Restaurant Review Sentiment & Aspect Analyzer

An explainable Python application that tells a restaurant what customers discuss and how they feel about it: **food, service, price, cleanliness and wait time**.

## Start in Windows
1. Install Python **3.12** with “Add Python to PATH” enabled if needed.
2. Extract the entire ZIP; open the `locallens` folder.
3. Double-click **start_windows.bat**. First launch installs dependencies and requires internet.
4. The app opens in your browser, normally at http://localhost:8501. Keep the terminal open while using it.

If your browser does not open, visit the local URL printed in the terminal. Python 3.12 was used for verification. A Python installation is required; this is source code, not a standalone executable.

## Manual setup / Antigravity terminal
Open this folder in your IDE and run:
```bash
python -m venv .venv
```
Windows:
```bat
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```
The pinned pandas version requires a compatible prebuilt wheel; use Python 3.12 for this project. If `.venv` was created with another Python version, create a new 3.12 environment instead of trying to build pandas from source. The Windows launcher checks for Python 3.12 and will use `.venv312` if an incompatible `.venv` already exists.
macOS/Linux:
```bash
bash start_mac_linux.sh
```

## Features
- Paste one review and get overall sentiment plus five aspect results.
- Inspect the exact clause and keywords behind every aspect score.
- Start with the bundled public Yelp CSV, or choose the synthetic demo dataset.
- Upload a UTF-8 CSV or enter a CSV path on the machine running Streamlit.
- Process large CSVs in chunks, monitor processed and skipped rows, and browse results page by page.
- View aspect averages, mention counts, sentiment distribution and potential improvement priorities.
- Filter the review table by sentiment/aspect.
- Download analyzed reviews, aspect summary and clause evidence as CSV.
- No API keys, training step, database or paid service required.

## CSV format
```csv
review
"The food was delicious, but the service was slow."
"The staff were polite and the restroom was clean."
```
Other columns are allowed; select the text column in the app. There is no application-level file-size, row-count, or review-length rejection. Blank reviews are skipped and counted; malformed CSV rows are reported and stop processing rather than being discarded. Duplicates remain. Processing reads bounded chunks, stores analyzed rows and matched evidence in temporary local SQLite/CSV files, and calculates dashboard totals across every processed row. Practical capacity depends on available memory, disk space and processing time. The single-review analysis still needs enough memory for that one review.

For large files, choose **Local CSV path** and provide a path accessible to the machine running Streamlit; this avoids transferring the file through the browser. Browser upload size is controlled by Streamlit, not by LocalLens. The project pins Streamlit 1.64.0, which supports `server.maxUploadSize`; its framework default is 200 MB. Override it using Streamlit configuration (for example, `server.maxUploadSize = 512` in `.streamlit/config.toml`) or the `STREAMLIT_SERVER_MAX_UPLOAD_SIZE` environment variable. This ceiling applies only to browser uploads; the local-path option avoids it. Row counts displayed are calculated from the selected file, not assumed from the bundled dataset. Export row_id refers to the original data-row position (starting at 1, excluding the header). Metadata columns such as ratings are not used in predictions or copied to result exports.

Results are paginated for display only. Downloads contain all analyzed reviews and all matched evidence, not only the current page or filtered view. CSV exports retain formula-injection protection. A processing or resource failure is reported as incomplete; the app does not present partial results as completed.

## Method
Whitespace normalization → sentence/contrast-clause splitting → whole-word aspect dictionary → VADER sentiment per matched clause → average within each review/aspect → average across reviews mentioning each aspect.

Capitalization, negation and punctuation are retained. A small restaurant lexicon extension is explicit in `analyzer.py`; it is manually chosen, not trained. Some conjunctions are split when each side names an aspect. An unsplit clause mentioning multiple aspects shares its sentiment with all those aspects.

Compound scores run from −1 to +1. Positive ≥ 0.05; negative ≤ −0.05; otherwise neutral. An overall **Mixed** label means at least one clause is positive and another negative. Whole-review compound is also shown, so a mixed review can still have a positive or negative aggregate. Aspect labels reflect their average, not a separate mixed category. Unmentioned aspects are missing, never zero-filled. Slow service can match both Service and Wait time.

## Evaluation
Run `python evaluate.py` to reproduce `evaluation_results.json`.

On the bundled 1,000 UCI Yelp sentences, whole-sentence VADER with the documented lexicon achieved **74.5% forced-binary accuracy**, positive-class precision **66.94%**, recall **96.8%**, F1 **79.15%**. Binary protocol: compound ≥ 0 → positive, otherwise negative; zero ties go to positive. Confusion counts: TN 261, FP 239, FN 16, TP 484. This choice is deliberately explicit; 226 sentences fell in VADER's neutral band.

These numbers **do not measure aspect accuracy or the UI's four sentiment classes**. The dataset has no aspect annotations. No training or parameter tuning used these labels. This is a single public dataset check, not proof of generalization. Sarcasm, implicit aspects, complex syntax, misspellings and non-English text remain limitations.

## Tests
```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```
Tests cover conflicting clauses, negation, word boundaries, absent aspects, per-review averaging, CSV handling, exports and Streamlit interactions. They are software correctness checks, not a language-accuracy benchmark.

## Files
- `app.py`: Streamlit interface and charts.
- `analyzer.py`: aspect tagging, sentiment, CSV handling, summaries.
- `data/`: synthetic demo, public dataset and attribution.
- `evaluate.py`, `evaluation_results.json`: reproducible sentiment evaluation.
- `PROJECT_REPORT.md`: concise project explanation and demo script.
- `tests/`: analysis and application tests.
- `start_windows.bat`, `start_mac_linux.sh`: launchers.

## GitHub / hosting
Source is ready to add to a GitHub repository. Do not include `.venv` or your own private review datasets. For Streamlit hosting, use `app.py` as the entry point and Python 3.12. This package itself does not create a repository or deploy a hosted app.

**Netlify:** `netlify.toml` publishes a static build (`index.html` + `app.py`, `analyzer.py`, `data/`) that runs the same Streamlit app in the visitor's browser using [stlite](https://github.com/whitphx/stlite) (Pyodide). No Python server is needed; reviews are processed locally in the browser. The "Local CSV path" option only sees the browser's in-memory filesystem there, so use upload instead.

## Data and references
Public Yelp sentences: Kotzias, D. (2015). Sentiment Labelled Sentences [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C57604. CC BY 4.0: https://creativecommons.org/licenses/by/4.0/. Original TSV converted to CSV, preserving text and labels. See `data/DATA_SOURCES.md`.

Hutto, C.J. & Gilbert, E.E. (2014). VADER: A Parsimonious Rule-based Model for Sentiment Analysis of Social Media Text. ICWSM. Source: https://github.com/cjhutto/vaderSentiment.

Streamlit documentation: https://docs.streamlit.io/. App testing: https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest.
