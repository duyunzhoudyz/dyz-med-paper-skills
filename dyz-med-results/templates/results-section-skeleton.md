# 结果部分分节骨架模板

用途：按稳定工件ID `analysis-results` 找到显式登记的实际结果文件，结合方法部分的调整集，
把已核实数字填入骨架。兼容`paper/data/stats/analysis-results.json`、`analysis-results.yaml`、
用户已有的`structured_results.yaml`等路径，不自动改名，也不假定存在固定的嵌套字段。
外部统计软件/统计人员的可追溯输出同样可用，不要求先跑`dyz-med-analyze`。
每个方括号 `[...]` 只填已有事实，缺项标待核实；分节顺序按研究与期刊要求调整。

---

## 1. 研究对象与基线特征（Table 1 叙述）

[总样本量]例患者纳入分析，其中[组别A名称] [nA]例，[组别B名称] [nB]例。基线特征见表1。
[从来源表中已映射的Table 1结果挑选需要文字点出的关键变量，通常是年龄、性别、疾病分期等核心变量，
逐一用一句话陈述组间是否均衡]。

> 提醒：Table 1 用于描述研究人群，不应用基线显著性检验自动决定协变量。调整集应来自预设方案、
> 因果结构和临床知识；如存在重要不平衡，可描述其绝对差异，并在方法或敏感性分析中说明处理方式。

## 2. 主要结局（Primary Outcome）

[主要结局变量名]为预设的主要结局。经[调整变量集，来自方法与该analysis_id实际模型输出]
调整后，[干预组/暴露组] 相较于 [对照组] 的 [效应量类型，如 HR/OR/β] 为 [point_estimate]
（[实际置信水平] CI [ci_lower]-[ci_upper]，[如适用：P值及其调整/检验口径]）
[，事件数 [n_events]/该分析实际分母 [n_total]]；[时间点/观察窗及必要单位]。

> 提醒：临床解释记录不是必需输入。有记录时仍反查实际效应、整个CI、尺度、方向和时间点，
> 不直接照抄分类标签；缺可信阈值只描述效应与不确定性，不推断临床重要性。非显著不等于无效。
> 不适用CI/P值或调整集时删除对应句式并说明，不补造结果；调整P值与未调整CI可合法并存。

## 3. 次要结局（Secondary Outcomes，按预设顺序排列）

对每个次要结局按方法适用性报告效应量、CI、P值与调整集，实际置信水平替换示例95%，不要求通用模型：

- [次要结局1名称]：调整[调整变量集]后，[效应量类型] [point_estimate]（95% CI [ci_lower]-[ci_upper]，
  P=[p_value]）。
- [次要结局2名称]：……

## 4. 敏感性分析（如 /dyz-med-sensitivity 已完成）

[简述做了哪些敏感性分析，例如改变缺失数据处理方式、剔除某类亚组重新分析等]，结果[与主要分析一致/
不完全一致，具体差异是……]。

## 5. 亚组分析（报告分层估计及交互检验）

[亚组变量名称]的亚组分析分别报告各亚组效应估计与置信区间，并报告交互检验P值为[interaction_p]。
仅陈述统计结果，不对差异原因做解读。

> 提醒：亚组分析部分容易被误写成逐个亚组内部的显著性检验（"在女性亚组中P=0.03，在男性亚组中P=0.21"），
> 这种写法不能证明亚组间存在差异。应结合各亚组效应估计、置信区间与交互检验报告。

## 6. 事后探索性分析（如有）

在事后探索性分析中，[分析内容]显示[结果]。

> 提醒：如果这项分析在方法部分/统计分析计划里没有预先设定，建议在此处清晰标注为
> "事后探索性分析"（如"In a post-hoc exploratory analysis, ..."），这是审稿人通常期待看到的标注方式，
> 但具体措辞由用户决定，不强制套用固定句式。

---

## 图表标题占位

- 图题写在图的下方："Figure [N]. [简要描述性标题]。"
- 表题写在表的上方："Table [N]. [简要描述性标题]。"

## 结构化对账输入合同

本节定义`check_result_consistency.py`的最小业务格式，非通用统计模型。工具仅接受UTF-8 JSON，
`schema_version`为字符串`"1.0"`。不解析任意Word/PDF，不自动抽取正文或执行分析。

### 工件身份与文件映射

显式manifest含`artifacts`列表，每项为`{id,path,version,sha256}`；ID唯一、版本非空、sha256为原始
字节的真实小写64位哈希。`path`相对于显式`--root`，禁止绝对路径、反斜杠、`.`、`..`和链接逃逸。
默认角色是`analysis-results`（结构化结果）和`reported-values`（人工核对的报告值清单）。
manifest不是passport；工具独立运行，不导入兄弟脚本，不自动更新项目状态。

既有结果是JSON时只登记真实路径，不论文件名叫`analysis-results.json`还是`structured_results.json`。
既有结果是YAML或其他导出时保留其`analysis-results`身份和原路径；如获准规范化为新JSON，
另登记派生ID（如`analysis-results-json`），显式指定：

```json
{"roles":{"results":"analysis-results-json","reported":"reported-values"}}
```

上面只是manifest可选`roles`片段，实际运行仍须完整`artifacts`及真实哈希。派生文件和原件都应注册，
人工核实字段转换，不以转换代替重新分析，不改原件。manifest还须包含来源统计输出、实际稿件/表格等
全部相关工件；如果计划、方法或脚本会影响本次判断，也登记并绑定。工具只能核对声明的依赖，不能发现
所有遗漏依赖或认证人工摘录。每次报告绑定清单中的全部工件，包含报告位置所引用的稿件版本。

### 结果JSON

顶层`{"schema_version":"1.0","results":[...]}`。每项字段：

| 字段 | 类型、适用性与含义 |
|---|---|
| `analysis_id` | 非空唯一字符串；区分模型、人群、结局、时间点和比较，不能仅靠结局名匹配 |
| `population/outcome/timepoint` | 各为非空字符串；准确分析集、结局及观察窗，不自动统一同义词 |
| `groups` | `{comparison,reference}`非空字符串；非比较结果用null并给不适用理由；顺序有意义 |
| `effect_scale/unit` | 非空字符串；HR、OR、RR、mean_difference、count等保持原尺度，单位如mg/dL或dimensionless |
| `estimate` | 有限数值或精确十进制字符串；count尺度必须非负JSON整数 |
| `ci` | `{lower,upper,level,adjustment,method}`；数值边界、0到1间置信水平、非空调整与方法说明 |
| `denominator` | `{value,kind,unit}`；count需非负JSON整数，continuous支持人年等有限数值，不将不同分母混用 |
| `source` | `{artifact_id,locator}`，引用已登记、非空的真实统计输出和具体表/行/模型位置 |
| `execution_status` | completed/not_run/blocked/failed；只有completed可供已核实对账，未知状态标unverified |
| `not_applicable` | 可选对象；groups/estimate/ci/denominator为null时，按同名键写非空理由；未知/未提供不是不适用 |
| `events` | 可选非负JSON整数，不使用舍入；复杂重复事件等按实际定义处理，不强制events≤人数 |
| `p` | 可选`{value,adjustment,method}`，value在0到1之间；与CI各记各的口径，不推算P/CI关系 |
| 其他扩展 | model、adjustment_set、结局层级、亚组/诊断定位等按适用性保留；工具不自动验证这些字段 |

数字建议用十进制字符串避免二进制浮点导出损失；计数例外，必须用JSON整数。工具读取JSON小数时保留
原始十进制文本。置信水平和方法等口径在两个文件里需使用相同表示。第一版每个十进制最多100个有效数字，
非零指数范围-100到100，超出范围未核实。CI无需包住点估计，P无需与CI对应同一显著性决策；不强加模型假设。
`estimate=null`并有明确理由时可以只核对其他适用数值；不得为null创建报告估计值。

### 报告值JSON

顶层`{"schema_version":"1.0","reported_values":[...]}`。每项均有：

- `id`：唯一非空报告项ID；同一分析可在正文和表格各建一项。
- `analysis_id`：显式引用一项结果，不模糊匹配，不自动倒转比较组或换算尺度。
- `locator:{artifact_id,location}`：实际稿件/表格工件与明确章节、页、行、表格单元位置；不得只写“正文”。
  工具仅验证非空和工件绑定，定位具体性/真实性由人工确认；稿件字节变化旧记录失效。
- `context`：必须有与结果同形的population、outcome、timepoint、groups、effect_scale、unit。
  核对CI字段另带`ci:{level,adjustment,method}`；核对P另带`p:{adjustment,method}`；
  核对分母另带`denominator:{kind,unit}`。元数据不一致即差异，缺元数据为unverified。
- `values`：非空对象，键仅支持estimate、ci.lower、ci.upper、ci.level、denominator.value、events、p.value；
  每个值为`{value,precision?}`。未知字段不会被静默跳过通过，而是unverified，须人工核对。

例如一个已定位报告项中的values片段（不是完整输入）：

```json
{
  "estimate":{"value":"0.82","precision":{"places":2,"mode":"half_up"}},
  "denominator.value":{"value":236}
}
```

非整数默认十进制精确相等；仅在确有展示舍入时逐值声明`precision:{places:0..12,mode:half_up|half_even}`。
按该规则将来源数值舍入，再与报告值精确比较；报告值本身须符合声明小数位。没有默认绝对/相对容差，
不接受任意tolerance参数。整数分母、events及count估计必须完全相等，且禁止precision，236≠235。
`P<0.001`、区间删失值、复杂自定义统计量等不受第一版数值接口支持，保留人工核对，不擅自转为等号或0。

### 报告、状态与限制

命令、退出码及输出见技能入口“可选只读数值对账”。领域值`consistent/discrepant/unverified`和执行状态
分列；发现数值差异仍是completed。差异与未核实项可并存，优先返回discrepant但保留两者。空清单不能通过。
报告含每项locator、差异位置、输入绑定和覆盖范围；未出现在报告清单中的分析列为`unreported_analyses`，
不在此次验证范围，不能因局部consistent宣称整个结果文件已核实。原始来源证据、人工摘录与模型适用性
仍须人审；不把非显著说成无效，也不把检查器当医学解释器。

工具先写领域报告，再另写R2同形`artifacts/checks`记录：scope.domain和domain_result.namespace均为
`result_consistency`，inputs绑定相关工件版本/哈希，report引用已落盘报告路径/字节哈希，checked_at带时区。
不把报告自身哈希写进自身；正常报告是completed+applicable。参数/解析/I/O错误不给可登记的完成检查，
stdout/stderr说明失败；不能把CLI错误摘要冒充完整passport failed记录。输出必须使用新路径和唯一check-id，
保留旧报告；工具不维护历史注册表，跨运行ID唯一性需由项目索引或人工保障。
