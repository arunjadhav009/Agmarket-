import os
import json
import time
import requests
from playwright.sync_api import sync_playwright

PAGES_JSON = os.environ.get("PAGES_JSON")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
IG_ACCOUNT_ID = os.environ.get("IG_ACCOUNT_ID")

def generate_image_for_page(page_data, output_image_path):
    with open("template.html", "r", encoding="utf-8") as f:
        html_template = f.read()

    rows_html = ""
    for r in page_data["PageData"]:
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
        page.screenshot(path=output_image_path, full_page=False)
        browser.close()

def post_to_social_media(state_name, image_paths):
    # तुमची सध्याची फेसबुक/इन्स्टा पोस्टिंग मेथड
    print(f"Posting {len(image_paths)} images for {state_name} to Facebook and Instagram...")
    # (टीप: तुमचे सध्याचे FB / Insta API कोड इथे थेट वापरा)

def main():
    if not PAGES_JSON:
        print("कोणताही डेटा मिळाला नाही.")
        return

    states_data = json.loads(PAGES_JSON)
    total_states = len(states_data)
    print(f"एकूण राज्ये: {total_states}")

    for idx, state_obj in enumerate(states_data):
        state_name = state_obj["state"]
        pages = state_obj["pages"]
        print(f"\n[{idx + 1}/{total_states}] राज्य सुरू आहे: {state_name} (Pages: {len(pages)})")

        image_files = []
        for p_idx, page in enumerate(pages):
            img_path = f"image_{state_name}_{p_idx+1}.png".replace(" ", "_")
            generate_image_for_page(page, img_path)
            image_files.append(img_path)

        # सोशल मीडियावर पोस्ट करा
        post_to_social_media(state_name, image_files)

        # इमेज फाइल्स क्लीनअप
        for img in image_files:
            if os.path.exists(img):
                os.remove(img)

        # शेवटचे राज्य नसल्यास पुढील राज्यासाठी १५ मिनिटे (900 सेकंद) गॅप
        if idx < total_states - 1:
            print(f"{state_name} पोस्ट पूर्ण. पुढील राज्यासाठी १५ मिनिटे वाट पाहत आहे...")
            time.sleep(900)

if __name__ == "__main__":
    main()
