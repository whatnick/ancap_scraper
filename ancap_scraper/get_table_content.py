import sys
import os
from typing import Dict, List, Tuple
import argparse

import pyocr
import pyocr.builders
from PIL import Image
import pandas as pd

from ancap_scraper.classify_result import predict

FEATURES_BOX = (175, 566, 1001, 3165)
AU_AVAIL_BOX = (1003, 566, 1116, 3165)
NZ_AVAIL_BOX = (1116, 566, 1229, 3165)


#TODO: Auto-detect these table location using templates or ML
FEATURES_BOX_2018_1 = (188, 705, 920, 2220)
AU_AVAIL_BOX_2018_1 = (920, 705, 1033, 2220)
NZ_AVAIL_BOX_2018_1 = (1033, 705, 1146, 2220)

FEATURES_BOX_2018_2 = (1134, 705, 2065, 2124)
AU_AVAIL_BOX_2018_2 = (2065, 705, 2178, 2124)
NZ_AVAIL_BOX_2018_2 = (2178, 705, 2291, 2124)

SAFETY_TYPES = 54
SAFETY_STEP = 47.3
NOUGHT_CROSS_WIDTH = 113
ENRICH = False #Enrich image samples for SVM for 2018 onwards symbology
WORD_MAP = {
    "noughts" : "STANDARD",
    "crosses" : "NOT AVAILABLE",
    "donut"   : "OPTIONAL",
    "sun"     : "PREMIUM STANDARD",
    "dashes"  : "SUBJECT TO CHANGE"
}

def main():
    args = parse_args()
    page_with_table = args.fname
    report_year = args.year
    file_xls = get_safety_table_all(page_with_table, report_year)
    print(f"Safety data saved to {file_xls}")


def parse_args():
    parser = argparse.ArgumentParser(
        description = 'This program reads an image to get safety features and their availability',
        epilog = 'Please select the page in with this data'
    )
    parser.add_argument("fname",help="File with rendered image from PDF of safety features data")
    parser.add_argument("-y","--year",dest="year",help="Year of report",default=2020,type=int)
    return parser.parse_args()

def get_tooling():
    tools = pyocr.get_available_tools()
    if len(tools) == 0:
        print("No OCR tool found")
        return False
    # The tools are returned in the recommended order of usage
    tool = tools[0]
    print("Will use tool '%s'" % (tool.get_name()))
    # Ex: Will use tool 'libtesseract'

    langs = tool.get_available_languages()
    print("Available languages: %s" % ", ".join(langs))
    lang = langs[0]
    print("Will use lang '%s'" % (lang))
    return tool

def get_safety_table_all(page_with_table : str, report_year : int):
    fname = os.path.basename(page_with_table)
    id = fname.split("_")[-1].replace(".jpg","")
    if report_year > 2019:
        file_xls = get_safety_table_2020(page_with_table,id)
    else:
        file_xls = get_safety_table_2018(page_with_table,id)
    return file_xls

def get_safety_table_2018(page_image : str, id : str) -> str:
    """Read particular page image and save excel file with
    features named after the ID of the car in the ANCAP
    database. Works on 2018,2019 edition files with double tables

    Args:
        page_image (str): name of image file from which to extract table
        id (str): Vehicle ID according to ANCAP database

    Returns:
        str: name of file with all features saved
    """
    ocr_tool = get_tooling()
    feature_set_1 = get_safety_features(page_image, ocr_tool, id, features_box = FEATURES_BOX_2018_1, au_box = AU_AVAIL_BOX_2018_1, nz_box = NZ_AVAIL_BOX_2018_1)
    feature_set_2 = get_safety_features(page_image, ocr_tool, id, features_box = FEATURES_BOX_2018_2, au_box = AU_AVAIL_BOX_2018_2, nz_box = NZ_AVAIL_BOX_2018_2)
    all_features = pd.concat([feature_set_1,feature_set_2])
    # TODO : DRY the file save
    file_table = f"{id}_features.xlsx"
    all_features.to_excel(file_table,index=False)
    return file_table

def get_safety_table_2020(page_image : str, id : str) -> str:
    """Read particular page image and save excel file with
    features named after the ID of the car in the ANCAP
    database.

    Args:
        page_image (str): name of image file from which to extract table
        id (str): Vehicle ID according to ANCAP database

    Returns:
        str: name of file with all features saved
    """
    ocr_tool = get_tooling()
    all_features = get_safety_features(page_image, ocr_tool, id)
    file_table = f"{id}_features.xlsx"
    all_features.to_excel(file_table,index=False)
    return file_table


def get_safety_features(page_image, tool, id, features_box = FEATURES_BOX, au_box = AU_AVAIL_BOX, nz_box = NZ_AVAIL_BOX) -> pd.DataFrame:
    img = Image.open(page_image)
    feat_img = img.crop(features_box)
    feat_img.save(f"{id}_{features_box}.jpg")
    line_and_word_boxes = tool.image_to_string(
        feat_img, lang="eng", builder=pyocr.builders.LineBoxBuilder()
    )
    df = pd.DataFrame(columns=["feature","au","nz"])
    features = []
    for lbox in line_and_word_boxes:
        features.append(lbox.content)
    steps = len(features)
    df["feature"] = features

    au_avail = get_feature_available(page_image, au_box, "AU", id, steps)
    nz_avail = get_feature_available(page_image, nz_box, "NZ", id, steps)

    df["au"] = [WORD_MAP[x] for x in au_avail]
    df["nz"] = [WORD_MAP[x] for x in nz_avail]

    return df


def get_feature_available(page_image, zone, country, id, s_type = SAFETY_TYPES):
    img = Image.open(page_image)
    crop_img = img.crop(zone)
    crop_img.save(f"{zone}_{country}.jpg")
    # 56 Rows of noughts and crosses
    # Could use OpenCV Template Matcher
    # https://docs.opencv.org/4.x/d4/dc6/tutorial_py_template_matching.html
    if s_type != SAFETY_TYPES:
        step = (zone[3] - zone[1]) / s_type
    else:
        step = SAFETY_STEP
    results = []
    for i in range(s_type):
        nought_cross = crop_img.crop((0, i * step, NOUGHT_CROSS_WIDTH, (i + 1) * step))
        test_img = f"test_{country}_{i}_{id}.jpg"
        nought_cross.save(test_img)
        result = predict(test_img,ENRICH)
        results.append(result)
    return results

if __name__ == "__main__":
    main()