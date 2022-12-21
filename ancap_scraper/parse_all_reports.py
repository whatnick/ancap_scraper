"""Outer loop to iterate through years and parse all file
"""
from ancap_scraper.get_model import glob_all_reports
from ancap_scraper.get_table_image import get_table
from ancap_scraper.get_table_content import get_safety_table_all

YEARS = [2018,2019,2020,2021,2022]

for year in YEARS:
    pdf_reports = glob_all_reports(str(year))
    for report in pdf_reports:
        all_images = get_table(report)
        table_image = all_images[-1]
        file_xls = get_safety_table_all(table_image, year)
        print(f"Parsed {file_xls} from {report}")
