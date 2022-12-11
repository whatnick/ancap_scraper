import sys
import os
from typing import Dict, List, Tuple

import pyocr
import pyocr.builders
from PIL import Image

from ancap_scraper.classify_result import predict

FEATURES_BOX = (175, 566, 1001, 3165)
AU_AVAIL_BOX = (1003, 566, 1116, 3165)
NZ_AVAIL_BOX = (1116, 566, 1229, 3165)
SAFETY_TYPES = 54
SAFETY_STEP = 47.3
NOUGHT_CROSS_WIDTH = 113


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


def get_safety_table(page_image, id) -> List[Dict[str, Tuple[bool, bool]]]:
    ocr_tool = get_tooling()
    all_features = get_safety_features(page_image, ocr_tool, id)


def get_safety_features(page_image, tool, id) -> list:
    img = Image.open(page_image)
    feat_img = img.crop(FEATURES_BOX)

    line_and_word_boxes = tool.image_to_string(
        feat_img, lang="eng", builder=pyocr.builders.LineBoxBuilder()
    )

    for lbox in line_and_word_boxes:
        print(lbox)

    au_avail = get_feature_available(page_image, AU_AVAIL_BOX, "AU", id)
    nz_avail = get_feature_available(page_image, NZ_AVAIL_BOX, "NZ", id)


def get_feature_available(page_image, zone, country, id):
    img = Image.open(page_image)
    crop_img = img.crop(zone)
    # 56 Rows of noughts and crosses
    # Could use OpenCV Template Matcher
    # https://docs.opencv.org/4.x/d4/dc6/tutorial_py_template_matching.html
    step = (zone[3] - zone[1]) / SAFETY_TYPES
    step = SAFETY_STEP
    x_template = "data/template_x.jpg"
    o_template = "data/template_o.jpg"
    for i in range(SAFETY_TYPES):
        nought_cross = crop_img.crop((0, i * step, NOUGHT_CROSS_WIDTH, (i + 1) * step))
        test_img = f"test_{country}_{i}_{id}.jpg"
        nought_cross.save(test_img)
        result = predict(test_img,True)
        print(result)

if __name__ == "__main__":
    page_with_table = sys.argv[1]
    fname = os.path.basename(page_with_table)
    id = fname.split("_")[-1].replace(".jpg","")
    get_safety_table(page_with_table,id)
