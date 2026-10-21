---
name: workbuddy-skills-encrypt
description: USB加密狗互通式加密系统——保护WorkBuddy技能不被未授权复制。支持单技能/批量加密、RSA-2048签名验证、AES-256加密正文、外壳+正文分层架构。初始化→生成密钥→签名U盘→加密技能，四步锁死。可通过 git clone 直接安装到 WorkBuddy。
---

# USB 加密狗互通式加密系统

## 核心能力

把 U 盘变成 WorkBuddy 技能的物理加密狗。加密后的技能采用「外壳+正文」分层架构——外壳（SKILL.md）始终可读，告诉 AI 如何解密；正文（SKILL.body.enc）AES-256 加密存放，只有插入授权 U 盘并输入密码才能获取。

本技能自己也可以被自己加密（互通式加密）。

## 使用场景

触发以下意图时使用本技能：
- "帮我给技能加密" / "给 XX 技能上锁" / "用U盘保护技能"
- "设置U盘加密狗" / "初始化加密狗"
- "加密所有技能" / "批量加密"
- "解密某个技能" / "解封技能"
- "验证U盘授权" / "检查加密狗状态"
- "给新U盘签名" / "多U盘冗余"

## 工作流程

### 初始化（仅需一次）

整个加密体系只需要初始化一次，之后所有技能共享同一套密钥和 U 盘授权：

1. **检查 U 盘** → `python scripts/read_serial.py`
   - 读取 U 盘硬件序列号，清洗异常字符
   - 序列号为空的 U 盘不可用，需要换盘
   - 记住盘符（如 E:），后面所有步骤都要用

2. **生成密钥对和加密密钥材料** → `python scripts/gen_keys.py E`
   - 生成 RSA-2048 密钥对（用于验签）
   - 生成 32 字节随机密钥材料 encryption.key（用于加密）
   - **私钥和密钥材料直接写入U盘根目录**（private_key.pem + encryption.key），不留在本地
   - 公钥留在 scripts/ 目录（public_key.pem），用于验签

3. **签名 license.dat** → `python scripts/sign_license.py E`
   - 从U盘读取 private_key.pem 签名
   - 将 license.dat 写入U盘根目录
   - 现在U盘上有 private_key.pem + encryption.key + license.dat

4. **部署公钥** → 将 public_key.pem 拷贝到目标技能目录的 scripts/

### 加密技能

5. **加密** → `echo "<密码>" | python scripts/encrypt_skill.py <SKILL.md路径> <U盘盘符>`（单个）或 `echo "<密码>" | python scripts/batch_encrypt.py all <U盘盘符>`（批量）
   - 从 U 盘读取 encryption.key，用 HKDF(密码, encryption.key) 派生加密密钥
   - 备份原始 SKILL.md 到异地备份目录
   - 加密正文 → SKILL.body.enc（AES-256）
   - 往返校验：立即解密比对 SHA256，确保加密成功
   - 删除本地明文备份（只保留异地备份）
   - 写入外壳 SKILL.md（明文 bootloader，告诉 AI 解密协议）
   - 自动部署验签和解密脚本到 scripts/

### 使用加密后的技能

AI 加载技能时自动执行：
1. 读取外壳 SKILL.md → 识别加密协议
2. 运行 `python scripts/verify.py` → 检查 U 盘 + RSA 验签
3. 验签通过 → 询问密码和U盘盘符 → 通过 stdin 传入密码解密：`echo "<密码>" | python scripts/decrypt_body.py <U盘盘符>` → 获取正文
4. 按正文指令执行任务

### 管理加密技能

**解封（恢复原始 SKILL.md）** → `python scripts/unseal_skill.py <技能目录>`
- 优先使用本地 .bak 或异地备份恢复
- 如果备份不存在，可通过密码+U盘解密恢复
- 解封后删除 SKILL.body.enc

**改密（用新密码重新加密）** → `echo "<旧密码>\n<新密码>" | python scripts/change_password.py <技能目录> <U盘盘符>`
- 用旧密码解密到内存
- 用新密码重新加密
- 往返校验确保新密码可用

**给新 U 盘签名（多 U 盘冗余）** → `python scripts/sign_multi.py <主U盘盘符> <备用U盘盘符1> [<备用U盘盘符2> ...]`
- 自动读取每个U盘的序列号并签名
- 主U盘 = 签发权杖（有 private_key.pem）+ 授权凭证（有 license.dat）
- 备用U盘 = 仅授权凭证（只有 license.dat，不能签新 license）

### 临时解密查看

```bash
echo "<密码>" | python scripts/decrypt_body.py <U盘盘符> > temp.md
```

解密输出到文件查看，看完删除。

### 异地备份（保险措施）

加密前，脚本会自动把原始 SKILL.md 拷贝到 `~/skill-backup/<日期>/<技能名>/` 目录。
这是一个物理隔离的保险措施——即使原 skill 目录被误删、磁盘损坏，备份目录里的明文原件依然完好。

修改 `BACKUP_DIR` 变量可自定义备份路径（建议设到另一块硬盘或加密文件夹）。

## 文件结构

```
workbuddy-skills-encrypt/              # 本技能（本地 skill 目录）
├── SKILL.md                           # 本文件
└── scripts/
    ├── read_serial.py                 # 读取U盘序列号（含异常字符清洗）
    ├── gen_keys.py                    # 生成RSA-2048密钥对+加密密钥材料（写入U盘）
    ├── sign_license.py                # 签名license.dat到U盘（从U盘读私钥）
    ├── sign_multi.py                  # 多U盘冗余签名（自动读序列号）
    ├── public_key.pem                 # 公钥（验签用，留在本地）
    ├── verify.py                      # U盘验签（WMI关联查询版）
    ├── encrypt_skill.py               # 加密单个技能（HKDF派生+往返校验）
    ├── decrypt_body.py                # 验签+解密正文到stdout
    ├── batch_encrypt.py               # 批量加密
    ├── unseal_skill.py                # 解封技能（恢复原始SKILL.md）
    └── change_password.py             # 改密（用新密码重新加密）

U盘根目录（物理加密狗）：                # 主U盘
├── private_key.pem                    # 私钥（签发权杖，仅主U盘持有）
├── encryption.key                     # 32字节随机密钥材料（加密用）
└── license.dat                        # RSA签名（授权凭证）

备用U盘根目录：                         # 备用U盘
├── encryption.key                     # 与主U盘相同的密钥材料（需手动复制）
└── license.dat                        # 仅授权凭证，无签发权

异地备份目录（保险措施）：                # 加密前自动复制明文原件
~/skill-backup/<日期>/<技能名>/
└── SKILL.md                           # 原始明文，加密后也不会被覆盖
```

## 安全架构

| 角色 | 存储位置 | 作用 |
|---|---|---|
| private_key.pem | **主U盘根目录** | 签发新 license 的唯一凭证，拔掉U盘谁也签不了 |
| encryption.key | **U盘根目录** | 32字节随机密钥材料，与密码一起派生加密密钥（HKDF） |
| public_key.pem | scripts/ 本地 | 验签用，公开无所谓 |
| license.dat | 每个U盘根目录 | RSA 签名，证明"这个U盘被授权了" |
| SKILL.body.enc | 被加密技能目录 | AES-256 加密的技能正文，加密密钥 = HKDF(密码, encryption.key) |

**v3 架构改进**：
- U盘不再只是验签流程检查，而是真正参与加密本身
- 加密密钥 = HKDF(密码, U盘密钥材料)，没有 U 盘物理上无法解密
- 即使知道密码，没有正确的 U 盘也解不开
- 整个加密体系的安全性完全绑定在物理U盘上

## 注意事项

- **私钥和密钥材料只存在于U盘上**，本地不留副本。拔了U盘 = 丢失签发权和解密能力，建议额外备份到密码管理器或加密压缩包
- **解密密码设置独立强密码**——v3 架构下，密码和 U 盘缺一不可，双因素保护
- **密码不进命令行**：所有脚本通过 stdin 或交互获取密码，禁止放在命令行参数里（会进进程列表、shell 历史和 AI 上下文日志）
- **备用U盘需要手动复制 encryption.key**：`sign_multi.py` 只签发 license.dat，encryption.key 需要手动从主U盘复制到备用U盘
- **多 U 盘冗余**：用 sign_multi.py 给多个 U 盘分别签 license.dat，丢一个不影响
- **互通式加密**：本技能也可以加密自己（运行 encrypt_skill.py 指向本技能的 SKILL.md），加密后会生成外壳，功能不变
- **v3 破坏性变更**：旧版（v2 及之前）加密的技能无法用 v3 解密，需要先用旧版解封再用新版重新加密
