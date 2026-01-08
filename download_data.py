from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from dotenv import load_dotenv, dotenv_values
import os
import sys
import time
import json
import gzip
import pandas as pd
import requests

# Add parent directory to path to import send_whatsapp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Create result folder if it doesn't exist
RESULT_FOLDER = "result"
if not os.path.exists(RESULT_FOLDER):
    os.makedirs(RESULT_FOLDER)

# WPPConnect API endpoint for sending messages
WPPCONNECT_URL = "http://localhost:21465/api/sendMessage"

# Import contacts from send_whatsapp
from send_whatsapp import CONTACTS

# Load environment variables from .env file
load_dotenv()
env_vars = dotenv_values(".env")

def send_error_notification(error_message):
    """Send error notification to admin contacts"""
    try:
        # Filter admin contacts
        admin_contacts = [c for c in CONTACTS if c.get("type") == "admin"]
        
        if not admin_contacts:
            print("No admin contacts to notify")
            return
        
        message = f"❌ Error: Gagal mengunduh data survei.\n\nError: {error_message}"
        
        print(f"\nSending error notification to {len(admin_contacts)} admin(s)...")
        print("=" * 80)
        
        for contact in admin_contacts:
            phone = contact["phone"]
            name = contact["name"]
            
            try:
                payload = {
                    "phone": phone,
                    "message": message
                }
                response = requests.post(WPPCONNECT_URL, json=payload, timeout=5)
                if response.status_code == 200:
                    print(f"✓ Notified {name} ({phone})")
                else:
                    print(f"✗ Failed to notify {name} ({phone})")
            except Exception as e:
                print(f"✗ Error notifying {name} ({phone}): {str(e)}")
            
            time.sleep(1)
        
        print("=" * 80)
    except Exception as e:
        print(f"Error sending notification: {str(e)}")

def getCredentialsFromEnv():
    """Get username and password from .env file"""
    username = env_vars.get('username')
    password = env_vars.get('password')
    if not username or not password:
        print("ERROR: username or password not found in .env file!")
        return None, None
    return username, password

def fillAndSubmitLoginForm(driver):
    """Fill the login form and submit it"""
    try:
        # Wait for the login form to appear
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div[2]/div/div/div/div/form/div[1]/input")))
        print("Login form loaded!")
        
        # Get credentials from .env
        username, password = getCredentialsFromEnv()
        if not username or not password:
            return False
        
        # Fill username field
        username_field = driver.find_element(By.XPATH, "/html/body/div/div[2]/div/div/div/div/form/div[1]/input")
        username_field.clear()
        username_field.send_keys(username)
        print(f"Username filled: {username}")
        
        # Fill password field
        password_field = driver.find_element(By.XPATH, "/html/body/div/div[2]/div/div/div/div/form/div[2]/input")
        password_field.clear()
        password_field.send_keys(password)
        print("Password filled!")
        
        # Submit the login form
        submit_button = driver.find_element(By.XPATH, "/html/body/div/div[2]/div/div/div/div/form/div[4]/input[2]")
        submit_button.click()
        print("Login form submitted!")
        return True
        
    except TimeoutException:
        print("ERROR: Login form did not appear within 10 seconds!")
        return False
    except NoSuchElementException:
        print("ERROR: One or more login form elements not found!")
        return False
    except Exception as e:
        print(f"ERROR: Failed to fill and submit login form - {str(e)}")
        return False

def clickLoginSsoButton(driver):
    """Click the login SSO button"""
    try:
        button = driver.find_element(By.XPATH, "/html/body/div/div[1]/div/div/div/div/span/form/div/div[4]/button")
        button.click()
        print("Button clicked!")
    except NoSuchElementException:
        print("ERROR: Button with the specified XPath not found!")
    except Exception as e:
        print(f"ERROR: Failed to click button - {str(e)}")

def waitForPageLoadAfterLogin(driver):
    """Wait for the page to load successfully after login"""
    try:
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div[1]/div[1]/div[1]/div[1]/div/h1/a/img")))
        print("Page loaded successfully!")
        return True
    except TimeoutException:
        print("ERROR: Page did not load within 10 seconds!")
        return False
    except Exception as e:
        print(f"ERROR: Failed to wait for page load - {str(e)}")
        return False

def captureNetworkRequest(driver, target_url):
    """Capture network requests matching the target URL"""
    try:
        matched_requests = []
        
        # Get all requests from the driver's request history
        # This requires selenium-wire to intercept network traffic
        for request in driver.requests:
            if target_url in request.url:
                print(f"Request URL: {request.url}")
                print(f"Request Method: {request.method}")
                
                # Try to get response body if available
                try:
                    if request.response is None:
                        print("ERROR: Response is None")
                        continue
                    
                    print(f"Response Status: {request.response.status_code}")
                    
                    response_body = request.response.body
                    
                    # Check if the response is gzip-compressed
                    if response_body.startswith(b'\x1f\x8b'):
                        response_text = gzip.decompress(response_body).decode('utf-8')
                    elif isinstance(response_body, bytes):
                        response_text = response_body.decode('utf-8')
                    else:
                        response_text = str(response_body)
                    
                    response_data = json.loads(response_text)
                    matched_requests.append({
                        'url': request.url,
                        'method': request.method,
                        'response': response_data
                    })
                except json.JSONDecodeError as e:
                    print(f"ERROR: Failed to parse JSON - {str(e)}")
                except gzip.BadGzipFile as e:
                    print(f"ERROR: Failed to decompress gzip - {str(e)}")
                except Exception as e:
                    print(f"ERROR: Could not parse response body - {str(e)}")
                    matched_requests.append({
                        'url': request.url,
                        'method': request.method,
                        'response': None
                    })
        
        if matched_requests:
            print(f"\nCaptured {len(matched_requests)} request(s) matching {target_url}")
            return matched_requests
        else:
            print(f"No requests found matching {target_url}")
            return []
            
    except AttributeError:
        print("ERROR: selenium-wire not installed! Install it with: pip install selenium-wire")
        return []
    except Exception as e:
        print(f"ERROR: Failed to capture network requests - {str(e)}")
        return []

def saveResponseToExcel(captured_data, filename="api_response.xlsx"):
    """Save the captured API response data to an Excel file"""
    try:
        if not captured_data:
            print("ERROR: captured_data is empty")
            return False
        
        if not captured_data[0].get('response'):
            print("ERROR: No valid response data to save")
            return False
        
        # Extract the response
        response = captured_data[0]['response']
        
        # Check if 'data' key exists
        if 'data' not in response:
            print(f"ERROR: 'data' key not found in response. Available keys: {list(response.keys())}")
            return False
        
        data_list = response['data']
        
        if not data_list:
            print("ERROR: data_list is empty")
            return False
        
        # Convert to DataFrame
        df = pd.DataFrame(data_list)
        
        # Save to Excel in result folder
        filepath = os.path.join(RESULT_FOLDER, filename)
        df.to_excel(filepath, index=False, sheet_name='Data')
        print(f"Data saved to {filepath} successfully!")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to save to Excel - {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# Create a Chrome driver instance
# Note: Make sure you have ChromeDriver installed and in your PATH
# Download from: https://chromedriver.chromium.org/
# For network request capture, this uses selenium-wire
# Install with: pip install selenium-wire
try:
    from seleniumwire import webdriver as wire_webdriver
    driver = wire_webdriver.Chrome()
except ImportError:
    print("WARNING: selenium-wire not installed. Using regular webdriver without request capture.")
    print("Install with: pip install selenium-wire")
    driver = webdriver.Chrome()

# Maximize the window
driver.maximize_window()

try:
    # Open a website
    url = "https://manajemen-mitra.bps.go.id/launcher"
    print(f"Opening {url}...")
    driver.get(url)
    
    # Wait for the page to load
    time.sleep(3)
    

    # Click the login SSO button
    clickLoginSsoButton(driver)
    
    # Fill and submit the login form
    fillAndSubmitLoginForm(driver)
    
    # Wait for the page to load successfully after login
    waitForPageLoadAfterLogin(driver)
    
    # Capture network requests matching the API endpoint
    api_url = "https://mitra-api.bps.go.id/api/dashboard/kegiatan-aktif"
    captured_data = captureNetworkRequest(driver, api_url)
    
    # Print the captured response data
    if captured_data:
        print("\n" + "="*80)
        print("CAPTURED API RESPONSE")
        print("="*80)
        for idx, data in enumerate(captured_data):
            print(f"\nRequest #{idx + 1}:")
            print(f"URL: {data['url']}")
            if data['response']:
                print(f"Response:\n{json.dumps(data['response'], indent=2)}")
            else:
                print("Response: Could not parse response data")
        print("="*80 + "\n")
        
        # Save the response data to Excel
        saveResponseToExcel(captured_data)
    
    # Keep the browser open for 5 seconds before closing
    time.sleep(5)
    
except Exception as error:
    print(f"\n✗ FATAL ERROR: {str(error)}")
    send_error_notification(str(error))
    
finally:
    # Close the browser
    driver.quit()
    print("Browser closed.")
