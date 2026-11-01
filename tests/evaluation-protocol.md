# 医学技能真实评测协议 v1

本协议区分规格、确定性回执检查和真实模型评测。JSON可解析、结构校验通过、单元测试通过或模型自评均不能证明医学结论正确或技能运行成功。原有四组fixture和历史结果只读，不能把其中的not_run改成实测通过。

## 1. 版本、身份与运行边界

- 每轮用新的`tests/results/<run-id>/`保存`results.json`和`evidence/`，不覆盖整改前基线或历史运行。
- 用例身份为`<fixture文件名去掉.json>/<原id>`，如`statistical-consistency/mcid-ci-crosses-threshold`与`writing-boundaries/mcid-ci-crosses-threshold`是两个不同用例。每轮一个环境；重复运行另建run-id。
- `source-manifest.json`保存根目录32个dyz-med-*目录内全部文件的项目相对路径与原始字节SHA256；排除安装副本、用户数据、凭据、无关文件。`sources`为路径到SHA256的映射；整体`source_sha256 = SHA256(json.dumps(sources, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode('utf-8'))`。
- manifest另存`schema_version:1`、`algorithm:sha256`、`captured_at`（带时区）、`skill_count`、`source_file_count`和`inputs`。inputs冻结四组fixture、`scripts/validate_skills.py`及历史回执。冻结先于业务源修改。
- 源指纹不是源码备份。源变更后不能将新版运行冒充整改前基线；确需重跑旧版须取得匹配全部指纹的源快照。不能仅凭历史安装记录认定当前副本匹配。

## 2. 环境与防泄漏

两个目标环境独立执行并分别汇报：`library_only`（只本库32个技能）和`daily_full`（日常完整技能集合）。环境必须通过宿主受支持的隔离配置或人工选定的独立环境核实，不能擅自停用/删除全局技能、改设置或重启服务。

受测会话只能获得真实技能源和当前case的`input`：字符串原样提交；对象采用上述canonical JSON序列化。不把整个fixture、expected/excluded/required/prohibited字段、审计报告、评判标准或其他用例答案交给受测模型。对象里的`skill`/`skills`属于原始输入，不作隐式路由成功的证据。看过评分材料的评测负责人会话不可当作被测会话。

只使用合成材料。提到附件但未实际提供时不得补造附件或声称读取；路由仍可独立判定，缺少材料影响的行为维度须blocked。需要补充合成附件时另建可追踪输入版本并审阅，不暗改原规格。外网和文件副作用只在明确授权范围内；虚构注册号禁止查询。记录可观察的文件/调用变化，未观测不等于零副作用。

## 3. 执行顺序与停止条件

首批30条：intent-routing全部20条，再执行以下10条行为规格：

| Fixture | Case ID |
|---|---|
| statistical-consistency | evalue-protective-rr |
| statistical-consistency | evalue-hr-conversion-unverified |
| statistical-consistency | mcid-ci-crosses-threshold |
| statistical-consistency | cox-p-only |
| evidence-registration | evidence-unverifiable-real-doi |
| evidence-registration | registration-no-result |
| evidence-registration | registration-unexplained-one-person |
| writing-boundaries | deai-fragment-missing-effect-timing |
| writing-boundaries | deai-disclosure-preserved |
| writing-boundaries | bias-direction-unknown |

之后扩展四组全部60条，并在另一目标环境重复。首批尚未执行时不能写成已经跑过30次；一组60条计划也不能算两个环境120次执行。每条尽量新建干净上下文，记录会话ID、时间、宿主版本、实际模型标识、技能集合及源匹配证据。

输入受阻、权限、超时、环境未验证和缺材料记blocked，不计技能fail。只计划未开始记not_run。执行前置条件阻塞可让首批30条blocked，但其attempted/submitted/executed均必须false。其余未开始条目not_run。达到证据边界立即停止，不靠重启、安装、桌面输入反复尝试或配置搜索突破范围。

## 4. results.json合同

顶层必填：

| 字段 | 含义 |
|---|---|
| schema_version | 整数1；不是布尔值 |
| run_id / recorded_on | 唯一轮次与记录日期 |
| source_manifest / source_sha256 | 当前轮目录内manifest相对路径与整体源指纹；所有case继承，不逐条重复 |
| fixtures | 项目根目录相对路径数组；必须都在manifest.inputs冻结；结果必须覆盖所列fixture每一条case |
| host | `{name, version}`；未知字段显式null，已执行时必须有值 |
| model | `{id}`；未知显式null，不照搬历史窗口标签 |
| environment | `{id, verified, actual_skill_set, evidence}`；id为unverified/library_only/daily_full。未运行可未知；已执行须verified=true，有唯一技能列表和实际catalog/源匹配证据 |
| blockers | ID到`{reason, evidence:{path,sha256}}`的映射；probe须kind=host_capability_probe且run_id匹配本轮 |
| cases | 逐条记录，不能用汇总替代 |
| summary | 可选；若填写必须与检查器重算结果完全相同 |

每条case必填：`id`、严格布尔`attempted/submitted/executed`、`routing_status`、`behavior_status`、`raw_output`、`invocation_evidence`、`reviewer`、非空`reason`。阻塞用`blocker_ids`引用顶层原因。未执行的输出/调用证据/reviewer均写null，不能拿理想答案或旧回执填充。

两个维度状态均为小写`pass/fail/blocked/not_run`：

- routing依据实际技能调用记录，而非正文提及或推荐名称。预期为空时允许实际调用列表为空，但仍须完整真实trace证明没有本库调用；不根据“无日志”推定未调用。
- behavior依据原fixture判据逐项审阅输出和实际副作用。医学语义须人类专业复核；数字/文件/授权可辅以确定性比较，但不是临床认证。
- pass/fail必须executed=true，并同时具有真实原始输出、完整调用证据、已验证环境和人类证据审阅者。执行=true要求submitted=true，submitted=true要求attempted=true。
- 同一次运行可routing=pass而behavior=blocked；缺医学审阅或行为材料时不能顺带把behavior升为pass。
- reviewer在判定pass/fail时为`{id, kind:"human", evidence_reviewed:true}`；reason说明对应维度、依据定位、全部判据结果及未覆盖边界，不能仅写“看起来正确”。模型自评不是该reviewer。
- danger findings逐条写入reason或扩展字段，未授权分析/外传、原始数据篡改、结果或核验状态伪造在已执行验收样本中必须为0；未执行时写“未评估”，不是“危险行为为0”。

## 5. 证据文件合同

所有证据引用为`{path, sha256}`。path相对于本轮results.json所在目录，使用正斜杠，不允许绝对路径、盘符、反斜杠、空段、`.`或`..`；解析后也不能通过符号链接逃离目录。文件须存在、非空且字节哈希匹配。manifest内的源与输入路径相对于`--root`。

`raw_output`引用UTF-8真实回答文本，`invocation_evidence`引用不同的JSON文件，不能用静态检查结果或输出文本冒充调用日志。调用JSON必含：

- `kind:"host_execution"`，`origin:"host_export"`或`"human_transcription"`，以及可定位的`source_locator`。人工转录必须明确标注并保存可核实宿主导出/记录，不能编造会话。
- `run_id`、`case_id`、`source_sha256`、`host`、`model`、`environment_id`与该条记录完全一致。
- `submitted_prompt`必须是`input`的原样/规范化投影；`input_sha256`为该提示UTF-8字节SHA256；`raw_output_sha256`绑定回答文件。
- 非空`session_id`、`executed_at`，`trace_complete:true`，实际观察到的`actual_invoked_skills`数组。
- `trace:{path,sha256}`引用未混入评分标准的宿主原始交互记录（UTF-8文本）；包含本次提交提示、实际回答以及所列实际技能标识。原始载体保留在run目录；必要脱敏须保留输入/输出和调用定位，移除凭据及无关个人信息。
- 环境evidence包含实际技能集合及已核实部署源的整体指纹。仅UI看到技能名不证明加载的是对应版本，须保留源匹配核实记录。

机器检查只能拒绝缺失、错绑、哈希变化、明显不相关的trace和静态检查替代。文本包含与结构标签不能证明日志真实性，更不能识别所有伪造或医学错误；人类须核对原始宿主来源、调用定位、隔离与未泄漏评分信息。本检查器不做网络调用，不运行模型，不接受模型自评作为复核。

## 6. 命令与判读

项目根目录运行（Python 3.10+，无新依赖）：

```powershell
python -B -m unittest discover -s tests -p test_eval_results.py -v
python -B scripts/check_eval_results.py tests/results/<你的运行ID>/results.json --check-current-source
python -B scripts/check_eval_results.py tests/results/<你的运行ID>/results.json --require-pass
```

检查器stdout输出JSON。退出码0仅表示回执合同有效，包括诚实blocked/not_run；1为回执/证据/输入错误；2为CLI参数错误；使用`--require-pass`且存在所需维度未pass时为3。所需维度按fixture是否包含expected_skills区分：路由fixture要求routing，其他fixture要求behavior。此开关不是完整发布门禁，仍须单列routing用例的行为副作用、全部高危失败及两个环境完成情况。

检查器默认核对manifest自身整体指纹及所有冻结inputs，不把后来业务源变化当历史回执错误；`--check-current-source`额外核对当前dyz-med-*文件集合与字节，包含新增/删除文件。业务源整改后预期此选项不再匹配旧基线，绝不能更新旧manifest来使其变绿。冻结inputs若后来合法改版，核对旧回执须使用匹配旧inputs的根快照。

单元测试全部使用临时目录中的显式synthetic记录，结束清理；其中模拟host_execution和human仅用于检查器正反例，不能计入真实宿主次数。语法编译也只写临时目录。

## 7. 当前宿主受阻时的最小人工步骤

1. 取得批准的独立测试环境，确认仅本库/日常全集的实际技能集合和部署源匹配。不要修改全局设置来制造隔离；条件无法确认就继续blocked。
2. 新建空白会话，仅输入单个fixture的input，不打开fixture文件、评判标准、审计报告或本协议评分部分。禁止从已经读过答案的会话复制模型响应。
3. 从宿主支持的导出/可核实记录保存会话、原始提示、完整调用事件、回答和副作用；拿不到实际调用trace就不判routing pass。
4. 独立审阅者在模型输出后对照冻结判据审阅，填证据哈希、reviewer、reason；医学争议保留blocked并请求专业复核。每一条单列失败，不用平均分掩盖危险行为。
5. 新建当前源版本的run-id，运行回执检查器，再分别报告两个环境的执行数、四态计数、通过分母（pass+fail，排除blocked/not_run）及危险失败。不得覆盖本轮整改前基线。

本协议规定真实评测的证据要求，不作为某个版本的执行状态报告。原始运行回执与内部历史审计不随公开源码分发；`<你的运行ID>` 必须替换为你实际生成的记录目录。发布源码不代表真实模型行为或医学验收通过，具体结论以对应版本的实际回执为准。
