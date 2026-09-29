from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / 'app.py')

def test_app_demo_and_review():
    app = AppTest.from_file(APP, default_timeout=30).run()
    assert not app.exception
    assert any(m.value == '1,000' for m in app.metric)
    app.text_area[0].set_value('The food was delicious, but the service was slow.')
    app.button[0].click().run()
    assert not app.exception
    assert any(m.value == 'Mixed' for m in app.metric)
    app.multiselect[0].set_value(['Negative']).run()
    assert not app.exception
    app.radio[0].set_value('Demo dataset').run()
    assert not app.exception
    assert any(m.value == '30' for m in app.metric)
    app.radio[0].set_value('Public Yelp dataset').run()
    assert not app.exception
    assert any(m.value == '1,000' for m in app.metric)
    app.radio[0].set_value('Upload CSV').run()
    assert not app.exception
    app.radio[0].set_value('Local CSV path').run()
    app.text_input[0].set_value(str(Path(APP).parent / 'data' / 'demo_reviews.csv')).run()
    assert not app.exception
    assert any(m.value == '30' for m in app.metric)

def test_blank_review_message():
    app = AppTest.from_file(APP, default_timeout=30).run()
    app.text_area[0].set_value('   ')
    app.button[0].click().run()
    assert not app.exception
    assert any('Enter a review' in w.value for w in app.warning)
