# batch_encrypt.py — 批量加密WorkBuddy技能
"""用法: python scripts/batch_encrypt.py
扫描 ~/.workbuddy/skills/ 下所有技能，选择加密目标"""
import os, shutil, pyAesCrypt
from datetime import datetime

SKILLS_DIR = os.path.expanduser('~/.workbuddy/skills')
PASSWORD   = ''  # 留空则运行时手动输入
BUFFER     = 64 * 1024

# 异地备份目录（加密前自动把原始 SKILL.md 拷贝到这里，按日期归档）
# 建议设到另一块硬盘或加密文件夹，跟 skill 目录物理隔离
BACKUP_DIR = os.path.expanduser('~/skill-backup')

SHELL_TEMPLATE = """---
name: {name}
description: {desc}
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


def get_skill_list():
    skills = []
    if not os.path.exists(SKILLS_DIR):
        print(f'技能目录不存在：{SKILLS_DIR}')
        return skills
    for name in os.listdir(SKILLS_DIR):
        skill_path = os.path.join(SKILLS_DIR, name)
        skill_md = os.path.join(skill_path, 'SKILL.md')
        if os.path.isdir(skill_path) and os.path.exists(skill_md):
            body_enc = os.path.join(skill_path, 'SKILL.body.enc')
            status = '已加密' if os.path.exists(body_enc) else '未加密'
            skills.append({'name': name, 'path': skill_path, 'md': skill_md, 'status': status})
    return skills


def encrypt_one(skill, password):
    name = skill['name']
    skill_path = skill['path']
    skill_md = skill['md']

    print(f'\n正在加密：{name}')

    # 0. 加密前先做异地备份（保险措施）
    date_str = datetime.now().strftime('%Y-%m-%d')
    backup_dir = os.path.join(BACKUP_DIR, date_str, name)
    os.makedirs(backup_dir, exist_ok=True)
    shutil.copy2(skill_md, os.path.join(backup_dir, 'SKILL.md'))
    print(f'  异地备份已保存: {backup_dir}/SKILL.md')

    bak_path = skill_md + '.bak'
    if os.path.exists(bak_path):
        print(f'  跳过：{name} 已有备份文件 (.bak)')
        return False
    shutil.copy2(skill_md, bak_path)
    print(f'  已备份 SKILL.md → SKILL.md.bak')

    with open(skill_md, 'r', encoding='utf-8') as f:
        first_lines = f.read(500)
    skill_name = name
    skill_desc = '技能内容已加密保护'
    for line in first_lines.split('\n'):
        if line.startswith('name:'):
            skill_name = line.split(':', 1)[1].strip()
        elif line.startswith('description:'):
            skill_desc = line.split(':', 1)[1].strip()

    body_enc = os.path.join(skill_path, 'SKILL.body.enc')
    with open(bak_path, 'rb') as fIn, \
         open(body_enc, 'wb') as fOut:
        pyAesCrypt.encryptStream(fIn, fOut, password, BUFFER)
    print(f'  已加密原始内容 → SKILL.body.enc')

    shell_content = SHELL_TEMPLATE.format(name=skill_name, desc=skill_desc)
    with open(skill_md, 'w', encoding='utf-8') as f:
        f.write(shell_content)
    print(f'  已写入外壳 SKILL.md（明文）')

    scripts_dir = os.path.join(skill_path, 'scripts')
    if not os.path.exists(scripts_dir):
        os.makedirs(scripts_dir)
        print(f'  已创建 scripts/ 目录')

    # 部署验证脚本和公钥（与 encrypt_skill.py 保持一致）
    src_scripts = os.path.dirname(os.path.abspath(__file__))
    for fname in ['verify.py', 'decrypt_body.py', 'public_key.pem']:
        src = os.path.join(src_scripts, fname)
        dst = os.path.join(scripts_dir, fname)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            print(f'  已部署 {fname} 到 {scripts_dir}/')

    print(f'  完成：{name}')
    return True


def main():
    print('WorkBuddy 技能批量加密工具')
    print(f'技能目录：{SKILLS_DIR}\n')

    skills = get_skill_list()
    if not skills:
        print('未找到任何技能')
        return

    print(f'找到 {len(skills)} 个技能：\n')
    for i, s in enumerate(skills):
        print(f'  [{i + 1}] {s["name"]}  ({s["status"]})')
    print()

    print('请输入要加密的技能编号（多个用逗号分隔，输入 all 加密全部未加密的，输入 q 退出）')
    choice = input('选择：').strip()

    if choice.lower() == 'q':
        print('已退出')
        return

    password = PASSWORD
    if not password:
        password = input('请输入加密密码：').strip()
        confirm = input('再输一遍确认：').strip()
        if password != confirm:
            print('两次密码不一致，退出')
            return

    to_encrypt = []
    if choice.lower() == 'all':
        to_encrypt = [s for s in skills if s['status'] == '未加密']
    else:
        indices = [int(x.strip()) - 1 for x in choice.split(',') if x.strip().isdigit()]
        to_encrypt = [skills[i] for i in indices if 0 <= i < len(skills)]

    if not to_encrypt:
        print('没有选中任何技能')
        return

    print(f'\n即将加密 {len(to_encrypt)} 个技能')
    confirm = input('确认？(y/n)：').strip().lower()
    if confirm != 'y':
        print('已退出')
        return

    success = 0
    for skill in to_encrypt:
        if skill['status'] == '已加密':
            print(f'  跳过（已加密）：{skill["name"]}')
            continue
        if encrypt_one(skill, password):
            success += 1

    print(f'\n完成！成功加密 {success} 个技能')
    print('\n使用方法：')
    print('  在 WorkBuddy 中正常使用技能即可，AI 读到外壳会自动走验签→解密流程')
    print('  你只需要在 AI 询问时输入解密密码')
    print(f'\n异地备份目录: {os.path.join(BACKUP_DIR, date_str)}/')


if __name__ == '__main__':
    main()
