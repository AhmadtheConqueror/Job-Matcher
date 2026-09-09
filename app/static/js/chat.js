(() => {
  const root = document.querySelector("[data-chat-root]");

  if (!root) {
    return;
  }

  const conversationsUrl = root.dataset.conversationsUrl;
  const contextUrl = root.dataset.contextUrl;
  const sendUrl = root.dataset.sendUrl;
  const coverLetterActionUrl = root.dataset.coverLetterActionUrl;
  const cvTailoringActionUrl = root.dataset.cvTailoringActionUrl;
  const interviewPrepActionUrl = root.dataset.interviewPrepActionUrl;
  const skillGapActionUrl = root.dataset.skillGapActionUrl;
  const careerRoadmapActionUrl = root.dataset.careerRoadmapActionUrl;
  const skillGapsUrl = root.dataset.skillGapsUrl;
  const sidebar = document.querySelector("#chatSidebar");
  const sidebarToggle = document.querySelector("#chatSidebarToggle");
  const mobileSidebarButton = document.querySelector("#chatMobileSidebarButton");
  const sidebarBackdrop = document.querySelector("#chatSidebarBackdrop");
  const conversationList = document.querySelector("#chatConversationList");
  const conversationMenu = document.querySelector("#chatConversationMenu");
  const skillGapList = document.querySelector("#chatSkillGapList");
  const skillGapDrawer = document.querySelector("#chatSkillGapDrawer");
  const skillGapDrawerToggle = document.querySelector("#chatSkillGapDrawerToggle");
  const skillGapDrawerClose = document.querySelector("#chatSkillGapDrawerClose");
  const drawerBackdrop = document.querySelector("#chatDrawerBackdrop");
  const messagesEl = document.querySelector("#chatMessages");
  const form = document.querySelector("#chatForm");
  const input = document.querySelector("#chatInput");
  const sendButton = document.querySelector("#chatSendButton");
  const stopButton = document.querySelector("#chatStopButton");
  const newButton = document.querySelector("#chatNewButton");
  const includeCv = document.querySelector("#chatIncludeCv");
  const cvSelect = document.querySelector("#chatCvSelect");
  const cvChip = document.querySelector("#chatCvChip");
  const cvToggleLabel = document.querySelector("#chatCvChipText");
  const cvUploadLink = document.querySelector("#chatCvUploadLink");
  const contextStatus = document.querySelector("#chatContextStatus");
  const starters = document.querySelector("#chatStarters");
  const jobToggle = document.querySelector("#chatJobToggle");
  const jobPanel = document.querySelector("#chatJobPanel");
  const jobDescription = document.querySelector("#chatJobDescription");
  const clearJobButton = document.querySelector("#chatClearJobButton");
  const coverLetterTemplate = document.querySelector("#chatCoverLetterActionTemplate");
  const cvPlanTemplate = document.querySelector("#chatCvPlanActionTemplate");
  const interviewTemplate = document.querySelector("#chatInterviewActionTemplate");
  const skillGapTemplate = document.querySelector("#chatSkillGapActionTemplate");
  const roadmapTemplate = document.querySelector("#chatRoadmapActionTemplate");
  const streamAccept = "application/x-ndjson";
  const streamRenderDelay = 80;
  const streamStatusDelay = 950;
  const statusStepSets = {
    careerCoach: [
      { active: "Reading your CV...", done: "CV context checked", requiresCv: true },
      { active: "Understanding your question...", done: "Question understood" },
      { active: "Reviewing relevant experience...", done: "Relevant experience reviewed", requiresCv: true },
      { active: "Preparing your response...", done: "Response prepared" },
    ],
    jobMatch: [
      { active: "Reading your CV...", done: "CV context checked", requiresCv: true },
      { active: "Reviewing job requirements...", done: "Job requirements reviewed", requiresJob: true },
      { active: "Comparing skills and experience...", done: "Skills and experience compared" },
      { active: "Identifying strengths and gaps...", done: "Strengths and gaps identified" },
      { active: "Preparing recommendations...", done: "Recommendations prepared" },
    ],
    cvReview: [
      { active: "Reviewing your CV...", done: "CV reviewed", requiresCv: true },
      { active: "Checking structure and content...", done: "Structure and content checked" },
      { active: "Identifying strengths...", done: "Strengths identified" },
      { active: "Preparing improvement suggestions...", done: "Suggestions prepared" },
    ],
    coverLetter: [
      { active: "Reading your CV...", done: "CV context checked", requiresCv: true },
      { active: "Reviewing the role...", done: "Role reviewed", requiresJob: true },
      { active: "Selecting relevant experience...", done: "Relevant experience selected" },
      { active: "Drafting your cover letter...", done: "Cover letter drafted" },
    ],
    cvPlan: [
      { active: "Reading your CV...", done: "CV context checked", requiresCv: true },
      { active: "Reviewing job requirements...", done: "Job requirements reviewed", requiresJob: true },
      { active: "Comparing skills and experience...", done: "Skills and experience compared" },
      { active: "Preparing your CV plan...", done: "CV plan prepared" },
    ],
    interview: [
      { active: "Reading your CV...", done: "CV context checked", requiresCv: true },
      { active: "Reviewing the role...", done: "Role reviewed", requiresJob: true },
      { active: "Selecting relevant experience...", done: "Relevant experience selected" },
      { active: "Preparing interview questions...", done: "Interview prep prepared" },
    ],
    skillGap: [
      { active: "Reading your CV...", done: "CV context checked", requiresCv: true },
      { active: "Reviewing job requirements...", done: "Job requirements reviewed", requiresJob: true },
      { active: "Comparing skills and experience...", done: "Skills and experience compared" },
      { active: "Preparing your skill-gap plan...", done: "Skill-gap plan prepared" },
    ],
    roadmap: [
      { active: "Reading your CV...", done: "CV context checked", requiresCv: true },
      { active: "Reviewing your target direction...", done: "Target direction reviewed" },
      { active: "Prioritizing next steps...", done: "Next steps prioritized" },
      { active: "Preparing your roadmap...", done: "Roadmap prepared" },
    ],
    generic: [
      { active: "Preparing context...", done: "Context prepared" },
      { active: "Sending request...", done: "Request sent" },
      { active: "Receiving response...", done: "Response received" },
      { active: "Finalizing response...", done: "Response finalized" },
    ],
  };

  let currentConversationId = null;
  let isSending = false;
  let latestContext = null;
  let activeAbortController = null;
  let menuConversationId = null;
  let menuConversationTitle = "";
  let activeConversationMenuButton = null;

  initChat();

  async function initChat() {
    bindEvents();
    updateComposerControls();
    updateSidebarToggleState();
    await loadContextStatus();
    await loadSkillGaps();
    await loadConversations();
  }

  function bindEvents() {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      await sendMessage();
    });

    input.addEventListener("input", updateComposerControls);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        form.requestSubmit();
      }
    });

    stopButton?.addEventListener("click", () => {
      activeAbortController?.abort();
    });

    newButton?.addEventListener("click", () => {
      closeConversationMenu();
      closeSidebarDrawer();
      currentConversationId = null;
      clearActiveConversation();
      resetJobContext();
      showWelcome();
      input.focus();
    });

    sidebarToggle?.addEventListener("click", () => {
      if (isMobileLayout()) {
        closeSidebarDrawer();
        return;
      }
      root.classList.toggle("is-sidebar-collapsed");
      updateSidebarToggleState();
      closeConversationMenu();
    });

    mobileSidebarButton?.addEventListener("click", openSidebarDrawer);
    sidebarBackdrop?.addEventListener("click", closeSidebarDrawer);

    skillGapDrawerToggle?.addEventListener("click", openSkillGapDrawer);
    skillGapDrawerClose?.addEventListener("click", closeSkillGapDrawer);
    drawerBackdrop?.addEventListener("click", closeSkillGapDrawer);

    conversationMenu?.addEventListener("click", async (event) => {
      const action = event.target.closest("[data-conversation-menu-action]");
      if (!action) {
        return;
      }
      await runConversationMenuAction(action.dataset.conversationMenuAction);
    });

    document.addEventListener("click", (event) => {
      if (
        conversationMenu
        && !conversationMenu.hidden
        && !conversationMenu.contains(event.target)
        && !event.target.closest(".chat-conversation-menu-button")
      ) {
        closeConversationMenu();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") {
        return;
      }
      closeConversationMenu({ restoreFocus: true });
      closeSkillGapDrawer();
      closeSidebarDrawer();
    });

    starters.addEventListener("click", (event) => {
      const button = event.target.closest("[data-starter-message]");
      if (!button) {
        return;
      }
      input.value = button.dataset.starterMessage;
      updateComposerControls();
      if (button.dataset.openJobContext === "true") {
        setJobPanelVisible(true);
        jobDescription.focus();
        return;
      }
      input.focus();
    });

    includeCv.addEventListener("change", updateContextStatusText);
    cvSelect?.addEventListener("change", updateContextStatusText);

    jobToggle.addEventListener("click", () => {
      setJobPanelVisible(jobPanel.classList.contains("is-hidden"));
      if (!jobPanel.classList.contains("is-hidden")) {
        jobDescription.focus();
      }
    });

    clearJobButton.addEventListener("click", () => {
      setJobDescription("");
      jobDescription.focus();
    });

    jobDescription.addEventListener("input", updateJobToggleState);
  }

  function isMobileLayout() {
    return window.matchMedia("(max-width: 992px)").matches;
  }

  function updateSidebarToggleState() {
    if (!sidebarToggle) {
      return;
    }
    const isCollapsed = root.classList.contains("is-sidebar-collapsed");
    const icon = sidebarToggle.querySelector("span");
    sidebarToggle.setAttribute("aria-expanded", String(!isCollapsed));
    sidebarToggle.setAttribute(
      "aria-label",
      isCollapsed ? "Expand conversations" : "Collapse conversations"
    );
    if (icon) {
      icon.textContent = isCollapsed ? ">" : "<";
    }
  }

  function openSidebarDrawer() {
    root.classList.add("is-sidebar-open");
    if (sidebarBackdrop) {
      sidebarBackdrop.hidden = false;
    }
  }

  function closeSidebarDrawer() {
    root.classList.remove("is-sidebar-open");
    if (sidebarBackdrop) {
      sidebarBackdrop.hidden = true;
    }
  }

  function openSkillGapDrawer() {
    if (!skillGapDrawer) {
      return;
    }
    closeConversationMenu();
    skillGapDrawer.classList.add("is-open");
    skillGapDrawer.setAttribute("aria-hidden", "false");
    if (drawerBackdrop) {
      drawerBackdrop.hidden = false;
    }
    skillGapDrawerClose?.focus();
  }

  function closeSkillGapDrawer() {
    if (!skillGapDrawer) {
      return;
    }
    skillGapDrawer.classList.remove("is-open");
    skillGapDrawer.setAttribute("aria-hidden", "true");
    if (drawerBackdrop) {
      drawerBackdrop.hidden = true;
    }
  }

  function updateComposerControls() {
    if (!sendButton || !input) {
      return;
    }
    sendButton.disabled = isSending || !input.value.trim();
    resizeChatInput();
  }

  function resizeChatInput() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
  }

  async function loadContextStatus() {
    try {
      const response = await fetch(contextUrl);
      latestContext = await response.json();
      renderCvOptions(latestContext.cvs || []);
      updateContextStatusText();
    } catch {
      contextStatus.textContent = "CV/job text may be sent to the AI provider.";
    } finally {
      root.querySelector("[data-chat-context-skeleton]")?.remove();
    }

  }

  function renderCvOptions(cvs) {
    if (!cvSelect) {
      return;
    }

    cvSelect.replaceChildren();
    const latestOption = document.createElement("option");
    latestOption.value = "";
    latestOption.textContent = "Latest CV";
    cvSelect.append(latestOption);
    cvs.forEach((cv) => {
      const option = document.createElement("option");
      option.value = cv.id;
      option.textContent = cv.filename;
      cvSelect.append(option);
    });
    cvSelect.classList.toggle("is-hidden", cvs.length <= 1);
  }

  async function loadSkillGaps() {
    if (!skillGapsUrl || !skillGapList) {
      return;
    }

    try {
      const response = await fetch(skillGapsUrl);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Could not load skill gaps.");
      }

      renderSkillGaps(data.skill_gaps || []);
    } catch {
      skillGapList.replaceChildren();
      const empty = document.createElement("p");
      empty.className = "chat-sidebar-empty mb-0";
      empty.textContent = "Skill gaps could not load.";
      skillGapList.append(empty);
    } finally {
      skillGapList?.removeAttribute("aria-busy");
    }
  }

  function renderSkillGaps(skillGaps) {
    skillGapList.replaceChildren();
    skillGapList.removeAttribute("aria-busy");

    if (!skillGaps.length) {
      const empty = document.createElement("p");
      empty.className = "chat-sidebar-empty mb-0";
      empty.textContent = "No tracked gaps yet.";
      skillGapList.append(empty);
      return;
    }

    skillGaps.forEach((gap) => {
      const item = document.createElement("div");
      item.className = "chat-skill-gap-item";

      const name = document.createElement("div");
      name.className = "chat-skill-gap-name";
      name.textContent = gap.skill;

      const meta = document.createElement("div");
      meta.className = "chat-skill-gap-meta";
      meta.textContent = `${gap.priority} priority`;

      const status = document.createElement("select");
      status.className = "form-select chat-skill-gap-status";
      [
        ["open", "Open"],
        ["learning", "Learning"],
        ["done", "Done"],
      ].forEach(([value, label]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        option.selected = gap.status === value;
        status.append(option);
      });
      status.addEventListener("change", async () => {
        await updateSkillGapStatus(gap.id, status.value);
      });

      item.append(name, meta, status);
      skillGapList.append(item);
    });
  }

  async function updateSkillGapStatus(gapId, status) {
    try {
      const response = await fetch(`${skillGapsUrl}/${gapId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ status }),
      });
      if (!response.ok) {
        await loadSkillGaps();
      }
    } catch {
      await loadSkillGaps();
    }
  }

  function updateContextStatusText() {
    const selectedCv = latestContext?.cvs?.find(
      (cv) => String(cv.id) === String(cvSelect?.value)
    );

    const hasCv = Boolean(latestContext?.has_latest_cv);
    if (!hasCv) {
      cvChip?.classList.add("is-hidden");
      cvSelect?.classList.add("is-hidden");
      cvUploadLink?.classList.remove("is-hidden");
      contextStatus.textContent = "No uploaded CV found. Chat will use your message only.";
      return;
    }

    cvChip?.classList.remove("is-hidden");
    cvUploadLink?.classList.add("is-hidden");
    cvSelect?.classList.toggle("is-hidden", (latestContext?.cvs || []).length <= 1);
    cvChip?.classList.toggle("is-off", !includeCv.checked);

    if (cvToggleLabel) {
      const filename = selectedCv?.filename || latestContext.latest_cv_filename;
      cvToggleLabel.textContent = includeCv.checked
        ? `${selectedCv ? "CV" : "Latest CV"}: ${compactText(filename, 32)}`
        : "CV off";
    }

    if (!includeCv.checked) {
      contextStatus.textContent = "CV context is off for the next message.";
      return;
    }

    const skills = latestContext.detected_skills || [];
    const skillText = skills.length
      ? ` Skills found: ${skills.slice(0, 5).join(", ")}.`
      : "";
    contextStatus.textContent = `Using ${latestContext.latest_cv_filename}.${skillText} CV/job text may be sent to the AI provider.`;
  }

  function compactText(text, maxLength) {
    const value = String(text || "").trim();
    if (value.length <= maxLength) {
      return value;
    }
    return `${value.slice(0, Math.max(0, maxLength - 3))}...`;
  }

  async function loadConversations() {
    conversationList.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(conversationsUrl);
      const data = await response.json();
      renderConversationList(data.conversations || []);

      if (data.conversations?.length) {
        await loadConversation(data.conversations[0].id);
      } else {
        showWelcome();
      }
    } catch {
      showError("Could not load conversations.");
    } finally {
      conversationList.removeAttribute("aria-busy");
    }
  }

  async function loadConversation(conversationId) {
    closeConversationMenu();
    closeSidebarDrawer();
    showMessageSkeleton();
    try {
      const response = await fetch(`${conversationsUrl}/${conversationId}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Could not load conversation.");
      }

      currentConversationId = data.conversation.id;
      setJobDescription(data.job_context?.content || "", { showPanel: false });
      markActiveConversation(currentConversationId);
      renderMessages(data.messages || []);
    } catch {
      showError("Could not load this conversation.");
    } finally {
      messagesEl.removeAttribute("aria-busy");
    }
  }

  function showMessageSkeleton() {
    messagesEl.setAttribute("aria-busy", "true");
    messagesEl.replaceChildren();
    const skeleton = document.createElement("div");
    skeleton.className = "skeleton-message";
    skeleton.setAttribute("aria-hidden", "true");
    skeleton.innerHTML = `
      <span class="skeleton skeleton-text skeleton-text-short"></span>
      <span class="skeleton skeleton-message-line"></span>
      <span class="skeleton skeleton-message-line skeleton-message-line-short"></span>
    `;
    messagesEl.append(skeleton);
  }

  async function sendMessage() {
    const message = input.value.trim();

    if (!message || isSending) {
      return;
    }

    const activeJobDescription = jobDescription.value.trim();
    const controller = new AbortController();
    setStreamingControls(true, controller);
    input.value = "";
    updateComposerControls();
    starters.classList.add("is-hidden");

    appendMessage({
      role: "user",
      content: message,
    });
    const streamMessage = appendStreamingAssistantMessage({
      statusKind: statusKindForMessage(message),
      usesCv: includeCv.checked && Boolean(latestContext?.has_latest_cv),
      usesJob: Boolean(activeJobDescription),
    });

    try {
      const data = await streamJsonResponse(
        sendUrl,
        {
          conversation_id: currentConversationId,
          message,
          include_latest_cv: includeCv.checked,
          cv_id: cvSelect?.value || null,
          job_description: activeJobDescription,
        },
        {
          signal: controller.signal,
          onStatus: (event) => streamMessage.setStatus(event.message),
          onChunk: (event) => streamMessage.append(event.text),
        }
      );

      currentConversationId = data.conversation.id;
      setJobDescription(data.job_context?.content || "", {
        showPanel: false,
      });
      streamMessage.complete(data.assistant_message);
      await loadConversationsWithoutOpening();
      if (data.skill_gaps?.length) {
        renderSkillGaps(data.skill_gaps);
      } else {
        await loadSkillGaps();
      }
      markActiveConversation(currentConversationId);
    } catch (error) {
      if (error.name === "AbortError") {
        streamMessage.stop();
        return;
      }

      const streamEvent = error.streamEvent || {};
      if (streamEvent.conversation?.id) {
        currentConversationId = streamEvent.conversation.id;
        await loadConversationsWithoutOpening();
        markActiveConversation(currentConversationId);
      }
      if (streamEvent.job_context) {
        setJobDescription(streamEvent.job_context.content || "", {
          showPanel: false,
        });
      }
      streamMessage.fail(
        error.message ||
          "The assistant could not reply right now. Check your connection and try again."
      );
    } finally {
      setStreamingControls(false);
      input.focus();
    }
  }

  function setStreamingControls(isStreaming, controller = null) {
    isSending = isStreaming;
    activeAbortController = controller;
    updateComposerControls();
    if (stopButton) {
      stopButton.disabled = !isStreaming;
      stopButton.classList.toggle("is-hidden", !isStreaming);
    }
  }

  async function streamJsonResponse(url, payload, callbacks = {}) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: streamAccept,
      },
      body: JSON.stringify({ ...payload, stream: true }),
      signal: callbacks.signal,
    });

    if (!response.ok) {
      throw new Error(
        await readErrorMessage(response, "The assistant could not reply right now.")
      );
    }

    if (!response.body) {
      const data = await response.json();
      if (data.error) {
        throw new Error(data.error);
      }
      return data;
    }

    const reader = response.body.getReader();
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
        throw new Error("The assistant returned an unreadable stream event.");
      }

      if (event.type === "status") {
        callbacks.onStatus?.(event);
        return;
      }
      if (event.type === "chunk") {
        callbacks.onChunk?.(event);
        return;
      }
      if (event.type === "done") {
        donePayload = event;
        return;
      }
      if (event.type === "error") {
        const error = new Error(
          event.error || "The assistant could not reply right now."
        );
        error.streamEvent = event;
        throw error;
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

  async function readErrorMessage(response, fallback) {
    try {
      const data = await response.json();
      return data.error || fallback;
    } catch {
      return fallback;
    }
  }

  function appendStreamingAssistantMessage({ statusKind, usesCv, usesJob }) {
    const item = appendMessage({
      role: "assistant",
      content: "",
      pending: true,
      streaming: true,
    });
    const bubble = item.querySelector(".chat-message-bubble");
    const status = createStreamStatus(statusKind, { usesCv, usesJob });
    item.insertBefore(status.element, bubble);

    let rawText = "";
    let renderTimer = null;

    const flush = () => {
      const shouldScroll = isNearBottom();
      if (renderTimer) {
        window.clearTimeout(renderTimer);
        renderTimer = null;
      }
      renderAssistantContent(bubble, rawText);
      if (shouldScroll) {
        scrollMessagesToBottom({ smooth: true });
      }
    };

    const scheduleRender = () => {
      if (renderTimer) {
        return;
      }
      renderTimer = window.setTimeout(flush, streamRenderDelay);
    };

    return {
      append(text) {
        if (!text) {
          return;
        }
        rawText += text;
        scheduleRender();
      },
      setStatus(message) {
        status.setMessage(message);
      },
      complete(message) {
        rawText = message?.content || rawText;
        flush();
        item.classList.remove("is-pending", "is-streaming");
        status.remove();
        item.append(buildAssistantActions(message));
        scrollMessagesToBottom({ smooth: true });
      },
      fail(message) {
        flush();
        item.classList.remove("is-pending", "is-streaming");
        if (rawText.trim()) {
          status.setError(message);
        } else {
          status.remove();
          item.classList.add("is-error");
          renderAssistantContent(bubble, message);
        }
        maybeScrollMessagesToBottom({ smooth: true });
      },
      stop() {
        flush();
        item.classList.remove("is-pending", "is-streaming");
        status.setStopped();
        maybeScrollMessagesToBottom({ smooth: true });
      },
    };
  }

  function createStreamStatus(kind, options = {}) {
    const element = document.createElement("div");
    element.className = "chat-stream-status";
    const steps = statusStepsForKind(kind, options);
    let activeIndex = 0;
    let backendMessage = "";
    let terminalMessage = "";
    let terminalClass = "";

    const render = () => {
      element.replaceChildren();
      if (terminalMessage) {
        element.className = `chat-stream-status ${terminalClass}`;
        const row = createStatusRow(terminalMessage, "current");
        element.append(row);
        return;
      }

      element.className = "chat-stream-status";
      steps.forEach((step, index) => {
        let state = "waiting";
        let label = step.active;
        if (index < activeIndex) {
          state = "done";
          label = step.done;
        } else if (index === activeIndex) {
          state = "current";
          label = backendMessage || step.active;
        }
        element.append(createStatusRow(label, state));
      });
    };

    const timer = window.setInterval(() => {
      if (activeIndex < steps.length - 1) {
        activeIndex += 1;
        backendMessage = "";
        render();
      }
    }, streamStatusDelay);

    render();

    return {
      element,
      setMessage(message) {
        if (kind !== "generic") {
          return;
        }
        backendMessage = message || backendMessage;
        render();
      },
      remove() {
        window.clearInterval(timer);
        element.remove();
      },
      setError(message) {
        window.clearInterval(timer);
        terminalMessage = message || "The assistant could not reply right now.";
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

  function createStatusRow(label, state) {
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

  function statusStepsForKind(kind, options = {}) {
    const steps = statusStepSets[kind] || statusStepSets.generic;
    const filtered = steps.filter((step) => {
      if (step.requiresCv && !options.usesCv) {
        return false;
      }
      if (step.requiresJob && !options.usesJob) {
        return false;
      }
      return true;
    });
    return filtered.length ? filtered : statusStepSets.generic;
  }

  function statusKindForMessage(message) {
    const text = String(message || "").toLowerCase();
    if (text.includes("cover letter") || text.includes("application letter")) {
      return "coverLetter";
    }
    if (text.includes("interview")) {
      return "interview";
    }
    if (text.includes("skill gap") || text.includes("missing skill")) {
      return "skillGap";
    }
    if (text.includes("roadmap") || text.includes("career plan")) {
      return "roadmap";
    }
    if (
      text.includes("tailor") ||
      text.includes("cv plan") ||
      text.includes("ats") ||
      text.includes("optimize")
    ) {
      return "cvPlan";
    }
    if (text.includes("review") && (text.includes("cv") || text.includes("resume"))) {
      return "cvReview";
    }
    if (jobDescription.value.trim()) {
      return "jobMatch";
    }
    return "careerCoach";
  }

  function buildActionMessage(base, role, company) {
    let text = base || "Run career action";
    if (role) {
      text = `${text} for ${role}`;
    }
    if (company) {
      text = `${text} at ${company}`;
    }
    return `${text}.`;
  }

  async function loadConversationsWithoutOpening() {
    const response = await fetch(conversationsUrl);
    const data = await response.json();
    renderConversationList(data.conversations || []);
  }

  function renderConversationList(conversations) {
    conversationList.replaceChildren();
    closeConversationMenu();

    if (!conversations.length) {
      const empty = document.createElement("p");
      empty.className = "chat-sidebar-empty";
      empty.textContent = "No conversations yet.";
      conversationList.append(empty);
      return;
    }

    conversations.forEach((conversation) => {
      const item = document.createElement("div");
      item.className = "chat-conversation-item";
      item.dataset.conversationId = conversation.id;

      const button = document.createElement("button");
      button.className = "chat-conversation-button";
      button.type = "button";
      button.dataset.initial = conversationInitial(conversation.title);
      button.title = conversation.title;

      const title = document.createElement("span");
      title.className = "chat-conversation-title";
      title.textContent = conversation.title;

      const preview = document.createElement("span");
      preview.className = "chat-conversation-preview";
      const contextPrefix = conversation.has_job_description ? "Job attached. " : "";
      preview.textContent = `${contextPrefix}${conversation.latest_message || "New conversation"}`;

      button.append(title, preview);
      button.addEventListener("click", () => {
        closeConversationMenu();
        closeSidebarDrawer();
        loadConversation(conversation.id);
      });
      button.addEventListener("keydown", (event) => {
        if (event.key === "F10" && event.shiftKey) {
          event.preventDefault();
          openConversationMenu(conversation, button);
        }
      });

      const menuButton = document.createElement("button");
      menuButton.className = "chat-conversation-menu-button";
      menuButton.type = "button";
      menuButton.textContent = "...";
      menuButton.title = "Conversation actions";
      menuButton.setAttribute("aria-haspopup", "menu");
      menuButton.setAttribute("aria-expanded", "false");
      menuButton.setAttribute("aria-label", `Actions for ${conversation.title}`);
      menuButton.addEventListener("click", (event) => {
        event.stopPropagation();
        openConversationMenu(conversation, menuButton);
      });

      item.addEventListener("contextmenu", (event) => {
        event.preventDefault();
        openConversationMenu(conversation, item, event.clientX, event.clientY);
      });

      item.append(button, menuButton);
      conversationList.append(item);
    });

    if (currentConversationId) {
      markActiveConversation(currentConversationId);
    }
  }

  function conversationInitial(title) {
    const first = String(title || "C").trim().charAt(0);
    return first ? first.toUpperCase() : "C";
  }

  function openConversationMenu(conversation, trigger, x = null, y = null) {
    if (!conversationMenu) {
      return;
    }

    closeConversationMenu();
    menuConversationId = conversation.id;
    menuConversationTitle = conversation.title || "New chat";
    activeConversationMenuButton = trigger?.matches?.(".chat-conversation-menu-button")
      ? trigger
      : null;

    if (activeConversationMenuButton) {
      activeConversationMenuButton.setAttribute("aria-expanded", "true");
    }

    conversationMenu.hidden = false;
    positionConversationMenu(trigger, x, y);
    conversationMenu.querySelector("[role='menuitem']")?.focus();
  }

  function positionConversationMenu(trigger, x, y) {
    let left = x;
    let top = y;
    if ((left === null || top === null) && trigger) {
      const rect = trigger.getBoundingClientRect();
      left = rect.right - conversationMenu.offsetWidth;
      top = rect.bottom + 4;
    }

    left = Number.isFinite(left) ? left : 16;
    top = Number.isFinite(top) ? top : 16;
    const padding = 8;
    const maxLeft = window.innerWidth - conversationMenu.offsetWidth - padding;
    const maxTop = window.innerHeight - conversationMenu.offsetHeight - padding;
    conversationMenu.style.left = `${Math.max(padding, Math.min(left, maxLeft))}px`;
    conversationMenu.style.top = `${Math.max(padding, Math.min(top, maxTop))}px`;
  }

  function closeConversationMenu(options = {}) {
    if (!conversationMenu) {
      return;
    }
    conversationMenu.hidden = true;
    if (activeConversationMenuButton) {
      activeConversationMenuButton.setAttribute("aria-expanded", "false");
      if (options.restoreFocus) {
        activeConversationMenuButton.focus();
      }
    }
    activeConversationMenuButton = null;
    menuConversationId = null;
    menuConversationTitle = "";
  }

  async function runConversationMenuAction(action) {
    const conversationId = menuConversationId;
    const title = menuConversationTitle;
    closeConversationMenu();

    if (!conversationId) {
      return;
    }
    if (action === "rename") {
      await renameConversation(conversationId, title);
      return;
    }
    if (action === "delete") {
      await deleteConversation(conversationId);
    }
  }

  async function renameConversation(conversationId, currentTitle) {
    const nextTitle = window.prompt("Rename conversation", currentTitle || "");
    if (nextTitle === null) {
      return;
    }

    const title = nextTitle.trim();
    if (!title || title === currentTitle) {
      return;
    }

    try {
      const response = await fetch(`${conversationsUrl}/${conversationId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ title }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Could not rename conversation.");
      }

      await loadConversationsWithoutOpening();
      if (currentConversationId) {
        markActiveConversation(currentConversationId);
      }
    } catch {
      window.alert("Could not rename this conversation.");
    }
  }

  async function deleteConversation(conversationId) {
    const shouldDelete = window.confirm("Delete this conversation?");
    if (!shouldDelete) {
      return;
    }

    try {
      const response = await fetch(`${conversationsUrl}/${conversationId}`, {
        method: "DELETE",
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Could not delete conversation.");
      }

      if (currentConversationId === conversationId) {
        currentConversationId = null;
        resetJobContext();
        showWelcome();
      }
      await loadConversationsWithoutOpening();
      if (currentConversationId) {
        markActiveConversation(currentConversationId);
      }
    } catch {
      showError("Could not delete this conversation.");
    }
  }

  function renderMessages(messages) {
    messagesEl.replaceChildren();
    messagesEl.removeAttribute("aria-busy");

    if (!messages.length) {
      showWelcome();
      return;
    }

    starters.classList.add("is-hidden");
    messages.forEach((message) => appendMessage(message));
    scrollMessagesToBottom();
  }

  function appendMessage(message) {
    const item = document.createElement("article");
    item.className = `chat-message chat-message-${message.role}`;
    if (message.pending) {
      item.classList.add("is-pending");
    }
    if (message.streaming) {
      item.classList.add("is-streaming");
    }
    if (message.error) {
      item.classList.add("is-error");
    }

    const role = document.createElement("div");
    role.className = "chat-message-role";
    role.textContent = message.role === "user" ? "You" : "Career Assistant";

    const bubble = document.createElement("div");
    bubble.className = "chat-message-bubble";
    if (message.role === "assistant") {
      renderAssistantContent(bubble, message.content);
    } else {
      bubble.textContent = message.content;
    }

    item.append(role, bubble);

    if (
      message.role === "assistant"
      && !message.pending
      && !message.streaming
      && !message.error
      && !message.welcome
    ) {
      const actions = buildAssistantActions(message);
      item.append(actions);
    }

    messagesEl.append(item);
    scrollMessagesToBottom();
    return item;
  }

  function renderAssistantContent(container, content) {
    container.replaceChildren();
    const lines = String(content || "").split(/\r?\n/);
    let paragraphLines = [];
    let activeList = null;

    const flushParagraph = () => {
      if (!paragraphLines.length) {
        return;
      }
      const paragraph = document.createElement("p");
      paragraph.textContent = paragraphLines.join(" ");
      container.append(paragraph);
      paragraphLines = [];
    };

    const flushList = () => {
      activeList = null;
    };

    lines.forEach((rawLine) => {
      const line = rawLine.trim();
      if (!line) {
        flushParagraph();
        flushList();
        return;
      }

      const heading = parseAssistantHeading(line);
      if (heading) {
        flushParagraph();
        flushList();
        const title = document.createElement("h3");
        title.textContent = heading;
        container.append(title);
        return;
      }

      const bullet = line.match(/^[-*]\s+(.+)$/);
      if (bullet) {
        flushParagraph();
        if (!activeList || activeList.tagName !== "UL") {
          activeList = document.createElement("ul");
          container.append(activeList);
        }
        const item = document.createElement("li");
        item.textContent = bullet[1];
        activeList.append(item);
        return;
      }

      const ordered = line.match(/^\d+[.)]\s+(.+)$/);
      if (ordered) {
        flushParagraph();
        if (!activeList || activeList.tagName !== "OL") {
          activeList = document.createElement("ol");
          container.append(activeList);
        }
        const item = document.createElement("li");
        item.textContent = ordered[1];
        activeList.append(item);
        return;
      }

      flushList();
      paragraphLines.push(line);
    });

    flushParagraph();

    if (!container.childElementCount) {
      container.textContent = content || "";
    }
  }

  function parseAssistantHeading(line) {
    const markdownHeading = line.match(/^#{1,4}\s+(.+)$/);
    if (markdownHeading) {
      return markdownHeading[1].trim();
    }

    const numberedHeading = line.match(/^\d+\.\s+([A-Z][A-Za-z0-9 &/-]{2,80})$/);
    if (numberedHeading) {
      return numberedHeading[1].trim();
    }

    const knownHeadings = new Set([
      "Fit summary",
      "Strong matches",
      "Gaps to address",
      "How to position yourself",
      "Next actions",
      "Target Role Snapshot",
      "CV Edits To Prioritize",
      "Bullet Points To Rewrite",
      "Skills And Keywords To Surface",
      "Gaps To Address Honestly",
      "Final CV Checklist",
      "Interview Focus Areas",
      "Likely Interview Questions",
      "STAR Stories To Prepare",
      "Technical Practice",
      "Questions To Ask The Employer",
      "Practice Schedule",
      "Priority Skill Gaps",
      "Evidence Already Present",
      "Learning Plan",
      "Mini Projects To Prove The Skills",
      "Keywords To Add Only If True",
      "Progress Tracker",
      "Best-Fit Direction",
      "30-Day Plan",
      "60-Day Plan",
      "90-Day Plan",
      "Portfolio And Proof Of Work",
      "Application Strategy",
    ]);

    return knownHeadings.has(line) ? line : "";
  }

  function buildAssistantActions(message) {
    const actions = document.createElement("div");
    actions.className = "chat-message-actions";

    const copyButton = document.createElement("button");
    copyButton.className = "btn btn-outline-dark btn-sm";
    copyButton.type = "button";
    copyButton.textContent = "Copy";
    copyButton.addEventListener("click", async () => {
      try {
        await copyToClipboard(message.content);
        copyButton.textContent = "Copied";
      } catch {
        copyButton.textContent = "Copy failed";
      }
      window.setTimeout(() => {
        copyButton.textContent = "Copy";
      }, 1500);
    });
    actions.append(copyButton);

    if (
      [
        "cover_letter",
        "cv_tailoring_plan",
        "interview_prep",
        "skill_gap_plan",
        "career_roadmap",
      ].includes(message.metadata?.tool_action)
      && message.metadata?.download_url
    ) {
      const downloadLink = document.createElement("a");
      downloadLink.className = "btn btn-outline-dark btn-sm";
      downloadLink.href = message.metadata.download_url;
      downloadLink.textContent = "Download PDF";
      actions.append(downloadLink);
    }

    if (message.id) {
      [
        ["helpful", "Helpful"],
        ["not_helpful", "Not helpful"],
      ].forEach(([rating, label]) => {
        const button = document.createElement("button");
        button.className = "btn btn-outline-dark btn-sm";
        button.type = "button";
        button.textContent = label;
        if (message.feedback === rating) {
          button.classList.add("is-selected");
        }
        button.addEventListener("click", () => sendFeedback(message.id, rating, button));
        actions.append(button);
      });
    }

    const suggestedActions = message.metadata?.suggested_actions || [];
    suggestedActions.forEach((action) => {
      const chip = document.createElement("button");
      chip.className = "chat-suggested-action";
      chip.type = "button";
      chip.textContent = action;
      chip.addEventListener("click", () => {
        const normalizedAction = action.toLowerCase();
        if (normalizedAction === "generate cover letter") {
          showCoverLetterActionForm(actions);
          return;
        }
        if (normalizedAction === "create cv tailoring plan") {
          showCvPlanActionForm(actions);
          return;
        }
        if (normalizedAction === "prepare interview questions") {
          showInterviewActionForm(actions);
          return;
        }
        if (normalizedAction === "identify skill gaps") {
          showSkillGapActionForm(actions);
          return;
        }
        if (normalizedAction === "create career roadmap") {
          showRoadmapActionForm(actions);
          return;
        }
        input.value = action;
        input.focus();
      });
      actions.append(chip);
    });

    return actions;
  }

  function showInterviewActionForm(actions) {
    showGeneratedArtifactForm({
      actions,
      template: interviewTemplate,
      selector: "[data-chat-interview-form]",
      fallbackPrompt: "Prepare interview questions",
      statusMessage: "This can use your active job description if one is attached.",
      submit: createInterviewPrepFromChat,
    });
  }

  function showSkillGapActionForm(actions) {
    showGeneratedArtifactForm({
      actions,
      template: skillGapTemplate,
      selector: "[data-chat-skill-gap-form]",
      fallbackPrompt: "Identify skill gaps",
      statusMessage: "Paste the job description above before tracking gaps.",
      requiresJobDescription: true,
      submit: createSkillGapPlanFromChat,
    });
  }

  function showRoadmapActionForm(actions) {
    showGeneratedArtifactForm({
      actions,
      template: roadmapTemplate,
      selector: "[data-chat-roadmap-form]",
      fallbackPrompt: "Create a career roadmap",
      statusMessage: "This can use your active job description if one is attached.",
      submit: createCareerRoadmapFromChat,
    });
  }

  function showGeneratedArtifactForm({
    actions,
    template,
    selector,
    fallbackPrompt,
    statusMessage,
    requiresJobDescription = false,
    submit,
  }) {
    if (!template) {
      input.value = fallbackPrompt;
      input.focus();
      return;
    }

    const existingForm = actions.querySelector(selector);
    if (existingForm) {
      existingForm.querySelector("input")?.focus();
      return;
    }

    const formNode = template.content.firstElementChild.cloneNode(true);
    const firstInput = formNode.querySelector("input");
    const cancelButton = formNode.querySelector("[data-chat-tool-cancel]");
    const status = formNode.querySelector(".chat-tool-status");

    cancelButton.addEventListener("click", () => formNode.remove());
    formNode.addEventListener("submit", async (event) => {
      event.preventDefault();
      await submit(formNode, status);
    });

    actions.append(formNode);
    if (requiresJobDescription && !jobDescription.value.trim()) {
      setJobPanelVisible(true);
    }
    status.textContent = statusMessage || "";
    firstInput?.focus();
  }

  async function createInterviewPrepFromChat(toolForm, status) {
    await runChatArtifactAction({
      toolForm,
      status,
      url: interviewPrepActionUrl,
      loadingText: "Preparing questions...",
      fallbackError: "Could not prepare interview questions.",
      requiresJobDescription: false,
      statusKind: "interview",
      actionBase: "Prepare interview questions",
    });
  }

  async function createSkillGapPlanFromChat(toolForm, status) {
    await runChatArtifactAction({
      toolForm,
      status,
      url: skillGapActionUrl,
      loadingText: "Tracking gaps...",
      fallbackError: "Could not identify skill gaps.",
      requiresJobDescription: true,
      refreshSkillGaps: true,
      statusKind: "skillGap",
      actionBase: "Identify skill gaps",
    });
  }

  async function createCareerRoadmapFromChat(toolForm, status) {
    await runChatArtifactAction({
      toolForm,
      status,
      url: careerRoadmapActionUrl,
      loadingText: "Creating roadmap...",
      fallbackError: "Could not create the roadmap.",
      requiresJobDescription: false,
      statusKind: "roadmap",
      actionBase: "Create a career roadmap",
      roleField: "target_role",
    });
  }

  async function runChatArtifactAction({
    toolForm,
    status,
    url,
    loadingText,
    fallbackError,
    requiresJobDescription,
    refreshSkillGaps = false,
    statusKind = "generic",
    actionBase = "",
    roleField = "role_title",
    requireRole = false,
    extraPayload = () => ({}),
  }) {
    if (isSending) {
      return;
    }

    const formData = new FormData(toolForm);
    const activeJobDescription = jobDescription.value.trim();
    const submitButton = toolForm.querySelector("button[type='submit']");
    const roleTitle = (formData.get("role_title") || "").trim();
    const targetRole = (formData.get("target_role") || "").trim();
    const company = (formData.get("company") || "").trim();

    status.classList.remove("is-error");
    if (latestContext && !latestContext.has_latest_cv) {
      status.textContent = "Upload a CV before using this action.";
      status.classList.add("is-error");
      return;
    }
    if (requireRole && !roleTitle) {
      status.textContent = "Add the role title first.";
      status.classList.add("is-error");
      return;
    }
    if (requiresJobDescription && !activeJobDescription) {
      setJobPanelVisible(true);
      jobDescription.focus();
      status.textContent = "Paste the job description first.";
      status.classList.add("is-error");
      return;
    }

    const controller = new AbortController();
    const localRole = roleField === "target_role" ? targetRole : roleTitle;
    appendMessage({
      role: "user",
      content: buildActionMessage(actionBase, localRole, company),
    });
    const streamMessage = appendStreamingAssistantMessage({
      statusKind,
      usesCv: true,
      usesJob: Boolean(activeJobDescription),
    });

    submitButton.disabled = true;
    status.textContent = loadingText;
    setStreamingControls(true, controller);

    try {
      const data = await streamJsonResponse(
        url,
        {
          conversation_id: currentConversationId,
          role_title: roleTitle,
          target_role: targetRole,
          company,
          job_description: activeJobDescription,
          ...extraPayload(formData),
        },
        {
          signal: controller.signal,
          onStatus: (event) => streamMessage.setStatus(event.message),
          onChunk: (event) => streamMessage.append(event.text),
        }
      );

      currentConversationId = data.conversation.id;
      setJobDescription(data.job_context?.content || activeJobDescription, {
        showPanel: false,
      });
      streamMessage.complete(data.assistant_message);
      toolForm.remove();
      await loadConversationsWithoutOpening();
      if (refreshSkillGaps) {
        if (data.skill_gaps?.length) {
          renderSkillGaps(data.skill_gaps);
        } else {
          await loadSkillGaps();
        }
      }
      markActiveConversation(currentConversationId);
    } catch (error) {
      if (error.name === "AbortError") {
        status.textContent = "Generation stopped";
        streamMessage.stop();
        return;
      }

      const streamEvent = error.streamEvent || {};
      if (streamEvent.conversation?.id) {
        currentConversationId = streamEvent.conversation.id;
        await loadConversationsWithoutOpening();
        markActiveConversation(currentConversationId);
      }
      streamMessage.fail(error.message || fallbackError);
      status.textContent = error.message || fallbackError;
      status.classList.add("is-error");
    } finally {
      submitButton.disabled = false;
      setStreamingControls(false);
    }
  }

  function showCvPlanActionForm(actions) {
    if (!cvPlanTemplate) {
      input.value = "Create a CV tailoring plan";
      input.focus();
      return;
    }

    const existingForm = actions.querySelector("[data-chat-cv-plan-form]");
    if (existingForm) {
      existingForm.querySelector("[name='role_title']")?.focus();
      return;
    }

    const formNode = cvPlanTemplate.content.firstElementChild.cloneNode(true);
    const roleInput = formNode.querySelector("[name='role_title']");
    const cancelButton = formNode.querySelector("[data-chat-tool-cancel]");
    const status = formNode.querySelector(".chat-tool-status");

    cancelButton.addEventListener("click", () => formNode.remove());
    formNode.addEventListener("submit", async (event) => {
      event.preventDefault();
      await createCvPlanFromChat(formNode, status);
    });

    actions.append(formNode);
    if (!jobDescription.value.trim()) {
      setJobPanelVisible(true);
      status.textContent = "Paste the job description above before creating the plan.";
    }
    roleInput.focus();
  }

  async function createCvPlanFromChat(toolForm, status) {
    await runChatArtifactAction({
      toolForm,
      status,
      url: cvTailoringActionUrl,
      loadingText: "Creating plan...",
      fallbackError: "Could not create the CV plan.",
      requiresJobDescription: true,
      statusKind: "cvPlan",
      actionBase: "Create a CV tailoring plan",
    });
  }

  function showCoverLetterActionForm(actions) {
    if (!coverLetterTemplate) {
      input.value = "Generate a cover letter";
      input.focus();
      return;
    }

    const existingForm = actions.querySelector("[data-chat-cover-letter-form]");
    if (existingForm) {
      existingForm.querySelector("[name='role_title']")?.focus();
      return;
    }

    const formNode = coverLetterTemplate.content.firstElementChild.cloneNode(true);
    const roleInput = formNode.querySelector("[name='role_title']");
    const cancelButton = formNode.querySelector("[data-chat-tool-cancel]");
    const status = formNode.querySelector(".chat-tool-status");

    cancelButton.addEventListener("click", () => formNode.remove());
    formNode.addEventListener("submit", async (event) => {
      event.preventDefault();
      await generateCoverLetterFromChat(formNode, status);
    });

    actions.append(formNode);
    if (!jobDescription.value.trim()) {
      setJobPanelVisible(true);
      status.textContent = "Paste the job description above before generating.";
    }
    roleInput.focus();
  }

  async function generateCoverLetterFromChat(toolForm, status) {
    await runChatArtifactAction({
      toolForm,
      status,
      url: coverLetterActionUrl,
      loadingText: "Generating letter...",
      fallbackError: "Could not generate the cover letter.",
      requiresJobDescription: true,
      statusKind: "coverLetter",
      actionBase: "Generate a cover letter",
      requireRole: true,
      extraPayload: (formData) => ({
        letter_style: formData.get("letter_style"),
        letter_length: formData.get("letter_length"),
      }),
    });
  }

  async function sendFeedback(messageId, rating, button) {
    if (!messageId) {
      return;
    }

    button.disabled = true;
    try {
      const response = await fetch(`/api/chat/messages/${messageId}/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ rating }),
      });

      if (!response.ok) {
        throw new Error("Feedback could not be saved.");
      }

      button.parentElement
        .querySelectorAll(".btn")
        .forEach((item) => item.classList.remove("is-selected"));
      button.classList.add("is-selected");
      button.textContent = "Saved";
      window.setTimeout(() => {
        button.textContent = rating === "helpful" ? "Helpful" : "Not helpful";
      }, 1400);
    } catch {
      button.textContent = "Try again";
      window.setTimeout(() => {
        button.textContent = rating === "helpful" ? "Helpful" : "Not helpful";
      }, 1400);
    } finally {
      button.disabled = false;
    }
  }

  function showWelcome() {
    messagesEl.replaceChildren();
    messagesEl.removeAttribute("aria-busy");
    starters.classList.remove("is-hidden");

    appendMessage({
      role: "assistant",
      content: "Hi. I can help review your CV, compare it with a role, prepare interview questions, or improve application writing.",
      welcome: true,
    });
  }

  function showError(message) {
    messagesEl.replaceChildren();
    starters.classList.add("is-hidden");
    appendMessage({
      role: "assistant",
      content: message,
      error: true,
    });
  }

  function clearActiveConversation() {
    conversationList
      .querySelectorAll(".chat-conversation-item, .chat-conversation-button")
      .forEach((button) => button.classList.remove("is-active"));
  }

  function markActiveConversation(conversationId) {
    clearActiveConversation();
    const active = conversationList.querySelector(
      `[data-conversation-id="${conversationId}"]`
    );
    active?.classList.add("is-active");
  }

  function setJobPanelVisible(isVisible) {
    jobPanel.classList.toggle("is-hidden", !isVisible);
    jobToggle.setAttribute("aria-expanded", String(isVisible));
  }

  function setJobDescription(value, options = {}) {
    jobDescription.value = value || "";
    if (Object.prototype.hasOwnProperty.call(options, "showPanel")) {
      setJobPanelVisible(Boolean(options.showPanel));
    } else if (!jobDescription.value.trim()) {
      setJobPanelVisible(false);
    }
    updateJobToggleState();
  }

  function resetJobContext() {
    setJobDescription("");
    setJobPanelVisible(false);
  }

  function updateJobToggleState() {
    const hasJobDescription = Boolean(jobDescription.value.trim());
    jobToggle.textContent = hasJobDescription
      ? "Job description attached"
      : "+ Job description";
    jobToggle.classList.toggle("is-attached", hasJobDescription);
  }

  function isNearBottom() {
    const distanceFromBottom =
      messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight;
    return distanceFromBottom < 140;
  }

  function maybeScrollMessagesToBottom(options = {}) {
    if (isNearBottom()) {
      scrollMessagesToBottom(options);
    }
  }

  function scrollMessagesToBottom(options = {}) {
    messagesEl.scrollTo({
      top: messagesEl.scrollHeight,
      behavior: options.smooth ? "smooth" : "auto",
    });
  }

  async function copyToClipboard(text) {
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
    document.execCommand("copy");
    textarea.remove();
  }
})();
