# Fingerprint Account Onboarding

一个面向**已授权多账户开户**的 Codex Skill。它把指纹浏览器开户、代理容量核算、MockAddress 地址生成、人工验证码交接、地址保存校验和轻量对话串成一套可复用流程。

> 本 Skill 不绕过图片验证码、短信验证码或平台风控，也不保存真实账号密码。只用于你有权管理的账号与合法测试场景。

## 为什么需要它

多账户开户真正的难点通常不是“打开网页”，而是这些容易出错的边界：

- “同一 IP 最多几个人”应按外部代理池计算，而不是按 AdsPower 等指纹浏览器里的绑定数量计算。
- 指纹浏览器、浏览器内核和指纹特征不断变化，不能把某一个供应商、UA 或设备型号写死。
- 手机区号、国家/地区、地址国家可以互不相同，不能在流程中擅自推导。
- 图片验证码、短信验证码、可信手机 2FA 必须由人工完成。
- 平台返回 `account cannot be created` 等硬风控后继续重试，往往只会加深封禁。
- Apple `Copy billing address from default payment method` 必须在最后勾选，并在保存后回读地址。

## 核心特性

- **指纹浏览器不固定**：核心流程只依赖统一的 `create/start/stop/CDP` 适配契约；AdsPower 只作为参考实现。
- **指纹不固定**：允许提供方随机生成或新建指纹，但可在运行时强制校验桌面 UA、窗口宽度等约束。
- **地区不固定**：国家代码、语言、时区、手机国家码、MockAddress 国家和省/州/都道府县均由运行参数决定。
- **地址来自 MockAddress**：通过 `https://mockaddress.com/` 生成，并校验结果不为重复。
- **人在回路**：图片/音频验证码、短信 OTP、可信手机验证全部留给用户。
- **硬停止**：目标服务明确拒绝开户时停止该环境，不进行无边界重试。
- **可审计状态**：记录 profile、代理、账户引用、地址和检查结果，但不回显凭据。
- **可清理**：临时截图、缓存和辅助浏览器文件统一放在项目 `.cache/`，任务完成后删除。

## 目录结构

```text
fingerprint-account-onboarding/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── scripts/
│   ├── check_ip_capacity.py
│   ├── generate_mockaddress.py
│   └── validate_desktop_cdp.py
├── references/
│   ├── apple-account-workflow.md
│   ├── mockaddress.md
│   ├── provider-adapters.md
│   └── recovery-and-status.md
└── assets/
    └── account-spec.example.json
```

## 安装

把整个目录放到 Codex 的用户 Skill 目录：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R fingerprint-account-onboarding "${CODEX_HOME:-$HOME/.codex}/skills/"
```

随后在 Codex 中调用：

```text
$fingerprint-account-onboarding
```

或者直接描述任务：

```text
使用 fingerprint-account-onboarding 处理一个已授权的多账户开户任务。
```

## 运行前必须确认

建议以 `assets/account-spec.example.json` 为模板，至少确认：

1. 指纹浏览器供应商、API 地址、认证凭据引用；
2. 外部代理池地址与每个 IP 的容量上限；
3. 国家/地区、语言、时区、手机国家码；
4. MockAddress 国家 slug 和目标省/州/都道府县；
5. 账号与 profile 的对应关系；
6. 验证码和短信由谁完成；
7. 是否需要 Apple 地址、`Copy billing address...` 或后续暖号对话。

不要在 Skill 文件、Git 历史或 README 中写入真实邮箱、密码、2FA 密钥、手机号或代理密钥。凭据应放在项目 `.secrets/`（`0600`）或环境变量中。

## 快速开始

### 1. 检查 IP 容量

```bash
cat > usage.json <<'JSON'
{
  "limit": 4,
  "usage": {
    "203.0.113.10": 3
  },
  "additions": {
    "203.0.113.10": 1
  }
}
JSON

python scripts/check_ip_capacity.py usage.json
```

任何 IP 超过上限时，脚本以退出码 `2` 结束。

### 2. 校验浏览器是否为桌面环境

连接已经启动的 CDP 端点：

```bash
python scripts/validate_desktop_cdp.py \
  --ws 127.0.0.1:50325 \
  --min-width 900
```

脚本会检查：

- UA 是否包含 `Mobile`、`Android`、`iPhone`、`iPad` 等移动标识；
- 实际视口宽度是否达到要求；
- 页面 URL、平台、DPR 和屏幕信息。

### 3. 从 MockAddress 生成身份

日本北海道示例：

```bash
python scripts/generate_mockaddress.py \
  --country jp \
  --subdivision 北海道 \
  --count 3 \
  --output .cache/onboarding-20260901/mockaddress.json
```

美国 California 示例：

```bash
python scripts/generate_mockaddress.py \
  --country usa \
  --subdivision California \
  --count 1
```

注意：MockAddress 的路径 slug 不一定等于 ISO 国家码，美国是 `usa` 而不是 `us`。完整说明见 `references/mockaddress.md`。

输出字段包括：

```text
lastName, firstName, gender, phone, zip, street, city, state, county, email, fullAddress
```

### 4. 执行开户流程

1. 选取或创建指纹浏览器 profile；
2. 通过本地 API 启动浏览器；
3. 使用 CDP 连接页面；
4. 登录目标账号；
5. 按运行配置填写地区和身份信息；
6. 到验证码或短信页时交由用户；
7. 成功后补收货地址或完成用户指定的后置动作；
8. 回读页面状态并写入运行台账。

Apple 专用字段顺序与常见错误见：

```text
references/apple-account-workflow.md
```

浏览器适配器契约和 AdsPower 示例见：

```text
references/provider-adapters.md
```

### 5. 收货地址与最后勾选

当用户要求：

```text
Copy billing address from default payment method
```

必须：

1. 先填完姓名、街道、城市、州/省、邮编；
2. 最后勾选该选项；
3. 保存前确认 `checked == true`；
4. 点击 `Save Changes`；
5. 保存后回读页面中的完整地址，而不是只看成功提示。

## 状态模型

| 状态 | 含义 |
|---|---|
| `planned` | 已分配，尚未改动浏览器 |
| `ready` | 环境就绪，桌面约束已通过 |
| `awaiting_user_captcha` | 等待人工图片/音频验证 |
| `awaiting_user_sms` | 等待人工短信/OTP |
| `email_verified` | 邮箱验证码已完成 |
| `created` | 目标账户创建成功 |
| `address_saved` | 收货地址已保存并回读 |
| `blocked` | 目标平台硬拒绝或账户不匹配 |
| `error` | 本地/网络/适配器错误 |

完整恢复策略见 `references/recovery-and-status.md`。

## 安全边界

- 必须有明确授权后再创建账号或修改账户设置。
- 不自动破解、猜解或重放验证码。
- 不在同一失败环境上连续重试。
- 不删除用户现有 profile、代理、浏览器会话或未提交数据。
- 不把“关闭浏览器”等同于“删除环境”。
- 不将真实密码、2FA、Cookie、API Key 或账号数据提交到 GitHub。
- 若平台服务条款不允许批量开户，应停止并改用平台授权的官方流程。

## 暖号对话（可选）

如果任务要求登录后的轻度对话：

- 每个账号发送 1 段，通常 2–3 句；
- 使用用户指定语言；
- 逐字输入，保持自然节奏；
- 顺序执行，避免多个账号同时并发刷请求；
- 每个账号等待完整回复后再处理下一个。

## 适配其它指纹浏览器

实现 `references/provider-adapters.md` 中的适配器契约即可。核心流程不要求使用 AdsPower，也不要求某个固定浏览器内核、UA、系统或屏幕尺寸。

至少需要支持：

- 列出已有 profile；
- 创建/更新 profile；
- 启动 profile 并取得 CDP 地址；
- 查询运行状态；
- 停止 profile；
- 保留浏览器状态；
- 返回可校验的指纹和代理信息。

## 验证

```bash
cd fingerprint-account-onboarding
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" .
python3 -m py_compile scripts/*.py
python3 -m json.tool assets/account-spec.example.json >/dev/null
```

本仓库当前不附带真实账号、密码、2FA 密钥、手机号、代理密钥或实人地址。

## License

未声明许可证。若计划公开复用，请先补充合适的 `LICENSE`。
