from PIL import Image
import sys
from typing import List, Dict, Tuple

import numpy as np
import pyocr
import pyocr.builders

FEATURES_BOX = (175,566,1001,3165)
AU_AVAIL_BOX = (1003,566,1116,3165)
NZ_AVAIL_BOX = (1116,566,1229,3165)
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

def get_safety_table(page_image) -> List[Dict[str,Tuple[bool,bool]]]:
    all_features = get_safety_features(page_image)
    au_avail = get_feature_available(page_image, AU_AVAIL_BOX,"AU")
    nz_avail = get_feature_available(page_image, NZ_AVAIL_BOX,"NZ")


def get_safety_features(page_image) -> list:
    img = Image.open(page_image)
    feat_img = img.crop(FEATURES_BOX)
    tool = get_tooling()
    line_and_word_boxes = tool.image_to_string(
        feat_img, lang="fra",
        builder=pyocr.builders.LineBoxBuilder()
    )

    for lbox in line_and_word_boxes:
        print(lbox)

def get_feature_available(page_image, zone, country):
    img = Image.open(page_image)
    crop_img = img.crop(zone)
    # 56 Rows of noughts and crosses
    step = (zone[3]-zone[1])/SAFETY_TYPES
    step = SAFETY_STEP
    for i in range(SAFETY_TYPES):
        nought_cross = crop_img.crop((0,i*step,NOUGHT_CROSS_WIDTH,(i+1)*step))
        nought_cross.save(f"test_{country}_{i}.jpg")
        arr = np.array(nought_cross)
        arr[arr>250] = 0
        print(i,arr.mean())
        

if __name__ == "__main__":
    page_with_table = sys.argv[1]
    get_safety_table(page_with_table)