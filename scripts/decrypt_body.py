# decrypt_body.py — 先验签U盘，通过后解密SKILL.body.enc并输出正文
"""用法: echo "<密码>" | python scripts/decrypt_body.py <U盘盘符>
密码通过 stdin 传入（推荐，避免进进程列表/历史），直接运行则交互式输入
需要 U 盘上的 encryption.key 参与密钥派生"""
import pyAesCrypt, os, sys, subprocess
from io import BytesIO
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

BUFFER = 64 * 1024

scripts_dir = os.path.dirname(os.path.abspath(__file__))
skill_dir = os.path.dirname(scripts_dir)
enc_path = os.path.join(skill_dir, 'SKILL.body.enc')
verify_script = os.path.join(scripts_dir, 'verify.py')


def derive_key_from_usb(password: str, drive: str) -> bytes:
    """从密码和U盘密钥材料派生加密密钥"""
    enc_key_path = os.path.join(f'{drive}:/', 'encryption.key')
    if not os.path.exists(enc_key_path):
        print(f'错误：U盘 {drive}: 上没有找到 encryption.key', file=sys.stderr)
        sys.exit(1)
    
    usb_key_material = open(enc_key_path, 'rb').read()
    if len(usb_key_material) != 32:
        print(f'错误：encryption.key 格式不正确（应为32字节）', file=sys.stderr)
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
    # 第一步：验证U盘
    if os.path.exists(verify_script):
        print('正在检查授权U盘...', file=sys.stderr)
        result = subprocess.run(
            [sys.executable, verify_script],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print('U盘验证失败，无法解密', file=sys.stderr)
            sys.exit(1)
        print('U盘验证通过', file=sys.stderr)

    # 第二步：获取密码（stdin 管道优先；不接受命令行参数，避免密码进进程列表/历史）
    if not sys.stdin.isatty():
        password = sys.stdin.readline().rstrip('\r\n')
    else:
        password = input('请输入解密密码：')
    if not password:
        print('错误：密码为空', file=sys.stderr)
        sys.exit(1)

    # 第三步：获取U盘盘符
    if len(sys.argv) >= 2:
        drive = sys.argv[1].strip(':').upper()
    else:
        drive = input('请输入U盘盘符（如 E）：').strip(':').upper()

    if not os.path.exists(enc_path):
        print(f'加密文件不存在：{enc_path}', file=sys.stderr)
        sys.exit(1)

    # 第四步：从U盘派生解密密钥
    derived_key = derive_key_from_usb(password, drive)
    encryption_password = derived_key.hex()

    # 第五步：解密到内存流，不留临时文件
    enc_size = os.path.getsize(enc_path)
    buf = BytesIO()

    try:
        with open(enc_path, 'rb') as fIn:
            pyAesCrypt.decryptStream(fIn, buf, encryption_password, BUFFER, enc_size)
    except ValueError:
        print('错误：解密失败（密码错误、U盘不匹配或文件损坏）', file=sys.stderr)
        sys.exit(1)

    buf.seek(0)
    # 直接输出原始字节：不经文本层换行转换，保证与加密前逐字节一致
    sys.stdout.buffer.write(buf.read())
    sys.stdout.buffer.flush()
