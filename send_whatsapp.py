import pandas as pd
import requests
import time
import os
import sys
from datetime import datetime, timedelta

# Create result folder if it doesn't exist
RESULT_FOLDER = "result"
if not os.path.exists(RESULT_FOLDER):
    os.makedirs(RESULT_FOLDER)

# WPPConnect API endpoint
WPPCONNECT_URL = "http://localhost:21465/api/sendMessage"

# Hardcoded contacts
CONTACTS = [
    # {"phone": "6282379883130", "name": "Ali", "type": "user"},
    {"phone": "6282236981385", "name": "Indra", "type": "admin"},
    # {"phone": "6281331890887", "name": "Sani", "type": "admin"},
]

# Debug mode: set to a specific date to test (e.g., "2024-01-15") or None for today
DEBUG_DATE = "2025-01-01"

# Reminder settings
ENABLE_INITIAL_REMINDER = False  # Enable/disable initial reminder (surveys starting today)
FINAL_REMINDER_DAYS = [7, 3]  # Send reminder when 7 days or 3 days to go

def get_today_date():
    """
    Get today's date for reminders
    Set DEBUG_DATE to a specific date string (YYYY-MM-DD) for testing
    """
    if DEBUG_DATE:
        try:
            parsed_date = datetime.strptime(DEBUG_DATE, "%Y-%m-%d").date()
            print(f"[DEBUG MODE] Using date: {parsed_date} (not today)")
            return parsed_date
        except ValueError:
            print(f"ERROR: Invalid DEBUG_DATE format. Use YYYY-MM-DD format.")
            sys.exit(1)
    
    return datetime.now().date()

def read_excel_file(filename="api_response.xlsx"):
    """Read the Excel file and return DataFrame"""
    try:
        filepath = os.path.join(RESULT_FOLDER, filename)
        df = pd.read_excel(filepath)
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

def get_initial_reminder_message(df):
    """
    Get initial reminder message based on today's date matching tgl_rek_mulai
    Returns the message and list of kd_survei
    """
    try:
        # Get today's date (with debug support)
        today = get_today_date()
        print(f"Today's date: {today}")
        
        # Filter rows where tgl_rek_mulai matches today
        # Convert tgl_rek_mulai column to date format (remove time if present)
        df['tgl_rek_mulai'] = pd.to_datetime(df['tgl_rek_mulai']).dt.date
        
        matching_rows = df[df['tgl_rek_mulai'] == today]
        
        if matching_rows.empty:
            print("No reminders for today")
            return None, []
        
        # Get unique kd_survei
        kd_survei_list = matching_rows['kd_survei'].unique().tolist()
        print(f"Found {len(kd_survei_list)} unique kd_survei: {kd_survei_list}")
        
        # Build message
        message = "Hari ini sudah mulai rekrutmen untuk survei berikut:\n"
        for idx, kd in enumerate(kd_survei_list, 1):
            message += f"{idx}. {kd}\n"
        
        return message.strip(), kd_survei_list
    
    except Exception as e:
        print(f"ERROR: Failed to get initial reminder message - {str(e)}")
        return None, []

def send_initial_reminder(df):
    """
    Send initial reminder message for surveys starting today
    """
    # Get initial reminder message based on today's date
    message, kd_survei_list = get_initial_reminder_message(df)
    
    if message is None or not kd_survei_list:
        print("No initial reminders to send today")
        return []
    
    print(f"\nInitial Reminder message:\n{message}\n")
    
    # Send messages
    results = send_messages_to_contacts(message)
    
    return results

def get_final_reminder_message(df):
    """
    Get final reminder message for surveys ending soon
    Returns list of (message, kd_survei_list) tuples for each reminder day
    """
    try:
        today = get_today_date()
        print(f"\nToday's date: {today}")
        
        # Convert tgl_rek_selesai column to date format
        df['tgl_rek_selesai'] = pd.to_datetime(df['tgl_rek_selesai']).dt.date
        
        reminders = []
        
        for days_to_go in FINAL_REMINDER_DAYS:
            # Calculate the date that is days_to_go days away
            target_date = today + timedelta(days=days_to_go)
            
            matching_rows = df[df['tgl_rek_selesai'] == target_date]
            
            if matching_rows.empty:
                continue
            
            # Get unique kd_survei
            kd_survei_list = matching_rows['kd_survei'].unique().tolist()
            print(f"Found {len(kd_survei_list)} unique kd_survei ending in {days_to_go} days: {kd_survei_list}")
            
            # Build message
            message = f"✅ Pengingat! ✅\nSurvei berikut akan selesai pada {target_date} ({days_to_go} hari lagi):\n"
            for idx, kd in enumerate(kd_survei_list, 1):
                message += f"{idx}. {kd}\n"
            message += "\nJangan lupa melakukan penawaran kerja ke mitra ya 🫰🏻"
            
            reminders.append((message.strip(), kd_survei_list))
            
        return reminders
    
    except Exception as e:
        print(f"ERROR: Failed to get final reminder message - {str(e)}")
        return []

def send_final_reminder(df):
    """
    Send final reminder messages for surveys ending soon
    """
    reminders = get_final_reminder_message(df)
    
    if not reminders:
        print("No final reminders to send today")
        return []
    
    all_results = []
    
    for message, kd_survei_list in reminders:
        print(f"\nFinal Reminder message:\n{message}\n")
        
        # Send messages
        results = send_messages_to_contacts(message)
        all_results.extend(results)
    
    return all_results

def send_no_reminder_notification():
    """
    Send notification to admin contacts when there are no reminders for today
    """
    results = []
    
    # Filter admin contacts
    admin_contacts = [c for c in CONTACTS if c.get("type") == "admin"]
    
    if not admin_contacts:
        print("No admin contacts to notify")
        return results
    
    message = "ℹ️ Info: Tidak ada pengingat survei untuk hari ini."
    
    print(f"\nNo reminders for today. Notifying {len(admin_contacts)} admin(s)...")
    print("=" * 80)
    
    for contact in admin_contacts:
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
        
        time.sleep(1)
    
    print("=" * 80)
    return results

def save_results(results, filename="whatsapp_results.xlsx"):
    """Save results to Excel file"""
    try:
        df = pd.DataFrame(results)
        filepath = os.path.join(RESULT_FOLDER, filename)
        df.to_excel(filepath, index=False, sheet_name='Results')
        print(f"\nResults saved to {filepath}")
    except Exception as e:
        print(f"ERROR: Failed to save results - {str(e)}")

def main():
    """Main function"""
    # Read Excel file
    df = read_excel_file()
    if df is None:
        return
    
    all_results = []
    
    # Send initial reminder messages (if enabled)
    if ENABLE_INITIAL_REMINDER:
        initial_results = send_initial_reminder(df)
        all_results.extend(initial_results)
    
    # Send final reminder messages
    final_results = send_final_reminder(df)
    all_results.extend(final_results)
    
    # If no reminders were sent, notify admins
    if not all_results:
        print("\nNo reminders to send today")
        no_reminder_results = send_no_reminder_notification()
        all_results.extend(no_reminder_results)
    
    if not all_results:
        print("No messages sent today")
        return
    
    # Save results
    save_results(all_results)
    
    # Print summary
    successful = sum(1 for r in all_results if r["status"] == "Sent")
    failed = sum(1 for r in all_results if r["status"] == "Failed")
    print(f"\nSummary: {successful} sent, {failed} failed")

if __name__ == "__main__":
    main()