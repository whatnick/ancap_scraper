"""Tests obtaining safety ratings and PDF for a given make, model, year
"""

from ancap_scraper.get_model import get_all_reports, glob_all_reports

def test_safety_report():
    assert get_all_reports(True)

def test_glob_year():
    rep_2018 =  glob_all_reports("2018")
    assert len(rep_2018) == 26