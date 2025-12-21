from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re, pandas as pd, time, sys
BASE = "https://kinosan.mn/actor/"
def grab(label, text):
    pattern = rf"{label}\s*:?\s*([^\n]+)?\n?([^\n]+)?"
    m = re.search(pattern, text)
    if not m:
        return None
    return (m.group(1) or m.group(2) or "").strip() or None
def extract_fields_from_text(text: str):
    born = grab("Төрсөн өдөр", text)
    name = grab("Овог нэр", text)
    profession = grab("Мэргэжил", text)
    intro = grab("Танилцуулга", text)
    return name, profession, born, intro
def safe_print(*args):
    s = " ".join(str(a) for a in args)
    enc = sys.stdout.encoding or "cp1252"
    sys.stdout.write(s.encode(enc, errors="replace").decode(enc) + "\n")
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=chrome_options)
results = []
try:
    for actor_id in range(1, 500):  
        url = BASE + str(actor_id)
        print("Loading", url)  
        driver.get(url)
        time.sleep(4)  
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        name, profession, born, intro = extract_fields_from_text(text)
        safe_print("DEBUG:", name, profession, born, intro)

        if not any([name, profession, born, intro]):
            print("No actor data found, skipping")
            continue
        results.append({
            "ID": actor_id,
            "Овог нэр": name,
            "Мэргэжил": profession,
            "Төрсөн өдөр": born,
            "Танилцуулга": intro
        })
finally:
    driver.quit()
df = pd.DataFrame(results)
df.to_excel("actors_36393.xlsx", index=False)
print("Saved Excel with", len(results), "rows")
