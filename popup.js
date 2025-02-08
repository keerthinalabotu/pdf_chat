document.getElementById('toggleChat').addEventListener('click', async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    chrome.tabs.sendMessage(tab.id, { action: 'toggleChat' });
  });
  
  document.getElementById('analyzePaper').addEventListener('click', async () => {
    const status = document.getElementById('status');
    status.style.display = 'block';
    
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        // Send URL to backend for analysis
        const response = await fetch('http://localhost:8000/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: tab.url
            })
        });

        const data = await response.json();
        
        if (data.success) {
            // Store the paper ID for chat functionality
            currentPaperId = data.paper_id;
            
            // Update the UI with paper details
            const result = document.getElementById('result');
            result.innerHTML = `
                <h3>${data.title}</h3>
                <p>Authors: ${data.authors.join(', ')}</p>
                <p>${data.abstract}</p>
                <div class="chat-interface">
                    <input type="text" id="chatInput" placeholder="Ask a question about the paper...">
                    <button onclick="sendMessage()">Send</button>
                </div>
                <div id="chatHistory"></div>
            `;
            
            status.textContent = 'Paper analyzed successfully!';
            status.className = 'success';
        } else {
            throw new Error(data.detail || 'Analysis failed');
        }
    } catch (error) {
        status.textContent = `Error: ${error.message}`;
        status.className = 'error';
    }
  });

let currentPaperId = null;  // Store the current paper ID

document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const analyzeBtn = document.getElementById('analyzeBtn');
    const pdfInput = document.getElementById('pdfInput');
    const result = document.getElementById('result');
    const status = document.getElementById('status');

    // Debug log to confirm event listeners are attached
    console.log('DOM Content Loaded, elements found:', {
        analyzeBtn: !!analyzeBtn,
        pdfInput: !!pdfInput,
        result: !!result,
        status: !!status
    });

    // Check if elements exist before adding listeners
    if (!analyzeBtn || !pdfInput || !result || !status) {
        console.error('Required DOM elements not found:', {
            analyzeBtn: !!analyzeBtn,
            pdfInput: !!pdfInput,
            result: !!result,
            status: !!status
        });
        return;
    }

    // Handle drag and drop
    const uploadBtn = document.querySelector('.upload-btn');
    if (uploadBtn) {
        uploadBtn.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadBtn.style.background = '#e9ecef';
        });

        uploadBtn.addEventListener('dragleave', () => {
            uploadBtn.style.background = '#f8f9fa';
        });

        uploadBtn.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadBtn.style.background = '#f8f9fa';
            const file = e.dataTransfer.files[0];
            if (file && file.type === 'application/pdf') {
                pdfInput.files = e.dataTransfer.files;
            } else {
                showStatus('Please upload a PDF file', 'error');
            }
        });
    }

    analyzeBtn.addEventListener('click', async () => {
        console.log('Analyze button clicked');
        const file = pdfInput.files[0];
        if (!file) {
            showStatus('Please select a PDF file first', 'error');
            return;
        }

        const spinner = document.getElementById('spinner');
        const processingSteps = document.getElementById('processingSteps');
        spinner.style.display = 'block';
        processingSteps.style.display = 'block';
        analyzeBtn.disabled = true;

        updateStep('uploadStep', 'in-progress');

        console.log('x selected:', file.name);
        showStatus('Analyzing paper...', 'loading');
        const formData = new FormData();
        formData.append('file', file);

        try {
            console.log('Sending request to server...');
            const response = await fetch('http://localhost:8000/upload', {
                method: 'POST',
                body: formData
            });

            updateStep('uploadStep', 'completed');
            updateStep('extractStep', 'in-progress');

            console.log('Response received:', response.status);
            const data = await response.json();
            console.log('Response data:', data);

            if (data.success) {
                updateStep('extractStep', 'completed');
                updateStep('analyzeStep', 'in-progress');
                currentPaperId = data.paper_id;
                await new Promise(resolve => setTimeout(resolve, 1000));
                updateStep('analyzeStep', 'completed');

                showPaperInterface(data);
                showStatus('Paper analyzed successfully!', 'success');

                showPaperInterface(data);
                
            } else {
                throw new Error(data.error || 'Analysis failed');
            }
        } catch (error) {
            console.error('Error during analysis:', error);
            showStatus(`Error: ${error.message}`, 'error');
            updateAllSteps('error');
        } finally {
            spinner.style.display = 'none';
            analyzeBtn.disabled = false;
        }
    });

    function showStatus(message, type) {
        if (status) {
            status.style.display = 'block';
            status.textContent = message;
            status.className = type;
        }
    }

    function updateStep(stepId, status) {
        const step = document.getElementById(stepId);
        const icon = step.querySelector('.step-icon');
        
        step.className = `step ${status}`;
        
        switch(status) {
            case 'in-progress':
                icon.textContent = '○';
                break;
            case 'completed':
                icon.textContent = '✓';
                break;
            case 'error':
                icon.textContent = '✗';
                break;
        }
    }

    function updateAllSteps(status) {
        ['uploadStep', 'extractStep', 'analyzeStep'].forEach(stepId => {
            updateStep(stepId, status);
        });
    }
    function showPaperInterface(data) {
        result.innerHTML = `
            <div class="paper-info">
                <h3>${data.title}</h3>
                <p>Authors: ${data.authors.join(', ')}</p>
                <p>${data.abstract}</p>
            </div>
            <div id="chatHistory"></div>
            <div class="chat-input-container">
                <input type="text" id="chatInput" placeholder="Ask a question about the paper...">
                <button onclick="sendMessage()">Send</button>
            </div>
        `;

        // Add enter key handler for chat input
        document.getElementById('chatInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
});

async function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const chatHistory = document.getElementById('chatHistory');
    const message = chatInput.value.trim();

    if (!message) return;

    try {
        // Add user message
        appendMessage(message, 'user');
        chatInput.value = '';

        // Show loading state
        const loadingId = showLoading();

        const response = await fetch('http://localhost:8000/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                paper_id: currentPaperId,
                message: message
            })
        });

        // Remove loading message
        removeLoading(loadingId);

        const data = await response.json();
        if (response.ok && data.success) {
            appendMessage(data.response, 'assistant');
        } else {
            throw new Error(data.detail || 'Failed to get response');
        }
    } catch (error) {
        appendMessage(`Error: ${error.message}`, 'error');
    }
}

function appendMessage(content, type) {
    const chatHistory = document.getElementById('chatHistory');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;
    messageDiv.textContent = content;
    chatHistory.appendChild(messageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function showLoading() {
    const chatHistory = document.getElementById('chatHistory');
    const loadingDiv = document.createElement('div');
    const loadingId = 'loading-' + Date.now();
    loadingDiv.id = loadingId;
    loadingDiv.className = 'loading';
    loadingDiv.textContent = 'Assistant is typing...';
    chatHistory.appendChild(loadingDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    return loadingId;
}

function removeLoading(loadingId) {
    const loadingDiv = document.getElementById(loadingId);
    if (loadingDiv) {
        loadingDiv.remove();
    }
}