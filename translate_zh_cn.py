#!/usr/bin/env python3
"""Generate and maintain the Simplified Chinese Sphinx message catalogs."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import polib

ROOT = Path(__file__).resolve().parent
LOCALE_DIR = ROOT / "source" / "locale" / "zh_CN" / "LC_MESSAGES"
CACHE_PATH = ROOT / "translation-cache-zh_CN.json"


def install_model() -> None:
    import argostranslate.package

    argostranslate.package.update_package_index()
    packages = argostranslate.package.get_available_packages()
    package = next(p for p in packages if p.from_code == "en" and p.to_code == "zh")
    print(f"Downloading Argos Translate model: {package}")
    archive = package.download()
    argostranslate.package.install_from_path(archive)
    print("English to Simplified Chinese model installed.")


# Markup, keyboard shortcuts, URLs, substitutions and code must survive unchanged.
TOKEN_PATTERNS = [
    re.compile(r"``[^`]+``"),
    re.compile(r"\|[^|\n]+\|"),
    re.compile(r"https?://[^\s<>]+"),
    re.compile(r":[A-Za-z][A-Za-z0-9_+.-]*:"),
    re.compile(r"<[^<>\n]+>"),
    re.compile(r"\{[^{}\n]+\}"),
    re.compile(r"%(?:\([^)]+\))?[#0 +\-]?\d*(?:\.\d+)?[diouxXeEfFgGcrs%]"),
    re.compile(r"\*\*|__|``|`"),
    re.compile(r"(?<=`)_(?!_)"),
]
TOKEN_RE = re.compile("|".join(f"(?:{p.pattern})" for p in TOKEN_PATTERNS))
PLACEHOLDER_RE = re.compile(r"(?:⟦|［|【|\[)\s*(\d+)\s*(?:⟧|］|】|\])")

# Consistent QElectroTech terminology. Applied after machine translation.
ZH_REPLACEMENTS = [
    ("对开本", "图幅"),
    ("活页", "图幅"),
    ("标题块", "图框"),
    ("标题栏", "图框"),
    ("指挥家", "导体"),
    ("售票员", "导体"),
    ("原理图元素", "原理图元件"),
    ("示意图元素", "示意图元件"),
    ("主元素", "主元件"),
    ("从元素", "从元件"),
    ("从属元素", "从属元件"),
    ("终端块", "端子排"),
    ("接线端子", "端子"),
    ("项目收藏", "元件集合"),
    ("要素收集", "元件集合"),
    ("元素收集", "元件集合"),
    ("元素集合", "元件集合"),
    ("发射QET", "启动 QET"),
    ("发射qet", "启动 QET"),
    ("\"约\"窗口", "“关于”窗口"),
    ("海关安装", "自定义安装"),
    ("工程", "项目"),
]

EXACT_TRANSLATIONS = {
    "Home": "首页",
    "QET Homepage": "QET 主页",
    "QET Forum": "QET 论坛",
    "Welcome to the QET Documentation": "欢迎使用 QET 文档",
    "User Docs": "用户文档",
    "Developer Docs": "开发者文档",
    "Documentation Changelog": "文档更新日志",
    "FAQ": "常见问题",
    "Project": "项目",
    "Projects": "项目",
    "File": "文件",
    "Edit": "编辑",
    "View": "视图",
    "Settings": "设置",
    "Help": "帮助",
    "New": "新建",
    "Open": "打开",
    "Save": "保存",
    "Save as": "另存为",
    "Close": "关闭",
    "Quit": "退出",
    "Copy": "复制",
    "Cut": "剪切",
    "Paste": "粘贴",
    "Delete": "删除",
    "Undo": "撤销",
    "Redo": "重做",
    "Select all": "全选",
    "Select none": "取消选择",
    "Fullscreen": "全屏",
    "Full screen": "全屏",
    "Search": "搜索",
    "Replace": "替换",
    "Print": "打印",
    "Export": "导出",
    "Import": "导入",
    "Properties": "属性",
    "General": "常规",
    "Display": "显示",
    "Appearance": "外观",
    "Language": "语言",
    "Elements": "元件",
    "Element": "元件",
    "Folio": "图幅",
    "Folios": "图幅",
    "Conductor": "导体",
    "Conductors": "导体",
    "Title block": "图框",
    "Title blocks": "图框",
    "App Changelog": "应用更新日志",
    "Linux": "Linux",
    "Windows": "Windows",
    "macOS": "macOS",
    "Native": "原生环境",
    "Containerized": "容器化环境",
    "Prerequisites": "前置条件",
    "project": "项目",
    "menu bar": "菜单栏",
    "toolbar": "工具栏",
    "properties": "属性",
    "element": "元件",
    "elements": "元件",
    "conductor": "导体",
    "conductors": "导体",
    "folio": "图幅",
    "folios": "图幅",
    "title block": "图框",
    "part": "部件",
    "parts": "部件",
    "workspace": "工作区",
    "drawing area": "绘图区",
    "text": "文本",
    "dynamic text field": "动态文本字段",
    "Line": "线条",
    "Rectangle": "矩形",
    "Ellipse": "椭圆",
    "Arc": "圆弧",
    "Polygon": "多边形",
    "Terminal": "端子",
}


def protect_markup(text: str) -> tuple[str, list[str]]:
    tokens: list[str] = []

    def replace(match: re.Match[str]) -> str:
        tokens.append(match.group(0))
        return f"[{len(tokens) - 1}]"

    return TOKEN_RE.sub(replace, text), tokens


def restore_markup(text: str, tokens: list[str]) -> str:
    text = PLACEHOLDER_RE.sub(lambda m: tokens[int(m.group(1))], text)
    return text


def has_translatable_text(text: str) -> bool:
    plain = TOKEN_RE.sub("", text)
    return bool(re.search(r"[A-Za-z]{2,}", plain))


def postprocess(text: str) -> str:
    for old, new in ZH_REPLACEMENTS:
        text = text.replace(old, new)
    # Machine translation often inserts spaces immediately inside RST markers.
    text = re.sub(r"\*\*\s*([^*\n]+?)\s*\*\*", lambda m: f"**{m.group(1).strip()}**", text)
    text = re.sub(r"(?<!\*)\*\s*([^*\n]+?)\s*\*(?!\*)", lambda m: f"*{m.group(1).strip()}*", text)
    text = re.sub(r"`\s*([^`]+?)\s*(`_)", lambda m: f"`{m.group(1).strip()}`_", text)
    text = re.sub(
        r"(:[A-Za-z][A-Za-z0-9_+.-]*:)`\s*([^`]+?)\s*`",
        lambda m: f"{m.group(1)}`{m.group(2).strip()}`",
        text,
    )

    def normalize_link(match: re.Match[str]) -> str:
        label = match.group(1).strip()
        target = match.group(2)
        if target.startswith("<http") and " " in target:
            target = "<" + target[1:].split()[0] + ">"
        return f"`{label} {target}`_"

    text = re.sub(r"`([^`<>]+?)\s*(<[^<>\n]+>)`_", normalize_link, text)
    text = re.sub(r"：(?=[A-Za-z][A-Za-z0-9_+.-]*:`)", ":", text)
    # Normalize Chinese punctuation, but never turn an RST role such as :doc: into text.
    text = re.sub(r"(?<=[\u4e00-\u9fff]) +(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s*,\s*", "，", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s*\.\s*", "。", text)
    text = re.sub(r"(?<=_)\s*,\s*", "，", text)
    text = re.sub(r"(?<=_)\s*\.\s*", "。", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s*:\s*(?![A-Za-z][A-Za-z0-9_+.-]*:)", "：", text)
    # Add spacing around complete inline constructs, never just inside delimiters.
    inline_re = re.compile(
        r"``[^`]+``|:[A-Za-z][A-Za-z0-9_+.-]*:`[^`]+`|\|[^|\n]+\|"
        r"|`[^`]+`_|\*\*[^*\n]+\*\*|(?<!\*)\*[^*\n]+\*(?!\*)"
    )

    def space_inline(match: re.Match[str]) -> str:
        before = text[match.start() - 1] if match.start() else ""
        after = text[match.end()] if match.end() < len(text) else ""
        prefix = " " if before and "一" <= before <= "鿿" else ""
        suffix = " " if after and "一" <= after <= "鿿" else ""
        return prefix + match.group(0) + suffix

    text = inline_re.sub(space_inline, text)
    return text.strip()


def normalize_references(source: str, translated: str) -> str:
    """Translate labels and embed the original named target in each simple ref."""
    translated = postprocess(translated)
    reference_re = re.compile(r"`([^`<>]+?)`_")
    originals = reference_re.findall(source)
    if not originals:
        return translated
    # Canonicalize aliases produced by earlier runs before processing simple refs.
    for original in originals:
        alias_re = re.compile(r"`([^`<>]+?)\s*<" + re.escape(original) + r"_?>`_")
        translated = alias_re.sub(lambda m: f"`{m.group(1).strip()} <{original}_>`_", translated)
    exact_lookup = {key.casefold(): value for key, value in EXACT_TRANSLATIONS.items()}
    index = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal index
        if index >= len(originals):
            return match.group(0)
        original = originals[index]
        index += 1
        label = exact_lookup.get(original.casefold(), match.group(1).strip())
        return f"`{label} <{original}_>`_"

    return postprocess(reference_re.sub(replace, translated))


def load_cache() -> dict[str, str]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict[str, str]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = CACHE_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(CACHE_PATH)


class ArgosBatchTranslator:
    """Use Argos' CTranslate2 model directly so catalogs translate in batches."""

    def __init__(self) -> None:
        import ctranslate2
        import argostranslate.package

        self.pkg = next(
            p for p in argostranslate.package.get_installed_packages()
            if p.from_code == "en" and p.to_code == "zh"
        )
        self.translator = ctranslate2.Translator(
            str(self.pkg.package_path / "model"), device="cpu"
        )

    def translate(self, texts: list[str]) -> list[str]:
        tokenized = [self.pkg.tokenizer.encode(text) for text in texts]
        options = {}
        if self.pkg.target_prefix:
            options["target_prefix"] = [[self.pkg.target_prefix]] * len(tokenized)
        results = self.translator.translate_batch(
            tokenized,
            replace_unknowns=True,
            max_batch_size=32,
            batch_type="tokens",
            beam_size=4,
            num_hypotheses=1,
            length_penalty=0.2,
            return_scores=False,
            **options,
        )
        output = []
        for result in results:
            value = self.pkg.tokenizer.decode(result.hypotheses[0])
            if self.pkg.target_prefix and value.startswith(self.pkg.target_prefix):
                value = value[len(self.pkg.target_prefix):]
            output.append(value.lstrip())
        return output


def translate_catalogs(limit: int | None = None) -> None:
    cache = {key: normalize_references(key, value) for key, value in load_cache().items()}
    files = sorted(LOCALE_DIR.rglob("*.po"))
    entries_by_id: dict[str, list[polib.POEntry]] = {}
    catalogs: list[polib.POFile] = []
    for path in files:
        catalog = polib.pofile(str(path), encoding="utf-8")
        catalogs.append(catalog)
        for entry in catalog:
            if entry.msgid and not entry.obsolete:
                entries_by_id.setdefault(entry.msgid, []).append(entry)

    for msgid, translated in EXACT_TRANSLATIONS.items():
        if msgid in entries_by_id:
            cache[msgid] = translated
    pending = [
        msgid for msgid in entries_by_id
        if msgid not in cache and has_translatable_text(msgid)
    ]
    if limit is not None:
        pending = pending[:limit]
    total = len(pending)
    print(f"Catalogs: {len(files)}; unique messages: {len(entries_by_id)}; pending: {total}")

    started = time.monotonic()
    translator = ArgosBatchTranslator() if pending else None
    failed = []
    for start in range(0, total, 64):
        source_batch = pending[start:start + 64]
        protected_batch = [protect_markup(msgid) for msgid in source_batch]
        raw_batch = translator.translate([item[0] for item in protected_batch])
        for msgid, (_, tokens), raw in zip(source_batch, protected_batch, raw_batch):
            try:
                translated = restore_markup(raw, tokens)
                expected_markup = Counter(TOKEN_RE.findall(msgid))
                actual_markup = Counter(TOKEN_RE.findall(translated))
                if actual_markup != expected_markup:
                    raise ValueError("inline markup placeholder was not preserved")
                translated = postprocess(translated)
                if not translated:
                    raise ValueError("empty translation")
                cache[msgid] = normalize_references(msgid, translated)
            except Exception:
                failed.append(msgid)
        save_cache(cache)
        elapsed = time.monotonic() - started
        print(f"Processed {min(start + 64, total)}/{total}; elapsed {elapsed:.1f}s", flush=True)

    if failed:
        from translate_fallback import translate_markup_safe

        print(f"Retrying {len(failed)} messages with markup-safe segmented translation.")
        fallback = translate_markup_safe(failed, translator, postprocess)
        for msgid, translated in zip(failed, fallback):
            if Counter(TOKEN_RE.findall(msgid)) == Counter(TOKEN_RE.findall(translated)):
                cache[msgid] = normalize_references(msgid, translated)
            else:
                print(f"WARNING: markup mismatch remains in {msgid!r}", file=sys.stderr)
        save_cache(cache)

    for msgid, entries in entries_by_id.items():
        if msgid in cache:
            for entry in entries:
                entry.msgstr = cache[msgid]
                if "fuzzy" in entry.flags:
                    entry.flags.remove("fuzzy")
        elif not has_translatable_text(msgid):
            for entry in entries:
                entry.msgstr = msgid

    for catalog in catalogs:
        catalog.metadata["Language"] = "zh_CN"
        catalog.metadata["PO-Revision-Date"] = time.strftime("%Y-%m-%d %H:%M%z")
        catalog.metadata["Last-Translator"] = "QElectroTech Chinese documentation contributors"
        catalog.save()
    save_cache(cache)
    print(f"Saved {len(catalogs)} Chinese catalogs and {len(cache)} cached translations.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install-model", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.install_model:
        install_model()
    else:
        translate_catalogs(args.limit)


if __name__ == "__main__":
    main()
