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
  const conversationList = document.querySelector("#chatConversationList");
  const skillGapList = document.querySelector("#chatSkillGapList");
  const messagesEl = document.querySelector("#chatMessages");
  const form = document.querySelector("#chatForm");
  const input = document.querySelector("#chatInput");
  const sendButton = document.querySelector("#chatSendButton");
  const newButton = document.querySelector("#chatNewButton");
  const includeCv = document.querySelector("#chatIncludeCv");
  const cvSelect = document.querySelector("#chatCvSelect");
  const cvToggleLabel = includeCv.closest(".chat-toggle")?.querySelector("span");
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

  let currentConversationId = null;
  let isSending = false;
  let latestContext = null;

  initChat();

  async function initChat() {
    bindEvents();
    await loadContextStatus();
    await loadSkillGaps();
    await loadConversations();
  }

  function bindEvents() {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      await sendMessage();
    });

    newButton.addEventListener("click", () => {
      currentConversationId = null;
      clearActiveConversation();
      resetJobContext();
      showWelcome();
      input.focus();
    });

    starters.addEventListener("click", (event) => {
      const button = event.target.closest("[data-starter-message]");
      if (!button) {
        return;
      }
      input.value = button.dataset.starterMessage;
      if (button.dataset.openJobContext === "true") {
        setJobPanelVisible(true);
        jobDescription.focus();
        return;
      }
      input.focus();
    });

    includeCv.addEventListener("change", updateContextStatusText);
    cvSelect.addEventListener("change", updateContextStatusText);

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

  async function loadContextStatus() {
    try {
      const response = await fetch(contextUrl);
      latestContext = await response.json();
      renderCvOptions(latestContext.cvs || []);
      updateContextStatusText();
    } catch {
      contextStatus.textContent = "CV/job text may be sent to the AI provider.";
    }

  }

  function renderCvOptions(cvs) {
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
    }
  }

  function renderSkillGaps(skillGaps) {
    skillGapList.replaceChildren();

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
      (cv) => String(cv.id) === String(cvSelect.value)
    );
    if (cvToggleLabel) {
      cvToggleLabel.textContent = selectedCv ? "Use selected CV" : "Use latest CV";
    }

    if (!includeCv.checked) {
      contextStatus.textContent = "CV context is off for the next message.";
      return;
    }

    if (!latestContext?.has_latest_cv) {
      contextStatus.textContent = "No uploaded CV found. Chat will use your message only.";
      return;
    }

    const skills = latestContext.detected_skills || [];
    const skillText = skills.length
      ? ` Skills found: ${skills.slice(0, 5).join(", ")}.`
      : "";
    contextStatus.textContent = `Using ${latestContext.latest_cv_filename}.${skillText} CV/job text may be sent to the AI provider.`;
  }

  async function loadConversations() {
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
    }
  }

  async function loadConversation(conversationId) {
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
    }
  }

  async function sendMessage() {
    const message = input.value.trim();

    if (!message || isSending) {
      return;
    }

    isSending = true;
    sendButton.disabled = true;
    input.value = "";
    starters.classList.add("is-hidden");

    appendMessage({
      role: "user",
      content: message,
    });
    const pending = appendMessage({
      role: "assistant",
      content: "Thinking...",
      pending: true,
    });

    try {
      const response = await fetch(sendUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          conversation_id: currentConversationId,
          message,
          include_latest_cv: includeCv.checked,
          cv_id: cvSelect.value || null,
          job_description: jobDescription.value.trim(),
        }),
      });
      const data = await response.json();

      pending.remove();

      if (!response.ok) {
        appendMessage({
          role: "assistant",
          content: data.error || "The assistant could not reply right now.",
          error: true,
        });
        if (data.conversation?.id) {
          currentConversationId = data.conversation.id;
          await loadConversationsWithoutOpening();
        }
        return;
      }

      currentConversationId = data.conversation.id;
      setJobDescription(data.job_context?.content || "", {
        showPanel: false,
      });
      appendMessage(data.assistant_message);
      await loadConversationsWithoutOpening();
      if (data.skill_gaps?.length) {
        renderSkillGaps(data.skill_gaps);
      } else {
        await loadSkillGaps();
      }
      markActiveConversation(currentConversationId);
    } catch {
      pending.remove();
      appendMessage({
        role: "assistant",
        content: "The assistant could not reply right now. Check your connection and try again.",
        error: true,
      });
    } finally {
      isSending = false;
      sendButton.disabled = false;
      input.focus();
    }
  }

  async function loadConversationsWithoutOpening() {
    const response = await fetch(conversationsUrl);
    const data = await response.json();
    renderConversationList(data.conversations || []);
  }

  function renderConversationList(conversations) {
    conversationList.replaceChildren();

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

      const title = document.createElement("span");
      title.className = "chat-conversation-title";
      title.textContent = conversation.title;

      const preview = document.createElement("span");
      preview.className = "chat-conversation-preview";
      const contextPrefix = conversation.has_job_description ? "Job attached. " : "";
      preview.textContent = `${contextPrefix}${conversation.latest_message || "New conversation"}`;

      button.append(title, preview);
      button.addEventListener("click", () => loadConversation(conversation.id));

      const deleteButton = document.createElement("button");
      deleteButton.className = "chat-conversation-delete";
      deleteButton.type = "button";
      deleteButton.textContent = "Del";
      deleteButton.title = "Delete conversation";
      deleteButton.setAttribute("aria-label", `Delete ${conversation.title}`);
      deleteButton.addEventListener("click", (event) => {
        event.stopPropagation();
        deleteConversation(conversation.id);
      });

      item.append(button, deleteButton);
      conversationList.append(item);
    });

    if (currentConversationId) {
      markActiveConversation(currentConversationId);
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
  }) {
    const formData = new FormData(toolForm);
    const activeJobDescription = jobDescription.value.trim();
    const submitButton = toolForm.querySelector("button[type='submit']");

    status.classList.remove("is-error");
    if (requiresJobDescription && !activeJobDescription) {
      setJobPanelVisible(true);
      jobDescription.focus();
      status.textContent = "Paste the job description first.";
      status.classList.add("is-error");
      return;
    }

    submitButton.disabled = true;
    status.textContent = loadingText;

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          conversation_id: currentConversationId,
          role_title: (formData.get("role_title") || "").trim(),
          target_role: (formData.get("target_role") || "").trim(),
          company: (formData.get("company") || "").trim(),
          job_description: activeJobDescription,
        }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || fallbackError);
      }

      currentConversationId = data.conversation.id;
      setJobDescription(data.job_context?.content || activeJobDescription, {
        showPanel: false,
      });
      appendMessage(data.user_message);
      appendMessage(data.assistant_message);
      toolForm.remove();
      await loadConversationsWithoutOpening();
      if (refreshSkillGaps) {
        await loadSkillGaps();
      }
      markActiveConversation(currentConversationId);
    } catch (error) {
      status.textContent = error.message || fallbackError;
      status.classList.add("is-error");
    } finally {
      submitButton.disabled = false;
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
    const formData = new FormData(toolForm);
    const activeJobDescription = jobDescription.value.trim();
    const submitButton = toolForm.querySelector("button[type='submit']");

    status.classList.remove("is-error");
    if (!activeJobDescription) {
      setJobPanelVisible(true);
      jobDescription.focus();
      status.textContent = "Paste the job description first.";
      status.classList.add("is-error");
      return;
    }

    submitButton.disabled = true;
    status.textContent = "Creating plan...";

    try {
      const response = await fetch(cvTailoringActionUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          conversation_id: currentConversationId,
          role_title: (formData.get("role_title") || "").trim(),
          company: (formData.get("company") || "").trim(),
          job_description: activeJobDescription,
        }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Could not create the CV plan.");
      }

      currentConversationId = data.conversation.id;
      setJobDescription(data.job_context?.content || activeJobDescription, {
        showPanel: false,
      });
      appendMessage(data.user_message);
      appendMessage(data.assistant_message);
      toolForm.remove();
      await loadConversationsWithoutOpening();
      markActiveConversation(currentConversationId);
    } catch (error) {
      status.textContent = error.message || "Could not create the CV plan.";
      status.classList.add("is-error");
    } finally {
      submitButton.disabled = false;
    }
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
    const formData = new FormData(toolForm);
    const roleTitle = (formData.get("role_title") || "").trim();
    const activeJobDescription = jobDescription.value.trim();
    const submitButton = toolForm.querySelector("button[type='submit']");

    status.classList.remove("is-error");
    if (!roleTitle) {
      status.textContent = "Add the role title first.";
      status.classList.add("is-error");
      return;
    }
    if (!activeJobDescription) {
      setJobPanelVisible(true);
      jobDescription.focus();
      status.textContent = "Paste the job description first.";
      status.classList.add("is-error");
      return;
    }

    submitButton.disabled = true;
    status.textContent = "Generating letter...";

    try {
      const response = await fetch(coverLetterActionUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          conversation_id: currentConversationId,
          role_title: roleTitle,
          company: (formData.get("company") || "").trim(),
          letter_style: formData.get("letter_style"),
          letter_length: formData.get("letter_length"),
          job_description: activeJobDescription,
        }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Could not generate the cover letter.");
      }

      currentConversationId = data.conversation.id;
      setJobDescription(data.job_context?.content || activeJobDescription, {
        showPanel: false,
      });
      appendMessage(data.user_message);
      appendMessage(data.assistant_message);
      toolForm.remove();
      await loadConversationsWithoutOpening();
      markActiveConversation(currentConversationId);
    } catch (error) {
      status.textContent = error.message || "Could not generate the cover letter.";
      status.classList.add("is-error");
    } finally {
      submitButton.disabled = false;
    }
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
    jobToggle.textContent = hasJobDescription ? "Job Added" : "Job Description";
    jobToggle.classList.toggle("btn-dark", hasJobDescription);
    jobToggle.classList.toggle("btn-outline-dark", !hasJobDescription);
  }

  function scrollMessagesToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
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
