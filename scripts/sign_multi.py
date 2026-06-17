# sign_multi.py — 用主U盘上的私钥，给多个U盘分别签名（冗余方案）
"""用法: python scripts/sign_multi.py
运行前修改下方的 DONGLES 列表，填入每个U盘的盘符和清洗后序列号"""
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# ⚠️ 修改这里：每个U盘的盘符和清洗后序列号
# 第一个是主U盘（持有 private_key.pem 的那个）
DONGLES = [
    {'drive': 'E', 'serial': 'AA0B1C2D3E4F'},   # 主U盘
    {'drive': 'F', 'serial': 'BB1C2D3E4F5G'},   # 备用U盘 1
    {'drive': 'G', 'serial': 'CC2D3E4F5G6H'},   # 备用U盘 2
]


def find_private_key_on_usb(drive):
    """在指定U盘上查找 private_key.pem"""
    path = os.path.join(f'{drive}:/', 'private_key.pem')
    if os.path.exists(path):
        return path
    return None


if __name__ == '__main__':
    # 先在主U盘上找到私钥
    master = DONGLES[0]
    priv_path = find_private_key_on_usb(master['drive'])

    if not priv_path:
        print(f'错误：主U盘 {master["drive"]}: 上没有找到 private_key.pem')
        print('请先运行 gen_keys.py 把私钥写入主U盘')
        sys.exit(1)

    priv = serialization.load_pem_private_key(
        open(priv_path, 'rb').read(), None
    )

    # 给每个U盘签名
    for dongle in DONGLES:
        drive = dongle['drive']
        serial = dongle['serial']
        sig = priv.sign(serial.encode(), padding.PKCS1v15(), hashes.SHA256())
        license_path = os.path.join(f'{drive}:/', 'license.dat')
        open(license_path, 'wb').write(sig)
        label = '（主U盘）' if dongle == DONGLES[0] else '（备用U盘）'
        print(f'✓ {drive}: license.dat 已写入 {label}')

    # 如果主U盘上还没有 private_key.pem 的备份说明
    print()
    print('全部签完！')
    print(f'主U盘 {master["drive"]}: 持有 private_key.pem + license.dat（签发权 + 授权凭证）')
    print('备用U盘只有 license.dat（仅授权凭证，不能签新license）')
