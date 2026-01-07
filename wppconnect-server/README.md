# WPPConnect Server Setup

This folder contains the WhatsApp server for the BPS reminder system.

## Installation Steps

### 1. Install Node.js
Download from: https://nodejs.org/ (LTS version recommended)

### 2. Install dependencies
Open PowerShell in this folder and run:
```powershell
npm install
```

### 3. Run the server
```powershell
npm start
```

Or simply:
```powershell
node server.js
```

## First Run
- A browser window will open with a QR code
- Scan the QR code with your phone's WhatsApp camera
- Once scanned successfully, the message "✓ WhatsApp connected!" will appear
- The server is now ready to send messages

## API Endpoints

### Send Message
- **URL:** `http://localhost:21465/api/sendMessage`
- **Method:** POST
- **Body:**
  ```json
  {
    "phone": "6281234567890",
    "message": "Your message here"
  }
  ```

### Health Check
- **URL:** `http://localhost:21465/api/health`
- **Method:** GET

## Troubleshooting

If the QR code doesn't appear:
- Make sure Chrome/Chromium is installed
- Check if a browser window opened (might be minimized)
- Try restarting the server

If messages aren't sending:
- Verify the phone number format (should start with country code, no + or spaces)
- Check if WhatsApp is connected (look for "✓ WhatsApp connected!" message)
- Make sure the server is running on port 21465
