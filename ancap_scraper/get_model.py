import os
import glob

import requests
from bs4 import BeautifulSoup

from ancap_scraper.headers import COOKIES, HEADERS

REPORTS_CACHE = "safety_data"

def glob_all_reports(year : str =""):
    g_pattern = os.path.join(REPORTS_CACHE,"*.pdf")
    # TODO: Make this generic to search cache by model, make, year
    if year != "":
        g_pattern = os.path.join(REPORTS_CACHE,f"*_{year}_*.pdf")
    return list(glob.glob(g_pattern))

def get_all_reports(use_cache = False):
    if use_cache:
        return glob_all_reports()
    response = requests.get(
        "https://www.ancap.com.au/api/config?", cookies=COOKIES, headers=HEADERS
    )
    all_make_models = response.json()
    all_reports = []
    for make in all_make_models:
        make_s = make["slug"]
        models = make["models"]
        for model in models[0]:
            model_s = model["slug"]
            params = {
                "manufacturer_slug": make_s,
                "model_slug": model_s,
                "per_page": "48",
                "sort_by": "rating_year",
                "sort_direction": "desc",
            }

            response = requests.get(
                "https://www.ancap.com.au/api/search",
                params=params,
                cookies=cookies,
                headers=headers,
            )
            result = response.json()
            car_results = result["results"]
            for car in car_results:
                id = car["id"]
                if car["ratingYear"] != None:
                    rating_year = int(car["ratingYear"])
                    rating_pdf = f"{make_s}_{model_s}_{rating_year}_{id}.pdf"
                    rating_pdf = os.path.join(REPORTS_CACHE,rating_pdf)
                    all_reports.append(rating_pdf)
                    if not os.path.exists(rating_pdf):
                        details_url = f"https://www.ancap.com.au/safety-ratings/{make_s}/{model_s}/{id}"
                        page = requests.get(details_url, cookies=cookies, headers=headers)
                        soup = BeautifulSoup(page.text, "html.parser")
                        pdf_link = soup.find_all(
                            class_="outline-none border-2 cursor-pointer rounded-full font-bold select-none flex justify-center items-center whitespace-nowrap text-black border-black hover:bg-transparent hover:text-black active:bg-gray-500 active:border-gray-500 active:text-white h-11 px-6 text-sm"
                        )
                        full_report_link = pdf_link[0]["href"]
                        response = requests.get(full_report_link)
                        with open(rating_pdf, "wb") as f:
                            f.write(response.content)
    return all_reports

# {"errors":{"vehicle_type":{"0":["must be one of: light_car, small_car, medium_car, large_car, sports_car, compact_suv, medium_suv, large_suv, people_mover, utility, van"]}}}
# {"errors":{"safety_rating":{"0":["must be one of: -1, 0, 1, 2, 3, 4, 5"]}}}

# https://api.ancap.com.au/v1/search?safety_rating=5&vehicle_type=small_suv

if __name__=="__main__":
    all_reports = get_all_reports(True)
    print(f"Downloaded {len(all_reports)} reports")
    print(all_reports)