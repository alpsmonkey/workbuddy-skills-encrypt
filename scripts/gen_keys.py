# gen_keys.py — 生成 RSA-2048 密钥对 + 加密密钥材料，私钥和密钥材料直接写入U盘
"""用法: python scripts/gen_keys.py <U盘盘符>
示例: python scripts/gen_keys.py E
生成 public_key.pem（公钥，留在本地 scripts/）+ private_key.pem（私钥，写入U盘根目录）+ encryption.key（32字节随机密钥材料，写入U盘根目录）"""
import sys
import os
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from secrets import token_bytes

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python gen_keys.py <U盘盘符>')
        print('示例: python gen_keys.py E')
        print()
        print('请先运行 read_serial.py 确认U盘盘符，然后传入盘符（不带冒号）')
        sys.exit(1)

    drive = sys.argv[1].strip(':').upper()
    usb_root = f'{drive}:/'

    # 检查U盘是否存在
    if not os.path.exists(usb_root):
        print(f'错误：找不到U盘 {usb_root}，请确认U盘已插入且盘符正确')
        sys.exit(1)

    # 检查是否已有密钥，避免误覆盖
    priv_path = os.path.join(usb_root, 'private_key.pem')
    enc_key_path = os.path.join(usb_root, 'encryption.key')
    if os.path.exists(priv_path) or os.path.exists(enc_key_path):
        print('⚠️ 警告：U盘上已存在密钥文件，覆盖后之前签发的 license 和加密的技能将全部失效！')
        confirm = input('确认覆盖？(yes/no): ').strip().lower()
        if confirm != 'yes':
            print('已取消')
            sys.exit(0)

    # 生成 RSA-2048 密钥对
    print('正在生成 RSA-2048 密钥对...')
    priv = rsa.generate_private_key(65537, 2048)
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()
    )
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # 生成 32 字节随机加密密钥材料
    print('正在生成加密密钥材料...')
    enc_key = token_bytes(32)

    # 公钥留在本地 scripts/ 目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pub_path = os.path.join(script_dir, 'public_key.pem')
    open(pub_path, 'wb').write(pub_pem)
    print(f'公钥已保存: {pub_path}')

    # 私钥和加密密钥材料写入U盘根目录
    open(priv_path, 'wb').write(priv_pem)
    print(f'私钥已写入U盘: {priv_path}')
    
    open(enc_key_path, 'wb').write(enc_key)
    print(f'加密密钥材料已写入U盘: {enc_key_path}')

    # 确认本地 scripts/ 目录没有私钥残留
    local_priv = os.path.join(script_dir, 'private_key.pem')
    if os.path.exists(local_priv):
        os.remove(local_priv)
        print(f'已删除本地残留私钥: {local_priv}')

    print()
    print('⚠️ 私钥和加密密钥材料只存在于U盘上！拔掉U盘 = 丢失签发权和解密能力，请妥善保管。')
    print('⚠️ 建议额外把 private_key.pem 和 encryption.key 备份到密码管理器或加密压缩包中。')
