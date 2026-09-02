import os
import json
import requests
from playwright.sync_api import sync_playwright

PAGES_JSON = os.environ.get("PAGES_JSON")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")

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

def post_facebook_album(state_name, post_date, image_paths):
    if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
        print("Facebook Credentials सापडले नाहीत.")
        return

    media_ids = []
    for img_path in image_paths:
        url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/photos"
        with open(img_path, "rb") as img_file:
            res = requests.post(
                url,
                params={"access_token": FB_PAGE_ACCESS_TOKEN, "published": "false"},
                files={"source": img_file}
            ).json()

        if "id" in res:
            media_ids.append({"media_fbid": res["id"]})
        else:
            print(f"Image Upload Failed: {res}")

    if not media_ids:
        print("एकही इमेज अपलोड झाली नाही.")
        return

    feed_url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed"
    payload = {
        "access_token": FB_PAGE_ACCESS_TOKEN,
        "message": f"📊 {state_name} Mandi Bhav Today ({post_date})\n\nDaily market rates update for {state_name}.",
        "attached_media": json.dumps(media_ids)
    }

    res = requests.post(feed_url, data=payload).json()
    if "id" in res:
        print(f"✅ Facebook वर {state_name} चा पूर्ण अल्बम पोस्ट झाला: {res['id']}")
    else:
        print(f"❌ Facebook Feed Post Error: {res}")

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
        print("डेटा फॉरमॅट जुळला नाही.")
        return

    if not pages:
        print("पेजेस सापडले नाहीत.")
        return

    state_name = pages[0].get("StateName", "All India")
    post_date = pages[0].get("PostDate", "")
    print(f"🚀 Processing State: {state_name} (Total Pages: {len(pages)})")

    image_paths = []
    for idx, page in enumerate(pages):
        img_name = f"output_{state_name}_{idx + 1}.png".replace(" ", "_")
        generate_image(page, img_name)
        image_paths.append(img_name)
        print(f"📸 तयार झाली: {img_name}")

    post_facebook_album(state_name, post_date, image_paths)

    for img in image_paths:
        if os.path.exists(img):
            os.remove(img)

if __name__ == "__main__":
    main()
