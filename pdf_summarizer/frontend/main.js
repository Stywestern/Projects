import { animateProgressBar, updateProgressSmooth, } from './utils.js';

document.addEventListener("DOMContentLoaded", () => {
  const fileInput = document.getElementById("fileInput");
  const dropZone = document.getElementById("drop-zone");
  const dropText = dropZone.querySelector(".drop-text");
  const fileNameSpan = dropZone.querySelector(".file-name");

  const outputDiv = document.getElementById("output");

  const progressContainer = document.getElementById("progress-container");
  const progressBar = document.getElementById("progress-bar");
  const timeEstimate = document.getElementById("time-estimate");
    
  const modelSelect = document.getElementById("model");

  // Click opens file picker
  dropZone.addEventListener("click", () => fileInput.click());

  // Drag & drop
  dropZone.addEventListener("dragover", e => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
  dropZone.addEventListener("drop", e => {
    e.preventDefault();
    dropZone.classList.remove("dragover");

    const files = e.dataTransfer.files;
    if (!files.length) return;
    const pdfFiles = Array.from(files).filter(f => f.type === "application/pdf");
    if (!pdfFiles.length) return alert("Only PDFs allowed.");

    fileInput.files = files;  // update hidden input
    updateFileDisplay();
  });

  // File picker selection
  function updateFileDisplay() {
    if (fileInput.files.length) {
      fileNameSpan.textContent = fileInput.files[0].name;
      dropText.style.display = "none";
    } else {
      fileNameSpan.textContent = "";
      dropText.style.display = "block";
    }
  }

  fileInput.addEventListener("change", updateFileDisplay);

  // Upload button is pressed
  document.getElementById("uploadBtn").addEventListener("click", async () => {
    const file = fileInput.files[0];
    const modelChoice = modelSelect.value;

    if (!file) {
      alert("Please select a PDF file first.");
      return;
    }

    // Reset UI
    outputDiv.textContent = "";
    progressBar.style.width = "0%";
    progressContainer.style.display = "block";
    timeEstimate.textContent = "";

    const formData = new FormData();
    formData.append("file", file);
    formData.append("model_choice", modelChoice);

    const response = await fetch("http://127.0.0.1:8000/upload", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      outputDiv.textContent = "Error during upload.";
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let receivedText = "";

    const startTime = Date.now();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      receivedText += decoder.decode(value, { stream: true });


      if (receivedText.includes("\n")) {
        const lines = receivedText.split("\n");
        receivedText = lines.pop();

        for (const line of lines) {
          if (line.startsWith("PROGRESS:")) {
              const [num, total] = line.replace("PROGRESS:", "").split("/").map(Number);
              if (!isNaN(num) && !isNaN(total) && total > 0) {
                  const percentage = (num / total) * 100;
                  updateProgressSmooth(progressBar, percentage, percentage);
              }

              // Estimate time remaining
              const elapsed = (Date.now() - startTime) / 1000; // seconds
              const estimatedTotal = (elapsed / num) * total;
              const remaining = Math.max(0, estimatedTotal - elapsed);

              // Format mm:ss
              const minutes = Math.floor(remaining / 60);
              const seconds = Math.floor(remaining % 60);
              timeEstimate.textContent = `Estimated time remaining: ${minutes}:${seconds.toString().padStart(2, '0')}`;
          }
          else if (line.startsWith("SUMMARY:")) {
            outputDiv.textContent = line.slice(8);
            progressBar.style.width = "100%";
            timeEstimate.textContent = "Completed!";
          }
        }
      }
    }

    progressContainer.style.display = "none";
  });

  document.getElementById("downloadSummary").addEventListener("click", () => {
    function downloadTextFile(filename, text) {
    const blob = new Blob([text], { type: "text/plain" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
  }

  function downloadPdfFile(filename, text) {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    const lines = doc.splitTextToSize(text, 180);
    doc.text(lines, 10, 10);
    doc.save(filename);
  }
    
    const summary = document.getElementById("output").textContent;
    if (!summary) return alert("No summary to download.");

    const format = prompt("Enter format: txt or pdf").toLowerCase();
    if (format === "txt") {
      downloadTextFile("summary.txt", summary);
    } else if (format === "pdf") {
      downloadPdfFile("summary.pdf", summary);
    } else {
      alert("Invalid format. Please type 'txt' or 'pdf'.");
    }
  });
});


