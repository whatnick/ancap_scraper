"""Outer loop to iterate through years and parse all file
"""
import os
import shutil

from ancap_scraper.get_model import glob_all_reports
from ancap_scraper.get_table_image import get_table
from ancap_scraper.get_table_content import get_safety_table_all

YEARS = [2018,2019,2020,2021,2022]
XLS_FOLDER = "safety_data_excel"

for year in YEARS:
    pdf_reports = glob_all_reports(str(year))
    for report in pdf_reports:
        excel_report = os.path.basename(report).replace(".pdf",".xlsx")
        excel_report = os.path.join(XLS_FOLDER, excel_report)
        all_images = get_table(report)
        table_image = all_images[-1]
        # HACK: Cache table images
        shutil.copy(table_image,"page_samples")
        #file_xls = get_safety_table_all(table_image, year)
        #print(f"Parsed {file_xls} from {report}")
        #shutil.move(file_xls,excel_report)


