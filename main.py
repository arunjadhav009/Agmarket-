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
        # अचूक 1:1 Square रेशो (1080x1080)
        page = browser.new_page(viewport={"width": 1080, "height": 1080})
        page.set_content(rendered_html)
        page.screenshot(path=output_path, full_page=False)
        browser.close()

def post_facebook(state_name, post_date, caption, image_paths):
    uploaded = []

    # १. सिंगल इमेज असल्यास थेट पब्लिश करणे
    if len(image_paths) == 1:
        url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/photos"
        with open(image_paths[0], "rb") as img_file:
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
            print(f"✅ Facebook Single Post यशस्वी: {res['id']}")
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
            print(f"❌ Facebook Single Upload Error: {res}")

    # २. मल्टिपल इमेजेस असल्यास स्वतंत्र अल्बम तयार करून अपलोड करणे
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
                        "caption": f"{state_name} - Page {idx + 1}",
                        "fields": "id,images"
                    },
                    files={"source": img_file}
                ).json()

            if "id" in photo_res:
                img_url = ""
                if "images" in photo_res and len(photo_res["images"]) > 0:
                    img_url = photo_res["images"][0].get("source", "")
                else:
                    det = requests.get(
                        f"https://graph.facebook.com/v20.0/{photo_res['id']}",
                        params={"access_token": FB_PAGE_ACCESS_TOKEN, "fields": "source"}
                    ).json()
                    img_url = det.get("source", "")
                uploaded.append({"id": photo_res["id"], "url": img_url})
            else:
                print(f"❌ Facebook Album Photo Upload Failed: {photo_res}")

        print(f"✅ Facebook Multi-image Album तयार झाला: {target_id} ({len(uploaded)} पेजेस)")

    return uploaded

def post_instagram(caption, uploaded_media):
    if not IG_ACCOUNT_ID:
        print("ℹ️ IG_ACCOUNT_ID सेट नाही, Instagram पोस्ट वगळली.")
        return

    # सिंगल इमेज
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
        else:
            print(f"❌ Instagram Container Error: {con_res}")

    # Carousel पोस्ट (मल्टी-इमेज)
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
        print("कोणताही पेज डेटा उपलब्ध नाही.")
        return

    state_name = pages[0].get("StateName", "All India")
    post_date = pages[0].get("PostDate", "")
    caption = f"🧅 {state_name} Onion Mandi Bhav Today ({post_date})\n\nDaily Onion Market Rates Update for {state_name}."

    print(f"🚀 Processing State: {state_name} ({len(pages)} पेजेस)")

    image_paths = []
    for idx, page in enumerate(pages):
        img_name = f"output_{state_name}_{idx + 1}.png".replace(" ", "_")
        generate_image(page, img_name)
        image_paths.append(img_name)

    # १. Facebook पोस्टिंग
    uploaded_media = post_facebook(state_name, post_date, caption, image_paths)

    # २. Instagram पोस्टिंग
    if uploaded_media:
        post_instagram(caption, uploaded_media)

    # क्लिनअप
    for img in image_paths:
        if os.path.exists(img):
            os.remove(img)

if __name__ == "__main__":
    main()
