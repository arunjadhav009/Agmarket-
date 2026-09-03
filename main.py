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

STATE_THEMES = {
    "Gujarat": {"primary": "#005a9c", "secondary": "#1976d2", "bg": "#f0f7ff"},
    "Karnataka": {"primary": "#311b92", "secondary": "#512da8", "bg": "#f4f1fa"},
    "Madhya Pradesh": {"primary": "#b71c1c", "secondary": "#c62828", "bg": "#fff5f5"},
    "Rajasthan": {"primary": "#bf360c", "secondary": "#d84315", "bg": "#fff8f5"},
    "Andhra Pradesh": {"primary": "#1b5e20", "secondary": "#2e7d32", "bg": "#f1f8f3"},
    "Telangana": {"primary": "#00695c", "secondary": "#00897b", "bg": "#f0fdfa"},
    "Uttar Pradesh": {"primary": "#4a148c", "secondary": "#6a1b9a", "bg": "#faf5ff"},
    "Punjab": {"primary": "#c2410c", "secondary": "#ea580c", "bg": "#fff7ed"},
    "Haryana": {"primary": "#0369a1", "secondary": "#0284c7", "bg": "#f0f9ff"},
    "West Bengal": {"primary": "#1e3a8a", "secondary": "#1d4ed8", "bg": "#eff6ff"},
    "Bihar": {"primary": "#831843", "secondary": "#9d174d", "bg": "#fdf2f8"},
    "Odisha": {"primary": "#0f766e", "secondary": "#14b8a6", "bg": "#f0fdfa"},
    "Tamil Nadu": {"primary": "#701a75", "secondary": "#86198f", "bg": "#fdf4ff"},
    "Kerala": {"primary": "#14532d", "secondary": "#166534", "bg": "#f0fdf4"},
    "Assam": {"primary": "#065f46", "secondary": "#059669", "bg": "#ecfdf5"},
    "Chhattisgarh": {"primary": "#854d0e", "secondary": "#a16207", "bg": "#fefce8"},
    "Jharkhand": {"primary": "#374151", "secondary": "#4b5563", "bg": "#f9fafb"},
    "Himachal Pradesh": {"primary": "#0e7490", "secondary": "#0891b2", "bg": "#ecfeff"},
    "Uttarakhand": {"primary": "#155e75", "secondary": "#0e7490", "bg": "#f0fdfa"},
    "Goa": {"primary": "#0284c7", "secondary": "#38bdf8", "bg": "#f0f9ff"},
    "Jammu and Kashmir": {"primary": "#334155", "secondary": "#475569", "bg": "#f8fafc"}
}

FALLBACK_PALETTES = [
    {"primary": "#1b5e20", "secondary": "#2e7d32", "bg": "#f1f8f3"},
    {"primary": "#005a9c", "secondary": "#1976d2", "bg": "#f0f7ff"},
    {"primary": "#311b92", "secondary": "#512da8", "bg": "#f4f1fa"},
    {"primary": "#b71c1c", "secondary": "#c62828", "bg": "#fff5f5"},
    {"primary": "#bf360c", "secondary": "#d84315", "bg": "#fff8f5"},
    {"primary": "#00695c", "secondary": "#00897b", "bg": "#f0fdfa"},
    {"primary": "#4a148c", "secondary": "#6a1b9a", "bg": "#faf5ff"},
]

def get_state_theme(state_name):
    for key, val in STATE_THEMES.items():
        if key.lower() in state_name.lower() or state_name.lower() in key.lower():
            return val
    hash_idx = int(hashlib.md5(state_name.encode()).hexdigest(), 16) % len(FALLBACK_PALETTES)
    return FALLBACK_PALETTES[hash_idx]

def generate_image(page_data, output_path):
    with open("template.html", "r", encoding="utf-8") as f:
        html_template = f.read()

    state_name = str(page_data.get("StateName", "State"))
    theme = get_state_theme(state_name)

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

    rendered_html = (
        html_template.replace("{{STATE_NAME}}", state_name)
        .replace("{{POST_DATE}}", str(page_data.get("PostDate", "")))
        .replace("{{CURRENT_PAGE}}", str(page_data.get("CurrentPage", "1")))
        .replace("{{TOTAL_PAGES}}", str(page_data.get("TotalPages", "1")))
        .replace("{{TABLE_ROWS}}", rows_html)
        .replace("{{PRIMARY_COLOR}}", theme["primary"])
        .replace("{{SECONDARY_COLOR}}", theme["secondary"])
        .replace("{{BG_COLOR}}", theme["bg"])
    )

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1080})
        page.set_content(rendered_html)
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

def post_facebook(state_name, post_date, caption, image_paths):
    uploaded = []

    # १. जर स्टेटचे फक्त १ च पेज असेल -> थेट सिंगल पोस्ट
    if len(image_paths) == 1:
        url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/photos"
        with open(image_paths[0], "rb") as img_file:
            res = requests.post(
                url,
                params={
                    "access_token": FB_PAGE_ACCESS_TOKEN,
                    "caption": caption,
                    "published": "true",
                    "fields": "id,images,source"
                },
                files={"source": img_file}
            ).json()

        if "id" in res:
            print(f"✅ Facebook Single Post यशस्वी: {res['id']}")
            img_url = ""
            if "images" in res and len(res["images"]) > 0:
                img_url = res["images"][0].get("source", "")
            elif "source" in res:
                img_url = res.get("source", "")
            else:
                img_url = get_photo_url(res["id"])
            uploaded.append({"id": res["id"], "url": img_url})
        else:
            print(f"❌ Facebook Single Upload Error: {res}")

    # २. जर स्टेटचे २ किंवा त्यापेक्षा जास्त पेजेस असतील (३, ७, १०, १३) -> १ Dedicated Album (ग्रुप)
    else:
        album_name = f"{state_name} Onion Rates ({post_date})"
        album_url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/albums"
        album_res = requests.post(
            album_url,
            data={
                "access_token": FB_PAGE_ACCESS_TOKEN,
                "name": album_name,
                "message": caption
            }
        ).json()

        target_id = album_res.get("id", FB_PAGE_ID)
        print(f"📁 Facebook Dedicated Album ID: {target_id}")

        for idx, img_path in enumerate(image_paths):
            upload_url = f"https://graph.facebook.com/v20.0/{target_id}/photos"
            with open(img_path, "rb") as img_file:
                photo_res = requests.post(
                    upload_url,
                    params={
                        "access_token": FB_PAGE_ACCESS_TOKEN,
                        "caption": f"{state_name} - Page {idx + 1} of {len(image_paths)}",
                        "fields": "id,images,source"
                    },
                    files={"source": img_file}
                ).json()

            if "id" in photo_res:
                img_url = ""
                if "images" in photo_res and len(photo_res["images"]) > 0:
                    img_url = photo_res["images"][0].get("source", "")
                elif "source" in photo_res:
                    img_url = photo_res.get("source", "")
                else:
                    img_url = get_photo_url(photo_res["id"])
                uploaded.append({"id": photo_res["id"], "url": img_url})
            else:
                print(f"❌ Facebook Photo Upload Error: {photo_res}")

        print(f"✅ Facebook Album मध्ये संपूर्ण ग्रुप यशस्वीपणे पोस्ट झाला: {target_id} ({len(uploaded)} पेजेस)")

    return uploaded

def post_instagram(caption, uploaded_media):
    if not IG_ACCOUNT_ID:
        return

    valid_media = [m for m in uploaded_media if m.get("url")]
    if not valid_media:
        print("❌ Instagram साठी व्हॅलिड URLs सापडल्या नाहीत.")
        return

    # १. जर स्टेटचे फक्त १ च पेज असेल -> सिंगल इमेज पोस्ट
    if len(valid_media) == 1:
        img_url = valid_media[0]["url"]
        con_res = requests.post(
            f"https://graph.facebook.com/v20.0/{IG_ACCOUNT_ID}/media",
            data={"access_token": FB_PAGE_ACCESS_TOKEN, "image_url": img_url, "caption": caption}
        ).json()

        if "id" in con_res:
            time.sleep(5)
            pub_res = requests.post(
                f"https://graph.facebook.com/v20.0/{IG_ACCOUNT_ID}/media_publish",
                data={"access_token": FB_PAGE_ACCESS_TOKEN, "creation_id": con_res["id"]}
            ).json()
            print(f"✅ Instagram Single Post Published: {pub_res}")

    # २. स्टेटच्या जितक्याही इमेजेस असतील (३, ७, १०, १३) -> त्या सर्वच्या सर्व एकाच सिंगल कॅरोसेल ग्रुपमध्ये!
    else:
        print(f"🚀 Instagram वर संपूर्ण {len(valid_media)} पेजेसचा १ अखंड ग्रुप (Carousel) तयार होत आहे...")
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
            print("❌ Instagram Carousel साठी चाइल्ड कंटेनर तयार झाले नाहीत.")
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
            # सर्व पेजेस प्रोसेस होण्यासाठी पुरेसा वेळ (इमेज संख्येनुसार वाढवला आहे)
            wait_time = max(15, len(child_ids) * 2)
            time.sleep(wait_time)

            pub_res = requests.post(
                f"https://graph.facebook.com/v20.0/{IG_ACCOUNT_ID}/media_publish",
                data={"access_token": FB_PAGE_ACCESS_TOKEN, "creation_id": car_res["id"]}
            ).json()
            print(f"✅ Instagram Carousel Published (सर्व {len(child_ids)} पेजेस एकाच ग्रुपमध्ये): {pub_res}")
        else:
            print(f"❌ Instagram Carousel Container Error: {car_res}")

def main():
    if not PAGES_JSON:
        print("❌ PAGES_JSON रिकामा आहे.")
        return

    data = json.loads(PAGES_JSON)
    if isinstance(data, str):
        data = json.loads(data)

    if isinstance(data, dict) and "pages" in data:
        pages = data["pages"]
    elif isinstance(data, list):
        pages = data
    else:
        pages = []

    if not pages:
        print("कोणताही डेटा सापडला नाही.")
        return

    state_name = pages[0].get("StateName", "All India")
    post_date = pages[0].get("PostDate", "")
    caption = f"🧅 {state_name} Onion Mandi Bhav Today ({post_date})\n\nDaily Onion Market Rates Update for {state_name}."

    print(f"🚀 State सुरू आहे: {state_name} ({len(pages)} पेजेस चा १ अखंड ग्रुप)")

    image_paths = []
    for idx, page in enumerate(pages):
        img_name = f"output_{state_name}_{idx + 1}.png".replace(" ", "_")
        generate_image(page, img_name)
        image_paths.append(img_name)

    # १. Facebook: सर्वच्या सर्व पेजेसचा १ अखंड ग्रुप
    uploaded_media = post_facebook(state_name, post_date, caption, image_paths)

    # २. Instagram: सर्वच्या सर्व पेजेसचा १ अखंड कॅरोसेल ग्रुप
    if uploaded_media:
        post_instagram(caption, uploaded_media)

    # क्लिनअप
    for img in image_paths:
        if os.path.exists(img):
            os.remove(img)

if __name__ == "__main__":
    main()
