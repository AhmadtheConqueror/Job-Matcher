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
