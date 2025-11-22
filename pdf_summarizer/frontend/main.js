document.addEventListener("DOMContentLoaded", () => {

  /* ==========================================================================
     FEATURE 1: DARK THEME MANAGEMENT
     --------------------------------------------------------------------------
     Variables are defined here because they are only used for this feature.
     We check LocalStorage immediately to avoid a "flash" of the wrong theme.
     ========================================================================== */
  const toggleBtn = document.getElementById('theme-toggle');
  const body = document.body;

  // 1. Check saved preference on load
  if (localStorage.getItem('theme') === 'dark') {
      body.classList.add('dark-mode');
      toggleBtn.innerText = "☀️ Light Mode";
  }

  // 2. Bind the toggle listener
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


  /* ==========================================================================
     FEATURE 2: FILE INPUT & DRAG-AND-DROP INTERFACE
     --------------------------------------------------------------------------
     This section handles the visual "Drop Zone" and syncs it with the hidden 
     HTML file input.
     ========================================================================== */
  const fileInput = document.getElementById("fileInput");
  const dropZone = document.getElementById("drop-zone");
  const dropText = dropZone.querySelector(".drop-text");
  const fileNameSpan = dropZone.querySelector(".file-name");

  // Helper: Visual update when file changes
  function updateFileDisplay() {
    if (fileInput.files.length) {
      fileNameSpan.textContent = fileInput.files[0].name;
      dropText.style.display = "none";
    } else {
      fileNameSpan.textContent = "";
      dropText.style.display = "block";
    }
  }

  // If user clicks instead of dropping
  dropZone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", updateFileDisplay);
  dropZone.addEventListener("dragover", e => {
    e.preventDefault(); // Essential: allows 'drop' to fire
    dropZone.classList.add("dragover");
  });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));

  // Handle the file drop
  dropZone.addEventListener("drop", e => {
    e.preventDefault();
    dropZone.classList.remove("dragover");

    const files = e.dataTransfer.files;
    if (!files.length) return;

    // Filter: Ensure it's a PDF
    const pdfFiles = Array.from(files).filter(f => f.type === "application/pdf");
    if (!pdfFiles.length) return alert("Only PDFs allowed.");

    // Critical: Sync the dropped files to the input element so it can be send later
    fileInput.files = files; 
    updateFileDisplay();
  });


  /* ==========================================================================
     FEATURE 3: UPLOAD & SUMMARIZATION 
     --------------------------------------------------------------------------
     This section gathers inputs, sends the request, and handles the
     complex streaming response from the backend.
     ========================================================================== */
  const uploadBtn = document.getElementById("uploadBtn");
  const modelSelect = document.getElementById("model");

  const outputDiv = document.getElementById("output");
  const progressContainer = document.getElementById("progress-container");
  const progressBar = document.getElementById("progress-bar");
  const timeEstimate = document.getElementById("time-estimate");

  /* Instead of the bar jumping from 10% to 20%, this function calculates small steps to make it slide smoothly over 300ms. */
  function updateProgressSmooth(barElement, currentPercent, targetPercent, duration = 300) {
    const start = parseFloat(barElement.style.width) || 0; 
    const change = targetPercent - start;                 
    const stepTime = 20;                                  
    const steps = Math.ceil(duration / stepTime);  
    let stepCount = 0;

    const interval = setInterval(() => {
      stepCount++;
      // Linear Interpolation formula: Start + (Distance * (CurrentStep / TotalSteps))
      const newPercent = start + (change * stepCount / steps);
      barElement.style.width = newPercent + "%";
      
      if (stepCount >= steps) clearInterval(interval); // Stop when finished
    }, stepTime);
  }

  // Upload clicked
  uploadBtn.addEventListener("click", async () => {
    const file = fileInput.files[0];
    const modelChoice = modelSelect.value;

    // Validation
    if (!file) {
      alert("Please select a PDF file first.");
      return;
    }

    // 1. Reset UI for new request
    outputDiv.textContent = "";
    progressBar.style.width = "0%";
    progressContainer.style.display = "block";
    timeEstimate.textContent = "Starting...";

    // 2. Prepare Data
    const formData = new FormData();
    formData.append("file", file);
    formData.append("model_choice", modelChoice);

    // 3. Initiate Stream Request (This section calls backend, namely routes/upload.py)
    const response = await fetch("http://127.0.0.1:8000/upload", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      outputDiv.textContent = "Error during upload.";
      return;
    }

    // 4. Handle the Stream (chunk by chunk)
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let receivedText = "";
    const startTime = Date.now();

    while (true) {
      // Check to see anything coming from the backend
      const { done, value } = await reader.read();
      if (done) break;

      receivedText += decoder.decode(value, { stream: true });

      // We only process complete lines (splitting by newline)
      if (receivedText.includes("\n")) {
        const lines = receivedText.split("\n");
        receivedText = lines.pop(); // Save partial line for next loop

        for (const line of lines) {
          // --- Protocol Handler ---
          
          if (line.startsWith("PROGRESS:")) {
              const [num, total] = line.replace("PROGRESS:", "").split("/").map(Number);
              
              if (!isNaN(num) && !isNaN(total) && total > 0) {
                  const percentage = (num / total) * 100;
                  updateProgressSmooth(progressBar, percentage, percentage);

                  // Math: Estimate remaining time
                  const elapsed = (Date.now() - startTime) / 1000; 
                  const estimatedTotal = (elapsed / num) * total;
                  const remaining = Math.max(0, estimatedTotal - elapsed);

                  const minutes = Math.floor(remaining / 60);
                  const seconds = Math.floor(remaining % 60);
                  timeEstimate.textContent = `Estimated time remaining: ${minutes}:${seconds.toString().padStart(2, '0')}`;
              }
          }
          else if (line.startsWith("SUMMARY:")) {
            const rawText = line.slice(8);
            const formattedText = rawText.replace(/\\n/g, "\n");

            outputDiv.textContent = formattedText;
            progressBar.style.width = "100%";
            timeEstimate.textContent = "Completed!";
          }
        }
      }
    }
    // Stream finished
    progressContainer.style.display = "none";
  });


  /* ==========================================================================
     FEATURE 4: DOWNLOAD RESULTS
     --------------------------------------------------------------------------
     Handles converting the text output into a file download (TXT or PDF).
     ========================================================================== */
  const downloadBtn = document.getElementById("downloadSummary");

  downloadBtn.addEventListener("click", () => {
    const summary = outputDiv.textContent; // Read directly from the DOM
    if (!summary) return alert("No summary to download.");

    const format = prompt("Enter format: txt or pdf").toLowerCase();

    // Strategy A: Text File (Blob)
    if (format === "txt") {
      const blob = new Blob([summary], { type: "text/plain" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "summary.txt";
      link.click();
    } 
    // Strategy B: PDF File (jsPDF Library)
    else if (format === "pdf") {
      // Ensure jspdf is available globally
      if (!window.jspdf) return alert("jsPDF library missing.");
      
      const { jsPDF } = window.jspdf;
      const doc = new jsPDF();
      const lines = doc.splitTextToSize(summary, 180);
      doc.text(lines, 10, 10);
      doc.save("summary.pdf");
    } 
    else {
      alert("Invalid format. Please type 'txt' or 'pdf'.");
    }
  });
});