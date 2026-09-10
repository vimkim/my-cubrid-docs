<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="stylesheet" href="/brand/skill/styles.css" />
    <title>Warp Brand Skill (Machine)</title>
    <meta
      name="description"
      content="Machine-facing Warp brand skill in markdown format."
    />
  </head>
  <body>
    <main class="skill-machine">
      <button
        id="copyBtn"
        class="copy-btn"
        type="button"
        title="Copy raw markdown"
        aria-label="Copy raw markdown"
      >
        <svg
          class="copy-icon copy-icon-default"
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden="true"
        >
          <rect
            x="5"
            y="1"
            width="9"
            height="11"
            rx="1"
            stroke="currentColor"
            stroke-width="1.2"
          />
          <path
            d="M3 4H2a1 1 0 00-1 1v9a1 1 0 001 1h9a1 1 0 001-1v-1"
            stroke="currentColor"
            stroke-width="1.2"
          />
        </svg>
        <svg
          class="copy-icon copy-icon-check"
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden="true"
        >
          <path
            d="M3 8l3.5 3.5L13 4.5"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>
      <div id="skillContent" class="skill-content">Loading markdown…</div>
    </main>
    <div class="machine-toggle">
      <a href="/brand/guide" class="machine-toggle-btn">Human</a>
      <a href="/brand/skill" class="machine-toggle-btn machine-toggle-btn-active">
        Machine
      </a>
    </div>
    <script>
      const contentEl = document.getElementById("skillContent");
      const copyBtn = document.getElementById("copyBtn");
      let markdownSource = "";
      let copyResetTimer;

      function parseInlineSegments(line) {
        const segments = [];
        const matcher = /`([^`]+)`|\[([^\]]+)\]\(([^)]*)\)/g;
        let cursor = 0;
        let match;

        while ((match = matcher.exec(line)) !== null) {
          if (match.index > cursor) {
            segments.push({ type: "text", content: line.slice(cursor, match.index) });
          }
          if (typeof match[1] !== "undefined") {
            segments.push({ type: "inlineCode", content: `\`${match[1]}\`` });
          } else {
            segments.push({
              type: "link",
              text: match[2],
              url: match[3],
              raw: match[0],
            });
          }
          cursor = match.index + match[0].length;
        }

        if (cursor < line.length) {
          segments.push({ type: "text", content: line.slice(cursor) });
        }
        return segments.length ? segments : [{ type: "text", content: line }];
      }

      function parseMarkdownLines(markdown) {
        const lines = markdown.split("\n");
        const parsed = [];
        let inCode = false;
        let frontmatterEnd = -1;

        if (lines.length > 0 && lines[0].trim() === "---") {
          for (let idx = 1; idx < lines.length; idx++) {
            if (lines[idx].trim() === "---") {
              frontmatterEnd = idx;
              break;
            }
          }
        }

        for (let lineIndex = 0; lineIndex < lines.length; lineIndex++) {
          const line = lines[lineIndex];
          const inFrontmatter =
            frontmatterEnd !== -1 && lineIndex >= 0 && lineIndex <= frontmatterEnd;

          if (!inFrontmatter && /^```/.test(line)) {
            parsed.push({
              raw: line,
              segments: [{ type: "text", content: line }],
              inCode,
              isCodeFence: true,
              isH1: false,
              isH2: false,
              isH3: false,
              isSeparator: false,
              isEmpty: false,
            });
            inCode = !inCode;
            continue;
          }
          const isCodeLike = inCode || inFrontmatter;
          const isH3 = !isCodeLike && /^### /.test(line);
          const isH2 = !isCodeLike && !isH3 && /^## /.test(line);
          const isH1 = !isCodeLike && !isH2 && !isH3 && /^# /.test(line);

          parsed.push({
            raw: line,
            segments: isCodeLike
              ? [{ type: "text", content: line }]
              : parseInlineSegments(line),
            inCode: isCodeLike,
            isCodeFence: false,
            isH1,
            isH2,
            isH3,
            isSeparator: !inFrontmatter && line.trim() === "---",
            isEmpty: line.trim() === "",
          });
        }

        return parsed;
      }

      function createSegmentNode(segment) {
        if (segment.type === "link") {
          if (segment.url) {
            const link = document.createElement("a");
            link.className = "skill-link";
            link.href = segment.url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = segment.raw;
            return link;
          }
          const span = document.createElement("span");
          span.className = "skill-link-raw";
          span.textContent = segment.raw;
          return span;
        }

        if (segment.type === "inlineCode") {
          const span = document.createElement("span");
          span.className = "skill-inline-code";
          span.textContent = segment.content;
          return span;
        }

        const span = document.createElement("span");
        span.textContent = segment.content;
        return span;
      }

      function renderMarkdown(markdown) {
        const lines = parseMarkdownLines(markdown);
        const fragment = document.createDocumentFragment();

        for (const line of lines) {
          if (line.isCodeFence) {
            const fence = document.createElement("div");
            fence.className = "skill-line skill-line-code-fence";
            fence.textContent = line.raw;
            fragment.appendChild(fence);
            continue;
          }

          if (line.inCode) {
            const code = document.createElement("div");
            code.className = "skill-line skill-line-code";
            code.textContent = line.raw || "\u00A0";
            fragment.appendChild(code);
            continue;
          }

          if (line.isSeparator) {
            const separator = document.createElement("div");
            separator.className = "skill-separator";
            fragment.appendChild(separator);
            continue;
          }

          if (line.isEmpty) {
            const empty = document.createElement("div");
            empty.className = "skill-empty";
            fragment.appendChild(empty);
            continue;
          }

          const lineEl = document.createElement("div");
          lineEl.className = "skill-line";
          if (line.isH1) lineEl.classList.add("skill-line-h1");
          if (line.isH2) lineEl.classList.add("skill-line-h2");
          if (line.isH3) lineEl.classList.add("skill-line-h3");

          for (const segment of line.segments) {
            lineEl.appendChild(createSegmentNode(segment));
          }
          fragment.appendChild(lineEl);
        }

        contentEl.innerHTML = "";
        contentEl.appendChild(fragment);
      }

      function setCopyState(isCopied) {
        copyBtn.classList.toggle("is-copied", isCopied);
      }

      async function loadMarkdown() {
        try {
          const response = await fetch("/brand/skill.md", { cache: "no-store" });
          markdownSource = await response.text();
          renderMarkdown(markdownSource);
        } catch (_) {
          contentEl.textContent =
            "Unable to load /brand/skill.md. Please refresh and try again.";
        }
      }

      copyBtn.addEventListener("click", async () => {
        if (!markdownSource) return;
        try {
          await navigator.clipboard.writeText(markdownSource);
          setCopyState(true);
          window.clearTimeout(copyResetTimer);
          copyResetTimer = window.setTimeout(() => setCopyState(false), 1800);
        } catch (_) {
          setCopyState(false);
        }
      });

      loadMarkdown();
    </script>
  </body>
</html>
