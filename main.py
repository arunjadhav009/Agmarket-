import os
import sys
import time
import json
import requests
from playwright.sync_api import sync_playwright

PAGE_ID = "609269705592123"
IG_USER_ID = "17841412056274162"
FB_TOKEN = "EAAOiHd2BNnwBSRqv9aKYlAunjYxuVj1cl8W1Os57BlHwAJPQJhhqqZBHQ4xHQRbru8dgM3fbhzK90TrRoZBRB2CV1lV0jsYrgI01t2A7alZCJCbSdhZAcQUZCZCwlmYnOdrj585llVWO1BVZCuJ8CcWUM4ZBHPu2yANurGZCqBAFeZANlZBV13RT3xUZCANfvZCz8wkY55mAQuC67rYJh8jPiCaOz7XPE"

def load_html_template():
    with open("template.html", "r", encoding="utf-8") as f:
        return f.read()

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

def publish_group_to_meta(group_fb_ids, group_ig_urls, caption):
    # १. Facebook Post
    print(f"\n--- Publishing Group ({len(group_fb_ids)} images) to Facebook ---")
    feed_url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed"
    attached_media = [{"media_fbid": pid} for pid in group_fb_ids]
    post_payload = {
        "message": caption,
        "attached_media": json.dumps(attached_media),
        "access_token": FB_TOKEN
    }
    fb_resp = requests.post(feed_url, data=post_payload).json()
    print("Facebook Post Response:", fb_resp)

    # २. Instagram Carousel Post
    if group_ig_urls:
        print(f"--- Publishing Group ({len(group_ig_urls)} images) to Instagram ---")
        ig_container_ids = []

        for idx, img_url in enumerate(group_ig_urls):
            create_item_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
            item_payload = {
                "image_url": img_url,
                "is_carousel_item": "true",
                "access_token": FB_TOKEN
            }
            c_res = requests.post(create_item_url, data=item_payload).json()
            if "id" in c_res:
                ig_container_ids.append(c_res["id"])
                print(f"  Container {idx + 1}/{len(group_ig_urls)} created: {c_res['id']}")
            else:
                print(f"  Error container {idx + 1}: {c_res}")

        if ig_container_ids:
            print("Waiting 8 seconds for Meta to process items...")
            time.sleep(8)

            main_carousel_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
            main_payload = {
                "media_type": "CAROUSEL",
                "children": json.dumps(ig_container_ids),
                "caption": caption,
                "access_token": FB_TOKEN
            }
            main_res = requests.post(main_carousel_url, data=main_payload).json()

            if "id" in main_res:
                creation_id = main_res["id"]
                print(f"Main Carousel Container ID: {creation_id}")

                # Polling for status 'FINISHED'
                status_url = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code&access_token={FB_TOKEN}"
                is_ready = False
                for attempt in range(1, 12):
                    print(f"Checking IG status (Attempt {attempt}/11)...")
                    s_res = requests.get(status_url).json()
                    status = s_res.get("status_code", "")
                    if status == "FINISHED":
                        is_ready = True
                        break
                    elif status == "ERROR":
                        print("Meta reported an error processing carousel.")
                        break
                    time.sleep(5)

                if is_ready:
                    pub_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
                    pub_res = requests.post(pub_url, data={"creation_id": creation_id, "access_token": FB_TOKEN}).json()
                    print("Instagram Final Publish Response:", pub_res)
                else:
                    print("Instagram Media was not ready in time.")
            else:
                print("Error creating main IG carousel:", main_res)

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

    first_page = pages_data[0]
    curr_state = first_page.get("StateName", "कांदा बाजार भाव")
    post_date = first_page.get("PostDate", "")

    template_html = load_html_template()
    all_fb_photo_ids = []
    all_ig_image_urls = []

    # पायरी १: सर्व १८-रो च्या इमेजेस तयार करणे
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--font-render-hinting=none"]
        )
        context = browser.new_context(
            viewport={"width": 1080, "height": 1350}, # 4:5 Portrait Ratio
            device_scale_factor=2
        )
        page = context.new_page()

        for index, item in enumerate(pages_data):
            final_html_content = fill_html_data(template_html, item)
            image_name = f"state_page_{index + 1}.png"
            
            print(f"Generating 4:5 Portrait Image {index + 1}/{len(pages_data)}: {image_name}...")
            page.set_content(final_html_content, wait_until="load")
            page.screenshot(path=image_name, full_page=False)

            # Facebook वर Unpublished फोटो अपलोड
            upload_url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"
            with open(image_name, "rb") as img_file:
                files = {"source": img_file}
                data = {"published": "false", "access_token": FB_TOKEN}
                res = requests.post(upload_url, files=files, data=data)
                result = res.json()

            if "id" in result:
                photo_id = result["id"]
                all_fb_photo_ids.append(photo_id)
                print(f"  Uploaded to FB. Photo ID: {photo_id}")

                # Instagram साठी High-Res Public URL मिळवणे
                pic_req = requests.get(
                    f"https://graph.facebook.com/v19.0/{photo_id}?fields=images&access_token={FB_TOKEN}"
                ).json()
                if "images" in pic_req and len(pic_req["images"]) > 0:
                    public_url = pic_req["images"][0]["source"]
                    all_ig_image_urls.append(public_url)
            else:
                print(f"  Error uploading page {index + 1}: {result}")

        browser.close()

    if not all_fb_photo_ids:
        print("No photos uploaded. Exiting.")
        sys.exit(1)

    # पायरी २: ग्रुपिंग करणे (Instagram च्या नियमानुसार कमाल १० इमेजेसचा एक ग्रुप)
    MAX_PER_GROUP = 10
    total_images = len(all_fb_photo_ids)
    num_groups = (total_images + MAX_PER_GROUP - 1) // MAX_PER_GROUP

    print(f"\nTotal Images: {total_images}. Dividing into {num_groups} group(s)...")

    for g_idx in range(num_groups):
        start = g_idx * MAX_PER_GROUP
        end = start + MAX_PER_GROUP
        group_fb = all_fb_photo_ids[start:end]
        group_ig = all_ig_image_urls[start:end]

        part_text = f" (Part {g_idx + 1}/{num_groups})" if num_groups > 1 else ""
        caption = (
            f"🧅 {curr_state} कांदा बाजारभाव{part_text} ({post_date})\n\n"
            f"दररोजच्या ताज्या कांदा बाजारभावासाठी पेजला नक्की फॉलो करा!\n"
            f"#कांदा #बाजारभाव #{curr_state.replace(' ', '_')} #OnionRates #greensourceonion"
        )

        publish_group_to_meta(group_fb, group_ig, caption)
        
        # ग्रुप्समध्ये १० सेकंदांचा गॅप ठेवणे
        if g_idx < num_groups - 1:
            print("Waiting 10 seconds before publishing next group...")
            time.sleep(10)

if __name__ == "__main__":
    main()
