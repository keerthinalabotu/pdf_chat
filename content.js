let chatContainer = null;

function createChatInterface() {
  chatContainer = document.createElement('div');
  chatContainer.id = 'paper-chat-container';
  chatContainer.style.cssText = `
    position: fixed;
    right: 20px;
    bottom: 20px;
    width: 350px;
    height: 500px;
    background: white;
    border: 1px solid #ccc;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    display: flex;
    flex-direction: column;
    z-index: 10000;
  `;

  // Create chat header
  const header = document.createElement('div');
  header.style.cssText = `
    padding: 10px;
    background: #f5f5f5;
    border-bottom: 1px solid #ccc;
    border-radius: 8px 8px 0 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
  `;
  header.innerHTML = `
    <span style="font-weight: bold;">Paper Chat</span>
    <button id="close-chat" style="border: none; background: none; cursor: pointer;">×</button>
  `;

  // Create messages container
  const messagesContainer = document.createElement('div');
  messagesContainer.id = 'chat-messages';
  messagesContainer.style.cssText = `
    flex-grow: 1;
    overflow-y: auto;
    padding: 10px;
  `;

  // Create input container
  const inputContainer = document.createElement('div');
  inputContainer.style.cssText = `
    padding: 10px;
    border-top: 1px solid #ccc;
    display: flex;
  `;
  inputContainer.innerHTML = `
    <input type="text" id="chat-input" placeholder="Ask about the paper..." style="
      flex-grow: 1;
      padding: 8px;
      border: 1px solid #ccc;
      border-radius: 4px;
      margin-right: 8px;
    ">
    <button id="send-message" style="
      padding: 8px 16px;
      background: #007bff;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    ">Send</button>
  `;

  // Assemble the components
  chatContainer.appendChild(header);
  chatContainer.appendChild(messagesContainer);
  chatContainer.appendChild(inputContainer);
  document.body.appendChild(chatContainer);

  // Add event listeners
  document.getElementById('close-chat').addEventListener('click', () => {
    chatContainer.remove();
    chatContainer = null;
  });

  document.getElementById('send-message').addEventListener('click', sendMessage);
  document.getElementById('chat-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
  });
}

// async function sendMessage() {
//   const input = document.getElementById('chat-input');
//   const message = input.value.trim();
//   if (!message) return;

//   const messagesContainer = document.getElementById('chat-messages');
  
//   // Add user message
//   appendMessage('user', message);
//   input.value = '';

//   try {
//     // Get current URL
//     const url = window.location.href;
    
//     // Send to backend
//     const response = await fetch('http://localhost:5000/chat', {  // Replace with your backend URL
//       method: 'POST',
//       headers: {
//         'Content-Type': 'application/json',
//       },
//       body: JSON.stringify({
//         message,
//         url
//       })
//     });

//     const data = await response.json();
//     appendMessage('assistant', data.response);
//   } catch (error) {
//     appendMessage('system', 'Error: Could not get response from server');
//   }
// }
// async function sendMessage() {
//     const input = document.getElementById('chat-input');
//     const message = input.value.trim();
//     if (!message) return;
  
//     appendMessage('user', message);
//     input.value = '';
  
//     try {
//       const response = await fetch('http://localhost:8000/chat', {
//         method: 'POST',
//         headers: {
//           'Content-Type': 'application/json',
//         },
//         body: JSON.stringify({
//           message,
//           paper_id: currentPaperId  // You'll need to store this when uploading
//         })
//       });
  
//       const data = await response.json();
//       if (data.success) {
//         appendMessage('assistant', data.response);
//       } else {
//         throw new Error(data.error);
//       }
//     } catch (error) {
//       appendMessage('system', 'Error: ' + error.message);
//     }
//   }
let currentConversationId = null;

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    appendMessage('user', message);
    input.value = '';

    try {
        const response = await fetch('http://localhost:8000/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message,
                paper_id: currentPaperId,
                conversation_id: currentConversationId
            })
        });

        const data = await response.json();
        if (data.success) {
            currentConversationId = data.conversation_id;
            appendMessage('assistant', data.response);
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        appendMessage('system', 'Error: ' + error.message);
    }
}

function appendMessage(sender, text) {
  const messagesContainer = document.getElementById('chat-messages');
  const messageDiv = document.createElement('div');
  messageDiv.style.cssText = `
    margin-bottom: 10px;
    padding: 8px;
    border-radius: 4px;
    max-width: 80%;
    ${sender === 'user' ? 'margin-left: auto; background: #007bff; color: white;' : 
      sender === 'assistant' ? 'margin-right: auto; background: #f0f0f0;' : 
      'margin: 10px auto; background: #ff4444; color: white;'}
  `;
  messageDiv.textContent = text;
  messagesContainer.appendChild(messageDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Listen for messages from the popup or background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'toggleChat') {
    if (chatContainer) {
      chatContainer.remove();
      chatContainer = null;
    } else {
      createChatInterface();
    }
  }
  return true;
});