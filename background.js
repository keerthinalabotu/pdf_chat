chrome.runtime.onInstalled.addListener(() => {
    console.log('Paper Chat Extension installed');
  });
  
  // Listen for messages from content script or popup
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'analyze') {
      // Handle paper analysis
      console.log('Analyzing paper:', request.url);
    }
    return true;
  });