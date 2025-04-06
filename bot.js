const qrcode = require('qrcode-terminal');
const { Client, LocalAuth } = require('whatsapp-web.js');
const { GoogleGenerativeAI } = require('@google/generative-ai');

// Initialize Google Gemini AI
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

// Create a new client instance
const client = new Client({
    authStrategy: new LocalAuth()
});

// Chat history storage
const chatHistory = new Map();

// Generate QR code
client.on('qr', (qr) => {
    qrcode.generate(qr, { small: true });
    console.log('QR Code generated. Please scan with WhatsApp!');
});

// When client is ready
client.on('ready', () => {
    console.log('Client is ready!');
});

// Function to get AI response
async function getChatbotResponse(prompt) {
    try {
        const model = genAI.getGenerativeModel({ model: "gemini-pro" });
        const result = await model.generateContent(prompt);
        const response = await result.response;
        return response.text();
    } catch (error) {
        console.error('Error getting AI response:', error);
        return "Sorry, I'm having trouble responding right now. Please try again later. 🙏";
    }
}

// Listen for messages
client.on('message', async (message) => {
    if (message.body === '!ping') {
        await message.reply('pong');
        return;
    }

    if (message.body === '!clear') {
        chatHistory.delete(message.from);
        await message.reply('Chat history cleared! 🗑️');
        return;
    }

    // Handle normal chat messages
    try {
        // Get or initialize chat history
        if (!chatHistory.has(message.from)) {
            chatHistory.set(message.from, []);
        }
        const userHistory = chatHistory.get(message.from);

        // Add user message to history
        userHistory.push({ role: 'user', content: message.body });

        // Keep last 5 messages
        if (userHistory.length > 5) {
            userHistory.shift();
        }

        // Create conversation history string
        const conversationHistory = userHistory
            .map(msg => `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}`)
            .join('\n');

        // Prepare prompt with context
        const prompt = `You are a friendly and helpful assistant. Previous conversation:\n${conversationHistory}\n\nUser: ${message.body}`;

        // Get AI response
        const response = await getChatbotResponse(prompt);

        // Add response to history
        userHistory.push({ role: 'assistant', content: response });

        // Send response
        await message.reply(response);

    } catch (error) {
        console.error('Error processing message:', error);
        await message.reply('Sorry, an error occurred. Please try again later.');
    }
});

// Initialize the client
client.initialize();