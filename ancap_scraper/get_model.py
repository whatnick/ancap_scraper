import os

import requests
from bs4 import BeautifulSoup

def get_all_reports():
    # TODO: Refactor this mega-function with separation of concerns
    cookies = {
        "_ga": "GA1.3.1517839011.1670030139",
        "_gid": "GA1.3.495649525.1670030139",
        "_gat_gtag_UA_3726693_1": "1",
        "_ga_F77H33C2BQ": "GS1.1.1670030139.1.1.1670030190.0.0.0",
    }

    headers = {
        "authority": "www.ancap.com.au",
        "accept": "*/*",
        "accept-language": "en-US,en-AU;q=0.9,en;q=0.8",
        "cookie": "_ga=GA1.3.1517839011.1670030139; _gid=GA1.3.495649525.1670030139; _gat_gtag_UA_3726693_1=1; _ga_F77H33C2BQ=GS1.1.1670030139.1.1.1670030190.0.0.0",
        "dnt": "1",
        "referer": "https://www.ancap.com.au/safety-ratings/land-rover/range-rover/edbc90",
        "sec-ch-ua": '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    }

    response = requests.get(
        "https://www.ancap.com.au/api/config?", cookies=cookies, headers=headers
    )
    all_make_models = response.json()
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
            all_reports = []
            for car in car_results:
                id = car["id"]
                if car["ratingYear"] != None:
                    rating_year = int(car["ratingYear"])
                    rating_pdf = f"{make_s}_{model_s}_{rating_year}_{id}.pdf"
                    rating_pdf = os.path.join("safety_data",rating_pdf)
                    all_reports.append(rating_pdf)
                    if rating_year >= 2018 and not os.path.exists(rating_pdf):
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
    get_all_reports()