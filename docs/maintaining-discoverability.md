# 维护文档、仓库元数据与可发现性

[项目首页](../README.md) · [English](../README_EN.md) · [技能索引](skills.md)

## 内容来源与构建

- `docs/repository-metadata.json` 保存批准使用的 Description、Topics 和文档站地址；修改它不会自动修改 GitHub 设置。
- `docs/catalog.json` 是 32 个技能名称、用途、输入、输出和示例链接的唯一索引源。
- `docs/site/zh/` 和 `docs/site/en/` 保存双语文档正文；每个页面必须有相同路径的另一语言版本。
- `docs/site/template.html` 管理标题、摘要、canonical、hreflang 和 Open Graph；结构化数据由 `scripts/build_docs.py` 的 `page_schema()` 生成。
- 每页通过 `@graph` 关联 WebSite 与 WebPage；非首页的 BreadcrumbList 与可见面包屑一致，英文页返回英文首页。`tutorials/` 下的任务教程另有 TechArticle；未核实的作者资质、机构关系、日期和评价不写入标记。
- 标题和摘要应简洁、准确、逐页区分；60/160 字符仅能作编辑参考，不是 Google 的硬性上限，中文双宽计数也不等于实际像素。最终展示可能依设备、查询和 Google 的改写变化。`scripts/check_docs.py` 检查重复标题、重复描述、结构化数据引用和面包屑一致性；不把字数当作排名标准。
- `scripts/build_docs.py` 只复制明确允许的公开页面和资源到 `dist/site/`；不发布整个仓库、测试输出或本机状态。

```bash
python -m pip install -r requirements-docs.txt
python scripts/build_docs.py --sync-indexes
python scripts/check_docs.py
```

日常构建可省略 `--sync-indexes`，此时会检查已提交的 Markdown 索引与 catalog 一致。Python 依赖仅用于维护文档，不是技能安装要求。

## GitHub Pages

在仓库 Settings → Pages 中选择 GitHub Actions。`.github/workflows/docs.yml` 在 pull request 中构建和检查，在 `main` 更新后部署 `dist/site`。About Website 指向已成功上线的文档站。

生成页面具有独立标题、摘要、相互对应的中英文链接及 sitemap。项目站位于 GitHub Pages 的仓库子路径；站点地图地址是 `https://duyunzhoudyz.github.io/dyz-med-paper-skills/sitemap.xml`。项目子路径下的 `robots.txt` 不是域名根级 robots 控制，应通过站点地图和 Search Console 正确发现页面，不依赖该文件限制域级抓取。

### 首次验证和提交站点地图

1. 用自己的 Google 账号打开 [Search Console](https://search.google.com/search-console/)，添加「网址前缀」资源，完整输入 `https://duyunzhoudyz.github.io/dyz-med-paper-skills/`。这是 GitHub Pages 项目子路径，不要选需要控制 `github.io` DNS 的「网域」资源。
2. 在所有权验证中选择「HTML 标记」，从 `<meta name="google-site-verification" content="…">` 复制 `content` 的真实值。此值是公开的站点验证码，不是密码。
3. 把 `docs/repository-metadata.json` 的 `site_verification` 改成 `"site_verification": {"google": "实际验证码"}`，或只把验证码交给维护者代填。保留外层 JSON 结构；验证标签由构建器安全转义后写入所有页面。提交并推送到 `main` 后，等「Documentation and Pages」成功，再回 Search Console 点「验证」。
4. 在「站点地图」提交 `https://duyunzhoudyz.github.io/dyz-med-paper-skills/sitemap.xml`。如输入框已显示资源前缀，只填写 `sitemap.xml`。在「网址检查」先检查首页和最需要推广的教程，按界面提示请求编入索引。
5. 可选：打开 [Bing Webmaster Tools](https://www.bing.com/webmasters/)，从已验证的 Search Console 导入这个站点；只选择本项目并确认授权范围。也可选择 HTML meta 验证，把提供的值加入同一对象的 `bing` 字段。

只有账号登录、取得验证码和确认站点所有权需要使用者操作；不需要修改 GitHub Pages 的 DNS。不要删除已用于验证的标签。验证成功、提交 sitemap 和搜索引擎实际收录是不同状态；索引与排名仍需后续观察。

官方说明：[Google 所有权验证](https://support.google.com/webmasters/answer/9008080?hl=zh-Hans) · [Google 站点地图](https://support.google.com/webmasters/answer/7451001?hl=zh-Hans) · [Bing 添加和验证网站](https://www.bing.com/webmasters/help/add-and-verify-site-12184f8b)。

## 元数据、预览图与发布

Description 和 Topics 位于仓库首页 About 齿轮；发布前核对 `docs/repository-metadata.json`。Topics 目前为 18 个，不按数量硬凑到上限。

社交预览上传 `docs/assets/social-preview.jpg`。更换时维持 1280×640、低于 1 MB，修改标题或技能数量后同步检查图片文字。README 中的封面与 GitHub Social preview 是两个独立配置。

发布测试版 Release 时，将 tag 绑定到已检查的提交，附上安装入口、变化、验证范围和已知限制。离线检查通过不表示实际宿主路由或医学质量已通过验收。

## 记录实际效果

可使用已认证的 GitHub CLI 将流量快照写入忽略的本地审计目录：

```bash
python scripts/snapshot_repo_traffic.py
```

脚本读取最近 14 天的 views、clones、来源和热门内容，记录 UTC 时间；不设置定时任务、不发送消息、不提交私有流量记录。每周自行留存一次即可比较变化；克隆数不等于成功安装量。

查验 Description、Topic 和 README 字段匹配可用：

```text
user:duyunzhoudyz 医学论文 in:description
user:duyunzhoudyz topic:agent-skills
user:duyunzhoudyz topic:medical-writing
user:duyunzhoudyz PubMed in:readme
```

这些查询检查字段覆盖，不能单独证明排名提升。教程内容应围绕实际输入、步骤与输出持续完善；不重复堆砌关键词。
