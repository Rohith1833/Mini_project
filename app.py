import math
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from analyzer import ASPECTS, analyze_review, csv_bytes, csv_columns, process_csv, write_query_csv

st.set_page_config(page_title='LocalLens • Review intelligence', page_icon='◈', layout='wide')
st.markdown('''<style>
:root, .stApp {
    color-scheme: light;
    --primary-color: #117b6c;
    --background-color: #f4f7f6;
    --secondary-background-color: #ffffff;
    --text-color: #19332f;
}
.stApp, [data-testid="stAppViewContainer"] {background: #f4f7f6; color: #19332f;}
[data-testid="stHeader"] {background: rgba(244, 247, 246, .94);}
.block-container {max-width: 1320px; padding: 2rem 2.5rem 4rem;}
.stApp h1 {color: #19332f; font-size: 2.65rem; line-height: 1.1; letter-spacing: 0;}
.stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp label {color: #19332f;}
[data-testid="stSidebar"] {background: #eaf2ef;}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label {color: #34524d;}
[data-testid="stMetric"] {
    background: #ffffff;
    padding: 1rem 1.15rem;
    border: 1px solid #dce7e3;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(25, 51, 47, .035);
}
[data-testid="stMetricLabel"] {color: #526a65;}
[data-testid="stMetricValue"] {color: #19332f;}
[data-testid="stTabs"] [role="tablist"] {gap: .4rem; border-bottom: 1px solid #d5e1dd;}
[data-testid="stTabs"] [role="tab"] {min-height: 2.8rem; color: #526a65;}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {color: #117b6c;}
[data-testid="stMarkdownContainer"] a {color: #117b6c;}
[data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input,
[data-baseweb="select"] > div {
    color: #19332f;
    background: #ffffff;
    border-color: #cbdad5;
}
[data-testid="stForm"] {border-color: #dce7e3; border-radius: 8px; background: #ffffff;}
[data-testid="stButton"] button[kind="primaryFormSubmit"],
[data-testid="stFormSubmitButton"] button {
    color: #ffffff;
    background: #117b6c;
    border-color: #117b6c;
    border-radius: 6px;
    font-weight: 600;
}
[data-testid="stFormSubmitButton"] button p {color: #ffffff;}
[data-testid="stRadio"] [role="radiogroup"] {gap: .45rem 1rem; flex-wrap: wrap;}
[data-testid="stCaptionContainer"] {color: #5d716c;}
@media (max-width: 700px) {
    .block-container {padding: 1.25rem 1rem 2.5rem;}
    .stApp h1 {font-size: 1.9rem; line-height: 1.15;}
    [data-testid="stTabs"] [role="tablist"] {gap: .05rem;}
    [data-testid="stTabs"] [role="tab"] {min-height: 2.6rem; padding-inline: .45rem; font-size: .82rem;}
    [data-testid="stMetric"] {padding: .8rem;}
}
</style>''', unsafe_allow_html=True)
st.caption('LOCALLENS / CUSTOMER EXPERIENCE INTELLIGENCE')
st.title('Every review has a story.')
st.write('Discover what customers love—and what needs attention. Five restaurant aspects, one clear view.')
with st.sidebar:
    st.header('LocalLens ◈')
    st.caption('Restaurant review analyzer')
    st.divider()
    st.write('**Aspects tracked**')
    for aspect in ASPECTS:
        st.write('• ' + aspect)
    st.divider()
    st.caption('English-language baseline. Scores are sentiment estimates, not star ratings or confidence percentages.')
    st.caption('No API key required. Reviews are analyzed in the Python process; this app does not send them to an AI service.')

single, batch, about = st.tabs(['Review explorer', 'Dataset dashboard', 'How it works'])
with single:
    st.subheader('Look beyond positive or negative')
    with st.form('review_form'):
        review = st.text_area('Customer review', 'The food was delicious, but the service was slow. The place was spotless.', height=135)
        submitted = st.form_submit_button('Analyze review', type='primary')
    if submitted:
        if not review.strip():
            st.warning('Enter a review first.')
        else:
            result = analyze_review(review)
            st.session_state['review_result'] = result
    result = st.session_state.get('review_result')
    if result:
        st.caption('Results for: ' + result['review'])
        left, right = st.columns(2)
        left.metric('Overall sentiment', result['sentiment'])
        right.metric('Aspects detected', len(result['aspects']))
        st.caption(f"Whole-review VADER compound: {result['compound']:+.3f}. Mixed means separate clauses contain both positive and negative signals.")
        table = [{'Aspect': a, 'Sentiment': result['aspects'].get(a, {}).get('sentiment', 'Not mentioned'),
                  'Score': result['aspects'].get(a, {}).get('score')} for a in ASPECTS]
        st.dataframe(pd.DataFrame(table), hide_index=True, width='stretch')
        if result['evidence']:
            with st.expander('Why these scores? View matched text', expanded=True):
                st.dataframe(pd.DataFrame(result['evidence']).rename(columns={'text': 'Matched clause'}), hide_index=True, width='stretch')
        else:
            st.info('No tracked aspects were mentioned. Try naming food, staff, price, cleanliness or waiting time.')

with batch:
    st.subheader('Turn customer feedback into priorities')
    st.caption('No LocalLens file-size, row-count or review-length limit. Practical capacity depends on memory, disk space and processing time; a local CSV path avoids browser upload limits.')
    source = st.radio('Data source', ['Public Yelp dataset', 'Demo dataset', 'Upload CSV', 'Local CSV path'], horizontal=True)
    data_path = Path(__file__).parent / 'data' / 'uci_yelp_reviews.csv'
    source_file = None
    source_key = None
    upload = None
    if source == 'Public Yelp dataset':
        st.info('UCI Sentiment Labelled Sentences (Yelp subset). All rows in the bundled CSV are analyzed; its row count is read from the file.')
        st.caption('Kotzias (2015) · CC BY 4.0 · https://doi.org/10.24432/C57604 · Converted from TSV to CSV.')
        source_file = data_path
        stat = data_path.stat()
        source_key = ('public', stat.st_size, stat.st_mtime_ns)
    elif source == 'Demo dataset':
        st.info('Demo mode: synthetic restaurant reviews created for this project. These are not real reviews or evaluation data.')
        data_path = Path(__file__).parent / 'data' / 'demo_reviews.csv'
        source_file = data_path
        stat = data_path.stat()
        source_key = ('demo', stat.st_size, stat.st_mtime_ns)
    elif source == 'Upload CSV':
        upload = st.file_uploader('Choose a UTF-8 CSV', type=['csv'])
        if upload is not None:
            source_file = upload
            source_key = ('upload', upload.name, upload.size)
    else:
        path_text = st.text_input('CSV path on the Streamlit machine', placeholder=r'C:\data\reviews.csv')
        st.caption('This path refers to the machine running Streamlit, not necessarily the computer viewing the browser.')
        if path_text.strip():
            data_path = Path(path_text.strip()).expanduser()
            if not data_path.is_file():
                st.error('The specified CSV file does not exist or is not a regular file.')
            else:
                try:
                    with data_path.open('rb'):
                        pass
                    stat = data_path.stat()
                    source_file = data_path
                    source_key = ('local', str(data_path.resolve()), stat.st_size, stat.st_mtime_ns)
                except OSError as exc:
                    st.error(f'Cannot read the specified CSV file: {exc}')

    if source_file is not None:
        try:
            columns = csv_columns(source_file)
            if not columns:
                raise ValueError('CSV must contain a header row with at least one column.')
            preferred = next((c for c in columns if c.lower() in ('review', 'reviews', 'text', 'review_text')), columns[0])
            column = st.selectbox('Review text column', columns, index=columns.index(preferred))
            chunksize = st.number_input('Rows per processing chunk', min_value=1, value=1000, step=100)
            process_key = (source_key, column, int(chunksize))
            if st.session_state.get('processed_key') != process_key:
                session_dir = st.session_state.get('session_dir')
                if session_dir is None:
                    session_dir = tempfile.mkdtemp(prefix='locallens-')
                    st.session_state['session_dir'] = session_dir
                database_path = Path(session_dir) / 'analysis.sqlite'
                try:
                    with st.status('Processing CSV chunks...', expanded=True) as status:
                        progress_text = st.empty()
                        stats = process_csv(
                            source_file, column, database_path, int(chunksize),
                            lambda progress: progress_text.write(
                                f"Processed {progress['rows_seen']:,} data rows: "
                                f"{progress['analyzed']:,} analyzed, {progress['skipped']:,} blank."
                            ),
                        )
                        export_paths = {
                        'reviews': str(Path(session_dir) / 'analyzed_reviews.csv'),
                        'evidence': str(Path(session_dir) / 'aspect_evidence.csv'),
                        }
                        write_query_csv(database_path, 'SELECT * FROM results ORDER BY row_id', export_paths['reviews'])
                        write_query_csv(database_path, 'SELECT row_id, aspect, text, keywords, score, sentiment FROM evidence ORDER BY evidence_id', export_paths['evidence'])
                        st.session_state['processed_key'] = process_key
                        st.session_state['database_path'] = str(database_path)
                        st.session_state['analysis_stats'] = stats
                        st.session_state['export_paths'] = export_paths
                        status.update(
                            label=(f"Complete: {stats['analyzed']:,} analyzed from "
                                   f"{stats['rows_seen']:,} rows; {stats['skipped']:,} blank skipped."),
                            state='complete',
                        )
                except (ValueError, OSError, MemoryError) as exc:
                    st.session_state.pop('processed_key', None)
                    st.session_state.pop('analysis_stats', None)
                    st.error(f'Processing did not complete. No partial result is marked complete. {exc}')

            if st.session_state.get('processed_key') == process_key:
                stats = st.session_state['analysis_stats']
                database_path = st.session_state['database_path']
                sentiment_counts = stats['sentiment_counts']
                summary = pd.DataFrame([
                    {'Aspect': aspect,
                     'Mean sentiment': round(stats['aspect_stats'][aspect]['mean'], 3) if stats['aspect_stats'][aspect]['mean'] is not None else None,
                     'Reviews mentioning': stats['aspect_stats'][aspect]['count'],
                     'Positive': stats['aspect_stats'][aspect]['Positive'],
                     'Neutral': stats['aspect_stats'][aspect]['Neutral'],
                     'Negative': stats['aspect_stats'][aspect]['Negative']}
                    for aspect in ASPECTS
                ])
                a, b, c, d = st.columns(4)
                a.metric('Reviews analyzed', f"{stats['analyzed']:,}")
                b.metric('Positive reviews', f"{sentiment_counts['Positive']:,}")
                c.metric('Negative reviews', f"{sentiment_counts['Negative']:,}")
                d.metric('Mixed reviews', f"{sentiment_counts['Mixed']:,}")
                chart_col, mix_col = st.columns([2, 1])
                with chart_col:
                    st.markdown('#### Sentiment by aspect')
                    plotted = summary.dropna(subset=['Mean sentiment'])
                    if plotted.empty:
                        st.info('No tracked aspects found in this dataset.')
                    else:
                        chart = alt.Chart(plotted).mark_bar(cornerRadiusEnd=5).encode(
                            x=alt.X('Mean sentiment:Q', scale=alt.Scale(domain=[-1, 1]), title='Negative ← 0 → Positive'),
                            y=alt.Y('Aspect:N', sort=list(ASPECTS), title=None),
                            color=alt.condition(alt.datum['Mean sentiment'] >= 0, alt.value('#12866f'), alt.value('#de6759')),
                            tooltip=['Aspect', 'Mean sentiment', 'Reviews mentioning', 'Negative'])
                        st.altair_chart(chart.properties(height=255), width='stretch')
                    st.caption('One score per review per aspect. Only reviews mentioning that aspect enter its average. No mentions = no score.')
                with mix_col:
                    st.markdown('#### Review sentiment mix')
                    counts = pd.DataFrame({'Sentiment': ['Positive', 'Neutral', 'Negative', 'Mixed'],
                                           'Reviews': [sentiment_counts[name] for name in ('Positive', 'Neutral', 'Negative', 'Mixed')]})
                    pie = alt.Chart(counts).mark_arc(innerRadius=60).encode(theta='Reviews:Q', color=alt.Color('Sentiment:N', scale=alt.Scale(domain=['Positive', 'Neutral', 'Negative', 'Mixed'], range=['#12866f', '#a3aabb', '#de6759', '#7f6bc6'])), tooltip=['Sentiment', 'Reviews'])
                    st.altair_chart(pie.properties(height=255), width='stretch')
                st.dataframe(summary, hide_index=True, width='stretch')
                eligible = summary[summary['Reviews mentioning'] >= 3]
                if not eligible.empty and eligible['Mean sentiment'].min() < 0:
                    weakest = eligible.loc[eligible['Mean sentiment'].idxmin()]
                    st.warning(f"Investigate {weakest['Aspect'].lower()}: lowest average among aspects with at least 3 mentions ({weakest['Mean sentiment']:+.3f}). Inspect the underlying reviews before making decisions.")
                st.markdown('#### Explore the feedback')
                selected = st.multiselect('Filter by sentiment', ['Positive', 'Neutral', 'Negative', 'Mixed'])
                aspect_filter = st.selectbox('Filter by aspect', ['All aspects', *ASPECTS])
                page_size = st.number_input('Rows per page', min_value=1, value=100, step=50)
                conditions, params = [], []
                if selected:
                    conditions.append(f"sentiment IN ({', '.join('?' for _ in selected)})")
                    params.extend(selected)
                if aspect_filter != 'All aspects':
                    conditions.append(f'"{aspect_filter} score" IS NOT NULL')
                where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
                with closing(sqlite3.connect(f'{Path(database_path).resolve().as_uri()}?mode=ro', uri=True)) as connection:
                    filtered_count = connection.execute(f'SELECT COUNT(*) FROM results{where}', params).fetchone()[0]
                    page_count = max(1, math.ceil(filtered_count / int(page_size)))
                    page_key = f"result_page_{hash((process_key, tuple(selected), aspect_filter, int(page_size)))}"
                    page_number = st.number_input('Page', min_value=1, max_value=page_count, value=1, step=1, key=page_key)
                    page = pd.read_sql_query(
                        f'SELECT * FROM results{where} ORDER BY row_id LIMIT ? OFFSET ?',
                        connection, params=[*params, int(page_size), (int(page_number) - 1) * int(page_size)])
                st.caption(f'Showing {len(page):,} of {filtered_count:,} matching reviews. Page {int(page_number)} of {page_count}.')
                st.dataframe(page, hide_index=True, width='stretch')
                st.caption('Filters and pagination affect only the visible table. All analyzed reviews and all matched evidence are included in their exports.')
                x, y, z = st.columns(3)
                with open(st.session_state['export_paths']['reviews'], 'rb') as reviews_file:
                    x.download_button('Download all analyzed reviews', reviews_file, 'analyzed_reviews.csv', 'text/csv')
                y.download_button('Download aspect summary', csv_bytes(summary), 'aspect_summary.csv', 'text/csv')
                with open(st.session_state['export_paths']['evidence'], 'rb') as evidence_file:
                    z.download_button('Download all matched evidence', evidence_file, 'aspect_evidence.csv', 'text/csv')
        except ValueError as exc:
            st.error(str(exc))
    elif source in ('Upload CSV', 'Local CSV path'):
        st.info('Choose a CSV file or enter its path on the machine running Streamlit to begin.')

with about:
    st.subheader('A transparent baseline')
    st.markdown('''1. Preserve punctuation, casing and negation while normalizing whitespace.
2. Split reviews into sentences and contrast clauses; split some conjunctions when both sides name an aspect.
3. Match whole-word restaurant keywords to five aspects.
4. Score each matched clause using VADER with a small, documented restaurant vocabulary extension.
5. Average clause scores within each review/aspect, then average those review-level scores across the dataset.

**Score range:** −1 to +1. Positive ≥ 0.05; negative ≤ −0.05; otherwise neutral. Scores are not probabilities.

**Limitations:** English only. Sarcasm, implicit aspects, misspellings and complex sentences may be wrong. Aspects in the same unsplit clause share its score. Keyword overlap can assign slow service to both service and waiting time. “Mixed” is a clause-level heuristic. This is not a trained aspect-based language model, and no real-world accuracy is claimed.

**Data:** Demo examples are synthetic. The bundled public Yelp CSV contains review sentences from UCI, credited to Kotzias (2015), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), [DOI](https://doi.org/10.24432/C57604). The dashboard reads its row count from the file. Original TSV converted to CSV without changing text or labels. No Google scraper is included.

**References:** [VADER source and paper](https://github.com/cjhutto/vaderSentiment) · [Streamlit documentation](https://docs.streamlit.io/)
''')
