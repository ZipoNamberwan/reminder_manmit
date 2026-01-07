# BPS Reminder System - Docker Setup

## Quick Start

### Prerequisites
- Docker installed ([Download Docker](https://www.docker.com/products/docker-desktop))
- `.env` file in the root directory with credentials

### Running Everything

```bash
# Build and start all services
docker-compose up --build

# Or just start (if already built)
docker-compose up

# Run in background
docker-compose up -d
```

### Services

1. **WPPConnect Server** (Port 21465)
   - WhatsApp service
   - Will show QR code on first run
   - Health check at: `http://localhost:21465/api/health`

2. **Python Scraper**
   - Downloads data from the website
   - Saves to `api_response.xlsx`
   - Sends WhatsApp messages via WPPConnect
   - Saves results to `whatsapp_results.xlsx`

## Running Specific Scripts

### Just scrape data (download_data.py)
```bash
docker-compose run --rm python-app python download_data.py
```

### Just send WhatsApp (send_whatsapp.py)
```bash
docker-compose run --rm python-app python send_whatsapp.py
```

### Interactive mode
```bash
docker-compose run --rm python-app bash
```

## Stopping Services

```bash
# Stop all services
docker-compose down

# Remove volumes (careful!)
docker-compose down -v

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f wppconnect
docker-compose logs -f python-app
```

## First Time Setup

1. Start the services:
   ```bash
   docker-compose up
   ```

2. Look for WPPConnect QR code in the terminal

3. Scan with your phone's WhatsApp

4. Once connected, you can run the Python scripts

## File Locations

- `api_response.xlsx` - Downloaded data
- `whatsapp_results.xlsx` - WhatsApp sending results
- `.env` - Credentials (not included in image)
- `send_whatsapp.py` - Update CONTACTS here

## Troubleshooting

### WPPConnect not connecting
- Check browser opened with QR code
- Look at wppconnect logs: `docker-compose logs wppconnect`

### Python script can't reach WPPConnect
- Verify both containers are on same network
- Check: `docker-compose logs python-app`

### File permissions issues
- Make sure `.env` file exists
- Check folder permissions

## Modifying Code

If you change the Python scripts:
```bash
docker-compose up --build
```

If you change server.js:
```bash
docker-compose up --build wppconnect
```
