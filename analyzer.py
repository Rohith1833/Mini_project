"""Explainable English restaurant-review baseline; no model training required."""
import csv
import io
import re
import sqlite3
from functools import lru_cache
from pathlib import Path

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

ASPECTS = {
    'Food': r'food|meal|meals|dish|dishes|pizza|pasta|burger|biryani|rice|chicken|dessert|taste|tasty|delicious|flavour|flavor|soup|salad|coffee|drink|drinks|portion|portions',
    'Service': r'service|staff|waiter|waiters|waitress|server|servers|manager|hospitality|employee|employees|rude|polite|friendly',
    'Price': r'price|prices|pricing|cost|costs|costly|expensive|cheap|affordable|bill|billing|value|overpriced|overcharged|budget|money',
    'Cleanliness': r'clean|cleanliness|dirty|hygiene|hygienic|unhygienic|filthy|spotless|restroom|washroom|toilet|cockroach|cockroaches',
    'Wait time': r'wait|waited|waiting|queue|queues|delay|delayed|slow|quick|quickly|prompt|minutes|hours',
}
PATTERNS = {a: re.compile(r'\b(?:' + words + r')\b', re.I) for a, words in ASPECTS.items()}
# Small, explicit restaurant vocabulary extension. Values are heuristic, not learned.
DOMAIN_LEXICON = {'slow': -1.5, 'delayed': -1.5, 'overpriced': -2.0,
                  'overcharged': -2.0, 'affordable': 1.5, 'spotless': 2.0,
                  'unhygienic': -2.5, 'bland': -1.5, 'tasteless': -2.0,
                  'quick': 1.2, 'prompt': 1.5}


@lru_cache(maxsize=1)
def engine():
    model = SentimentIntensityAnalyzer()
    model.lexicon.update(DOMAIN_LEXICON)
    return model


def label(score):
    return 'Positive' if score >= 0.05 else 'Negative' if score <= -0.05 else 'Neutral'


def clauses(text):
    # Keep casing, punctuation and negation for VADER. Avoid splitting "not only ... but also".
    text = re.sub(r'\bbut\s+also\b', 'and', text, flags=re.I)
    chunks = re.split(r'(?<=[.!?;])\s+|[;\n]+|\s*\b(?:but|however|although|whereas|yet)\b\s*', text, flags=re.I)
    result = []
    for chunk in chunks:
        # Split conjunctions only when both sides explicitly name an aspect.
        parts = re.split(r'\s+and\s+|,\s*', chunk, flags=re.I)
        if len(parts) > 1 and all(any(p.search(s) for p in PATTERNS.values()) for s in parts):
            result.extend(parts)
        else:
            result.append(chunk)
    return [s.strip(' ,') for s in result if s.strip(' ,')]


def analyze_review(text, evidence_callback=None):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Enter a non-empty review.')
    text = re.sub(r'[\t\r ]+', ' ', text).strip()
    evidence = []
    clause_scores = []
    aspect_totals = {aspect: [0.0, 0] for aspect in ASPECTS}
    for clause in clauses(text):
        score = engine().polarity_scores(clause)['compound']
        clause_scores.append(score)
        for aspect, pattern in PATTERNS.items():
            matches = list(dict.fromkeys(m.group().lower() for m in pattern.finditer(clause)))
            if matches:
                entry = {'aspect': aspect, 'text': clause, 'keywords': ', '.join(matches),
                         'score': score, 'sentiment': label(score)}
                aspect_totals[aspect][0] += score
                aspect_totals[aspect][1] += 1
                if evidence_callback is None:
                    evidence.append(entry)
                else:
                    evidence_callback(entry)
    whole_score = engine().polarity_scores(text)['compound']
    mixed = any(s >= .05 for s in clause_scores) and any(s <= -.05 for s in clause_scores)
    aspect_results = {}
    for aspect in ASPECTS:
        total, count = aspect_totals[aspect]
        if count:
            score = total / count
            aspect_results[aspect] = {'score': round(score, 4), 'sentiment': label(score)}
    return {'review': text, 'sentiment': 'Mixed' if mixed else label(whole_score),
            'compound': whole_score, 'aspects': aspect_results, 'evidence': evidence}


def load_csv(content):
    try:
        frame = pd.read_csv(io.BytesIO(content), encoding='utf-8-sig', dtype=str,
                    keep_default_na=False, on_bad_lines='error', skip_blank_lines=False)
    except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise ValueError(f'Could not read CSV. Use a UTF-8 CSV with a valid header and rows: {exc}') from exc
    if frame.empty:
        raise ValueError('CSV has no data rows.')
    return frame


def csv_columns(source):
    """Read only the CSV header and leave file-like sources ready for processing."""
    try:
        if hasattr(source, 'seek'):
            source.seek(0)
        frame = pd.read_csv(source, encoding='utf-8-sig', dtype=str, nrows=0,
                            on_bad_lines='error')
        return frame.columns.tolist()
    except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError, OSError) as exc:
        raise ValueError(f'Could not read CSV header. Use a readable UTF-8 CSV with a valid header: {exc}') from exc
    finally:
        if hasattr(source, 'seek'):
            source.seek(0)


def process_csv(source, column, database_path, chunksize=1000, progress_callback=None):
    """Analyze every CSV row into SQLite, retaining only one input chunk in memory."""
    if chunksize < 1:
        raise ValueError('Chunk size must be at least one row.')
    columns = csv_columns(source)
    if column not in columns:
        raise ValueError('Select a review column present in the CSV.')

    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        database_path.unlink()
    connection = sqlite3.connect(database_path)
    connection.execute('PRAGMA journal_mode = DELETE')
    result_columns = ['row_id INTEGER PRIMARY KEY', 'review TEXT NOT NULL',
                      'sentiment TEXT NOT NULL', 'compound REAL NOT NULL']
    for aspect in ASPECTS:
        result_columns.extend((f'"{aspect} score" REAL', f'"{aspect} sentiment" TEXT NOT NULL'))
    connection.execute(f'CREATE TABLE results ({", ".join(result_columns)})')
    connection.execute('''CREATE TABLE evidence (
        evidence_id INTEGER PRIMARY KEY, row_id INTEGER NOT NULL, aspect TEXT NOT NULL,
        text TEXT NOT NULL, keywords TEXT NOT NULL, score REAL NOT NULL, sentiment TEXT NOT NULL
    )''')

    sentiment_counts = {name: 0 for name in ('Positive', 'Neutral', 'Negative', 'Mixed')}
    aspect_totals = {aspect: {'sum': 0.0, 'count': 0, 'Positive': 0, 'Neutral': 0, 'Negative': 0}
                     for aspect in ASPECTS}
    rows_seen = analyzed = skipped = 0
    result_names = ['row_id', 'review', 'sentiment', 'compound']
    for aspect in ASPECTS:
        result_names.extend((f'{aspect} score', f'{aspect} sentiment'))
    result_sql = f"INSERT INTO results VALUES ({', '.join('?' for _ in result_names)})"

    try:
        reader = pd.read_csv(source, encoding='utf-8-sig', dtype=str, keep_default_na=False,
                     chunksize=chunksize, on_bad_lines='error', skip_blank_lines=False)
        for chunk in reader:
            result_rows = []
            for value in chunk[column].tolist():
                rows_seen += 1
                if not isinstance(value, str) or not value.strip():
                    skipped += 1
                    continue

                row_id = rows_seen
                evidence_writer = lambda item, current_id=row_id: connection.execute(
                    'INSERT INTO evidence (row_id, aspect, text, keywords, score, sentiment) VALUES (?, ?, ?, ?, ?, ?)',
                    (current_id, item['aspect'], item['text'], item['keywords'], item['score'], item['sentiment']))
                result = analyze_review(value, evidence_callback=evidence_writer)
                row = [row_id, result['review'], result['sentiment'], result['compound']]
                sentiment_counts[result['sentiment']] += 1
                for aspect in ASPECTS:
                    entry = result['aspects'].get(aspect)
                    row.extend((entry['score'] if entry else None,
                                entry['sentiment'] if entry else 'Not mentioned'))
                    if entry:
                        stats = aspect_totals[aspect]
                        stats['sum'] += entry['score']
                        stats['count'] += 1
                        stats[entry['sentiment']] += 1
                result_rows.append(row)
                analyzed += 1
            connection.executemany(result_sql, result_rows)
            connection.commit()
            if progress_callback:
                progress_callback({'rows_seen': rows_seen, 'analyzed': analyzed, 'skipped': skipped})
        if rows_seen == 0:
            raise ValueError('CSV has no data rows.')
        connection.commit()
    except ValueError:
        connection.close()
        database_path.unlink(missing_ok=True)
        raise
    except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        connection.close()
        database_path.unlink(missing_ok=True)
        raise ValueError(f'CSV processing stopped because the file is malformed or unreadable: {exc}') from exc
    except (OSError, MemoryError, sqlite3.Error) as exc:
        connection.close()
        database_path.unlink(missing_ok=True)
        raise ValueError(f'CSV processing failed before completion (resource or disk error): {exc}') from exc
    except Exception:
        connection.close()
        database_path.unlink(missing_ok=True)
        raise
    connection.close()

    return {
        'rows_seen': rows_seen,
        'analyzed': analyzed,
        'skipped': skipped,
        'sentiment_counts': sentiment_counts,
        'aspect_stats': {
            aspect: {
                'mean': stats['sum'] / stats['count'] if stats['count'] else None,
                'count': stats['count'],
                'Positive': stats['Positive'],
                'Neutral': stats['Neutral'],
                'Negative': stats['Negative'],
            }
            for aspect, stats in aspect_totals.items()
        },
    }


def write_query_csv(database_path, query, output_path):
    """Write a SQLite query to CSV with spreadsheet formula protection."""
    connection = sqlite3.connect(f'{Path(database_path).resolve().as_uri()}?mode=ro', uri=True)
    try:
        cursor = connection.execute(query)
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as output:
            writer = csv.writer(output)
            writer.writerow([description[0] for description in cursor.description])
            for row in cursor:
                writer.writerow([
                    "'" + value if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')) else value
                    for value in row
                ])
    finally:
        connection.close()
    return output_path


def analyze_dataset(frame, column):
    if column not in frame:
        raise ValueError('Select a review column present in the CSV.')
    rows, evidence = [], []
    skipped = 0
    for row_id, value in enumerate(frame[column].tolist(), 1):
        if not isinstance(value, str) or not value.strip():
            skipped += 1
            continue
        result = analyze_review(value)
        row = {'row_id': row_id, 'review': result['review'], 'sentiment': result['sentiment'],
               'compound': result['compound']}
        for aspect in ASPECTS:
            entry = result['aspects'].get(aspect)
            row[f'{aspect} score'] = entry['score'] if entry else None
            row[f'{aspect} sentiment'] = entry['sentiment'] if entry else 'Not mentioned'
        rows.append(row)
        evidence.extend({'row_id': row_id, **e} for e in result['evidence'])
    return pd.DataFrame(rows), pd.DataFrame(evidence), skipped


def aspect_summary(results):
    rows = []
    for aspect in ASPECTS:
        scores = results[f'{aspect} score'].dropna() if not results.empty else pd.Series(dtype=float)
        rows.append({'Aspect': aspect, 'Mean sentiment': round(float(scores.mean()), 3) if len(scores) else None,
                     'Reviews mentioning': len(scores), 'Positive': int((scores >= .05).sum()),
                     'Neutral': int(((scores > -.05) & (scores < .05)).sum()),
                     'Negative': int((scores <= -.05).sum())})
    return pd.DataFrame(rows)


def csv_bytes(frame):
    # Prevent review text from becoming a formula when opened in spreadsheet software.
    safe = frame.copy()
    for col in safe.select_dtypes(include=['object', 'string']).columns:
        safe[col] = safe[col].map(lambda v: "'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v)
    return safe.to_csv(index=False).encode('utf-8-sig')
