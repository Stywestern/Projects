document.addEventListener("DOMContentLoaded", () => {

    /* ==========================================================================
       FEATURE 1: DARK THEME MANAGEMENT
       --------------------------------------------------------------------------
       Check LocalStorage immediately to avoid a flash of the wrong theme.
       ========================================================================== */
    const toggleBtn = document.querySelector('.theme-btn');
    const body = document.body;

    // 1. Check saved preference on load
    if (localStorage.getItem('theme') === 'dark') {
        body.classList.add('dark-mode');
        if (toggleBtn) toggleBtn.innerText = "☀️ Light Mode";
    }

    // 2. Bind the toggle listener
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            body.classList.toggle('dark-mode');

            if (body.classList.contains('dark-mode')) {
                localStorage.setItem('theme', 'dark'); 
                toggleBtn.innerText = "☀️ Light Mode";
            } else {
                localStorage.setItem('theme', 'light'); 
                toggleBtn.innerText = "🌙 Dark Mode";
            }
        });
    }

    /* ==========================================================================
       FEATURE 2: CHAT INTERFACE & DOM ELEMENTS
       --------------------------------------------------------------------------
       Initialize references to the chat area, input fields, and loading state.
       ========================================================================== */
    const chatBox = document.getElementById("chat-box");
    const userInput = document.getElementById("user-input");
    const sendBtn = document.getElementById("send-btn");
    const typingIndicator = document.getElementById("typing-indicator");

    // Helper: Scroll to bottom of chat
    function scrollToBottom() {
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // Helper: Append a message bubble to the UI
    function appendMessage(text, type) {
        const messageDiv = document.createElement("div");
        messageDiv.className = `message ${type}`;
        
        const bubble = document.createElement("div");
        bubble.className = "bubble";
        bubble.innerText = text;

        messageDiv.appendChild(bubble);
        chatBox.appendChild(messageDiv);
        scrollToBottom();
    }

    /* ==========================================================================
       FEATURE 3: CORE INTERACTION LOGIC
       --------------------------------------------------------------------------
       Handles validation, network requests to the FastAPI backend, and 
       UI state updates (loading/thinking).
       ========================================================================== */
    
    // Handler for sending messages
    async function handleSendMessage() {
        const question = userInput.value.trim();

        // Validation: Do not send empty strings
        if (!question) return;

        // 1. Update UI: Show user message immediately
        appendMessage(question, "user-message");
        
        // 2. Reset Input State
        userInput.value = "";
        userInput.disabled = true;
        sendBtn.disabled = true;
        if (typingIndicator) typingIndicator.style.display = "block";

        // 3. Send Request to Backend
        try {
            const response = await fetch("/api/ask", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ question: question })
            });

            if (!response.ok) {
                throw new Error("Network response was not ok");
            }

            // 4. Process Response
            const data = await response.json();
            appendMessage(data.answer, "bot-message");

        } catch (error) {
            console.error("Error:", error);
            appendMessage("Error: Could not reach the knowledge base.", "bot-message");
        } finally {
            // 5. Cleanup: Re-enable inputs and hide loader
            if (typingIndicator) typingIndicator.style.display = "none";
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
            scrollToBottom();
        }
    }

    /* ==========================================================================
       FEATURE 4: EVENT LISTENERS
       --------------------------------------------------------------------------
       Bind click and keyboard events to the logic functions.
       ========================================================================== */
    
    if (sendBtn) {
        sendBtn.addEventListener("click", handleSendMessage);
    }

    if (userInput) {
        userInput.addEventListener("keypress", (event) => {
            if (event.key === "Enter") {
                handleSendMessage();
            }
        });
    }

});