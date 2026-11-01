# 文献导入与检索工具

## 本地导入

```text
python "<技能目录>/scripts/import_references.py" input.ris input.bib export.nbib pubmed.xml --output-dir library-v1
```

输出新目录，包含 library.json 与每批最多100条的 identity-batch-XXX.json。后者可直接交给 verify_references.py。前者保存原始字段、输入哈希、记录位置、合并来源和疑似冲突；导入成功不代表题录或全文已核实。

支持 UTF-8 RIS、字面值 BibTeX（嵌套花括号/引号）、PubMed NBIB 与 PubmedArticle XML。BibTeX 宏、字符串拼接与无法识别的格式明确拒绝，使用文献管理器导出字面字段后重试。不执行任何 BibTeX 内容。输入单文件上限20 MB。

相同 DOI/PMID 且无明确冲突才合并；标识符/题名冲突和相同题名年份保留人工复核。题名匹配会忽略大小写、标点和 BibTeX 保护花括号，但保留原始题名与字段；疑似重复仅发提示，不凭题名自动合并。输出顺序稳定，原文件不变。metadata 的导入和身份核验、摘要阅读、全文阅读仍是不同维度。

## PubMed 检索

query.txt 只放获准发送的公开主题检索式。不得放患者信息、未发表结果或正文。

```text
python "<技能目录>/scripts/search_pubmed.py" --query-file query.txt --online --authorization search-approval.json --max-records 500 --output-dir search-v1
```

授权文件含 query_sha256（query.txt 原始字节）、purpose=public_literature_search、destination=https://eutils.ncbi.nlm.nih.gov/entrez/eutils/、confirmed_at，以及 source.kind=human、actor_id、statement、reference。由助手根据真实会话授权记录填写，不要求用户手写，不补造确认。记录仅供追溯，不认证身份。已有明确授权可复用其真实来源。

检索使用 ESearch history 与 EFetch 分页，每页最多100条，最多取回10000条。保存 query、服务端翻译、总命中数、实际取回数、每页原始响应及哈希、错误和有限重试记录。429/5xx 最多3次请求，不打印凭据；固定主机、无代理、无重定向。超过限额或中途失败返回 partial，不能称全量完成；零命中可 completed，但不是“证明不存在”。

```text
python "<技能目录>/scripts/search_pubmed.py" --query-file query.txt --replay-dir previous-search/responses --max-records 500 --output-dir replay-v1
```

重放标记 offline_replay，不当作当前在线证据。responses/context.json 必须存在且查询哈希一致，不可给旧响应换一条新检索式。输出 pubmed.xml 可交给导入器；只保留成功完整页，不把缺页当完整。退出0=complete，1=partial/blocked 检索回执，2=启动条件错误。在线未获授权时零请求。

接口依据：[NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/)。本工具不宣称完成中文数据库检索、全文阅读、撤稿核查或系统综述纳入。
