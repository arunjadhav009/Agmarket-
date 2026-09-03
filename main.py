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

def generate_html_page(data):
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
        <tr style="background: {bg}; border-bottom: 1px solid #e2e8f0; height: 50px;">
          <td style="text-align: left; padding: 6px 14px; font-weight: 700; font-size: 19px; color: #1e293b;">{apmc}</td>
          <td style="text-align: center; padding: 6px 8px; font-size: 17px; color: #475569; font-weight: 500;">{variety}</td>
          <td style="text-align: center; padding: 6px 8px; font-size: 18px; font-weight: 700; color: #0f172a;">{qty}</td>
          <td style="text-align: center; padding: 6px 8px; font-size: 18px; font-weight: 700; color: #dc2626;">₹{lrate}</td>
          <td style="text-align: center; padding: 6px 8px; font-size: 18px; font-weight: 700; color: #16a34a;">₹{hrate}</td>
          <td style="text-align: center; padding: 6px 8px; font-size: 19px; font-weight: 800; color: #881337; background: rgba(225, 29, 72, 0.08); border-radius: 6px;">₹{modal}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="mr">
<head>
<meta charset="UTF-8">
<style>
  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }}
  body {{
    width: 1080px;
    height: 1080px;
    background: #f1f5f9;
    font-family: 'Noto Sans Devanagari', 'Lohit Devanagari', sans-serif;
    padding: 20px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    overflow: hidden;
  }}
  .header-card {{
    background: linear-gradient(135deg, #881337 0%, #be123c 60%, #e11d48 100%);
    border-radius: 16px;
    padding: 14px 20px;
    color: #ffffff;
    box-shadow: 0 6px 18px rgba(136, 19, 55, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.15);
  }}
  .header-card h1 {{
    font-size: 30px;
    font-weight: 800;
    text-align: center;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
  }}
  .meta-chips {{
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .chip {{
    background: rgba(255, 255, 255, 0.2);
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 17px;
    font-weight: 700;
  }}
  .table-wrapper {{
    background: #ffffff;
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.05);
    border: 1px solid #cbd5e1;
    margin: 10px 0;
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
  }}
  thead th {{
    background: #1e293b;
    color: #ffffff;
    font-size: 18px;
    font-weight: 700;
    padding: 12px 8px;
    text-align: center;
    border-bottom: 2px solid #0f172a;
    height: 48px;
  }}
  .footer-bar {{
    background: #0f172a;
    color: #f8fafc;
    border-radius: 12px;
    padding: 10px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }}
  .footer-bar .left {{
    font-size: 17px;
    font-weight: 700;
    color: #fbbf24;
  }}
  .footer-bar .right {{
    font-size: 16px;
    font-weight: 600;
    color: #cbd5e1;
  }}
</style>
</head>
<body>
  <div class="header-card">
    <h1>🧅 महाराष्ट्र राज्य - आजचे कांदा बाजार भाव 🧅</h1>
    <div class="meta-chips">
      <div class="chip">तारीख: {post_date}</div>
      <div class="chip">राज्य: {state_name}</div>
      <div class="chip">पेज: {current_page} / {total_pages}</div>
    </div>
  </div>

  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th style="text-align: left; padding-left: 14px; width: 28%;">बाजार समिती</th>
          <th style="width: 16%;">जात/प्रकार</th>
          <th style="width: 14%;">आवक (क्विं.)</th>
          <th style="width: 14%;">कमी भाव</th>
          <th style="width: 14%;">जास्त भाव</th>
          <th style="width: 14%;">सरासरी भाव</th>
        </tr>
      </thead>
      <tbody>
        {table_rows}
      </tbody>
    </table>
  </div>

  <div class="footer-bar">
    <div class="left">⚖️ दर प्रति क्विंटल (₹)</div>
    <div class="right">दररोजच्या ताज्या बाजारभावासाठी फॉलो करा</div>
  </div>
</body>
</html>"""
    return html

def main():
    raw_pages = os.environ.get("PAGES_JSON", "").strip()
    if not raw_pages:
        print("Error: No PAGES_JSON provided.")
        sys.exit(1)

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
            html_content = generate_html_page(page_info)
            image_name = f"mandi_page_{index + 1}.png"

            print(f"Generating Ultra-HD Image {index + 1}/{len(pages_data)}: {image_name}...")
            page.set_content(html_content, wait_until="load")
            page.screenshot(path=image_name, full_page=False)

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

                # २. Instagram साठी Facebook कडून फोटोची Public URL मिळवणे
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

    # Facebook वर Multi-Photo Post करणे
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

    # Instagram वर Multi-Photo Carousel Post करणे
    if ig_image_urls:
        print("\n--- 2. Publishing to Instagram (@greensourceonion) ---")
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

        if ig_container_ids:
            # आयटम्स प्रोसेस होण्यासाठी सुरुवातीला ८ सेकंद वाट पाहणे
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

                # कंटेनर स्टेटस 'FINISHED' होईपर्यंत तपासणे (Status Polling Loop)
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
