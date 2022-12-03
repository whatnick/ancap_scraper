import requests

cookies = {
    '_ga': 'GA1.3.1517839011.1670030139',
    '_gid': 'GA1.3.495649525.1670030139',
    '_gat_gtag_UA_3726693_1': '1',
    '_ga_F77H33C2BQ': 'GS1.1.1670030139.1.1.1670030190.0.0.0',
}

headers = {
    'authority': 'www.ancap.com.au',
    'accept': '*/*',
    'accept-language': 'en-US,en-AU;q=0.9,en;q=0.8',
    'cookie': '_ga=GA1.3.1517839011.1670030139; _gid=GA1.3.495649525.1670030139; _gat_gtag_UA_3726693_1=1; _ga_F77H33C2BQ=GS1.1.1670030139.1.1.1670030190.0.0.0',
    'dnt': '1',
    'referer': 'https://www.ancap.com.au/safety-ratings/land-rover/range-rover/edbc90',
    'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sec-gpc': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
}

params = {
    'safety_rating': '5',
    'vehicle_type': 'large_suv',
    'per_page': '5',
    'is_current_model': 'true',
}

response = requests.get('https://www.ancap.com.au/api/search', params=params, cookies=cookies, headers=headers)
print(response.json())

params = {
    'manufacturer_slug': 'land-rover',
    'model_slug': 'range-rover',
    'per_page': '48',
    'sort_by': 'rating_year',
    'sort_direction': 'desc',
}

response = requests.get('https://www.ancap.com.au/api/search', params=params, cookies=cookies, headers=headers)
print(response.json())

params = {
    'manufacturer_slug': 'kia',
    'model_slug': 'ev6',
    'per_page': '48',
    'sort_by': 'rating_year',
    'sort_direction': 'desc',
}

response = requests.get('https://www.ancap.com.au/api/search', params=params, cookies=cookies, headers=headers)
print(response.json())

params = {
    'makeAndModel': [
        'hyundai',
        'i30',
        '0cd5d0',
    ],
}

response = requests.get(
    'https://www.ancap.com.au/_next/data/P3_wVNZZeGh1UT3kecVro/safety-ratings/hyundai/i30/0cd5d0.json',
    params=params,
    cookies=cookies,
    headers=headers,
)

print(response.json())

def get_report():
    return None

def get_pdf():
    #Land Rover Range Rover
    "https://s3.amazonaws.com/cdn.ancap.com.au/app/public/assets/966fe66ca8fe258bba1b5d83847ef7f47bce4e27/original.pdf?1668579806"

    #KIA EV6
    "https://s3.amazonaws.com/cdn.ancap.com.au/app/public/assets/f28a0b6aac3ac9eb1e3aabea1c85a2ed2b9c7b91/original.pdf?1663120918"

    #Hyundai i30 Wagon
    "https://s3.amazonaws.com/cdn.ancap.com.au/app/public/assets/8602393abb988132b1cec572844b9cb6d6f17138/original.pdf?1513826339"