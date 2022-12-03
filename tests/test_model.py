    """Tests obtaining safety ratings and PDF for a given make, model, year
    """

from ancap_scraper.get_model import get_report

def test_safety_report():
    get_report("Landcruiser")