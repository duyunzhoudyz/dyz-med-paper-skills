# 检索记录骨架（对应 `paper/evidence/search-record.md`）

> 复制本文件到 `paper/evidence/search-record.md`（如尚不存在），每次检索后追加一条记录，不要覆盖
> 已有记录。若项目采用 PRISMA-S 编号体系，请同时标注对应的 S1-S11 条目编号（参见
> `templates/data/search-protocol.yaml` 里的 `prisma_s_checklist`）。

## 检索记录 SEARCH-001

- **检索日期**：<YYYY-MM-DD>
- **数据库/来源**：<PubMed / CNKI / 万方 / 维普 / Crossref / Google Scholar / 其他，按实际来源填写>
- **访问接口/平台**：<数据库原生网站 / 官方API / 机构平台 / 用户导出 / 普通网页搜索>
- **检索方式**：<实际原生数据库检索 / 标识符定向核验 / 网页线索发现 / 已有导入记录核对>
- **检索语言**：<中文 / 英文 / 其他；语言不决定接口或核实程度>
- **访问状态**：<实际已访问 / discovery_only / 未执行 / 权限受限 / 网络失败，附依据；中文来源不预设为网页发现>
- **精确检索式**：
  ```
  <粘贴实际执行的检索式，不要预先编造>
  ```
- **过滤条件**：日期范围 <...>；语种 <...>；研究类型 <...>；其他 <...>
- **结果数量**：<N>
- **关键 PMID / DOI**：<列出本次检索中判断为关键的文献标识符>
- **获取/阅读状态**：<full_text_read / abstract_only / discovery_only / access_failure_recorded；只读API题录另记metadata_only，不冒充读过摘要或全文>
- **题录身份核验**：<matched / mismatch / unverified；独立报告路径、条目ID、字段、日期与输入版本；未执行则明确写未执行>
- **论断支持裁定**：<由实际内容审计另行记录；题录匹配不自动生成SUPPORTED>
- **PRISMA-S 对应条目**（如适用）：<S1, S4, S9 等>
- **备注**：<例如"中文文献部分仅为网页搜索线索发现，未核实是否为核心期刊/最新版本">

---

## 检索记录 SEARCH-002

（复制上面的结构继续追加）

## 题录身份核验接口

Python 3.10+，仅标准库；工具为`dyz-med-cnki/scripts/verify_references.py`。可独立运行，不需安装/导入
兄弟技能，也不自动创建passport。默认离线，不解析RIS/BibTeX，不下载全文，不修改原始题录。

### 规范化题录

JSON顶层：`{"schema_version":"1.0","references":[...]}`；CSV首行为唯一表头，至少含`id,title`。
每批最多100条；每条字段只允许`id,doi,pmid,title,year,first_author,journal`，值均为字符串，最长4000字符。
JSON中的id须非空唯一；title缺失/空值保留unverified而不凭标识符通过。未知字段（含URL、摘要、正文、
凭据等）拒绝，需人工整理最小输入，不静默发送。示例只是虚构字段形状：

```json
{"schema_version":"1.0","references":[
  {"id":"R001","doi":"10.5555/synthetic.1","title":"Synthetic cohort study","year":"2020"}
]}
```

- DOI仅接受裸`10.<4至9位数字>/<安全ASCII后缀>`；DOI URL、空白、查询参数和片段拒绝发送，标unverified。
  极少数不在首版允许字符集内的合法DOI也交人工核实，不据格式判虚构。PMID为1至10位正整数字符串。
- 同时提供PMID/DOI时仅请求PubMed，取得元数据后在本地核对两个字段；仅DOI时请求Crossref。
  没有可用标识符不做题名猜搜；固定目的地为`https://api.crossref.org`与`https://eutils.ncbi.nlm.nih.gov`。
- 至少核对请求标识符和title；可选字段仅在提供时核对。题名/期刊/作者使用Unicode NFKC、大小写、
  HTML标签/实体及标点空白规范化后精确比较，不做模糊相似度。DOI忽略大小写，年份/PMID精确比较。
- year为Crossref published年份或PubMed pubdate年份；first_author分别使用Crossref首作者family或
  PubMed首作者name。出版版本、期刊缩写、姓名表达不同可能mismatch，不能自动替换用户字段，应人工复核。
  服务缺少应核对字段是unverified；缺项与差异同时存在时保留两者，汇总优先mismatch。

### 工件清单与离线响应

manifest为JSON，含R2同形`artifacts:[{id,path,version,sha256}]`：ID唯一、版本非空、真实字节SHA256。
默认题录ID为`references`；可用`roles:{references:"其他稳定ID",responses:"固定响应ID"}`显式映射。
所有引用及输出路径相对于显式`--root`；禁止绝对路径、盘符、反斜杠、空段、`.`、`..`与链接逃逸。
manifest参数本身相对于调用目录。不要按文件名猜身份，不重命名用户文件。

离线响应须登记为工件并通过roles.responses映射，格式为：

```json
{"schema_version":"1.0","responses":[
  {"provider":"crossref","identifier":"10.5555/synthetic.1","attempts":[
    {"status":404,"error":"http_error"}
  ]}
]}
```

成功attempt用`{status:200,body:<该API原始JSON对象>}`；超时可用`{status:null,error:"timeout"}`。
PubMed identifier用PMID，Crossref用小写DOI。响应可合成或来自合法已保存材料，但都属于离线重放，
本次不产生实时访问证据；原采集来源/日期另存证据，不能把重放时间当原采集时间。缺固定响应保持未核实。
完整成功/失败合成样例见仓库`tests/fixtures/reference-verification.json`，不是生产题录或真实批准。

### 联网授权（默认不启用）

只有人工核实当前来源与授权范围后才使用`--online --authorization <已登记授权JSON的artifact ID>`。
此参数不是文件路径或布尔值；授权JSON及其中人类来源证据文件均须在manifest.artifacts登记并哈希绑定。
授权JSON形状（尖括号均需真实记录替换，不能拿教学值当授权）：

```json
{
  "purpose":"reference_identity_verification",
  "content_category":"public_bibliographic_identifiers",
  "destinations":["https://api.crossref.org","https://eutils.ncbi.nlm.nih.gov"],
  "fields":["doi","pmid"],
  "approval":{
    "state":"confirmed",
    "targets":[{"artifact_id":"references","version":"<当前版本>","sha256":"<题录真实哈希>"}],
    "role":"<确认人角色>","confirmed_at":"<带时区时间>",
    "source":{
      "kind":"human","actor_id":"<角色化名>","statement":"<真实原话，说明用途、目的地、允许发送字段>",
      "reference":{"path":"<确认记录相对路径>","sha256":"<记录真实哈希>"},
      "locator":"<消息或段落定位>"
    }
  }
}
```

targets必须精确绑定本批题录；destinations/fields可更窄但必须覆盖本批每个计划请求。不接受未知目的地或
字段，任何授权维度缺失/不匹配整批blocked且零发送。当前人类授权来源不能由模型转述、布尔值或伪造时间替代；
机器预检结果仅`recorded_not_authenticated`，不认证身份、权限或法律有效性。输入/目的/接收方改变须重新确认。
没有可核实授权时保留not_confirmed和blocked，不用合成测试许可作真实联网授权。

只发送DOI或PMID和固定API协议参数，不发送题名、作者、年份、摘要或稿件。HTTP连接不读取代理环境凭据、
不加载cookie、不读API key，不跟随任何重定向；3xx、404、429均记录未核实，不能通过浏览器或换主机绕过。
默认每请求超时10秒，可用`--timeout`设置>0且≤30秒；这是网络请求超时，不是整批硬时限。
`--max-attempts`仅1或2，默认1；仅timeout/network_error/5xx允许有限重试，429与重定向不自动重试。
实际HTTP请求间隔至少0.4秒；失败尝试全部保留，不通过“最后成功”隐去早前失败。

### 命令、报告和退出码

```powershell
python -B dyz-med-cnki/scripts/verify_references.py paper/evidence/reference-artifacts.json --root . --report paper/evidence/reference-check-run-001.json --record paper/evidence/reference-check-run-001.check.json --check-id reference-check-run-001
python -B -m unittest discover -s tests -p test_verify_references.py -v
```

只有在上述授权来源已人工核实时才向第一条命令附加`--online --authorization <授权工件ID>`。
输出必须为新文件，不覆盖输入或旧报告。manifest内全部工件均纳入inputs并在运行前后核对字节；运行中改变
则不给当前检查回执。报告包含mode、每条identity_status、fields/differences/missing_fields、固定计划接口、
实际attempts及日期/HTTP状态/错误、network_requests、输入绑定和限制。未发送项的source仅为计划接口，
不是访问成功证据；offline时间是重放时间。成功网络响应记录原始字节哈希及比较字段，不保存全文。

独立check采用R2 1.1字段：scope.domain与domain_result.namespace为`reference_identity`，
inputs绑定工件版本/哈希，report引用已落盘领域报告的真实SHA256，checked_at带时区。报告不自哈希，
不自动写passport；检查ID跨运行唯一性由项目索引/人工负责。

| 退出码 | 含义 |
|---|---|
| 0 | 本次模式、输入和字段范围全部matched；离线0不是实时核实，在线0也不代表全文/论断得到支持 |
| 1 | 存在mismatch；保留并列未核实项，正常执行为completed而非failed |
| 3 | 无已检出差异但存在unverified/空清单，或授权不足blocked（domain_result=null，零发送） |
| 2 | CLI参数、输入解析/路径/文件/hash/I/O错误；无可登记完成检查，后段写失败可能留下报告 |

正常请求即使网络失败也输出completed+unverified和失败尝试，不伪装通过；授权不足输出blocked和reason。
`matched/mismatch/unverified`只描述题录身份。访问范围固定metadata_only，claim_support=not_assessed，
不能直接映射为SUPPORTED/PARTIAL/MISSTATED/UNSUPPORTED/UNVERIFIABLE/CONFLICTING；这些六类由内容审计
根据实际材料另行裁定。来源真实性、全文阅读和人工权限仍需人审。
