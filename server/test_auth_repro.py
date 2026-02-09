import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8000"

async def test_register():
    print(f"Testing Registration against {BASE_URL}...")
    async with httpx.AsyncClient() as client:
        try:
            # 1. Register
            reg_data = {
                "username": "testuser_repro",
                "email": "test_repro@example.com",
                "password": "password123"
            }
            print(f"Sending register request: {reg_data}")
            response = await client.post(f"{BASE_URL}/auth/register", json=reg_data)
            print(f"Register Status: {response.status_code}")
            print(f"Register Response: {response.text}")

            if response.status_code == 200:
                print("Registration Success!")
            elif response.status_code == 400 and "already registered" in response.text:
                print("User already exists, proceeding to login test.")
            else:
                print("Registration Failed.")
                # Don't return, try login anyway just in case

            # 2. Login (Get Token)
            print("\nTesting Login...")
            login_data = {
                "username": "testuser_repro",
                "password": "password123"
            }
            # OAuth2PasswordRequestForm expects form data, not json
            print(f"Sending login request (form data): {login_data}")
            response = await client.post(f"{BASE_URL}/auth/token", data=login_data)
            print(f"Login Status: {response.status_code}")
            print(f"Login Response: {response.text}")

            if response.status_code == 200:
                token = response.json().get("access_token")
                print(f"Login Success! Token: {token[:10]}...")
                return token
            else:
                print("Login Failed.")
                return None

        except httpx.ConnectError:
            print("Connection Error: Could not connect to the server. Is it running?")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    if "multiproc" in sys.modules:
        pass # avoid issue with win/mac
    asyncio.run(test_register())
