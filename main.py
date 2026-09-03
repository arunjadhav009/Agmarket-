import os
import json
import time
import hashlib
import requests
from playwright.sync_api import sync_playwright

PAGES_JSON = os.environ.get("PAGES_JSON")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
IG_ACCOUNT_ID = os.environ.get("IG_ACCOUNT_ID")

# भारतातील राज्ये, स्थानिक भाषा, कोड आणि सिनेमॅटिक थीम्स
STATE_CONFIG = {
    "Gujarat": {
        "code": "GJ", "local": "ગુજરાત ડુંગળી બજાર ભાવ",
        "theme": "#0284c7", "theme_light": "rgba(2, 132, 199, 0.4)",
        "table_primary": "#0369a1", "table_sec": "#0284c7", "bg": "#f0f9ff"
    },
    "Karnataka": {
        "code": "KA", "local": "ಕರ್ನಾಟಕ ಈರುಳ್ಳಿ ಮಾರುಕಟ್ಟೆ ದರಗಳು",
        "theme": "#7c3aed", "theme_light": "rgba(124, 58, 237, 0.4)",
        "table_primary": "#5b21b6", "table_sec": "#7c3aed", "bg": "#f5f3ff"
    },
    "Madhya Pradesh": {
        "code": "MP", "local": "मध्य प्रदेश प्याज मंडी भाव",
        "theme": "#dc2626", "theme_light": "rgba(220, 38, 38, 0.4)",
        "table_primary": "#991b1b", "table_sec": "#dc2626", "bg": "#fef2f2"
    },
    "Rajasthan": {
        "code": "RJ", "local": "राजस्थान प्याज मंडी भाव",
        "theme": "#ea580c", "theme_light": "rgba(234, 88, 12, 0.4)",
        "table_primary": "#9a3412", "table_sec": "#ea580c", "bg": "#fff7ed"
    },
    "Tamil Nadu": {
        "code": "TN", "local": "தமிழ்நாடு வெங்காய சந்தை விலை",
        "theme": "#a21caf", "theme_light": "rgba(162, 28, 175, 0.4)",
        "table_primary": "#701a75", "table_sec": "#a21caf", "bg": "#fdf4ff"
    },
    "Andhra Pradesh": {
        "code": "AP", "local": "ఆంధ్రప్రదేశ్ ఉల్లిపాయ ధరలు",
        "theme": "#16a34a", "theme_light": "rgba(22, 163, 74, 0.4)",
        "table_primary": "#14532d", "table_sec": "#16a34a", "bg": "#f0fdf4"
    },
    "Telangana": {
        "code": "TS", "local": "తెలంగాణ ఉల్లిపాయ మార్కెట్ ధరలు",
        "theme": "#0d9488", "theme_light": "rgba(13, 148, 136, 0.4)",
        "table_primary": "#115e59", "table_sec": "#0d9488", "bg": "#f0fdfa"
    },
    "Uttar Pradesh": {
        "code": "UP", "local": "उत्तर प्रदेश प्याज मंडी भाव",
        "theme": "#9333ea", "theme_light": "rgba(147, 51, 234, 0.4)",
        "table_primary": "#6b21a8", "table_sec": "#9333ea", "bg": "#faf5ff"
    },
    "Punjab": {
        "code": "PB", "local": "ਪੰਜਾਬ ਪਿਆਜ਼ ਮੰਡੀ ਦੇ ਭਾਅ",
        "theme": "#f59e0b", "theme_light": "rgba(245, 158, 11, 0.4)",
        "table_primary": "#b45309", "table_sec": "#d97706", "bg": "#fffbeb"
    },
    "Haryana": {
        "code": "HR", "local": "हरियाणा प्याज मंडी भाव",
        "theme": "#2563eb", "theme_light": "rgba(37, 99, 235, 0.4)",
        "table_primary": "#1e40af", "table_sec": "#2563eb", "bg": "#eff6ff"
    },
    "West Bengal": {
        "code": "WB", "local": "পশ্চিমবঙ্গ পেঁয়াজ বাজার দর",
        "theme": "#0891b2", "theme_light": "rgba(8, 145, 178, 0.4)",
        "table_primary": "#155e75", "table_sec": "#0891b2", "bg": "#ecfeff"
    },
    "Bihar": {
        "code": "BR", "local": "बिहार प्याज मंडी भाव",
        "theme": "#be123c", "theme_light": "rgba(190, 18, 60, 0.4)",
        "table_primary": "#881337", "table_sec": "#be123c", "bg": "#fff1f2"
    },
    "Kerala": {
        "code": "KL", "local": "കേരള സവാള വിപണി നിരക്കുകൾ",
        "theme": "#059669", "theme_light": "rgba(5, 150, 105, 0.4)",
        "table_primary": "#064e3b", "table_sec": "#059669", "bg": "#ecfdf5"
    },
    "Odisha": {
        "code": "OD", "local": "ଓଡ଼ିଶା ପିଆଜ ବଜାର ଦର",
        "theme": "#0284c7", "theme_light": "rgba(2, 132, 199, 0.4)",
        "table_primary": "#0369a1", "table_sec": "#0284c7", "bg": "#f0f9ff"
    }
}

def get_state_info(state_name):
    for key, val in STATE_CONFIG.items():
        if key.lower() in state_name.lower() or state_name.lower() in key.lower():
            return val
    return {
        "code": "IN", "local": "आजचे कांदा बाजार भाव",
        "theme": "#e11d48", "theme_light": "rgba(225, 29, 72, 0.4)",
        "table_primary": "#1b5e20", "table_sec": "#2e7d32", "bg": "#f8fafc"
    }

def generate_cover_image(state_name, post_date, total_records, output_path):
    with open("cover_template.html", "r", encoding="utf-8") as f:
        html = f.read()

    conf = get_state_info(state_name)

    rendered = (
        html.replace("{{STATE_NAME}}", state_name)
        .replace("{{STATE_CODE}}", conf["code"])
        .replace("{{LOCAL_TITLE}}", conf["local"])
        .replace("{{POST_DATE}}", post_date)
        .replace("{{TOTAL_RECORDS}}", str(total_records))
        .replace("{{THEME_COLOR}}", conf["theme"])
        .replace("{{THEME_COLOR_LIGHT}}", conf["theme_light"])
    )

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        page.set_content(rendered)
        page.screenshot(path=output_path, full_page=False)
        browser.close()

def generate_data_image(page_data, output_path):
    with open("template.html", "r", encoding="utf-8") as f:
        html = f.read()

    state_name = str(page_data.get("StateName", "State"))
    conf = get_state_info(state_name)

    rows_html = ""
    for r in page_data.get("PageData", []):
        rows_html += f"""
        <tr>
            <td>{r.get('District', '-')}</td>
            <td>{r.get('Market', '-')}</td>
            <td>₹{r.get('MinPrice', 0)}</td>
            <td>₹{r.get('MaxPrice', 0)}</td>
            <td class="modal-price">₹{r.get('ModalPrice', 0)}</td>
        </tr>
        """

    rendered = (
        html.replace("{{STATE_NAME}}", state_name)
        .replace("{{POST_DATE}}", str(page_data.get("PostDate", "")))
        .replace("{{CURRENT_PAGE}}", str(page_data.get("CurrentPage", "1")))
        .replace("{{TOTAL_PAGES}}", str(page_data.get("TotalPages", "1")))
        .replace("{{TABLE_ROWS}}", rows_html)
        .replace("{{PRIMARY_COLOR}}", conf["table_primary"])
        .replace("{{SECONDARY_COLOR}}", conf["table_sec"])
        .replace("{{BG_COLOR}}", conf["bg"])
    )

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        page.set_content(rendered)
        page.screenshot(path=output_path, full_page=False)
        browser.close()

def get_photo_url(photo_id):
    for _ in range(4):
        res = requests.get(
            f"https://graph.facebook.com/v20.0/{photo_id}",
            params={"access_token": FB_PAGE_ACCESS_TOKEN, "fields": "source,images"}
        ).json()
        if "images" in res and len(res["images"]) > 0:
            return res["images"][0]["source"]
        if "source" in res:
            return res["source"]
        time.sleep(2)
    return ""

def post_facebook_bundle(caption, image_paths):
    uploaded = []
    total = len(image_paths)

    for idx, img_path in enumerate(image_paths):
        url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/photos"
        page_caption = caption if idx == 0 else f"{caption}\n\n[Page {idx + 1} of {total}]"

        with open(img_path, "rb") as img_file:
            res = requests.post(
                url,
                params={
                    "access_token": FB_PAGE_ACCESS_TOKEN,
                    "caption": page_caption,
                    "published": "true",
                    "fields": "id,images,source"
                },
                files={"source": img_file}
            ).json()

        if "id" in res:
            img_url = get_photo_url(res["id"])
            uploaded.append({"id": res["id"], "url": img_url})
            print(f"✅ FB Image {idx + 1}/{total} Uploaded: {res['id']}")
        else:
            print(f"❌ FB Upload Error: {res}")

    return uploaded

def post_instagram_carousel(caption, uploaded_media):
    if not IG_ACCOUNT_ID:
        return

    valid_media = [m for m in uploaded_media if m.get("url")]
    if not valid_media:
        return

    # Instagram मर्यादा: १० इमेजेस (१ कव्हर + ९ डेटा पेजेस)
    if len(valid_media) > 10:
        valid_media = valid_media[:10]

    child_ids = []
    for item in valid_media:
        img_url = item["url"]
        child_res = requests.post(
            f"https://graph.facebook.com/v20.0/{IG_ACCOUNT_ID}/media",
            data={
                "access_token": FB_PAGE_ACCESS_TOKEN,
                "image_url": img_url,
                "is_carousel_item": "true"
            }
        ).json()
        if "id" in child_res:
            child_ids.append(child_res["id"])
        time.sleep(2)

    if not child_ids:
        return

    car_res = requests.post(
        f"https://graph.facebook.com/v20.0/{IG_ACCOUNT_ID}/media",
        data={
            "access_token": FB_PAGE_ACCESS_TOKEN,
            "media_type": "CAROUSEL",
            "caption": caption,
            "children": ",".join(child_ids)
        }
    ).json()

    if "id" in car_res:
        time.sleep(12)
        pub_res = requests.post(
            f"https://graph.facebook.com/v20.0/{IG_ACCOUNT_ID}/media_publish",
            data={"access_token": FB_PAGE_ACCESS_TOKEN, "creation_id": car_res["id"]}
        ).json()
        print(f"✅ Instagram Carousel Published (१ कव्हर + डेटा पेजेस): {pub_res}")

def main():
    if not PAGES_JSON:
        return

    data = json.loads(PAGES_JSON)
    if isinstance(data, str):
        data = json.loads(data)

    pages = data if isinstance(data, list) else data.get("pages", [])
    if not pages:
        return

    state_name = pages[0].get("StateName", "All India")
    post_date = pages[0].get("PostDate", "")
    total_records = pages[0].get("TotalRecords", len(pages) * 20)

    conf = get_state_info(state_name)
    caption = f"🧅 {state_name} Onion Mandi Bhav Today ({post_date})\n{conf['local']}\n\nSwipe left to check all mandi rates."

    print(f"🎬 Generating 4K Cover Poster for {state_name}...")

    image_paths = []

    # १. पहिले सिनेमॅटिक कव्हर पोस्टर तयार करणे (Page 1)
    cover_img = f"cover_{state_name}.png".replace(" ", "_")
    generate_cover_image(state_name, post_date, total_records, cover_img)
    image_paths.append(cover_img)

    # २. नंतर डेटा पेजेस तयार करणे (Page 2 onwards)
    for idx, page in enumerate(pages):
        img_name = f"data_{state_name}_{idx + 1}.png".replace(" ", "_")
        generate_data_image(page, img_name)
        image_paths.append(img_name)

    # ३. Facebook आणि Instagram वर पोस्ट करणे
    uploaded = post_facebook_bundle(caption, image_paths)
    if uploaded:
        post_instagram_carousel(caption, uploaded)

    # क्लिनअप
    for img in image_paths:
        if os.path.exists(img):
            os.remove(img)

if __name__ == "__main__":
    main()
