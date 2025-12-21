import time
import re
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = "https://kinosan.mn/movie/"
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver
def get_rendered_html(driver, url: str, wait_sec: int = 3) -> str:
    driver.get(url)
    time.sleep(wait_sec)
    return driver.page_source
def extract_movie_header_and_genres(text: str):
    lines_raw = text.split("\n")
    lines = [ln.strip() for ln in lines_raw if ln.strip()]

    movie_name = movie_type = release_year = age_range = runtime = None
    genres = None

    if not lines:
        return movie_name, movie_type, release_year, age_range, runtime, genres
    info_idx = None
    info_line = None
    for i, line in enumerate(lines):
        if any(tok in line for tok in ["Кино", "УСК", "Баримтат"]):
            if re.search(r"\d{4}", line):
                info_idx = i
                info_line = line
                break

    if info_idx is not None and info_idx > 0:
        movie_name = lines[info_idx - 1]
    else:
        movie_name = lines[0]
    if info_line:
        parts = [p.strip() for p in info_line.split(".") if p.strip()]
        if len(parts) >= 1:
            movie_type = parts[0]
        if len(parts) >= 2:
            release_year = parts[1]
        if len(parts) >= 3:
            age_range = parts[2]
        if len(parts) >= 4:
            runtime = parts[3]
    genres_list = []
    if info_idx is not None:
        for j in range(info_idx + 1, len(lines)):
            l = lines[j]
            if any(stop in l for stop in [
                "Найруулагч",
                "Зохиолч",
                "Жүжигчид",
                "Продакшн",
                "Сэтгэгдэл",
                "Тусламж",
                "Бидний тухай",
                "Сурталчилгаа",
                "Кино нэмэх",
                "Жүжигчин нэмэх",
                "Нууцлалын бодлого",
                "Үйлчилгээний нөхцөл",
                "Холбоо барих",
                "©",
            ]):
                break
            if (
                "Kinosan үнэлгээ" in l
                or "Таны үнэлгээ" in l
                or l == "movie image"
                or re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", l)
            ):
                continue
            if not re.search(r"\d", l) and len(l) <= 30:
                genres_list.append(l)
    if genres_list:
        genres = ", ".join(dict.fromkeys(genres_list))
    return movie_name, movie_type, release_year, age_range, runtime, genres
def extract_rating(text: str):
    m = re.search(r"Kinosan үнэлгээ\s*[:\n\r]*\s*([0-9]+(?:\.[0-9]+)?)", text)
    return m.group(1) if m else None
def extract_movie_staff(text: str):
    lines_raw = text.split("\n")
    lines = [ln.rstrip() for ln in lines_raw]
    staff = {"Найруулагч": [], "Зохиолч": [], "Жүжигчид": [], "Продакшн": []}
    stop_keywords = [
        "Kinosan үнэлгээ",
        "Сэтгэгдэл",
        "Тусламж",
        "Бидний тухай",
        "Сурталчилгаа",
        "Кино нэмэх",
        "Жүжигчин нэмэх",
        "Нууцлалын бодлого",
        "Үйлчилгээний нөхцөл",
        "Холбоо барих",
        "©",
    ]
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        for label in staff.keys():
            if line.startswith(label):
                after = line[len(label):].lstrip()
                if after.startswith(":"):
                    after = after[1:].lstrip()

                collected = []
                if after:
                    collected.append(after)

                i += 1
                while i < len(lines):
                    nxt = lines[i].strip()
                    if not nxt:
                        i += 1
                        continue

                    if any(nxt.startswith(other) for other in staff.keys() if other != label) \
                       or any(kw in nxt for kw in stop_keywords):
                        i -= 1  
                        break

                    collected.append(nxt)
                    i += 1

                cleaned = [ln.strip() for ln in collected if ln.strip()]
                staff[label] = " ".join(cleaned) if cleaned else None
        i += 1

    return staff["Найруулагч"], staff["Зохиолч"], staff["Жүжигчид"], staff["Продакшн"]

def main():
    results = []
    driver = create_driver()
    try:
        for movie_id in range(2500, 3000):
            url = f"{BASE_URL}{movie_id}"
            print(f"Processing movie ID {movie_id}: {url}")
            try:
                html = get_rendered_html(driver, url, wait_sec=3)
            except Exception as e:
                print(f"  -> Error loading page: {e}")
                continue
            soup = BeautifulSoup(html, "html.parser")
            full_text = soup.get_text(separator="\n", strip=True)
            (
                movie_name,
                movie_type,
                release_year,
                age_range,
                runtime,
                genres,
            ) = extract_movie_header_and_genres(full_text)
            rating = extract_rating(full_text)
            director, writer, cast, production = extract_movie_staff(full_text)
            if movie_name == "КИНО САН" :
                print(f"  -> ID {movie_id} is NOT a valid movie. Skip.")
                continue
            if not any(
                [
                    movie_name,
                    movie_type,
                    release_year,
                    rating,
                    director,
                    writer,
                    cast,
                    production,
                ]
            ):
                print("  -> No movie info found, skipping.")
                continue
            print("  -> Found data.")
            results.append(
                {
                    "ID": movie_id,
                    "Movie Name": movie_name,
                    "Type": movie_type,
                    "Genres": genres,
                    "Release Year": release_year,
                    "Age Range": age_range,
                    "Runtime": runtime,
                    "Kinosan Rating": rating,
                    "Найруулагч": director,
                    "Зохиолч": writer,
                    "Жүжигчид": cast,
                    "Продакшн": production,
                }
            )
    finally:
        driver.quit()
    if not results:
        print("No data collected. Check labels / HTML structure.")
        return
    df = pd.DataFrame(results, columns=[
        "ID","Movie Name", "Type","Genres","Release Year","Age Range","Runtime","Kinosan Rating", "Найруулагч","Зохиолч","Жүжигчид","Продакшн",
    ])
    output_file = "kinosan_movies5.xlsx"
    df.to_excel(output_file, index=False)
    print(f"\nDONE! Saved: {output_file}")
if __name__ == "__main__":
    main()
