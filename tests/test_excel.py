"""Test getting excel files from various year sample safety features.
"""
from ancap_scraper.get_table_content import get_safety_features

def test_safety_2018():
    assert get_safety_table_all("tests/data/out_7_49951c.jpg",2018)

def test_safety_2020():
    assert get_safety_table_all("tests/data/out_6_3cd72b.jpg",2020)