# unseal_skill.py — 解封加密技能，恢复原始 SKILL.md
"""用法: python scripts/unseal_skill.py <技能目录路径>
示例: python scripts/unseal_skill.py ~/.workbuddy/skills/my-skill

解封优先级：
1. 技能目录下的 SKILL.md.bak（如果存在）
2. 异地备份目录中最新的备份
3. 如果都不存在，需要手动提供解密密码和U盘来恢复

解封后会：
- 恢复原始 SKILL.md
- 删除 SKILL.body.enc
- 保留 scripts/ 目录（验签脚本和公钥可能还有用）
"""
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# 异地备份目录（与 encrypt_skill.py 保持一致）
BACKUP_DIR = os.path.expanduser('~/skill-backup')


def find_latest_backup(skill_name):
    """在异地备份目录中查找最新的备份"""
    if not os.path.exists(BACKUP_DIR):
        return None
    
    # 按日期倒序扫描
    backups = []
    for date_dir in sorted(os.listdir(BACKUP_DIR), reverse=True):
        date_path = os.path.join(BACKUP_DIR, date_dir)
        if not os.path.isdir(date_path):
            continue
        
        skill_backup = os.path.join(date_path, skill_name, 'SKILL.md')
        if os.path.exists(skill_backup):
            backups.append((date_dir, skill_backup))
    
    return backups[0] if backups else None


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python unseal_skill.py <技能目录路径>')
        print('示例: python unseal_skill.py ~/.workbuddy/skills/my-skill')
        sys.exit(1)
    
    skill_dir = Path(sys.argv[1]).resolve()
    if not skill_dir.exists():
        print(f'错误：技能目录不存在: {skill_dir}')
        sys.exit(1)
    
    skill_md = skill_dir / 'SKILL.md'
    body_enc = skill_dir / 'SKILL.body.enc'
    bak_path = skill_dir / 'SKILL.md.bak'
    
    if not body_enc.exists():
        print(f'该技能未加密（{body_enc} 不存在）')
        sys.exit(0)
    
    print(f'技能目录: {skill_dir}')
    print(f'技能名称: {skill_dir.name}')
    print()
    
    # 优先级1：本地 .bak
    if bak_path.exists():
        print(f'✓ 找到本地备份: {bak_path}')
        confirm = input('使用本地备份恢复？(y/n): ').strip().lower()
        if confirm == 'y':
            shutil.copy2(bak_path, skill_md)
            print(f'已恢复原始 SKILL.md')
            
            body_enc.unlink()
            print(f'已删除 {body_enc.name}')
            
            bak_path.unlink()
            print(f'已删除 {bak_path.name}')
            
            print('\n✅ 解封完成！')
            sys.exit(0)
    
    # 优先级2：异地备份
    backup_info = find_latest_backup(skill_dir.name)
    if backup_info:
        date_str, backup_path = backup_info
        print(f'✓ 找到异地备份: {backup_path}')
        print(f'  备份日期: {date_str}')
        confirm = input('使用异地备份恢复？(y/n): ').strip().lower()
        if confirm == 'y':
            shutil.copy2(backup_path, skill_md)
            print(f'已恢复原始 SKILL.md')
            
            body_enc.unlink()
            print(f'已删除 {body_enc.name}')
            
            print('\n✅ 解封完成！')
            sys.exit(0)
    
    # 优先级3：解密恢复
    print('未找到备份文件，需要通过解密恢复')
    print()
    password = input('请输入解密密码：')
    drive = input('请输入U盘盘符（如 E）：').strip(':').upper()
    
    if not password or not drive:
        print('错误：密码或盘符为空')
        sys.exit(1)
    
    # 导入解密逻辑
    sys.path.insert(0, str(skill_dir / 'scripts'))
    try:
        from decrypt_body import derive_key_from_usb
        import pyAesCrypt
        from io import BytesIO
        
        BUFFER = 64 * 1024
        
        # 派生密钥
        derived_key = derive_key_from_usb(password, drive)
        encryption_password = derived_key.hex()
        
        # 解密到内存
        enc_size = body_enc.stat().st_size
        buf = BytesIO()
        
        with open(body_enc, 'rb') as fIn:
            pyAesCrypt.decryptStream(fIn, buf, encryption_password, BUFFER, enc_size)
        
        buf.seek(0)
        skill_md.write_bytes(buf.read())
        print(f'已恢复原始 SKILL.md')
        
        body_enc.unlink()
        print(f'已删除 {body_enc.name}')
        
        print('\n✅ 解封完成！')
        
    except Exception as e:
        print(f'❌ 解密失败：{e}')
        print('可能的原因：密码错误、U盘不匹配或文件损坏')
        sys.exit(1)
