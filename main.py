import os
import json
import time
import requests
from playwright.sync_api import sync_playwright

PAGES_JSON = os.environ.get("PAGES_JSON")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
IG_ACCOUNT_ID = os.environ.get("IG_ACCOUNT_ID")

def generate_image(page_data, output_path):
    with open("template.html", "r", encoding="utf-8") as f:
        html_template = f.read()

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
        html_template.replace("{{STATE_NAME}}", str(page_data.get("StateName", "")))
        .replace("{{POST_DATE}}", str(page_data.get("PostDate", "")))
        .replace("{{CURRENT_PAGE}}", str(page_data.get("CurrentPage", "1")))
        .replace("{{TOTAL_PAGES}}", str(page_data.get("TotalPages", "1")))
        .replace("{{TABLE_ROWS}}", rows_html)
    )

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        page.set_content(rendered_html)
        page.screenshot(path=output_path, full_page=False)
        browser.close()

def post_facebook_and_get_urls(caption, image_paths):
    uploaded = []
    
    # केस १: सिंगल इमेज पोस्ट
    if len(image_paths) == 1:
        img_path = image_paths[0]
        url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/photos"
        with open(img_path, "rb") as img_file:
            res = requests.post(
                url,
                params={
                    "access_token": FB_PAGE_ACCESS_TOKEN,
                    "caption": caption,
                    "published": "true",
                    "fields": "id,images"
                },
                files={"source": img_file}
            ).json()

        if "id" in res:
            print(f"✅ Facebook Single Post: {res['id']}")
            img_url = ""
            if "images" in res and len(res["images"]) > 0:
                img_url = res["images"][0].get("source", "")
            else:
                det = requests.get(
                    f"https://graph.facebook.com/v20.0/{res['id']}",
                    params={"access_token": FB_PAGE_ACCESS_TOKEN, "fields": "source"}
                ).json()
                img_url = det.get("source", "")
            uploaded.append({"id": res["id"], "url": img_url})
        else:
            print(f"❌ Facebook Single Post Failed: {res}")

    # केस २: मल्टिपल इमेजेस अल्बम पोस्ट
    else:
        media_ids = []
        for img_path in image_paths:
            url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/photos"
            with open(img_path, "rb") as img_file:
                res = requests.post(
                    url,
                    params={
                        "access_token": FB_PAGE_ACCESS_TOKEN,
                        "published": "false",
                        "fields": "id,images"
                    },
                    files={"source": img_file}
                ).json()

            if "id" in res:
                media_ids.append({"media_fbid": res["id"]})
                img_url = ""
                if "images" in res and len(res["images"]) > 0:
                    img_url = res["images"][0].get("source", "")
                else:
                    det = requests.get(
                        f"https://graph.facebook.com/v20.0/{res['id']}",
                        params={"access_token": FB_PAGE_ACCESS_TOKEN, "fields": "source"}
                    ).json()
                    img_url = det.get("source", "")
                uploaded.append({"id": res["id"], "url": img_url})

        if media_ids:
            feed_url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed"
            payload = {
                "access_token": FB_PAGE_ACCESS_TOKEN,
                "message": caption,
                "attached_media": json.dumps(media_ids)
            }
            feed_res = requests.post(feed_url, data=payload).json()
            if "id" in feed_res:
                print(f"✅ Facebook Multi-image Album: {feed_res['id']}")
            else:
                print(f"❌ Facebook Album Error: {feed_res}")

    return uploaded

def post_instagram(caption, uploaded_media):
    if not IG_ACCOUNT_ID:
        print("ℹ️ IG_ACCOUNT_ID सेट नाही, Instagram पोस्ट वगळली.")
        return

    # केस १: सिंगल इमेज
    if len(uploaded_media) == 1:
        img_url = uploaded_media[0].get("url")
        if not img_url:
            return

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

    # केस २: Carousel पोस्ट
    else:
        child_ids = []
        for item in uploaded_media:
            img_url = item.get("url")
            if not img_url:
                continue
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
            time.sleep(8)
            pub_res = requests.post(
                f"https://graph.facebook.com/v20.0/{IG_ACCOUNT_ID}/media_publish",
                data={"access_token": FB_PAGE_ACCESS_TOKEN, "creation_id": car_res["id"]}
            ).json()
            print(f"✅ Instagram Carousel Published: {pub_res}")

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
        print("कोणताही पेज डेटा उपलब्ध नाही.")
        return

    state_name = pages[0].get("StateName", "All India")
    post_date = pages[0].get("PostDate", "")
    
    # संपूर्ण इंग्रजी कॅप्शन
    caption = f"🧅 {state_name} Onion Mandi Bhav Today ({post_date})\n\nDaily Onion Market Rates Update for {state_name}."

    print(f"🚀 State सुरू आहे: {state_name} ({len(pages)} पेजेस)")

    image_paths = []
    for idx, page in enumerate(pages):
        img_name = f"output_{state_name}_{idx + 1}.png".replace(" ", "_")
        generate_image(page, img_name)
        image_paths.append(img_name)

    # १. Facebook वर पोस्ट करून URLs मिळवणे
    uploaded_media = post_facebook_and_get_urls(caption, image_paths)

    # २. Instagram वर पोस्ट करणे
    if uploaded_media:
        post_instagram(caption, uploaded_media)

    for img in image_paths:
        if os.path.exists(img):
            os.remove(img)

if __name__ == "__main__":
    main()
