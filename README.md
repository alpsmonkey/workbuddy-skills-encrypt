<p align="center">
  <b style="font-size: 28px">🔐 WorkBuddy Skills Encrypt</b>
</p>

<p align="center">
  <b>USB 加密狗互通式加密系统 — 保护你的 WorkBuddy 技能不被未授权复制</b>
</p>

<p align="center">
  <a href="README_EN.md">English</a> · <a href="README.md">简体中文</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/版本-v3.0.0-orange" alt="版本" />
  <img src="https://img.shields.io/badge/许可证-MIT-blue" alt="许可证" />
  <img src="https://img.shields.io/badge/加密-RSA--2048%20%2B%20AES--256%20%2B%20HKDF-green" alt="加密" />
</p>

<p align="center">
  <b>把你优化好的技能锁起来。没有你的 U 盘，谁也用不了。</b>
</p>

---

> **定位声明**：本项目只做一件事——用物理 U 盘保护你的 WorkBuddy 技能文件。基于 RSA-2048 数字签名 + HKDF 密钥派生 + AES-256 内容加密，外壳与正文分层隔离。它不是 DRM，不是云授权，是**纯本地、纯物理**的加密方案。

> **v3 架构升级**：U 盘不再只是验签流程检查，而是真正参与加密本身。加密密钥 = HKDF(密码, U盘密钥材料)，没有 U 盘物理上无法解密，即使知道密码也解不开。

## 它能做什么

你在 WorkBuddy 里花了几十个小时打磨的技能——SAP 成本分析、公众号写作、报表自动化——别人把技能文件夹一拷，就能直接用。本工具把你的 U 盘变成物理加密狗，拔走 U 盘，技能立刻失效。

```
初始化 → 生成 RSA 密钥对 → 签名 U 盘 → 加密技能 → 插 U 盘才能用
```

### 核心架构

| 层次 | 文件 | 状态 | 作用 |
|------|------|------|------|
| **外壳引导器** | `SKILL.md` | 明文，永不加密 | AI 读到就知道解密协议：验签 → 输密码 → 解密 |
| **加密正文** | `SKILL.body.enc` | AES-256 密文 | 真正的技能内容，没有密码解不开 |
| **U 盘验签** | `scripts/verify.py` | 本地脚本 + 公钥 | 遍历 USB 设备，RSA 验签 license.dat |
| **解密器** | `scripts/decrypt_body.py` | 本地脚本 | 验签通过后解密正文到 stdout，不留明文痕迹 |

### 为什么不是"加密整个 SKILL.md"

WorkBuddy 的技能加载机制很简单——直接读 SKILL.md 的内容给 AI。如果整体加密成乱码，AI 看到一堆密文直接卡死，连"怎么解密"都不知道。

新的双层架构解决了这个问题：外壳始终可读，就像电脑的 BIOS——它本身不做任何实质工作，但它告诉 AI 下一步该干什么。

```
旧方案（有断层）：
  WorkBuddy 加载 → SKILL.md（密文乱码）→ AI 无法解析 → 卡死

新方案（自举的）：
  WorkBuddy 加载 → SKILL.md（明文外壳）→ AI 读取解密协议
                  → 自动运行 verify.py 验签
                  → 验签通过 → 询问密码 → decrypt_body.py 解密正文
                  → 按正文指令执行
```

## 安全层次

| 层次 | 机制 | v3 改进 |
|------|------|---------|
| 硬件绑定 | U 盘序列号 + RSA-2048 签名 | 物理 U 盘必须插入 |
| **密钥派生** | **HKDF(密码, U盘密钥材料)** | **U 盘参与加密本身，没有 U 盘解不开** |
| 内容加密 | AES-256（pyAesCrypt） | 密钥由密码+U盘共同派生，缺一不可 |
| 验签前置 | 解密前必须先过 RSA 验签 | 硬件 + 密码双因素保护 |
| 密码传输 | 全部脚本走 stdin / 交互，禁止命令行参数 | 密码不进进程列表与 shell 历史 |
| 私钥管控 | 私钥只存主 U 盘，本地无副本 | U 盘被物理偷走 |
| 异地备份 | 加密前自动拷贝到 `~/skill-backup/` | 跟 skill 目录物理隔离 |
| 往返校验 | 加密后立即解密比对 SHA256 | 确保加密成功，失败自动回滚 |
| 多 U 盘冗余 | `sign_multi.py` 给多个 U 盘签名 | 丢一个不影响 |

**v3 核心变化**：
- 旧版：加密密钥只由密码派生，U 盘只是验签流程检查（改 verify.py 即可绕过）
- v3：加密密钥 = HKDF(密码, encryption.key)，U 盘密钥材料参与密钥派生，没有 U 盘物理上无法解密

## 快速开始

### 环境依赖

```bash
pip install pyAesCrypt cryptography wmi
```

### 一次性初始化（约 2 分钟）

```bash
# 1. 读取 U 盘序列号
python scripts/read_serial.py
# 输出：检测到U盘序列号: AA0B1C2D3E4F（记下来）

# 2. 生成 RSA 密钥对 + 加密密钥材料（私钥和密钥材料直接写入 U 盘）
python scripts/gen_keys.py E
# 公钥 → scripts/public_key.pem（本地）
# 私钥 → E:/private_key.pem（U 盘，本地不留副本）
# 密钥材料 → E:/encryption.key（U 盘，32字节随机，用于 HKDF 派生）

# 3. 签名 license.dat 到 U 盘
python scripts/sign_license.py E
# 自动读取 U 盘序列号并签名
# U 盘现在有：private_key.pem + encryption.key + license.dat
```

### 加密技能

```bash
# 单个技能加密（密码走 stdin）
echo "你的强密码" | python scripts/encrypt_skill.py /path/to/SKILL.md E
# 流程：
#   1. 从 U 盘读取 encryption.key
#   2. 用 HKDF(密码, encryption.key) 派生加密密钥
#   3. 异地备份原始 SKILL.md
#   4. AES-256 加密正文 → SKILL.body.enc
#   5. 往返校验（立即解密比对 SHA256）
#   6. 删除本地明文备份（只保留异地）
#   7. 写入外壳 SKILL.md

# 批量加密所有未加密技能（非交互）
echo "你的强密码" | python scripts/batch_encrypt.py all E
# 或指定编号：echo "密码" | python scripts/batch_encrypt.py 1,3,5 E
```

### 使用加密后的技能

跟平时用 WorkBuddy 完全一样，不需要手动跑脚本。AI 自动完成加载流程：

```
你正常使用 WorkBuddy → AI 加载技能 → 读外壳 → 验签 → 询问密码和U盘盘符 → 解密 → 执行
```

唯一需要你做的：在 AI 询问时输入解密密码和 U 盘盘符（AI 会通过 stdin 传给脚本，不会出现在命令行参数里）。

### 管理加密技能

**解封（恢复原始 SKILL.md）**
```bash
python scripts/unseal_skill.py ~/.workbuddy/skills/my-skill
# 三级恢复：本地 .bak → 异地备份 → 密码解密
```

**改密（用新密码重新加密）**
```bash
echo "旧密码\n新密码" | python scripts/change_password.py ~/.workbuddy/skills/my-skill E
# 流程：旧密码解密 → 新密码加密 → 往返校验 → 失败自动回滚
```

**多 U 盘冗余**
```bash
python scripts/sign_multi.py E F G
# 自动读取每个 U 盘序列号并签名
# 主U盘 E: 有 private_key.pem（签发权）
# 备用U盘 F:/G: 只有 license.dat（授权凭证）
# ⚠️ 需手动复制 encryption.key 到备用U盘
```

## 文件结构

```
workbuddy-skills-encrypt/                # 本仓库
├── SKILL.md                             # WorkBuddy 技能定义（可加密自己）
├── README.md                            # 英文文档
├── README_CN.md                         # 中文文档（本文件）
└── scripts/
    ├── read_serial.py                   # 读取 U 盘序列号（含异常字符清洗）
    ├── gen_keys.py                      # 生成 RSA-2048 密钥对 + 加密密钥材料（写入 U 盘）
    ├── sign_license.py                  # 签名 license.dat（从 U 盘读取私钥，自动读序列号）
    ├── sign_multi.py                    # 多 U 盘冗余签名（命令行传盘符，自动读序列号）
    ├── verify.py                        # U 盘 RSA 验签（WMI 关联查询 + 公钥验证）
    ├── encrypt_skill.py                 # 加密单个技能（HKDF 派生 + 往返校验 + 异地备份）
    ├── decrypt_body.py                  # 验签 + HKDF 派生 + 解密正文 → stdout
    ├── batch_encrypt.py                 # 批量加密（非交互 all/编号 + 交互菜单双模式）
    ├── unseal_skill.py                  # 解封技能（三级恢复：.bak → 异地备份 → 密码解密）
    ├── change_password.py               # 改密（旧密码解密 → 新密码加密 + 往返校验）
    └── public_key.pem                   # 公钥（仅验签用，公开无所谓）
```

### 加密后的技能目录结构

```
~/.workbuddy/skills/你的技能名/
├── SKILL.md              # 外壳引导器（明文，AI 读到就知道怎么解密）
├── SKILL.body.enc        # 加密正文（AES-256 密文，密钥 = HKDF(密码, U盘密钥)）
└── scripts/
    ├── verify.py         # U 盘验证脚本
    ├── decrypt_body.py   # 验签 + HKDF 派生 + 解密 → stdout
    └── public_key.pem    # 公钥（验签用）
```

### U 盘结构

```
主 U 盘（E:）：
├── private_key.pem       # 签发权杖（只有这个 U 盘能签新 license）
├── encryption.key        # 32字节随机密钥材料（HKDF 派生用）
└── license.dat           # RSA 签名（256 字节，绑定此 U 盘序列号）

备用 U 盘（F:）：
├── encryption.key        # 与主 U 盘相同（需手动复制）
└── license.dat           # 仅授权凭证（无法签发新 license）

异地备份：
~/skill-backup/<日期>/<技能名>/SKILL.md
```

## 多 U 盘冗余

U 盘会丢。准备 2-3 个：

```bash
# 同时插入主 U 盘（有 private_key.pem）和备用 U 盘
python scripts/sign_multi.py E F G
# 自动读取每个 U 盘序列号并签名
```

| 角色 | 盘上有什么 | 能干什么 |
|------|-----------|---------|
| 主 U 盘 | private_key.pem + encryption.key + license.dat | 既能解密技能，又能给新 U 盘签发 license |
| 备用 U 盘 | encryption.key + license.dat | 只能解密技能，不能签发新 license |

**重要**：`sign_multi.py` 只签发 license.dat，encryption.key 需要手动从主 U 盘复制到备用 U 盘：

```bash
# Windows
copy E:\encryption.key F:\
copy E:\encryption.key G:\

# Linux/macOS
cp /media/usb-main/encryption.key /media/usb-backup1/
```

主 U 盘锁抽屉，日常用备用 U 盘。丢哪个都不影响。

## 安装为本机 WorkBuddy 技能

```bash
# 从 GitHub 直接安装到 WorkBuddy
git clone https://github.com/alpsmonkey/workbuddy-skills-encrypt.git ~/.workbuddy/skills/workbuddy-skills-encrypt

# 之后在 WorkBuddy 中直接对话触发：
# "帮我初始化U盘加密狗"
# "帮我加密 sap-cost-analysis 技能"
# "批量加密所有技能"
```

## 常见问题

### 加密后还能恢复吗？

能。加密前会做异地备份到 `~/skill-backup/<日期>/`。用 `unseal_skill.py` 可以三级恢复：本地 .bak（v3 已删除）→ 异地备份 → 密码解密。

### 别人复制了整个 skill 文件夹，能用吗？

不能。`SKILL.body.enc` 是 AES-256 密文，加密密钥 = HKDF(密码, U盘上的 encryption.key)。即使知道密码，没有正确的 U 盘也解不开。即使复制了 encryption.key 到自己的 U 盘，验签环节会检查 license.dat，序列号不匹配则 RSA 验签失败。

### v3 和旧版有什么区别？

| 项目 | 旧版 (v2) | v3 |
|------|----------|-----|
| 加密密钥 | 只由密码派生 | HKDF(密码, U盘密钥材料) |
| U 盘作用 | 只是验签检查 | 真正参与加密 |
| 没有 U 盘 | 知道密码可解密 | 物理上无法解密 |
| 往返校验 | 无 | 加密后立即验证 |
| 本地明文 | .bak 保留 | 验证通过后删除 |

**破坏性变更**：旧版加密的技能无法用 v3 解密。需要先用旧版解封，再用 v3 重新加密。

### U 盘序列号有异常字符怎么办？

部分 U 盘固件返回的序列号末尾夹带了不可打印的控制字符。`read_serial.py`、`sign_license.py` 和 `verify.py` 都内置了统一的 `clean_serial()` 函数，先删除不可打印字符再 strip，签名和验签用的是同一个清洗逻辑，序列号一致则通过。

### 加密过程中能拔 U 盘吗？

- 初始化（生成密钥 + 签名）阶段：不能拔
- 加密技能阶段：需要 U 盘（读取 encryption.key 派生密钥）
- 使用技能时：验签 + 解密阶段不能拔，解密完成后正文已在 AI 上下文中，拔了不影响当前会话

### 加密过程需要联网吗？

完全不需要。密钥生成、签名、加密全部纯本地运行，离线完成。

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=alpsmonkey/workbuddy-skills-encrypt&type=Date)](https://star-history.com/#alpsmonkey/workbuddy-skills-encrypt&Date)

## 开源许可

[MIT](LICENSE) — 自由使用、修改、分发。

## 安全声明

本项目提供的是基于密码学的物理访问控制，适用于防止技能被无意识复制和传播。

**v3 安全增强**：
- 加密密钥由密码和 U 盘密钥材料共同派生（HKDF），双因素保护
- 往返校验确保加密成功，失败自动回滚
- 本地明文残留已删除（只保留异地备份）

**安全边界**：
- 对于有明确技术能力和动机的攻击者（例如反编译 Python 脚本、修改验签逻辑、提取内存中的密钥），本方案的安全性取决于代码混淆和系统安全层面的附加措施
- 私钥和密钥材料是你的最终责任——如果主 U 盘和所有备份都丢失了，加密的技能无法恢复
- 使用过程中，解密后的正文会进入 AI 会话上下文，本方案无法防止技能在使用时被观察
