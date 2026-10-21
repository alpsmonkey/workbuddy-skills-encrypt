# change_password.py — 改密：用新密码重新加密技能
"""用法: echo "<旧密码>\n<新密码>" | python scripts/change_password.py <技能目录路径> <U盘盘符>
示例: echo "old-pwd\nnew-pwd" | python scripts/change_password.py ~/.workbuddy/skills/my-skill E

需要提供：
- 旧密码（用于解密）
- 新密码（用于重新加密）
- U盘盘符（密钥派生需要 encryption.key）

流程：
1. 用旧密码解密 SKILL.body.enc → 内存
2. 用新密码重新加密 → SKILL.body.enc
3. 往返校验确保新密码可用
"""
import os
import sys
import hashlib
from pathlib import Path
from io import BytesIO

# 修复 Windows 终端 GBK 编码问题
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('用法: echo "<旧密码>\\n<新密码>" | python change_password.py <技能目录路径> <U盘盘符>')
        print('示例: echo "old-pwd\\nnew-pwd" | python change_password.py ~/.workbuddy/skills/my-skill E')
        sys.exit(1)
    
    skill_dir = Path(sys.argv[1]).resolve()
    drive = sys.argv[2].strip(':').upper()
    
    if not skill_dir.exists():
        print(f'错误：技能目录不存在: {skill_dir}')
        sys.exit(1)
    
    body_enc = skill_dir / 'SKILL.body.enc'
    if not body_enc.exists():
        print(f'该技能未加密（{body_enc} 不存在）')
        sys.exit(0)
    
    # 读取密码（stdin 优先，否则交互）
    if not sys.stdin.isatty():
        lines = sys.stdin.read().strip().split('\n')
        if len(lines) < 2:
            print('错误：需要提供旧密码和新密码（用换行分隔）')
            sys.exit(1)
        old_password = lines[0]
        new_password = lines[1]
    else:
        old_password = input('请输入旧密码：')
        new_password = input('请输入新密码：')
        confirm = input('再输一遍新密码确认：')
        if new_password != confirm:
            print('两次新密码不一致，退出')
            sys.exit(1)
    
    if not old_password or not new_password:
        print('错误：密码为空')
        sys.exit(1)
    
    # 导入解密逻辑
    sys.path.insert(0, str(skill_dir / 'scripts'))
    try:
        from decrypt_body import derive_key_from_usb
        import pyAesCrypt
        
        BUFFER = 64 * 1024
        
        print(f'技能目录: {skill_dir}')
        print(f'U盘盘符: {drive}:')
        print()
        
        # 步骤1：用旧密码解密到内存
        print('正在用旧密码解密...')
        old_key = derive_key_from_usb(old_password, drive)
        old_enc_pwd = old_key.hex()
        
        enc_size = body_enc.stat().st_size
        buf = BytesIO()
        
        with open(body_enc, 'rb') as fIn:
            pyAesCrypt.decryptStream(fIn, buf, old_enc_pwd, BUFFER, enc_size)
        
        buf.seek(0)
        plaintext = buf.read()
        original_hash = hashlib.sha256(plaintext).hexdigest()
        print(f'✓ 解密成功 (SHA256: {original_hash[:16]}...)')
        
        # 步骤2：用新密码重新加密
        print('正在用新密码重新加密...')
        new_key = derive_key_from_usb(new_password, drive)
        new_enc_pwd = new_key.hex()
        
        # 备份旧的加密文件
        backup_enc = body_enc.with_suffix('.enc.old')
        body_enc.rename(backup_enc)
        
        try:
            # 加密
            buf.seek(0)
            with open(body_enc, 'wb') as fOut:
                pyAesCrypt.encryptStream(buf, fOut, new_enc_pwd, BUFFER)
            print(f'✓ 加密完成')
            
            # 步骤3：往返校验
            print('正在进行往返校验...')
            enc_size_new = body_enc.stat().st_size
            buf2 = BytesIO()
            
            with open(body_enc, 'rb') as fIn:
                pyAesCrypt.decryptStream(fIn, buf2, new_enc_pwd, BUFFER, enc_size_new)
            
            buf2.seek(0)
            decrypted_hash = hashlib.sha256(buf2.read()).hexdigest()
            
            if decrypted_hash != original_hash:
                print(f'❌ 往返校验失败！')
                print(f'   原文件: {original_hash[:16]}...')
                print(f'   解密后: {decrypted_hash[:16]}...')
                print(f'   正在恢复旧的加密文件...')
                body_enc.unlink()
                backup_enc.rename(body_enc)
                sys.exit(1)
            
            print(f'✓ 往返校验通过（SHA256 一致）')
            
            # 删除备份
            backup_enc.unlink()
            
            print('\n✅ 改密完成！')
            print('下次解密时请使用新密码')
            
        except Exception as e:
            print(f'❌ 重新加密失败：{e}')
            print('正在恢复旧的加密文件...')
            if body_enc.exists():
                body_enc.unlink()
            backup_enc.rename(body_enc)
            sys.exit(1)
        
    except ValueError as e:
        print(f'❌ 解密失败：旧密码错误或文件损坏')
        sys.exit(1)
    except Exception as e:
        print(f'❌ 错误：{e}')
        sys.exit(1)
