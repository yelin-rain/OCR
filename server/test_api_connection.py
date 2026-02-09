import httpx
import base64
import json
import os
from dotenv import load_dotenv

def test_ocr():
    # Load from .env
    load_dotenv()
    
    url = os.getenv("OCR_API_URL", "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs")
    token = os.getenv("OCR_ACCESS_TOKEN")
    model = os.getenv("OCR_MODEL", "PaddleOCR-VL-1.5")
    
    print(f"Testing URL: {url}")
    print(f"Model: {model}")
    print(f"Token: {token[:5]}...{token[-5:]}" if token else "No Token found")

    if not token:
        print("Error: OCR_ACCESS_TOKEN is missing")
        return

    # Create a slightly larger transparent PNG (10x10) to avoid "image too small" errors
    # This is a solid red 10x10 PNG
    red_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAACXBIWXMAAAsTAAALEwEAmpwYAAA"
        "A9ElEQVQYV2P8//8/AyZgYmBggAJkNf8Z4IIoAqwGKMBoIMDIIKAAZWA0mAApIGZgYGAEIiMDEx"
        "MTEMf/Z4AJmBgYGAkY4IDRQAAmAAIoyMAAZYAEGBlgAijIQACmAAMYGKAAkAEyBhhAAMpAVoO0"
        "EGBkIBNgNIDYjAxMAgwMEE0MkADIAKshwMgADFAAsRqkAasBxGZkYBJgYIBoYmCCBIAKshqkAas"
        "BxGZkYBJgYIBoYmCAiCArQAFIIDMDiAVkgDQxEiAExAyMDHAFMApAAlkN0kKAAUiAkQFMgAooiw"
        "EqoCzIKlAAEmBkIBNgaIBoAmZAIACMC8mNImdAAAAAElFTkSuQmCC"
    )
    
    # Variations to test
    print("\n--- Testing JSON with x-aistudio-access-token only ---")
    headers = {
        "Content-Type": "application/json",
        "x-aistudio-access-token": token
    }
    # Remove any potential whitespace from base64
    clean_b64 = red_png_b64.replace("\n", "").replace(" ", "")
    payload = {"file": clean_b64, "fileType": 1, "model": model}
    resp = httpx.post(url, json=payload, headers=headers)
    print(f"Status: {resp.status_code}, Body: {resp.text}")

    print("\n--- Testing Multipart with x-aistudio-access-token ---")
    headers = {"x-aistudio-access-token": token}
    img_data = base64.b64decode(clean_b64)
    files = {"file": ("test.png", img_data, "image/png")}
    data = {"fileType": 1, "model": model}
    resp = httpx.post(url, files=files, data=data, headers=headers)
    print(f"Multipart Status: {resp.status_code}, Body: {resp.text}")
    
    auth_headers = [
        f"token {token}",
        token, # No prefix
    ]

    for p_idx, p in enumerate(payloads):
        for h_idx, auth in enumerate(auth_headers):
            print(f"\n--- Testing Variation P{p_idx} H{h_idx} ---")
            headers = {
                "Content-Type": "application/json",
                "Authorization": auth,
                "x-aistudio-access-token": token
            }
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, json=p, headers=headers)
                    print(f"Status: {resp.status_code}")
                    if resp.status_code == 200:
                        print(f"SUCCESS! Response: {resp.text[:100]}...")
                        return
                    else:
                        print(f"Failed: {resp.text}")
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    test_ocr()
