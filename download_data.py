from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from dotenv import load_dotenv, dotenv_values
import os
import socket
import subprocess
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

# Import contacts helpers from send_whatsapp
from send_whatsapp import CONTACTS, read_contacts_file, send_whatsapp_message

# Load environment variables from .env file
load_dotenv()
env_vars = dotenv_values(".env")

def getAdminContacts():
    """Load admin contacts from contacts.xlsx when needed."""
    if not CONTACTS:
        CONTACTS.extend(read_contacts_file())

    return [c for c in CONTACTS if c.get("type") == "admin"]

def send_admin_notification(message, label):
    """Send a WhatsApp notification to all admin contacts."""
    try:
        admin_contacts = getAdminContacts()

        if not admin_contacts:
            print("No admin contacts to notify")
            return

        print(f"\nSending {label} notification to {len(admin_contacts)} admin(s)...")
        print("=" * 80)

        for contact in admin_contacts:
            phone = contact["phone"]
            name = contact["name"]

            try:
                if send_whatsapp_message(phone, message):
                    print(f"✓ Notified {name} ({phone})")
                else:
                    print(f"✗ Failed to notify {name} ({phone})")
            except Exception as e:
                print(f"✗ Error notifying {name} ({phone}): {str(e)}")

            time.sleep(1)

        print("=" * 80)
    except Exception as e:
        print(f"Error sending {label} notification: {str(e)}")

def send_error_notification(error_message):
    """Send error notification to admin contacts"""
    message = f"❌ Error: Gagal mengunduh data survei.\n\nError: {error_message}"
    send_admin_notification(message, "error")

def send_success_notification(record_count, filename="api_response.xlsx"):
    """Send success notification to admin contacts."""
    filepath = os.path.join(RESULT_FOLDER, filename)
    message = (
        "✅ Success: Data survei berhasil diunduh.\n\n"
        f"Jumlah data: {record_count}\n"
        f"File: {filepath}"
    )
    send_admin_notification(message, "success")

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
        return True
    except NoSuchElementException:
        print("ERROR: Button with the specified XPath not found!")
        return False
    except Exception as e:
        print(f"ERROR: Failed to click button - {str(e)}")
        return False

def loginUiIsPresent(driver):
    """Check whether the page is currently showing the SSO button or login form."""
    sso_button_xpath = "/html/body/div/div[1]/div/div/div/div/span/form/div/div[4]/button"
    username_xpath = "/html/body/div/div[2]/div/div/div/div/form/div[1]/input"

    for xpath in (sso_button_xpath, username_xpath):
        try:
            driver.find_element(By.XPATH, xpath)
            return True
        except NoSuchElementException:
            continue

    return False

def completeLoginIfNeeded(driver):
    """Run the SSO/login flow when the launcher still shows login UI."""
    if not loginUiIsPresent(driver):
        print("Login UI not detected. Assuming session is already authenticated.")
        return True

    clickLoginSsoButton(driver)
    if not fillAndSubmitLoginForm(driver):
        return False

    return waitForPageLoadAfterLogin(driver)

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

def is_debug_port_open(port):
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=1):
            return True
    except Exception:
        return False

def startEdgeDebugSession(port):
    """Start Edge with remote debugging enabled using the configured profile directory."""
    edge_path = env_vars.get("EDGE_PATH") or r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    user_data_dir = env_vars.get("EDGE_USER_DATA_DIR") or r"C:\edge-dev-profile"

    if not os.path.exists(edge_path):
        print(f"ERROR: EDGE_PATH not found: {edge_path}")
        return False

    command = [
        edge_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
    ]

    try:
        print(f"Starting Edge debug session on port {port}...")
        subprocess.Popen(command)
        for _ in range(30):
            if is_debug_port_open(port):
                print("Edge debug port is ready.")
                time.sleep(2)
                return True
            time.sleep(1)
    except Exception as e:
        print(f"ERROR: Failed to start Edge debug session - {str(e)}")

    print(f"ERROR: Edge debug port {port} did not open in time")
    return False

def createDriver():
    """Create Edge driver, preferring an existing Edge session when configured."""
    use_existing_browser = str(env_vars.get("USE_EXISTING_BROWSER", "true")).lower() in ("1", "true", "yes")
    auto_start_edge = str(env_vars.get("AUTO_START_EDGE_DEBUG", "true")).lower() in ("1", "true", "yes")
    allow_fresh_browser_fallback = str(env_vars.get("USE_FRESH_BROWSER_FALLBACK", "false")).lower() in ("1", "true", "yes")
    debug_port = str(env_vars.get("EDGE_DEBUG_PORT", env_vars.get("CHROME_DEBUG_PORT", "9222")))
    driver_path = env_vars.get("EDGE_DRIVER_PATH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "msedgedriver.exe")

    if not os.path.exists(driver_path):
        raise RuntimeError(f"EdgeDriver not found: {driver_path}")

    service = Service(driver_path)

    if use_existing_browser:
        if auto_start_edge and not is_debug_port_open(debug_port):
            if not startEdgeDebugSession(debug_port):
                if not allow_fresh_browser_fallback:
                    raise RuntimeError(
                        f"Could not start Edge debug session on port {debug_port}. "
                        "Open Edge manually with remote debugging or verify EDGE_PATH and EDGE_USER_DATA_DIR."
                    )

        if is_debug_port_open(debug_port):
            options = Options()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
            driver = webdriver.Edge(service=service, options=options)
            print(f"Connected to existing Edge session at 127.0.0.1:{debug_port}")
            return driver, True

        if not allow_fresh_browser_fallback:
            raise RuntimeError(
                f"Could not attach to existing Edge at 127.0.0.1:{debug_port}. "
                "Set USE_FRESH_BROWSER_FALLBACK=true only if you intentionally want a fresh automated browser."
            )

    print("Starting a fresh Edge browser instance.")
    return webdriver.Edge(service=service), False

def getAuthTokenFromBrowser(driver):
        """Try to locate an auth token in localStorage or sessionStorage."""
        script = """
const storages = [window.localStorage, window.sessionStorage];
const tokenHints = ['token', 'access', 'auth', 'jwt', 'bearer'];

function looksLikeJwt(value) {
    return typeof value === 'string' && value.split('.').length === 3;
}

function searchValue(value) {
    if (typeof value === 'string') {
        const trimmed = value.trim();
        if (!trimmed) {
            return null;
        }

        if (trimmed.startsWith('Bearer ')) {
            return trimmed;
        }

        if (looksLikeJwt(trimmed)) {
            return trimmed;
        }

        try {
            return searchValue(JSON.parse(trimmed));
        } catch (e) {
            return null;
        }
    }

    if (Array.isArray(value)) {
        for (const item of value) {
            const found = searchValue(item);
            if (found) {
                return found;
            }
        }
        return null;
    }

    if (value && typeof value === 'object') {
        for (const [key, nestedValue] of Object.entries(value)) {
            const loweredKey = key.toLowerCase();
            if (tokenHints.some((hint) => loweredKey.includes(hint))) {
                const found = searchValue(nestedValue);
                if (found) {
                    return found;
                }
            }
        }

        for (const nestedValue of Object.values(value)) {
            const found = searchValue(nestedValue);
            if (found) {
                return found;
            }
        }
    }

    return null;
}

for (const storage of storages) {
    for (let index = 0; index < storage.length; index++) {
        const key = storage.key(index);
        const value = storage.getItem(key);
        const loweredKey = (key || '').toLowerCase();

        if (tokenHints.some((hint) => loweredKey.includes(hint))) {
            const found = searchValue(value);
            if (found) {
                return { key, token: found };
            }
        }

        const nested = searchValue(value);
        if (nested) {
            return { key, token: nested };
        }
    }
}

return null;
"""

        try:
                token_info = driver.execute_script(script)
                if token_info and token_info.get("token"):
                        print(f"Found auth token in browser storage key: {token_info.get('key')}")
                        return token_info.get("token")
        except Exception as e:
                print(f"WARNING: Could not inspect browser storage for auth token - {str(e)}")

        return None

def fetchApiInBrowser(driver, target_url, auth_token=None):
    """Call the API from inside the browser context so existing session/auth state is preserved."""
    script = """
const targetUrl = arguments[0];
const authToken = arguments[1];
const callback = arguments[arguments.length - 1];

const headers = {
    'Accept': 'application/json, text/plain, */*'
};

if (authToken) {
    headers['Authorization'] = authToken.startsWith('Bearer ') ? authToken : `Bearer ${authToken}`;
}

fetch(targetUrl, {
    method: 'GET',
    credentials: 'include',
    headers
}).then(async (response) => {
    const text = await response.text();
    callback({
        ok: response.ok,
        status: response.status,
        text
    });
}).catch((error) => {
    callback({
        ok: false,
        error: String(error)
    });
});
"""

    try:
        result = driver.execute_async_script(script, target_url, auth_token)
        if result.get("error"):
            print(f"ERROR: Browser fetch failed - {result['error']}")
            return []

        print(f"Browser API status: {result.get('status')}")
        if not result.get("ok"):
            return []

        return [{
            "url": target_url,
            "method": "GET",
            "response": json.loads(result.get("text", "{}")),
        }]
    except Exception as e:
        print(f"ERROR: Failed to fetch API in browser context - {str(e)}")
        return []

def captureDataWithBrowserSession(driver, target_url):
    """Fetch API response using cookies from the active browser session."""
    try:
        auth_token = getAuthTokenFromBrowser(driver)
        browser_captured_data = fetchApiInBrowser(driver, target_url, auth_token=auth_token)
        if browser_captured_data:
            return browser_captured_data

        session = requests.Session()

        for cookie in driver.get_cookies():
            session.cookies.set(
                cookie.get("name"),
                cookie.get("value"),
                domain=cookie.get("domain"),
                path=cookie.get("path", "/")
            )

        headers = {
            "User-Agent": driver.execute_script("return navigator.userAgent;"),
            "Accept": "application/json, text/plain, */*",
            "Referer": driver.current_url,
        }

        if auth_token:
            headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"

        response = session.get(target_url, headers=headers, timeout=20)
        print(f"Session API status: {response.status_code}")
        response.raise_for_status()

        return [{
            "url": target_url,
            "method": "GET",
            "response": response.json(),
        }]
    except Exception as e:
        print(f"ERROR: Failed to fetch API via browser session - {str(e)}")
        return []

def waitForApiSessionReady(driver, target_url, timeout_seconds=180, interval_seconds=5):
    """Wait until the attached browser session is authenticated and API data is available."""
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        captured_data = captureDataWithBrowserSession(driver, target_url)
        if captured_data and captured_data[0].get("response"):
            print("Authenticated Edge session is ready.")
            return captured_data

        elapsed = int(time.time() - start_time)
        print(f"Session not ready yet ({elapsed}s). Retrying in {interval_seconds}s...")
        time.sleep(interval_seconds)

    print(f"ERROR: Session did not become ready within {timeout_seconds} seconds")
    return []

driver = None
is_existing_browser = False

try:
    driver, is_existing_browser = createDriver()
except Exception as startup_error:
    print(f"\n✗ STARTUP ERROR: {str(startup_error)}")
    send_error_notification(str(startup_error))
    sys.exit(1)

# Maximize only when opening a fresh browser instance
if not is_existing_browser:
    driver.maximize_window()

try:
    # Open a website
    url = "https://manajemen-mitra.bps.go.id/launcher"
    print(f"Opening {url}...")
    driver.get(url)
    
    # Wait for the page to load
    time.sleep(3)

    is_interactive = sys.stdin.isatty()
    require_manual_login = str(env_vars.get("REQUIRE_MANUAL_LOGIN_CONFIRM", "false")).lower() in ("1", "true", "yes")

    if is_existing_browser:
        print("Using existing Edge browser session.")
        if require_manual_login and is_interactive:
            print("Please complete login manually if needed, then press Enter to continue...")
            input()
        else:
            completeLoginIfNeeded(driver)
    else:
        completeLoginIfNeeded(driver)
    
    # Fetch the API using the browser's authenticated session
    api_url = "https://mitra-api.bps.go.id/api/dashboard/kegiatan-aktif"
    if is_existing_browser and not require_manual_login:
        wait_timeout = int(env_vars.get("SESSION_READY_TIMEOUT", "180"))
        retry_interval = int(env_vars.get("SESSION_RETRY_INTERVAL", "5"))
        captured_data = waitForApiSessionReady(
            driver,
            api_url,
            timeout_seconds=wait_timeout,
            interval_seconds=retry_interval
        )
    else:
        captured_data = captureDataWithBrowserSession(driver, api_url)
    
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
        if not saveResponseToExcel(captured_data):
            raise RuntimeError("Failed to save API response to Excel")

        record_count = len(captured_data[0]["response"].get("data", []))
        send_success_notification(record_count)
    else:
        raise RuntimeError("No data captured from the API")
    
    # Keep the browser open for 5 seconds before closing
    time.sleep(5)
    
except Exception as error:
    print(f"\n✗ FATAL ERROR: {str(error)}")
    send_error_notification(str(error))
    
finally:
    if driver is None:
        print("Browser was not started.")
    elif is_existing_browser:
        print("Attached Edge browser was not closed.")
    else:
        driver.quit()
        print("Browser closed.")
