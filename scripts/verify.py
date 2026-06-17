# verify.py — 检测是否有已授权的U盘插入，RSA验签
"""用法: python scripts/verify.py
返回 0 = 验证通过    返回 1 = 验证失败"""
import wmi, sys, os, re
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# 修复 Windows 终端 GBK 编码问题
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def clean_serial(raw):
    """清洗序列号：去除不可打印字符，只保留字母数字和常见符号"""
    if not raw:
        return ''
    cleaned = re.sub(r'[^\x20-\x7e]', '', raw)
    return cleaned.strip()


def check_usb():
    """检测是否有已授权的U盘插入，任一通过即放行"""
    c = wmi.WMI()
    pub_path = os.path.join(os.path.dirname(__file__), 'public_key.pem')

    if not os.path.exists(pub_path):
        print('缺少公钥文件 public_key.pem，技能无法加载')
        return False

    pub = serialization.load_pem_public_key(open(pub_path, 'rb').read())

    for d in c.Win32_DiskDrive():
        if 'USB' not in d.InterfaceType:
            continue
        serial = clean_serial(d.SerialNumber)
        if not serial:
            continue

        try:
            partitions = d.associators("Win32_DiskDriveToDiskPartition")
            for part in partitions:
                logicals = part.associators("Win32_LogicalDiskToPartition")
                for ld in logicals:
                    license_path = os.path.join(ld.DeviceID, 'license.dat')
                    if os.path.exists(license_path):
                        sig = open(license_path, 'rb').read()
                        try:
                            pub.verify(
                                sig,
                                serial.encode(),
                                padding.PKCS1v15(),
                                hashes.SHA256()
                            )
                            return True
                        except Exception:
                            pass
        except Exception:
            continue

    return False


if __name__ == '__main__':
    if not check_usb():
        print('验证失败：未检测到授权U盘，技能无法加载')
        sys.exit(1)
    # 验证通过，静默退出（returncode 0）
