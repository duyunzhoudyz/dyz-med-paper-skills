---
title: 项目状态、验证范围与使用许可
description: 了解 DYZ MedPaper 公开测试版的验证范围、工具依赖、PolyForm Noncommercial 许可、问题反馈和维护方式。
---
## 当前状态

DYZ MedPaper 是面向中国医生与医学研究生的公开测试版医学论文 Agent Skills 集合。核心内容包括 32 个技能、模板、参考资料、合成示例和本地脚本。

| 检查范围 | 能说明什么 | 不能说明什么 |
|---|---|---|
| 安装与文件自检 | 完整目录复制与字节一致性 | 宿主实际加载或调用正确 |
| 离线回归与合成流程 | 明确实现的工具和文件合同行为 | 模型写作质量或医学结论正确 |
| 文档站构建检查 | 页面、链接、语言和索引结构完整 | 搜索引擎已收录或排名提高 |

实际宿主路由、连续多轮写作和独立医学质量尚未全部完成验收。请查看 [实时离线检查]({{repo}}/actions/workflows/check.yml)、[详细验证说明]({{repo}}/blob/main/docs/readme-reference.md#validation) 和 [发布记录]({{repo}}/releases)。

## 工具与访问条件

- 内置在线文献检索脚本覆盖 PubMed。知网、万方、维普及其他数据库需要合法访问权限；仅发现线索不能当作完成检索或全文获取。
- 统计执行需要批准的具体计划、R 或既定统计引擎及所需包。安装技能不包含这些环境。
- 基础 DOCX 审阅稿可由本地脚本生成；复杂排版、公式、原生修订以及文件视觉检查需要其他工具。
- 本地数字或引用检查只覆盖明确实现的范围，不认证来源对论断的语义支持。

## 使用许可

项目源码公开，采用 [PolyForm Noncommercial License 1.0.0]({{repo}}/blob/main/LICENSE)。可在许可证允许的非商业范围内使用；超出许可范围需要[单独书面商业授权]({{repo}}/blob/main/COMMERCIAL-LICENSE.md)。第三方材料遵循各自条款。

## 反馈与参与

在 [GitHub Issues]({{repo}}/issues) 提供系统、宿主、复现步骤和脱敏报错。示例改进、术语修正和安装问题都可以反馈；请勿上传患者资料或账号凭据。

[贡献说明]({{repo}}/blob/main/CONTRIBUTING.md) · [维护与发布]({{repo}}/blob/main/docs/maintaining-discoverability.md) · [项目介绍与引用文案]({{repo}}/blob/main/docs/discovery-kit.md)
