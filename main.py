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

def upload_images_to_facebook(image_paths):
    uploaded = []
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
            print(f"❌ Facebook Photo Upload Error: {res}")
    return uploaded

def post_facebook_album(caption, uploaded_media):
    if len(uploaded_media) == 1:
        # १ इमेज असल्यास पोस्ट पब्लिश करणे
        res = requests.post(
            f"https://graph.facebook.com/v20.0/{uploaded_media[0]['id']}",
            data={"access_token": FB_PAGE_ACCESS_TOKEN, "is_published": "true", "message": caption}
        ).json()
        print(f"✅ Facebook Single Post: {res}")
    else:
        # २ किंवा जास्त इमेजेससाठी अल्बम पोस्ट
        media_fbid_list = [{"media_fbid": m["id"]} for m in uploaded_media]
        res = requests.post(
            f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed",
            data={
                "access_token": FB_PAGE_ACCESS_TOKEN,
                "message": caption,
                "attached_media": json.dumps(media_fbid_list)
            }
        ).json()
        print(f"✅ Facebook Album Post: {res}")

def post_instagram(caption, uploaded_media):
    if not IG_ACCOUNT_ID:
        print("ℹ️ IG_ACCOUNT_ID सेट नाही, Instagram पोस्ट वगळली.")
        return

    # केस १: सिंगल इमेज पोस्ट
    if len(uploaded_media) == 1:
        img_url = uploaded_media[0]["url"]
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
            print(f"❌ Instagram Container Failed: {con_res}")

    # केस २: Carousel पोस्ट (मल्टी-इमेज)
    else:
        child_ids = []
        for item in uploaded_media:
            child_res = requests.post(
                f"https://graph.facebook.com/v20.0/{IG_ACCOUNT_ID}/media",
                data={
                    "access_token": FB_PAGE_ACCESS_TOKEN,
                    "image_url": item["url"],
                    "is_carousel_item": "true"
                }
            ).json()
            if "id" in child_res:
                child_ids.append(child_res["id"])
            time.sleep(2)

        if not child_ids:
            print("❌ Instagram Carousel साठी कोणतेही चाइल्ड कंटेनर बनले नाहीत.")
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
        print("PAGES_JSON रिकामा आहे.")
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
    caption = f"🧅 {state_name} Onion Mandi Bhav Today ({post_date})\n\nआजचे {state_name} राज्यातील कांदा बाजार भाव (Daily Onion Market Rates Update)."

    print(f"🚀 State सुरू आहे: {state_name} ({len(pages)} पेजेस)")

    image_paths = []
    for idx, page in enumerate(pages):
        img_name = f"output_{state_name}_{idx + 1}.png".replace(" ", "_")
        generate_image(page, img_name)
        image_paths.append(img_name)

    # १. Facebook वर इमेजेस अपलोड करून URL व IDs मिळवणे
    uploaded_media = upload_images_to_facebook(image_paths)

    if uploaded_media:
        # २. Facebook पोस्ट
        post_facebook_album(caption, uploaded_media)
        # ३. Instagram पोस्ट
        post_instagram(caption, uploaded_media)

    for img in image_paths:
        if os.path.exists(img):
            os.remove(img)

if __name__ == "__main__":
    main()
