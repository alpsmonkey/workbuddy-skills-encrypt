# read_serial.py — 读取当前插入U盘的硬件序列号（含异常字符清洗）
"""用法: python scripts/read_serial.py"""
import wmi
import re
import sys

# 修复 Windows 终端 GBK 编码问题
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def clean_serial(raw):
    """清洗序列号：去除不可打印字符，只保留字母数字和常见符号"""
    if not raw:
        return ''
    cleaned = re.sub(r'[^\x20-\x7e]', '', raw)
    return cleaned.strip()

if __name__ == '__main__':
    c = wmi.WMI()
    found = False
    for d in c.Win32_DiskDrive():
        if 'USB' in d.InterfaceType:
            raw_serial = d.SerialNumber
            serial = clean_serial(raw_serial)
            print(f'原始序列号（含不可见字符）: {repr(raw_serial)}')
            print(f'清洗后序列号: {serial}')
            print(f'设备标识: {d.DeviceID}')
            print(f'厂商: {d.Manufacturer}')
            if not serial:
                print('⚠️ 警告：该U盘序列号清洗后为空，无法用于加密狗方案，请换一个U盘！')
            else:
                print('✅ 序列号正常，可以继续')
                found = True
            break
    if not found:
        print('未检测到任何USB设备，请确认U盘已插入')
