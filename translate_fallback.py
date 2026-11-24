"""Translate prose around reStructuredText inline markup without moving markup."""

from __future__ import annotations

import re

INLINE_RE = re.compile(
    r"``[^`]+``"
    r"|:[A-Za-z][A-Za-z0-9_+.-]*:`[^`]+`"
    r"|\|[^|\n]+\|"
    r"|`[^`]+`_"
    r"|\*\*[^*\n]+\*\*"
    r"|(?<!\*)\*[^*\n]+\*(?!\*)"
)
MARKER_RE = re.compile(r"\x00(\d+)\x00")
TARGET_RE = re.compile(r"\s*(<[^<>\n]+>)$")
LITERAL_ROLES = {
    "code", "literal", "kbd", "file", "path", "command", "program",
    "option", "envvar", "regexp", "samp", "mimetype", "abbr",
}


def translate_markup_safe(messages, translator, postprocess):
    """Translate text and visible labels separately, then reassemble each message."""
    tasks = []
    templates = []

    for message in messages:
        parts = []

        def add_text(text):
            if not text:
                return
            leading = re.match(r"^\s*", text).group(0)
            trailing = re.search(r"\s*$", text).group(0)
            core = text[len(leading):len(text) - len(trailing) if trailing else None]
            if not core or not re.search(r"[A-Za-z]{2,}", core):
                parts.append(text)
                return
            index = len(tasks)
            tasks.append(core)
            parts.append(f"{leading}\x00{index}\x00{trailing}")

        def add_labeled_markup(prefix, label, suffix):
            index = len(tasks)
            tasks.append(label)
            parts.append(f"{prefix}\x00{index}\x00{suffix}")

        cursor = 0
        for match in INLINE_RE.finditer(message):
            add_text(message[cursor:match.start()])
            token = match.group(0)
            if token.startswith("``") or token.startswith("|"):
                parts.append(token)
            elif token.startswith(":"):
                role, content = re.match(r"^:([^:]+):`([^`]+)`$", token).groups()
                if role in LITERAL_ROLES:
                    parts.append(token)
                else:
                    target_match = TARGET_RE.search(content)
                    target = target_match.group(1) if target_match else ""
                    label = content[:target_match.start()] if target_match else content
                    add_labeled_markup(f":{role}:`", label, f"{target}`")
            elif token.startswith("`"):
                content = token[1:-2]
                target_match = TARGET_RE.search(content)
                target = target_match.group(1) if target_match else ""
                label = content[:target_match.start()] if target_match else content
                add_labeled_markup("`", label, f"{target}`_")
            elif token.startswith("**"):
                add_labeled_markup("**", token[2:-2], "**")
            elif token.startswith("*"):
                add_labeled_markup("*", token[1:-1], "*")
            else:
                parts.append(token)
            cursor = match.end()
        add_text(message[cursor:])
        templates.append("".join(parts))

    translated_tasks = translator.translate(tasks) if tasks else []
    translated_tasks = [postprocess(text) for text in translated_tasks]
    output = []
    for template in templates:
        output.append(MARKER_RE.sub(lambda m: translated_tasks[int(m.group(1))], template))
    return output
