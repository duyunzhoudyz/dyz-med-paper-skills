# 维护文档、仓库元数据与可发现性

[项目首页](../README.md) · [English](../README_EN.md) · [技能索引](skills.md)

## 内容来源与构建

- `docs/repository-metadata.json` 保存批准使用的 Description、Topics 和文档站地址；修改它不会自动修改 GitHub 设置。
- `docs/catalog.json` 是 32 个技能名称、用途、输入、输出和示例链接的唯一索引源。
- `docs/site/zh/` 和 `docs/site/en/` 保存双语文档正文；每个页面必须有相同路径的另一语言版本。
- `docs/site/template.html` 管理标题、摘要、canonical、hreflang、Open Graph 和 WebPage 结构化数据。
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

如需 Search Console，使用有权限的 Google 账号添加该文档站的 URL-prefix property，按其界面提供的验证方式完成所有权验证，然后提交上述 sitemap。不要在仓库域名页面上虚构已验证状态；索引和排名需要后续观察。

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
