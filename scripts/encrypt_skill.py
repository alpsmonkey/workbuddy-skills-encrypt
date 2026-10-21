# encrypt_skill.py — 拆分目标SKILL.md为外壳+加密正文
"""用法: echo "<密码>" | python scripts/encrypt_skill.py <SKILL.md路径> <U盘盘符>
密码通过 stdin 传入（推荐）或交互式输入；不带参数则完全交互式运行
需要 U 盘上的 encryption.key 参与密钥派生"""
import pyAesCrypt, os, shutil, sys, hashlib
from datetime import datetime
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from io import BytesIO

# 修复 Windows 终端 GBK 编码问题
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 异地备份目录（修改为你自己的安全位置，如另一块硬盘、加密文件夹）
BACKUP_DIR = os.path.expanduser('~/skill-backup')
BUFFER = 64 * 1024


def derive_key_from_usb(password: str, drive: str) -> bytes:
    """从密码和U盘密钥材料派生加密密钥"""
    enc_key_path = os.path.join(f'{drive}:/', 'encryption.key')
    if not os.path.exists(enc_key_path):
        print(f'错误：U盘 {drive}: 上没有找到 encryption.key')
        print('请先运行 gen_keys.py 生成密钥')
        sys.exit(1)
    
    usb_key_material = open(enc_key_path, 'rb').read()
    if len(usb_key_material) != 32:
        print(f'错误：encryption.key 格式不正确（应为32字节）')
        sys.exit(1)
    
    # HKDF 派生：密码 + U盘密钥材料 -> 32字节密钥
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=usb_key_material,
        info=b'workbuddy-skill-encryption'
    )
    return hkdf.derive(password.encode('utf-8'))


if __name__ == '__main__':
    # 密码优先走 stdin 管道（不进进程列表/历史），路径和盘符走 argv；都不给则交互式
    if not sys.stdin.isatty():
        password = sys.stdin.readline().rstrip('\r\n')
    else:
        password = input('请输入加密密码（自定义强密码）：')
    if not password:
        print('错误：密码为空')
        sys.exit(1)
    
    if len(sys.argv) >= 2:
        skill_path = sys.argv[1]
    else:
        skill_path = input('请输入目标 SKILL.md 的完整路径：')
    
    if len(sys.argv) >= 3:
        drive = sys.argv[2].strip(':').upper()
    else:
        drive = input('请输入U盘盘符（如 E）：').strip(':').upper()

    if not os.path.exists(skill_path):
        print(f'文件不存在：{skill_path}')
        sys.exit(1)

    skill_dir = os.path.dirname(skill_path)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    date_str = datetime.now().strftime('%Y-%m-%d')
    body_enc = os.path.join(skill_dir, 'SKILL.body.enc')

    # 0. 防重复加密：检查是否已加密
    if os.path.exists(body_enc):
        print(f'错误：技能已加密（{body_enc} 已存在）')
        print('如需重新加密，请先手动删除 SKILL.body.enc 和 SKILL.md.bak，或使用解封脚本恢复原件')
        sys.exit(1)

    # 0.1 从U盘派生加密密钥
    print(f'正在从U盘 {drive}: 读取密钥材料...')
    derived_key = derive_key_from_usb(password, drive)
    # pyAesCrypt 需要字符串密码，我们用派生密钥的十六进制表示
    encryption_password = derived_key.hex()

    # 0.2 创建 scripts 目录并部署公钥和验证脚本
    target_scripts = os.path.join(skill_dir, 'scripts')
    os.makedirs(target_scripts, exist_ok=True)
    
    # 复制公钥
    src_pub = os.path.join(script_dir, 'public_key.pem')
    if os.path.exists(src_pub):
        shutil.copy2(src_pub, os.path.join(target_scripts, 'public_key.pem'))
        print(f'已部署公钥到 {target_scripts}/public_key.pem')
    
    # 复制验证和解密脚本
    for script_name in ['verify.py', 'decrypt_body.py']:
        src_script = os.path.join(script_dir, script_name)
        if os.path.exists(src_script):
            shutil.copy2(src_script, os.path.join(target_scripts, script_name))
            print(f'已部署 {script_name} 到 {target_scripts}/')

    # 0.3 加密前先做异地备份（保险措施，按技能名分目录避免同天覆盖）
    skill_name = os.path.basename(skill_dir)
    backup_dir = os.path.join(BACKUP_DIR, date_str, skill_name)
    os.makedirs(backup_dir, exist_ok=True)
    shutil.copy2(skill_path, os.path.join(backup_dir, 'SKILL.md'))
    print(f'异地备份已保存: {backup_dir}/SKILL.md')

    # 1. 备份原始 SKILL.md → SKILL.md.bak（若已存在则拒绝，防止覆盖）
    bak_path = skill_path + '.bak'
    if os.path.exists(bak_path):
        print(f'错误：已存在备份文件 {bak_path}，请先手动处理后再加密')
        sys.exit(1)
    shutil.copy2(skill_path, bak_path)
    print(f'已备份原文件为 {bak_path}')

    # 2. 计算原文件哈希
    with open(skill_path, 'rb') as f:
        original_hash = hashlib.sha256(f.read()).hexdigest()
    print(f'原文件 SHA256: {original_hash[:16]}...')

    # 3. 加密原始内容 → SKILL.body.enc
    with open(skill_path, 'rb') as fIn, \
         open(body_enc, 'wb') as fOut:
        pyAesCrypt.encryptStream(fIn, fOut, encryption_password, BUFFER)
    print(f'加密完成：{body_enc}')

    # 4. 往返校验：立即解密到内存并比对哈希
    print('正在进行往返校验...')
    enc_size = os.path.getsize(body_enc)
    buf = BytesIO()
    try:
        with open(body_enc, 'rb') as fIn:
            pyAesCrypt.decryptStream(fIn, buf, encryption_password, BUFFER, enc_size)
        buf.seek(0)
        decrypted_hash = hashlib.sha256(buf.read()).hexdigest()
        
        if decrypted_hash != original_hash:
            print(f'❌ 往返校验失败！')
            print(f'   原文件: {original_hash[:16]}...')
            print(f'   解密后: {decrypted_hash[:16]}...')
            print(f'   加密文件可能损坏，已保留 .bak 和异地备份，请检查')
            sys.exit(1)
        print(f'✓ 往返校验通过（SHA256 一致）')
    except Exception as e:
        print(f'❌ 往返校验失败：{e}')
        print(f'   已保留 .bak 和异地备份，请检查')
        sys.exit(1)

    # 5. 读取原始 frontmatter 的 name（只扫描前 500 字节，避免正文干扰）
    with open(bak_path, 'r', encoding='utf-8') as f:
        header = f.read(500)

    name = '未知技能'
    in_frontmatter = False
    for line in header.split('\n'):
        if line.strip() == '---':
            if not in_frontmatter:
                in_frontmatter = True
            else:
                break  # 遇到第二个 --- 就退出
        elif in_frontmatter and line.startswith('name:'):
            name = line.split(':', 1)[1].strip()
            break

    # 6. 写入外壳 SKILL.md（明文，永不加密；description 只留中性触发词，不暴露技能主题）
    shell = f"""---
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

    with open(skill_path, 'w', encoding='utf-8') as f:
        f.write(shell)
    print('外壳 SKILL.md 已写入（明文，永不加密）')

    # 7. 往返校验通过后删除 .bak 明文（只保留异地备份）
    os.remove(bak_path)
    print(f'已删除本地明文备份 {bak_path}（异地备份已保存）')
    
    print(f'\n✓ 加密完成！')
    print(f'  原件备份: {backup_dir}/SKILL.md')
    print(f'  请确认异地备份内容完整！')
