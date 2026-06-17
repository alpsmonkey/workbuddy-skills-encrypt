# decrypt_body.py — 先验签U盘，通过后解密SKILL.body.enc并输出正文
"""用法: python scripts/decrypt_body.py "<密码>"
密码可通过命令行传入（推荐），也可交互式输入"""
import pyAesCrypt, os, sys, subprocess
from io import BytesIO

BUFFER = 64 * 1024

scripts_dir = os.path.dirname(os.path.abspath(__file__))
skill_dir = os.path.dirname(scripts_dir)
enc_path = os.path.join(skill_dir, 'SKILL.body.enc')
verify_script = os.path.join(scripts_dir, 'verify.py')

if __name__ == '__main__':
    # 第一步：验证U盘
    if os.path.exists(verify_script):
        print('正在检查授权U盘...')
        result = subprocess.run(
            [sys.executable, verify_script],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print('U盘验证失败，无法解密')
            sys.exit(1)
        print('U盘验证通过')

    # 第二步：获取密码
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = input('请输入解密密码：')

    if not os.path.exists(enc_path):
        print(f'加密文件不存在：{enc_path}')
        sys.exit(1)

    # 第三步：解密到内存流，不留临时文件
    enc_size = os.path.getsize(enc_path)
    buf = BytesIO()

    with open(enc_path, 'rb') as fIn:
        pyAesCrypt.decryptStream(fIn, buf, password, BUFFER, enc_size)

    buf.seek(0)
    content = buf.read().decode('utf-8')
    print(content)
