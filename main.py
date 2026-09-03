import os
import sys
import time
import json
import requests
from playwright.sync_api import sync_playwright

PAGE_ID = "609269705592123"
IG_USER_ID = "17841412056274162"
FB_TOKEN = "EAAOiHd2BNnwBSRqv9aKYlAunjYxuVj1cl8W1Os57BlHwAJPQJhhqqZBHQ4xHQRbru8dgM3fbhzK90TrRoZBRB2CV1lV0jsYrgI01t2A7alZCJCbSdhZAcQUZCZCwlmYnOdrj585llVWO1BVZCuJ8CcWUM4ZBHPu2yANurGZCqBAFeZANlZBV13RT3xUZCANfvZCz8wkY55mAQuC67rYJh8jPiCaOz7XPE"

# HTML टेंप्लेट वाचणे
def load_html_template():
    with open("template.html", "r", encoding="utf-8") as f:
        return f.read()

# १८ रो सह HTML टेंप्लेटमध्ये डेटा भरणे
def fill_html_data(template, data):
    rows_data = data.get("PageData", [])
    current_state = data.get("StateName", "कांदा बाजार भाव")
    post_date = data.get("PostDate", "आजचे भाव")
    
    table_rows_html = ""
    for idx, r in enumerate(rows_data):
        is_even = (idx % 2 == 1)
        bg = "#f8fafc" if is_even else "#ffffff"
        apmc = r.get("APMC", r.get("Market", "-"))
        variety = r.get("Variety", "-")
        qty = r.get("Quantity", "0")
        lrate = r.get("Lrate", r.get("Min_Price", "0"))
        hrate = r.get("Hrate", r.get("Max_Price", "0"))
        modal = r.get("Modal", r.get("Modal_Price", "0"))

        table_rows_html += f"""
        <tr style="background: {bg}; border-bottom: 1px solid #e2e8f0; height: 50px;">
          <td style="text-align: left; padding: 0 14px; font-weight: 700; font-size: 19px; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{apmc}</td>
          <td style="text-align: center; padding: 0 8px; font-size: 17px; color: #475569; font-weight: 500;">{variety}</td>
          <td style="text-align: center; padding: 0 8px; font-size: 18px; font-weight: 700; color: #0f172a;">{qty}</td>
          <td style="text-align: center; padding: 0 8px; font-size: 18px; font-weight: 700; color: #dc2626;">₹{lrate}</td>
          <td style="text-align: center; padding: 0 8px; font-size: 18px; font-weight: 700; color: #16a34a;">₹{hrate}</td>
          <td style="text-align: center; padding: 0 8px; font-size: 19px; font-weight: 800; color: #881337; background: rgba(225, 29, 72, 0.08); border-radius: 6px;">₹{modal}</td>
        </tr>
        """
        
    template = template.replace("{{ StateName }}", current_state)
    template = template.replace("{{ PostDate }}", post_date)
    template = template.replace("{{ CurrentPage }}", str(data.get("CurrentPage", 1)))
    template = template.replace("{{ TotalPages }}", str(data.get("TotalPages", 1)))
    template = template.replace("{{ TableRows }}", table_rows_html)
    
    return template

def main():
    raw_pages = os.environ.get("PAGES_JSON", "").strip()
    if not raw_pages:
        print("Error: No PAGES_JSON provided.")
        sys.exit(1)

    pages_data = json.loads(raw_pages)
    print(f"Total pages received for this state: {len(pages_data)}")
    
    if not pages_data:
        print("No pages data found. Exiting.")
        sys.exit(1)

    # फेसबुक आणि इन्स्टाग्राम कॅप्शन
    first_page = pages_data[0]
    curr_state = first_page.get("StateName", "इतर राज्य")
    post_date = first_page.get("PostDate", "")
    post_caption = (
        f"🧅 {curr_state} कांदा बाजारभाव ({post_date})\n\n"
        f"दररोजच्या ताज्या कांदा बाजारभावासाठी पेजला नक्की फॉलो करा!\n"
        f"#कांदा #बाजारभाव #{curr_state.replace(' ', '_')} #OnionRates #greensourceonion"
    )

    template_html = load_html_template()
    fb_photo_ids = []
    ig_image_urls = []

    # इमेज जनरेशन (Playwright) - 4:5 Portrait रेशोसह
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox", "--font-render-hinting=none"])
        context = browser.new_context(
            viewport={"width": 1080, "height": 1350}, # 4:5 Portrait Ratio
            device_scale_factor=2 # Ultra-HD इमेजसाठी
        )
        page = context.new_page()

        for index, item in enumerate(pages_data):
            # टेंप्लेटमध्ये डेटा भरणे
            final_html_content = fill_html_data(template_html, item)
            
            # तात्पुरती HTML फाईल बनवणे जेणेकरून Playwright ती वाचू शकेल
            temp_html_path = f"mandi_state_temp_{index}.html"
            with open(temp_html_path, "w", encoding="utf-8") as f:
                f.read() # साफ करणे
                f.write(final_html_content)
            
            image_name = f"state_page_{index + 1}.png"
            print(f"Generating 4:5 Portrait Image {index + 1}/{len(pages_data)}: {image_name}...")
            
            # HTML लोड करणे आणि स्क्रीनशॉट घेणे
            local_url = f"file://{os.path.abspath(temp_html_path)}"
            page.goto(local_url, wait_until="load")
            page.screenshot(path=image_name, full_page=False)
            
            # तात्पुरती HTML फाईल डिलीट करणे
            os.remove(temp_html_path)

            # १. Facebook वर Unpublished फोटो अपलोड
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

                # २. Instagram साठी Facebook कडून फोटोची High-Res Public URL मिळवणे
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

    # --- Facebook पोस्ट करणे (Multi-Photo Post) ---
    print(f"\n--- 1. Publishing {curr_state} to Facebook ---")
    feed_url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed"
    attached_media = [{"media_fbid": pid} for pid in fb_photo_ids]
    post_payload = {
        "message": post_caption,
        "attached_media": json.dumps(attached_media),
        "access_token": FB_TOKEN
    }
    fb_resp = requests.post(feed_url, data=post_payload)
    print("Facebook Post Response:", fb_resp.text)

    # --- Instagram पोस्ट करणे (Multi-Photo Carousel Post) ---
    if ig_image_urls:
        print(f"\n--- 2. Publishing {curr_state} to Instagram ---")
        ig_container_ids = []

        # प्रत्येक इमेजचा Instagram Item Container तयार करणे
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

        # सर्व आयटम्स एकत्र करून मुख्य Carousel Container तयार करणे
        if ig_container_ids:
            # आयटम्स प्रोसेस होण्यासाठी सुरुवातीला ८ सेकंद वाट पाहणे (Wait before Main Carousel)
            print("Waiting 8 seconds for item containers to process...")
            time.sleep(8)

            main_carousel_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
            main_payload = {
                "media_type": "CAROUSEL",
                "children": json.dumps(ig_container_ids),
                "caption": post_caption,
                "access_token": FB_TOKEN
            }
            main_res = requests.post(main_carousel_url, data=main_payload).json()

            if "id" in main_res:
                creation_id = main_res["id"]
                print(f"Main IG Carousel Container ID: {creation_id}")

                # कंटेनर स्टेटस 'FINISHED' होईपर्यंत तपासणे (Status Polling Loop)
                # इन्स्टाग्रामला ४:५ रेशोच्या ५ इमेजेस रेंडर करायला वेळ लागतो.
                status_url = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code&access_token={FB_TOKEN}"
                is_ready = False
                # जास्तीत जास्त ४५ सेकंद वाट पाहणे (९ ट्राय * ५ सेकंद)
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

                # फायनल पब्लिश करणे
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
