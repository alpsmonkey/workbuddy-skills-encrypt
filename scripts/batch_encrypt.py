# batch_encrypt.py — 批量加密WorkBuddy技能
"""用法: echo "<密码>" | python scripts/batch_encrypt.py all <U盘盘符>
       echo "<密码>" | python scripts/batch_encrypt.py 1,3,5 <U盘盘符>
非交互模式：第一个参数为 all 或逗号分隔的技能编号，第二个参数为U盘盘符，密码走 stdin。
不带参数则进入原来的交互式菜单。"""
import os, shutil, sys, pyAesCrypt, hashlib
from datetime import datetime
from io import BytesIO
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

SKILLS_DIR = os.path.expanduser('~/.workbuddy/skills')
PASSWORD   = ''  # 留空则运行时手动输入
BUFFER     = 64 * 1024

# 异地备份目录（加密前自动把原始 SKILL.md 拷贝到这里，按日期归档）
# 建议设到另一块硬盘或加密文件夹，跟 skill 目录物理隔离
BACKUP_DIR = os.path.expanduser('~/skill-backup')

SHELL_TEMPLATE = """---
name: {name}
description: 已加密技能：需授权U盘验签+密码解密后使用。用户要求使用本技能或涉及解密/验签/加密狗/U盘授权时加载。
read_when: 用户要求使用本技能，或提到解密/验签/加密狗/U盘授权时
---

⚠️ 本技能已加密，需要先解密才能使用。

## 加密技能加载协议

检测 `SKILL.body.enc` 是否存在，若存在则执行以下步骤：

1. 运行 `python scripts/verify.py` 检查授权U盘是否插入
2. 如果验证通过，向用户询问解密密码和U盘盘符
3. 通过 stdin 传入密码解密（不要放命令行参数，避免密码进进程列表/历史）：`echo "<密码>" | python scripts/decrypt_body.py <U盘盘符>`
4. 读取解密输出作为本技能的实际指令，继续处理用户请求

如果 `SKILL.body.enc` 不存在，说明技能未加密或已解密，直接读取 SKILL.md 正文即可。
如果验证失败，告知用户技能无法加载，请插入授权U盘。
"""


def derive_key_from_usb(password: str, drive: str) -> bytes:
    """从密码和U盘密钥材料派生加密密钥"""
    enc_key_path = os.path.join(f'{drive}:/', 'encryption.key')
    if not os.path.exists(enc_key_path):
        print(f'错误：U盘 {drive}: 上没有找到 encryption.key')
        sys.exit(1)
    
    usb_key_material = open(enc_key_path, 'rb').read()
    if len(usb_key_material) != 32:
        print(f'错误：encryption.key 格式不正确（应为32字节）')
        sys.exit(1)
    
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=usb_key_material,
        info=b'workbuddy-skill-encryption'
    )
    return hkdf.derive(password.encode('utf-8'))


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


def encrypt_one(skill, encryption_password, date_str):
    name = skill['name']
    skill_path = skill['path']
    skill_md = skill['md']
    body_enc = os.path.join(skill_path, 'SKILL.body.enc')

    print(f'\n正在加密：{name}')

    # 0. 防重复加密
    if os.path.exists(body_enc):
        print(f'  跳过：{name} 已加密')
        return False

    # 1. 加密前先做异地备份（保险措施）
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

    # 2. 计算原文件哈希
    with open(skill_md, 'rb') as f:
        original_hash = hashlib.sha256(f.read()).hexdigest()

    # 3. 读取 frontmatter name（只扫描前 500 字节）
    with open(skill_md, 'r', encoding='utf-8') as f:
        header = f.read(500)
    skill_name = name
    in_frontmatter = False
    for line in header.split('\n'):
        if line.strip() == '---':
            if not in_frontmatter:
                in_frontmatter = True
            else:
                break
        elif in_frontmatter and line.startswith('name:'):
            skill_name = line.split(':', 1)[1].strip()
            break

    # 4. 加密
    with open(bak_path, 'rb') as fIn, \
         open(body_enc, 'wb') as fOut:
        pyAesCrypt.encryptStream(fIn, fOut, encryption_password, BUFFER)
    print(f'  已加密原始内容 → SKILL.body.enc')

    # 5. 往返校验
    enc_size = os.path.getsize(body_enc)
    buf = BytesIO()
    try:
        with open(body_enc, 'rb') as fIn:
            pyAesCrypt.decryptStream(fIn, buf, encryption_password, BUFFER, enc_size)
        buf.seek(0)
        decrypted_hash = hashlib.sha256(buf.read()).hexdigest()
        
        if decrypted_hash != original_hash:
            print(f'  ❌ 往返校验失败！已保留 .bak 和异地备份')
            return False
        print(f'  ✓ 往返校验通过')
    except Exception as e:
        print(f'  ❌ 往返校验失败：{e}')
        return False

    # 6. 写入外壳
    shell_content = SHELL_TEMPLATE.format(name=skill_name)
    with open(skill_md, 'w', encoding='utf-8') as f:
        f.write(shell_content)
    print(f'  已写入外壳 SKILL.md（明文）')

    # 7. 部署脚本和公钥（强制覆盖，确保多技能密钥一致）
    scripts_dir = os.path.join(skill_path, 'scripts')
    if not os.path.exists(scripts_dir):
        os.makedirs(scripts_dir)

    src_scripts = os.path.dirname(os.path.abspath(__file__))
    for fname in ['verify.py', 'decrypt_body.py', 'public_key.pem']:
        src = os.path.join(src_scripts, fname)
        dst = os.path.join(scripts_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f'  已部署 {fname}')

    # 8. 删除 .bak 明文
    os.remove(bak_path)
    print(f'  已删除 .bak（异地备份已保存）')

    print(f'  完成：{name}')
    return True


def read_password(prompt='请输入加密密码：'):
    """密码优先走 stdin 管道（不进进程列表/历史），否则交互输入"""
    if not sys.stdin.isatty():
        pwd = sys.stdin.readline().rstrip('\r\n')
    else:
        pwd = input(prompt)
    if not pwd:
        print('错误：密码为空')
        sys.exit(1)
    return pwd


def main():
    date_str = datetime.now().strftime('%Y-%m-%d')
    print('WorkBuddy 技能批量加密工具')
    print(f'技能目录：{SKILLS_DIR}\n')

    skills = get_skill_list()
    if not skills:
        print('未找到任何技能')
        return

    args = sys.argv[1:]
    if args:
        # 非交互模式：显式命令即确认，不再二次询问
        choice = args[0]
        drive = args[1].strip(':').upper() if len(args) >= 2 else input('请输入U盘盘符（如 E）：').strip(':').upper()
        password = read_password()
        
        print(f'正在从U盘 {drive}: 读取密钥材料...')
        derived_key = derive_key_from_usb(password, drive)
        encryption_password = derived_key.hex()
        
        if choice.lower() == 'all':
            to_encrypt = [s for s in skills if s['status'] == '未加密']
        else:
            indices = [int(x.strip()) - 1 for x in choice.split(',') if x.strip().isdigit()]
            to_encrypt = [skills[i] for i in indices if 0 <= i < len(skills)]
    else:
        print(f'找到 {len(skills)} 个技能：\n')
        for i, s in enumerate(skills):
            print(f'  [{i + 1}] {s["name"]}  ({s["status"]})')
        print()

        print('请输入要加密的技能编号（多个用逗号分隔，输入 all 加密全部未加密的，输入 q 退出）')
        choice = input('选择：').strip()

        if choice.lower() == 'q':
            print('已退出')
            return

        drive = input('请输入U盘盘符（如 E）：').strip(':').upper()

        password = PASSWORD
        if not password:
            password = read_password()
            confirm = input('再输一遍确认：').strip()
            if password != confirm:
                print('两次密码不一致，退出')
                return

        print(f'正在从U盘 {drive}: 读取密钥材料...')
        derived_key = derive_key_from_usb(password, drive)
        encryption_password = derived_key.hex()

        to_encrypt = []
        if choice.lower() == 'all':
            to_encrypt = [s for s in skills if s['status'] == '未加密']
        else:
            indices = [int(x.strip()) - 1 for x in choice.split(',') if x.strip().isdigit()]
            to_encrypt = [skills[i] for i in indices if 0 <= i < len(skills)]

    if not to_encrypt:
        print('没有选中任何技能')
        return

    if args:
        print(f'非交互模式：即将加密 {len(to_encrypt)} 个技能')
    else:
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
        if encrypt_one(skill, encryption_password, date_str):
            success += 1

    print(f'\n完成！成功加密 {success} 个技能')
    print('\n使用方法：')
    print('  在 WorkBuddy 中正常使用技能即可，AI 读到外壳会自动走验签→解密流程')
    print('  你只需要在 AI 询问时输入解密密码和U盘盘符')
    print(f'\n异地备份目录: {os.path.join(BACKUP_DIR, date_str)}/')


if __name__ == '__main__':
    main()
