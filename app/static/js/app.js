const alerts = document.querySelectorAll(".alert");

alerts.forEach((alert) => {
  window.setTimeout(() => {
    const instance = bootstrap.Alert.getOrCreateInstance(alert);
    instance.close();
  }, 6000);
});

const loadingScreen = document.querySelector("#aiLoadingScreen");
const loadingTitle = document.querySelector("#aiLoadingTitle");
const loadingMessage = document.querySelector("#aiLoadingMessage");
const aiForms = document.querySelectorAll("form[data-ai-loading]");

aiForms.forEach((form) => {
  form.addEventListener("submit", () => {
    if (!form.checkValidity() || !loadingScreen) {
      return;
    }

    if (loadingTitle && form.dataset.loadingTitle) {
      loadingTitle.textContent = form.dataset.loadingTitle;
    }

    if (loadingMessage && form.dataset.loadingMessage) {
      loadingMessage.textContent = form.dataset.loadingMessage;
    }

    loadingScreen.classList.add("is-visible");
    loadingScreen.setAttribute("aria-hidden", "false");

    form.querySelectorAll("button[type='submit']").forEach((button) => {
      button.disabled = true;
    });
  });
});

const aiStreamForms = document.querySelectorAll("form[data-ai-stream-form]");
const aiStreamAccept = "application/x-ndjson";
const aiStreamRenderDelay = 80;
const aiStreamStatusDelay = 950;
const aiStreamSteps = {
  match: [
    { active: "Reading your CV...", done: "CV context checked" },
    { active: "Reviewing job requirements...", done: "Job requirements reviewed" },
    { active: "Comparing skills and experience...", done: "Skills and experience compared" },
    { active: "Identifying strengths and gaps...", done: "Strengths and gaps identified" },
    { active: "Preparing recommendations...", done: "Recommendations prepared" },
  ],
  "cover-letter": [
    { active: "Reading your CV...", done: "CV context checked" },
    { active: "Reviewing the role...", done: "Role reviewed" },
    { active: "Selecting relevant experience...", done: "Relevant experience selected" },
    { active: "Drafting your cover letter...", done: "Cover letter drafted" },
  ],
  generic: [
    { active: "Preparing context...", done: "Context prepared" },
    { active: "Sending request...", done: "Request sent" },
    { active: "Receiving response...", done: "Response received" },
    { active: "Finalizing response...", done: "Response finalized" },
  ],
};

aiStreamForms.forEach((form) => {
  bindAiStreamForm(form);
});

function bindAiStreamForm(form) {
  const kind = form.dataset.aiStreamKind || "generic";
  const result = document.querySelector(`[data-ai-stream-result="${kind}"]`);
  const output = result?.querySelector("[data-ai-stream-output]");
  const status = result?.querySelector("[data-ai-stream-status]");
  const resultLink = result?.querySelector("[data-ai-stream-result-link]");
  const downloadLink = result?.querySelector("[data-ai-stream-download-link]");
  const downloadForm = result?.querySelector("[data-ai-stream-download-form]");
  const copyButton = result?.querySelector("[data-copy-target]");
  const stopButton = form.querySelector("[data-ai-stream-stop]");
  let activeController = null;

  stopButton?.addEventListener("click", () => {
    activeController?.abort();
  });

  form.addEventListener("submit", async (event) => {
    if (!form.checkValidity()) {
      return;
    }
    if (!form.dataset.aiStreamUrl || !result || !output || !status) {
      return;
    }

    event.preventDefault();
    activeController = new AbortController();
    let rawText = "";
    let renderTimer = null;
    const statusController = createAiStreamStatus(status, kind);

    const flushOutput = () => {
      const shouldScroll = pageIsNearBottom();
      if (renderTimer) {
        window.clearTimeout(renderTimer);
        renderTimer = null;
      }
      output.textContent = rawText;
      if (shouldScroll) {
        window.scrollTo({
          top: document.documentElement.scrollHeight,
          behavior: "smooth",
        });
      }
    };

    const scheduleOutput = () => {
      if (renderTimer) {
        return;
      }
      renderTimer = window.setTimeout(flushOutput, aiStreamRenderDelay);
    };

    result.hidden = false;
    output.textContent = "";
    output.classList.add("is-streaming");
    resultLink && (resultLink.hidden = true);
    downloadLink && (downloadLink.hidden = true);
    downloadForm && (downloadForm.hidden = true);
    copyButton && (copyButton.hidden = true);
    setAiStreamFormControls(form, stopButton, true);
    result.scrollIntoView({ behavior: "smooth", block: "start" });

    try {
      const done = await readAiStream(
        form.dataset.aiStreamUrl,
        Object.fromEntries(new FormData(form).entries()),
        activeController.signal,
        {
          onChunk(event) {
            rawText += event.text || "";
            scheduleOutput();
          },
          onStatus(event) {
            statusController.setMessage(event.message);
          },
        }
      );

      flushOutput();
      output.classList.remove("is-streaming");
      statusController.remove();
      applyAiStreamDone(kind, done, {
        resultLink,
        downloadLink,
        downloadForm,
        copyButton,
        result,
      });
    } catch (error) {
      flushOutput();
      output.classList.remove("is-streaming");
      if (error.name === "AbortError") {
        statusController.setStopped();
        return;
      }

      statusController.setError(
        error.message || "The AI response could not be generated."
      );
      if (!rawText.trim()) {
        output.textContent = error.message || "The AI response could not be generated.";
      }
    } finally {
      setAiStreamFormControls(form, stopButton, false);
      activeController = null;
    }
  });
}

async function readAiStream(url, payload, signal, callbacks = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: aiStreamAccept,
    },
    body: JSON.stringify({ ...payload, stream: true }),
    signal,
  });

  if (!response.ok) {
    throw new Error(
      await readJsonError(response, "The AI response could not be generated.")
    );
  }

  const reader = response.body?.getReader();
  if (!reader) {
    const data = await response.json();
    if (data.error) {
      throw new Error(data.error);
    }
    return data;
  }

  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let donePayload = null;

  const processLine = (line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      return;
    }

    let event;
    try {
      event = JSON.parse(trimmed);
    } catch {
      throw new Error("The AI stream returned unreadable data.");
    }

    if (event.type === "chunk") {
      callbacks.onChunk?.(event);
      return;
    }
    if (event.type === "status") {
      callbacks.onStatus?.(event);
      return;
    }
    if (event.type === "done") {
      donePayload = event;
      return;
    }
    if (event.type === "error") {
      throw new Error(event.error || "The AI response could not be generated.");
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split(/\r?\n/);
    buffer = lines.pop() || "";
    lines.forEach(processLine);
  }

  buffer += decoder.decode();
  processLine(buffer);

  if (!donePayload) {
    throw new Error("No response was returned. Please try again.");
  }

  return donePayload;
}

async function readJsonError(response, fallback) {
  try {
    const data = await response.json();
    return data.error || fallback;
  } catch {
    return fallback;
  }
}

function createAiStreamStatus(container, kind) {
  const steps = aiStreamSteps[kind] || aiStreamSteps.generic;
  let activeIndex = 0;
  let terminalMessage = "";
  let terminalClass = "";

  const render = () => {
    container.replaceChildren();
    if (terminalMessage) {
      container.className = `chat-stream-status ${terminalClass}`;
      container.append(createAiStatusRow(terminalMessage, "current"));
      return;
    }

    container.className = "chat-stream-status";
    steps.forEach((step, index) => {
      let state = "waiting";
      let label = step.active;
      if (index < activeIndex) {
        state = "done";
        label = step.done;
      } else if (index === activeIndex) {
        state = "current";
      }
      container.append(createAiStatusRow(label, state));
    });
  };

  const timer = window.setInterval(() => {
    if (activeIndex < steps.length - 1) {
      activeIndex += 1;
      render();
    }
  }, aiStreamStatusDelay);

  render();

  return {
    setMessage() {},
    remove() {
      window.clearInterval(timer);
      container.replaceChildren();
    },
    setError(message) {
      window.clearInterval(timer);
      terminalMessage = message;
      terminalClass = "is-error";
      render();
    },
    setStopped() {
      window.clearInterval(timer);
      terminalMessage = "Generation stopped";
      terminalClass = "is-stopped";
      render();
    },
  };
}

function createAiStatusRow(label, state) {
  const row = document.createElement("div");
  row.className = `chat-stream-step is-${state}`;

  const icon = document.createElement("span");
  icon.className = "chat-stream-step-icon";
  icon.setAttribute("aria-hidden", "true");

  const text = document.createElement("span");
  text.textContent = label;

  row.append(icon, text);
  return row;
}

function applyAiStreamDone(kind, done, elements) {
  if (kind === "match" && done.result) {
    if (elements.resultLink) {
      elements.resultLink.href = done.result.url;
      elements.resultLink.hidden = false;
    }
    if (elements.downloadLink) {
      elements.downloadLink.href = done.result.download_url;
      elements.downloadLink.hidden = false;
    }
    return;
  }

  if (kind === "cover-letter" && done.letter) {
    const text = done.letter.text || "";
    const payload = done.letter.payload || "";
    const copySource = elements.result?.querySelector("[data-ai-stream-copy-source]");
    const payloadField = elements.result?.querySelector("[data-ai-stream-letter-payload]");
    const textField = elements.result?.querySelector("[data-ai-stream-letter-text]");
    const roleField = elements.result?.querySelector("[data-ai-stream-role-title]");
    const companyField = elements.result?.querySelector("[data-ai-stream-company]");

    if (copySource) {
      copySource.value = text;
    }
    if (payloadField) {
      payloadField.value = payload;
    }
    if (textField) {
      textField.value = text;
    }
    if (roleField) {
      roleField.value = done.letter.role_title || "";
    }
    if (companyField) {
      companyField.value = done.letter.company || "";
    }
    elements.copyButton && (elements.copyButton.hidden = false);
    elements.downloadForm && (elements.downloadForm.hidden = false);
  }
}

function setAiStreamFormControls(form, stopButton, isStreaming) {
  form.querySelectorAll("button[type='submit']").forEach((button) => {
    button.disabled = isStreaming;
  });
  if (stopButton) {
    stopButton.disabled = !isStreaming;
    stopButton.hidden = !isStreaming;
  }
}

function pageIsNearBottom() {
  const bottom = window.scrollY + window.innerHeight;
  return document.documentElement.scrollHeight - bottom < 160;
}

const copyButtons = document.querySelectorAll("[data-copy-target]");

copyButtons.forEach((button) => {
  const defaultLabel = button.textContent;

  button.addEventListener("click", async () => {
    const target = document.querySelector(button.dataset.copyTarget);
    const text = target?.value || target?.textContent || "";

    if (!text.trim()) {
      return;
    }

    try {
      await copyText(text);
      button.textContent = "Copied";
      window.setTimeout(() => {
        button.textContent = defaultLabel;
      }, 1800);
    } catch {
      button.textContent = "Copy failed";
      window.setTimeout(() => {
        button.textContent = defaultLabel;
      }, 1800);
    }
  });
});

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.top = "-1000px";
  document.body.appendChild(textarea);
  textarea.select();

  const copied = document.execCommand("copy");
  textarea.remove();

  if (!copied) {
    throw new Error("Copy command failed");
  }
}
