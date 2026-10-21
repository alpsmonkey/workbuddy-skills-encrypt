# sign_multi.py — 用主U盘上的私钥，给多个U盘分别签名（冗余方案）
"""用法: python scripts/sign_multi.py <主U盘盘符> <备用U盘盘符1> [<备用U盘盘符2> ...]
示例: python scripts/sign_multi.py E F G

自动读取每个U盘的序列号并签名，无需手动编辑源码"""
import os
import sys
import re
import wmi
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def clean_serial(raw):
    """清洗序列号：先删除不可打印字符，再 strip 空白（与 verify.py 保持一致）"""
    if not raw:
        return ''
    cleaned = re.sub(r'[^\x20-\x7e]', '', raw)
    return cleaned.strip()


def read_usb_serial(drive):
    """读取指定盘符U盘的序列号"""
    c = wmi.WMI()
    for d in c.Win32_DiskDrive():
        if 'USB' not in d.InterfaceType:
            continue
        try:
            for part in d.associators("Win32_DiskDriveToDiskPartition"):
                for ld in part.associators("Win32_LogicalDiskToPartition"):
                    if ld.DeviceID.strip(':').upper() == drive.upper():
                        serial = clean_serial(d.SerialNumber)
                        return serial
        except Exception:
            continue
    return None


def find_private_key_on_usb(drive):
    """在指定U盘上查找 private_key.pem"""
    path = os.path.join(f'{drive}:/', 'private_key.pem')
    if os.path.exists(path):
        return path
    return None


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python sign_multi.py <主U盘盘符> <备用U盘盘符1> [<备用U盘盘符2> ...]')
        print('示例: python sign_multi.py E F G')
        print()
        print('主U盘：持有 private_key.pem 的那个')
        print('备用U盘：需要签发 license.dat 的其他U盘')
        sys.exit(1)
    
    drives = [arg.strip(':').upper() for arg in sys.argv[1:]]
    
    if len(drives) < 1:
        print('错误：至少需要指定主U盘盘符')
        sys.exit(1)
    
    master_drive = drives[0]
    
    # 读取主U盘序列号
    print(f'正在读取主U盘 {master_drive}: 的序列号...')
    master_serial = read_usb_serial(master_drive)
    if not master_serial:
        print(f'错误：无法读取主U盘 {master_drive}: 的序列号')
        sys.exit(1)
    print(f'主U盘序列号: {master_serial}')
    
    # 在主U盘上找到私钥
    priv_path = find_private_key_on_usb(master_drive)
    if not priv_path:
        print(f'错误：主U盘 {master_drive}: 上没有找到 private_key.pem')
        print('请先运行 gen_keys.py 把私钥写入主U盘')
        sys.exit(1)
    
    print(f'找到私钥: {priv_path}')
    print()
    
    # 加载私钥
    priv = serialization.load_pem_private_key(
        open(priv_path, 'rb').read(), None
    )
    
    # 给每个U盘签名
    dongles = []
    for i, drive in enumerate(drives):
        serial = read_usb_serial(drive)
        if not serial:
            print(f'⚠️ 警告：无法读取U盘 {drive}: 的序列号，跳过')
            continue
        
        dongles.append({'drive': drive, 'serial': serial, 'is_master': i == 0})
    
    if not dongles:
        print('错误：没有可签名的U盘')
        sys.exit(1)
    
    print(f'准备签名 {len(dongles)} 个U盘：')
    for d in dongles:
        label = '主U盘（私钥+license）' if d['is_master'] else '备用U盘（仅license）'
        print(f'  {d["drive"]}: {d["serial"]} - {label}')
    print()
    
    confirm = input('确认签名？(y/n): ').strip().lower()
    if confirm != 'y':
        print('已取消')
        sys.exit(0)
    
    for d in dongles:
        drive = d['drive']
        serial = d['serial']
        
        # 签名
        sig = priv.sign(serial.encode(), padding.PKCS1v15(), hashes.SHA256())
        license_path = os.path.join(f'{drive}:/', 'license.dat')
        open(license_path, 'wb').write(sig)
        
        label = '（主U盘）' if d['is_master'] else '（备用U盘）'
        print(f'✓ {drive}: license.dat 已写入 {label}')
    
    print()
    print('全部签完！')
    print(f'主U盘 {master_drive}: 持有 private_key.pem + license.dat（签发权 + 授权凭证）')
    print('备用U盘只有 license.dat（仅授权凭证，不能签新license）')
