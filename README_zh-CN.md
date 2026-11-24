# QElectroTech 简体中文文档

本仓库包含 QElectroTech 官方文档的简体中文机器翻译版本。英文 reStructuredText 源文件保持不变，中文译文采用 Sphinx 标准的 gettext 消息目录保存，便于后续同步上游更新。

上游源版本：`175435e635838822e17a4bc1c9f776aa4af62e55`。

## 直接阅读

构建后的首页位于 `build/html/zh_CN/index.html`。构建目录不参与版本控制。

## 本地构建

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/sphinx-build -b html -D language=zh_CN source build/html/zh_CN
```

在浏览器中打开 `build/html/zh_CN/index.html` 即可阅读。

## 翻译文件

- 中文消息目录：`source/locale/zh_CN/LC_MESSAGES/`
- 翻译缓存：`translation-cache-zh_CN.json`
- 离线翻译脚本：`translate_zh_cn.py`
- 复杂行内标记处理：`translate_fallback.py`
- 构建警告定位修复：`repair_zh_markup.py`

如需重新生成译文，请额外安装翻译依赖并下载英中模型：

```bash
.venv/Scripts/python -m pip install -r requirements-translate.txt
.venv/Scripts/python translate_zh_cn.py --install-model
.venv/Scripts/python translate_zh_cn.py
```

这是机器翻译初版。涉及操作步骤或电气专业术语时，建议结合 QElectroTech 的实际中文界面进行人工校订。
