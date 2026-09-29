import io
import sqlite3
from pathlib import Path

import pandas as pd
import pytest
from analyzer import (analyze_review, analyze_dataset, aspect_summary, load_csv,
                      csv_bytes, process_csv, write_query_csv)

def test_contrast_separates_aspects():
    r = analyze_review('The food was delicious, but the service was slow.')
    assert r['sentiment'] == 'Mixed'
    assert r['aspects']['Food']['sentiment'] == 'Positive'
    assert r['aspects']['Service']['sentiment'] == 'Negative'

def test_conjunction_separates_explicit_aspects():
    r = analyze_review('The food was great and the service was terrible.')
    assert r['aspects']['Food']['score'] > 0
    assert r['aspects']['Service']['score'] < 0

def test_negation_preserved():
    assert analyze_review('The food was not good.')['aspects']['Food']['score'] < 0
    assert analyze_review('The staff were not rude.')['aspects']['Service']['score'] > 0

def test_whole_words_and_absent_aspects():
    assert not analyze_review('We sat beside a priceless painting.')['aspects']

def test_only_mentioned_reviews_in_average():
    results, _, skipped = analyze_dataset(pd.DataFrame({'text': ['The food was great.', 'The staff were rude.', '', None]}), 'text')
    s = aspect_summary(results).set_index('Aspect')
    assert skipped == 2
    assert s.loc['Food', 'Reviews mentioning'] == 1
    assert s.loc['Food', 'Mean sentiment'] == round(results.iloc[0]['Food score'], 3)
    assert pd.isna(s.loc['Cleanliness', 'Mean sentiment'])

def test_each_review_has_equal_weight():
    r, _, _ = analyze_dataset(pd.DataFrame({'review': ['Great food. Amazing food.', 'Terrible food.']}), 'review')
    summary = aspect_summary(r).set_index('Aspect')
    assert summary.loc['Food', 'Reviews mentioning'] == 2
    assert summary.loc['Food', 'Mean sentiment'] == round(r['Food score'].mean(), 3)

@pytest.mark.parametrize('content', [b'', b'review\n', b'\xff\xfe\x00', b'review,stars\na,1,2\nb,1,2,3'])
def test_bad_csv(content):
    with pytest.raises(ValueError):
        load_csv(content)

def test_csv_quotes_and_bom():
    f = load_csv('\ufeffreview,stars\n"Great food, rude staff",3\n'.encode('utf-8'))
    assert f.iloc[0]['review'] == 'Great food, rude staff'

def test_export_formula_protection():
    assert "'=1+1" in csv_bytes(pd.DataFrame({'review': ['=1+1']})).decode('utf-8-sig')


def test_streamed_export_formula_protection(tmp_path):
    database = tmp_path / 'formula.sqlite'
    process_csv(io.BytesIO(b'review\n=1+1\n'), 'review', database)
    exported = write_query_csv(database, 'SELECT * FROM results ORDER BY row_id', tmp_path / 'safe.csv')
    assert "'=1+1" in Path(exported).read_text(encoding='utf-8-sig')


def test_empty_column():
    r, _, n = analyze_dataset(pd.DataFrame({'review': ['', ' ']}), 'review')
    assert r.empty and n == 2
    assert aspect_summary(r)['Reviews mentioning'].sum() == 0

def test_long_review_is_processed_without_truncation():
    review = 'The food was delicious. ' + ('The room was quiet. ' * 700) + 'The staff were not rude.'
    assert len(review) > 10000
    result = analyze_review(review)
    assert result['review'] == review
    assert result['aspects']['Service']['score'] > 0


def test_streamed_chunks_have_equivalent_counts_and_aspect_averages(tmp_path):
    content = b'review\nGreat food.\nTerrible food.\nThe staff were polite.\n\n'
    first_db, second_db = tmp_path / 'one.sqlite', tmp_path / 'many.sqlite'
    first_stats = process_csv(io.BytesIO(content), 'review', first_db, chunksize=1)
    second_stats = process_csv(io.BytesIO(content), 'review', second_db, chunksize=20)
    assert first_stats == second_stats
    with sqlite3.connect(first_db) as first, sqlite3.connect(second_db) as second:
        first_rows = pd.read_sql_query('SELECT * FROM results ORDER BY row_id', first)
        second_rows = pd.read_sql_query('SELECT * FROM results ORDER BY row_id', second)
    pd.testing.assert_frame_equal(first_rows, second_rows)
    assert first_stats['rows_seen'] == 4
    assert first_stats['analyzed'] == 3
    assert first_stats['skipped'] == 1


def test_csv_larger_than_10mb_and_10000_rows_exports_every_review(tmp_path):
    source = tmp_path / 'large.csv'
    with source.open('w', encoding='utf-8', newline='') as output:
        output.write('review,padding\n')
        for _ in range(10001):
            output.write('Great food.,' + ('x' * 1100) + '\n')
    assert source.stat().st_size > 10 * 1024 * 1024

    database = tmp_path / 'large.sqlite'
    stats = process_csv(source, 'review', database, chunksize=257)
    assert stats['rows_seen'] == stats['analyzed'] == 10001
    assert stats['aspect_stats']['Food']['count'] == 10001

    exported = write_query_csv(database, 'SELECT * FROM results ORDER BY row_id', tmp_path / 'all.csv')
    result_export = pd.read_csv(exported)
    assert len(result_export) == 10001
    assert result_export.iloc[-1]['row_id'] == 10001
    evidence_export = write_query_csv(
        database,
        'SELECT row_id, aspect, text, keywords, score, sentiment FROM evidence ORDER BY evidence_id',
        tmp_path / 'all_evidence.csv',
    )
    assert len(pd.read_csv(evidence_export)) == 10001


def test_malformed_stream_is_reported_and_not_completed(tmp_path):
    with pytest.raises(ValueError, match='CSV processing stopped|Expected'):
        process_csv(io.BytesIO(b'review,stars\nGreat,5\nBad,row,extra\n'), 'review', tmp_path / 'bad.sqlite')
