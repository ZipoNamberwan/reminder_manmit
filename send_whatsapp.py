import pandas as pd
import requests
import time

# Hardcoded contacts
CONTACTS = [
    {"phone": "6281234567890", "name": "John"},
    {"phone": "6289876543210", "name": "Jane"},
]

# WPPConnect API endpoint
WPPCONNECT_URL = "http://localhost:21465/api/sendMessage"

def read_excel_file(filename="api_response.xlsx"):
    """Read the Excel file and return DataFrame"""
    try:
        df = pd.read_excel(filename)
        print(f"Excel file loaded: {len(df)} rows")
        return df
    except Exception as e:
        print(f"ERROR: Failed to read Excel file - {str(e)}")
        return None

def send_whatsapp_message(phone, message):
    """Send WhatsApp message using WPPConnect"""
    try:
        payload = {
            "phone": phone,
            "message": message
        }
        response = requests.post(WPPCONNECT_URL, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: Failed to send message to {phone} - {str(e)}")
        return False

def send_messages_to_contacts(message):
    """Send message to all contacts"""
    results = []
    
    print(f"\nSending messages to {len(CONTACTS)} contacts...")
    print("=" * 80)
    
    for contact in CONTACTS:
        phone = contact["phone"]
        name = contact["name"]
        
        print(f"Sending to {name} ({phone})...", end=" ")
        
        success = send_whatsapp_message(phone, message)
        
        if success:
            print("✓ Sent")
            results.append({
                "phone": phone,
                "name": name,
                "status": "Sent",
                "message": message
            })
        else:
            print("✗ Failed")
            results.append({
                "phone": phone,
                "name": name,
                "status": "Failed",
                "message": message
            })
        
        # Small delay between messages
        time.sleep(1)
    
    print("=" * 80)
    return results

def save_results(results, filename="whatsapp_results.xlsx"):
    """Save results to Excel file"""
    try:
        df = pd.DataFrame(results)
        df.to_excel(filename, index=False, sheet_name='Results')
        print(f"\nResults saved to {filename}")
    except Exception as e:
        print(f"ERROR: Failed to save results - {str(e)}")

def main():
    """Main function"""
    # Read Excel file
    df = read_excel_file()
    if df is None:
        return
    
    # Simple message (can be customized later)
    message = "Hello! This is a test message from BPS."
    
    # Send messages
    results = send_messages_to_contacts(message)
    
    # Save results
    save_results(results)
    
    # Print summary
    successful = sum(1 for r in results if r["status"] == "Sent")
    failed = sum(1 for r in results if r["status"] == "Failed")
    print(f"\nSummary: {successful} sent, {failed} failed")

if __name__ == "__main__":
    main()
