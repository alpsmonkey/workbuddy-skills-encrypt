# WorkBuddy Skills Encrypt — USB 加密狗保护系统

为 WorkBuddy Agent 技能提供物理 U 盘加密保护。基于 RSA-2048 数字签名 + AES-256 内容加密，防止技能文件被未授权复制使用。

## 核心架构

```
┌─ 本地技能目录 ────────────────────────────────────────────────┐
│  SKILL.md              ← 外壳引导器（明文，永不加密）
│  SKILL.body.enc        ← 加密技能正文（AES-256 密文）
│  SKILL.md.bak          ← 本地原始备份
│  scripts/
│  ├── verify.py         ← U 盘验证（WMI + RSA 验签）
│  ├── decrypt_body.py   ← 验签 → 解密 → stdout 输出正文
│  └── public_key.pem    ← 公钥（只验签，公开无妨）
└──────────────────────────────────────────────────────────────┘

┌─ 主U盘（加密狗）──────────────────────────────────────────────┐
│  private_key.pem       ← 签发权杖（妥善保管！）
│  license.dat           ← RSA 签名（256 字节，绑定此 U 盘）
└──────────────────────────────────────────────────────────────┘

┌─ 备用U盘 ────────────────────────────────────────────────────┐
│  license.dat           ← 仅授权凭证（无法签发新 license）
└──────────────────────────────────────────────────────────────┘

┌─ 异地备份（加密前自动生成）──────────────────────────────────┐
│  ~/skill-backup/<日期>/<技能名>/SKILL.md  ← 物理隔离明文备份
└──────────────────────────────────────────────────────────────┘
```

## 工作原理

1. **生成密钥** → RSA-2048 密钥对，私钥直接写入 U 盘，本地不留副本
2. **签名授权** → 私钥对 U 盘序列号签名 → license.dat
3. **加密技能** → 原始 SKILL.md 拆分为外壳引导器 + SKILL.body.enc（AES-256）
4. **使用技能** → AI 读外壳 → 自动跑 verify.py 验签 → 输入密码 → decrypt_body.py 解密正文 → 执行

外壳始终明文，WorkBuddy 的 AI 随时能读到解密协议。技能正文 AES-256 加密单独存放，没有密码和 U 盘谁也解不开。

## 快速开始

### 环境依赖

```bash
pip install pyAesCrypt cryptography wmi
```

### 一次性初始化

```bash
# 1. 读取 U 盘序列号
python scripts/read_serial.py

# 2. 生成 RSA 密钥（私钥直接写入 U 盘）
python scripts/gen_keys.py E

# 3. 签名 license.dat 到 U 盘
python scripts/sign_license.py E AA0B1C2D3E4F
```

### 加密技能

```bash
# 单个技能
python scripts/encrypt_skill.py

# 批量加密所有技能
python scripts/batch_encrypt.py
```

### 使用加密后的技能

跟平时用 WorkBuddy 一样，不需要额外操作。AI 加载加密技能时会自动：
1. 读取外壳引导器
2. 运行 verify.py 检查 U 盘
3. 验签通过 → 询问密码
4. 解密正文并执行

## 安全层次

| 层次 | 机制 | 作用 |
|---|---|---|
| 硬件绑定 | U 盘序列号 + RSA-2048 签名 | 只有授权 U 盘通过验签 |
| 内容加密 | AES-256（pyAesCrypt） | 没有密码，正文就是一坨密文 |
| 外壳隔离 | 外壳（明文）/ 正文（密文） | AI 能看到协议，看不到内容 |
| 私钥管控 | 私钥只存 U 盘 | 签发权绑定物理设备，拔掉谁也签不了 |
| 异地备份 | 加密前自动拷贝 | 即使原目录损坏，备份完好 |
| 多 U 盘冗余 | sign_multi.py | 丢一个 U 盘不影响，还有备用 |

## 文件结构

```
usb-dongle-encrypt/
├── SKILL.md              # WorkBuddy 技能定义（可加密自己，互通式加密）
└── scripts/
    ├── read_serial.py    # 读 U 盘序列号（含异常字符清洗）
    ├── gen_keys.py       # 生成 RSA-2048 密钥对（私钥 → U 盘）
    ├── sign_license.py   # 签名 license.dat（从 U 盘读私钥）
    ├── sign_multi.py     # 多 U 盘冗余签名
    ├── verify.py         # U 盘 RSA 验签（WMI 关联查询）
    ├── encrypt_skill.py  # 加密单个技能（外壳+正文+异地备份）
    ├── decrypt_body.py   # 验签 + 解密 → stdout
    ├── batch_encrypt.py  # 批量加密（含异地备份）
    └── public_key.pem    # 公钥（验签用）
```

## 常见问题

**Q: U 盘丢了怎么办？**

A: 准备 2-3 个 U 盘，用 sign_multi.py 给每个都签 license.dat。主 U 盘（存私钥的）锁抽屉，日常用备用 U 盘。

**Q: 加密后还能恢复吗？**

A: 加密前会做两重备份：本地 .bak + 异地 ~/skill-backup/。只要备份还在，随时恢复。

**Q: 别人把整个 skill 文件夹复制走能用吗？**

A: 不能。SKILL.body.enc 是 AES-256 密文，没有密码解不开。即使有密码，没有授权 U 盘，verify.py 验签不通过，decrypt_body.py 不会执行。即使复制了 license.dat 到自己的 U 盘，序列号不匹配，RSA 验签照样失败。

**Q: 加密过程需要联网吗？**

A: 完全不需要。整个流程纯本地运行，密钥生成、签名、加密全部离线完成。

## 许可证

本项目仅供学习和个人使用。私钥是你的责任——如果主 U 盘和所有备份都丢了，加密的技能无法恢复。
