const wppconnect = require('@wppconnect-team/wppconnect');
const express = require('express');
const app = express();

app.use(express.json());

let client;

// Initialize WhatsApp connection
wppconnect
  .create({
    session: 'bot',
    headless: true,
    devtools: false,
    useChrome: true,
  })
  .then((cli) => {
    client = cli;
    console.log('\n✓ WhatsApp connected!');
    console.log('Ready to send messages...\n');
  })
  .catch((error) => {
    console.error('✗ Failed to connect WhatsApp:', error);
  });

// Health check endpoint
app.get('/api/health', (req, res) => {
  if (client) {
    res.json({ status: 'connected' });
  } else {
    res.status(503).json({ status: 'disconnected' });
  }
});

// Send message endpoint
app.post('/api/sendMessage', async (req, res) => {
  try {
    const { phone, message } = req.body;

    if (!phone || !message) {
      return res.status(400).json({
        success: false,
        error: 'phone and message are required'
      });
    }

    if (!client) {
      return res.status(503).json({
        success: false,
        error: 'WhatsApp client not connected'
      });
    }

    // Format phone number (add @c.us for WhatsApp)
    const formattedPhone = phone.includes('@') ? phone : phone + '@c.us';

    await client.sendText(formattedPhone, message);

    res.json({
      success: true,
      message: 'Message sent successfully',
      phone: phone,
      sentAt: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error sending message:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Start server
const PORT = 21465;
app.listen(PORT, () => {
  console.log(`\n${'='.repeat(50)}`);
  console.log(`WPPConnect server running on http://localhost:${PORT}`);
  console.log(`${'='.repeat(50)}\n`);
  console.log('Waiting for WhatsApp connection...');
  console.log('If no QR code appears, check if browser opened.\n');
});

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\nShutting down...');
  if (client) {
    await client.close();
  }
  process.exit(0);
});
