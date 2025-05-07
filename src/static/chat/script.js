document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const chatWindow = document.getElementById('chat-window');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    // API endpoint
    const API_URL = '/api/v1/nlp/index/answer/';
    
    // Default project ID (since we removed the selector)
    const DEFAULT_PROJECT_ID = 'collection_1';

    // Event listeners
    sendButton.addEventListener('click', handleUserInput);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleUserInput();
        }
    });

    // Handle user input
    function handleUserInput() {
        const message = userInput.value.trim();
        if (message === '') return;

        // Add user message to chat (note: swap user/bot for RTL)
        appendMessage(message, 'user');
        
        // Clear input field
        userInput.value = '';
        
        // Show typing indicator
        showTypingIndicator();
        
        // Use default project ID
        const projectId = DEFAULT_PROJECT_ID;
        
        // Call RAG API
        fetchAnswer(message, projectId);
    }

    // Append message to chat window
    function appendMessage(message, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender === 'user' ? 'user-message' : 'bot-message');
        
        const messageContent = document.createElement('div');
        messageContent.classList.add('message-content');
        messageContent.textContent = message;
        
        messageDiv.appendChild(messageContent);
        chatWindow.appendChild(messageDiv);
        
        // Scroll to bottom
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    // Show typing indicator
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.classList.add('typing-indicator');
        typingDiv.id = 'typing-indicator';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.classList.add('typing-dot');
            typingDiv.appendChild(dot);
        }
        
        chatWindow.appendChild(typingDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    // Remove typing indicator
    function removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    // Fetch answer from RAG API
    async function fetchAnswer(question, projectId) {
        try {
            const response = await fetch(API_URL + projectId, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: question,
                    limit: 5
                }),
            });

            if (!response.ok) {
                throw new Error('API request failed');
            }

            const data = await response.json();
            
            // Remove typing indicator
            removeTypingIndicator();
            
            // Display bot response
            if (data.signal === 'rag_answer_success') {
                appendMessage(data.answer, 'bot');
            } else {
                appendMessage("عذراً، لم أتمكن من العثور على إجابة لسؤالك.", 'bot');
            }
        } catch (error) {
            console.error('Error:', error);
            
            // Remove typing indicator
            removeTypingIndicator();
            
            // Display error message
            appendMessage("عذراً، حدث خطأ أثناء معالجة طلبك.", 'bot');
        }
    }
});