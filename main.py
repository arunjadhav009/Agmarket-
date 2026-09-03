import os
import sys
import time
import json
import requests
from playwright.sync_api import sync_playwright

PAGE_ID = "609269705592123"
IG_USER_ID = "17841412056274162"
FB_TOKEN = "EAAOiHd2BNnwBSRqv9aKYlAunjYxuVj1cl8W1Os57BlHwAJPQJhhqqZBHQ4xHQRbru8dgM3fbhzK90TrRoZBRB2CV1lV0jsYrgI01t2A7alZCJCbSdhZAcQUZCZCwlmYnOdrj585llVWO1BVZCuJ8CcWUM4ZBHPu2yANurGZCqBAFeZANlZBV13RT3xUZCANfvZCz8wkY55mAQuC67rYJh8jPiCaOz7XPE"

POST_CAPTION = (
    "महाराष्ट्र राज्य कांदा बाजारभाव\n\n"
    "दररोजच्या ताज्या बाजारभावासाठी पेजला नक्की फॉलो करा!\n"
    "#कांदा #बाजारभाव #महाराष्ट्र #OnionRates #Maharashtra #greensourceonion"
)

def render_html_template(template_str, data):
    rows = data.get("PageData", [])
    post_date = data.get("PostDate", "आजचे भाव")
    state_name = data.get("StateName", "महाराष्ट्र")
    current_page = data.get("CurrentPage", 1)
    total_pages = data.get("TotalPages", 1)

    table_rows = ""
    for idx, r in enumerate(rows):
        is_even = (idx % 2 == 1)
        bg = "#f8fafc" if is_even else "#ffffff"
        apmc = r.get("APMC", "-")
        variety = r.get("Variety", "-")
        qty = r.get("Quantity", "0")
        lrate = r.get("Lrate", "0")
        hrate = r.get("Hrate", "0")
        modal = r.get("Modal", "0")

        table_rows += f"""
        <tr style="background: {bg}; border-bottom: 1px solid #e2e8f0; height: 48px;">
          <td style="text-align: left; padding: 0 12px; font-weight: 700; font-size: 19px; color: #0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{apmc}</td>
          <td style="text-align: center; padding: 0 6px; font-size: 17px; color: #475569; font-weight: 600;">{variety}</td>
          <td style="text-align: center; padding: 0 6px; font-size: 18px; font-weight: 700; color: #0f172a;">{qty}</td>
          <td style="text-align: center; padding: 0 6px; font-size: 18px; font-weight: 700; color: #dc2626;">₹{lrate}</td>
          <td style="text-align: center; padding: 0 6px; font-size: 18px; font-weight: 700; color: #16a34a;">₹{hrate}</td>
          <td style="text-align: center; padding: 0 6px; font-size: 19px; font-weight: 800; color: #881337; background: rgba(225, 29, 72, 0.08);">₹{modal}</td>
        </tr>
        """

    html = template_str.replace("{{POST_DATE}}", str(post_date))
    html = html.replace("{{STATE_NAME}}", str(state_name))
    html = html.replace("{{CURRENT_PAGE}}", str(current_page))
    html = html.replace("{{TOTAL_PAGES}}", str(total_pages))
    html = html.replace("{{TABLE_ROWS}}", table_rows)
    return html

def main():
    raw_pages = os.environ.get("PAGES_JSON", "").strip()
    if not raw_pages:
        print("Error: No PAGES_JSON provided.")
        sys.exit(1)

    template_path = os.path.join(os.path.dirname(__file__), "template.html")
    if not os.path.exists(template_path):
        print(f"Error: {template_path} not found.")
        sys.exit(1)

    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()

    pages_data = json.loads(raw_pages)
    print(f"Total pages received: {len(pages_data)}")

    fb_photo_ids = []
    ig_image_urls = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--font-render-hinting=none"
            ]
        )
        context = browser.new_context(
            viewport={"width": 1080, "height": 1080},
            device_scale_factor=2
        )
        page = context.new_page()

        for index, item in enumerate(pages_data):
            page_info = item.get("json", item)
            html_content = render_html_template(template_str, page_info)
            image_name = f"mandi_page_{index + 1}.png"

            print(f"Generating Ultra-HD Image {index + 1}/{len(pages_data)}: {image_name}...")
            page.set_content(html_content, wait_until="load")
            page.screenshot(path=image_name, full_page=False)

            upload_url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"
            with open(image_name, "rb") as img_file:
                files = {"source": img_file}
                data = {"published": "false", "access_token": FB_TOKEN}
                res = requests.post(upload_url, files=files, data=data)
                result = res.json()

            if "id" in result:
                photo_id = result["id"]
                fb_photo_ids.append(photo_id)
                print(f"Page {index + 1} uploaded to FB. Photo ID: {photo_id}")

                pic_req = requests.get(
                    f"https://graph.facebook.com/v19.0/{photo_id}?fields=images&access_token={FB_TOKEN}"
                ).json()
                if "images" in pic_req and len(pic_req["images"]) > 0:
                    public_url = pic_req["images"][0]["source"]
                    ig_image_urls.append(public_url)
            else:
                print(f"Error uploading page {index + 1}: {result}")

        browser.close()

    if not fb_photo_ids:
        print("No photos uploaded. Exiting.")
        sys.exit(1)

    print("\n--- 1. Publishing to Facebook ---")
    feed_url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed"
    attached_media = [{"media_fbid": pid} for pid in fb_photo_ids]
    post_payload = {
        "message": POST_CAPTION,
        "attached_media": json.dumps(attached_media),
        "access_token": FB_TOKEN
    }
    fb_resp = requests.post(feed_url, data=post_payload)
    print("Facebook Post Response:", fb_resp.text)

    if ig_image_urls:
        print("\n--- 2. Publishing to Instagram (@greensourceonion) ---")
        ig_container_ids = []

        for idx, img_url in enumerate(ig_image_urls):
            create_item_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
            item_payload = {
                "image_url": img_url,
                "is_carousel_item": "true",
                "access_token": FB_TOKEN
            }
            c_res = requests.post(create_item_url, data=item_payload).json()
            if "id" in c_res:
                ig_container_ids.append(c_res["id"])
                print(f"IG Carousel item {idx + 1} container created: {c_res['id']}")
            else:
                print(f"Error creating IG item {idx + 1}: {c_res}")

        if ig_container_ids:
            print("Waiting 8 seconds for item containers to process...")
            time.sleep(8)

            main_carousel_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
            main_payload = {
                "media_type": "CAROUSEL",
                "children": json.dumps(ig_container_ids),
                "caption": POST_CAPTION,
                "access_token": FB_TOKEN
            }
            main_res = requests.post(main_carousel_url, data=main_payload).json()

            if "id" in main_res:
                creation_id = main_res["id"]
                print(f"Main IG Carousel Container ID: {creation_id}")

                status_url = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code&access_token={FB_TOKEN}"
                is_ready = False
                for attempt in range(1, 10):
                    print(f"Checking media readiness (Attempt {attempt}/9)...")
                    s_res = requests.get(status_url).json()
                    status = s_res.get("status_code", "")
                    print(f"Current Status: {status}")

                    if status == "FINISHED":
                        is_ready = True
                        break
                    elif status == "ERROR":
                        print("Meta reported an error processing this carousel container.")
                        break
                    time.sleep(5)

                if is_ready:
                    publish_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
                    pub_res = requests.post(publish_url, data={"creation_id": creation_id, "access_token": FB_TOKEN}).json()
                    print("Instagram Final Publish Response:", pub_res)
                else:
                    print("Could not publish: Media container was not ready in time.")
            else:
                print("Error creating main IG carousel:", main_res)

if __name__ == "__main__":
    main()
