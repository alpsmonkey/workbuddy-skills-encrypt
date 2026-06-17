# sign_license.py — 用U盘上的私钥签名，生成license.dat到U盘
"""用法: python scripts/sign_license.py <U盘盘符> [序列号]
示例: python scripts/sign_license.py E AA0B1C2D3E4F
如果不传序列号，会自动调用 read_serial.py 的逻辑读取当前U盘序列号"""
import sys
import os
import re
import wmi
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def clean_serial(raw):
    """清洗序列号，只保留可打印ASCII字符"""
    return re.sub(r'[^\x20-\x7e]', '', raw.strip())


def find_private_key_on_usb(drive):
    """在指定U盘上查找 private_key.pem"""
    path = os.path.join(f'{drive}:/', 'private_key.pem')
    if os.path.exists(path):
        return path
    return None


def read_usb_serial(drive):
    """读取指定盘符U盘的序列号"""
    c = wmi.WMI()
    for d in c.Win32_DiskDrive():
        if 'USB' not in d.InterfaceType:
            continue
        # 通过关联查询找到对应的逻辑盘符
        try:
            for part in d.associators("Win32_DiskDriveToDiskPartition"):
                for ld in part.associators("Win32_LogicalDiskToPartition"):
                    if ld.DeviceID.strip(':').upper() == drive.upper():
                        serial = clean_serial(d.SerialNumber)
                        return serial
        except Exception:
            continue
    return None


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python sign_license.py <U盘盘符> [序列号]')
        print('示例: python sign_license.py E')
        print('      python sign_license.py E AA0B1C2D3E4F')
        sys.exit(1)

    drive = sys.argv[1].strip(':').upper()
    usb_root = f'{drive}:/' if len(sys.argv[1]) <= 2 else sys.argv[1]

    # 获取序列号
    if len(sys.argv) >= 3:
        serial = sys.argv[2]
    else:
        print(f'正在读取U盘 {drive}: 的序列号...')
        serial = read_usb_serial(drive)
        if not serial:
            print(f'错误：无法读取U盘 {drive}: 的序列号，请手动指定')
            sys.exit(1)

    print(f'序列号: {serial}')

    # 在U盘上查找私钥
    priv_path = find_private_key_on_usb(drive)
    if not priv_path:
        print(f'错误：U盘 {drive}: 上没有找到 private_key.pem')
        print('请先运行 gen_keys.py 把私钥写入U盘')
        sys.exit(1)

    # 用私钥签名
    priv = serialization.load_pem_private_key(
        open(priv_path, 'rb').read(), None
    )
    sig = priv.sign(
        serial.encode(),
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    # 写入 license.dat 到U盘根目录
    license_path = os.path.join(f'{drive}:/', 'license.dat')
    open(license_path, 'wb').write(sig)
    print(f'license.dat 已写入: {license_path}')
    print(f'U盘 {drive}: 现在既是授权凭证（license.dat），又是签发权杖（private_key.pem）')
