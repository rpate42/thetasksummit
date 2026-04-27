const form = document.getElementById("intake-form");
const roleSelect = document.getElementById("interview-role");
const otherRoleGroup = document.getElementById("other-role-group");
const otherRoleInput = document.getElementById("other-role");
const transcriptInput = document.getElementById("transcript-file");
const preview = document.getElementById("role-preview");
const statusBox = document.getElementById("form-status");
const errorBox = document.getElementById("form-error");
const submitButton = document.getElementById("generate-button");
const MAX_TRANSCRIPT_BYTES = 100 * 1024;

function getSelectedRoleLabel() {
  const selectedValue = roleSelect.value;

  if (selectedValue === "other") {
    const customRole = otherRoleInput.value.trim();
    return customRole || "Other";
  }

  if (!selectedValue) {
    return "Not selected yet";
  }

  const selectedOption = roleSelect.options[roleSelect.selectedIndex];
  return selectedOption.text;
}

function updateRoleUI() {
  const isOther = roleSelect.value === "other";

  otherRoleGroup.classList.toggle("hidden", !isOther);
  otherRoleInput.required = isOther;

  if (!isOther) {
    otherRoleInput.value = "";
  }

  preview.innerHTML = `Report will identify the interviewee as: <strong>${getSelectedRoleLabel()}</strong>`;
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function clearError() {
  errorBox.textContent = "";
  errorBox.classList.add("hidden");
}

function showStatus(message) {
  statusBox.textContent = message;
  statusBox.classList.remove("hidden");
}

function clearStatus() {
  statusBox.textContent = "";
  statusBox.classList.add("hidden");
}

function setSubmitting(isSubmitting) {
  submitButton.disabled = isSubmitting;
  submitButton.textContent = isSubmitting ? "Generating..." : "Generate Report";
}

function getDownloadFilename(response, fallbackName) {
  const disposition = response.headers.get("Content-Disposition") || "";
  const utfMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utfMatch) {
    return decodeURIComponent(utfMatch[1]);
  }

  const basicMatch = disposition.match(/filename="([^"]+)"/i);
  if (basicMatch) {
    return basicMatch[1];
  }

  return fallbackName;
}

async function downloadGeneratedReport(response, fallbackName) {
  const blob = await response.blob();
  const downloadName = getDownloadFilename(response, fallbackName);
  const blobUrl = URL.createObjectURL(blob);
  const downloadLink = document.createElement("a");

  downloadLink.href = blobUrl;
  downloadLink.download = downloadName;
  document.body.appendChild(downloadLink);
  downloadLink.click();
  downloadLink.remove();
  URL.revokeObjectURL(blobUrl);

  return downloadName;
}

roleSelect.addEventListener("change", () => {
  clearError();
  clearStatus();
  updateRoleUI();
});

otherRoleInput.addEventListener("input", () => {
  clearError();
  clearStatus();
  updateRoleUI();
});

transcriptInput.addEventListener("change", () => {
  clearError();
  clearStatus();

  const selectedFile = transcriptInput.files && transcriptInput.files[0];
  if (selectedFile && selectedFile.size > MAX_TRANSCRIPT_BYTES) {
    showError("Transcript files must be 100 KB or smaller.");
    transcriptInput.value = "";
    transcriptInput.focus();
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  clearStatus();

  if (!roleSelect.value) {
    showError("Select who was interviewed before continuing.");
    roleSelect.focus();
    return;
  }

  if (roleSelect.value === "other" && !otherRoleInput.value.trim()) {
    showError('Enter a name or title when "Other" is selected.');
    otherRoleInput.focus();
    return;
  }

  if (!transcriptInput.files || transcriptInput.files.length === 0) {
    showError("Choose a transcript .docx file before continuing.");
    transcriptInput.focus();
    return;
  }

  const transcriptFile = transcriptInput.files[0];
  if (transcriptFile.size > MAX_TRANSCRIPT_BYTES) {
    showError("Transcript files must be 100 KB or smaller.");
    transcriptInput.focus();
    return;
  }

  const roleLabel = getSelectedRoleLabel();
  const formData = new FormData();

  formData.append("interviewRole", roleSelect.value);
  formData.append("interviewRoleLabel", roleLabel);
  formData.append("transcriptFile", transcriptFile);

  setSubmitting(true);
  showStatus("Generating report...");

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let message = "Report generation failed.";
      try {
        const errorPayload = await response.json();
        if (errorPayload && errorPayload.error) {
          message = errorPayload.error;
        }
      } catch (jsonError) {
        // Ignore JSON parse failures and keep the fallback message.
      }
      throw new Error(message);
    }

    const fallbackName = `${transcriptFile.name.replace(/\.docx$/i, "")} - generated summary.docx`;
    const downloadName = await downloadGeneratedReport(response, fallbackName);
    showStatus(`Report ready: ${downloadName}`);
  } catch (error) {
    showError(error.message || "Report generation failed.");
  } finally {
    setSubmitting(false);
  }
});

updateRoleUI();
