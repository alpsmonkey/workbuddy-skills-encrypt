# encrypt_skill.py — 拆分目标SKILL.md为外壳+加密正文
"""用法: python scripts/encrypt_skill.py
交互式输入密码和目标SKILL.md路径"""
import pyAesCrypt, os, shutil, sys
from datetime import datetime

# 修复 Windows 终端 GBK 编码问题
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 异地备份目录（修改为你自己的安全位置，如另一块硬盘、加密文件夹）
BACKUP_DIR = os.path.expanduser('~/skill-backup')

if __name__ == '__main__':
    password = input('请输入加密密码（U盘序列号或自定义强密码）：')
    skill_path = input('请输入目标 SKILL.md 的完整路径：')

    if not os.path.exists(skill_path):
        print(f'文件不存在：{skill_path}')
        exit(1)

    skill_dir = os.path.dirname(skill_path)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    BUFFER = 64 * 1024
    date_str = datetime.now().strftime('%Y-%m-%d')

    # 0. 创建 scripts 目录并部署公钥和验证脚本
    target_scripts = os.path.join(skill_dir, 'scripts')
    os.makedirs(target_scripts, exist_ok=True)
    
    # 复制公钥
    src_pub = os.path.join(script_dir, 'public_key.pem')
    if os.path.exists(src_pub):
        shutil.copy2(src_pub, os.path.join(target_scripts, 'public_key.pem'))
        print(f'已部署公钥到 {target_scripts}/public_key.pem')
    
    # 复制验证脚本
    for script_name in ['verify.py', 'decrypt_body.py']:
        src_script = os.path.join(script_dir, script_name)
        if os.path.exists(src_script):
            shutil.copy2(src_script, os.path.join(target_scripts, script_name))
            print(f'已部署 {script_name} 到 {target_scripts}/')

    # 0.5. 加密前先做异地备份（保险措施，按技能名分目录避免同天覆盖）
    skill_name = os.path.basename(skill_dir)
    backup_dir = os.path.join(BACKUP_DIR, date_str, skill_name)
    os.makedirs(backup_dir, exist_ok=True)
    shutil.copy2(skill_path, os.path.join(backup_dir, 'SKILL.md'))
    print(f'异地备份已保存: {backup_dir}/SKILL.md')

    # 1. 备份原始 SKILL.md → SKILL.md.bak（若已存在则拒绝，防止覆盖）
    bak_path = skill_path + '.bak'
    if os.path.exists(bak_path):
        print(f'错误：已存在备份文件 {bak_path}，请先手动处理后再加密')
        exit(1)
    shutil.copy2(skill_path, bak_path)
    print(f'已备份原文件为 {bak_path}')

    # 2. 加密原始内容 → SKILL.body.enc
    body_enc = os.path.join(skill_dir, 'SKILL.body.enc')
    with open(skill_path, 'rb') as fIn, \
         open(body_enc, 'wb') as fOut:
        pyAesCrypt.encryptStream(fIn, fOut, password, BUFFER)
    print(f'加密完成：{body_enc}')

    # 3. 读取原始 frontmatter 的 name 和 description
    with open(skill_path + '.bak', 'r', encoding='utf-8') as f:
        content = f.read()

    name = '未知技能'
    desc = '技能内容已加密保护'
    for line in content.split('\n'):
        if line.startswith('name:'):
            name = line.split(':', 1)[1].strip()
        elif line.startswith('description:'):
            desc = line.split(':', 1)[1].strip()

    # 4. 写入外壳 SKILL.md（明文，永不加密；description 脱敏，不暴露技能内容）
    shell = f"""---
name: {name}
description: category: utility
---

⚠️ 本技能已加密，需要先解密才能使用。

## 加密技能加载协议

检测 `SKILL.body.enc` 是否存在，若存在则执行以下步骤：

1. 运行 `python scripts/verify.py` 检查授权U盘是否插入
2. 如果验证通过，向用户询问解密密码
3. 运行 `python scripts/decrypt_body.py "<密码>"` 解密技能正文
4. 读取解密输出作为本技能的实际指令，继续处理用户请求

如果 `SKILL.body.enc` 不存在，说明技能未加密或已解密，直接读取 SKILL.md 正文即可。
如果验证失败，告知用户技能无法加载，请插入授权U盘。
"""

    with open(skill_path, 'w', encoding='utf-8') as f:
        f.write(shell)
    print('外壳 SKILL.md 已写入（明文，永不加密）')
    print(f'\n⚠️ 原件已备份到两处：')
    print(f'  本地备份: {skill_path}.bak')
    print(f'  异地备份: {backup_dir}/SKILL.md')
    print('  请确认 .bak 文件和异地备份均内容完整！')
