<p align="center">
  <b style="font-size: 28px">🔐 WorkBuddy Skills Encrypt</b>
</p>

<p align="center">
  <b>USB Dongle Encryption System — Protect Your WorkBuddy Skills from Unauthorized Copying</b>
</p>

<p align="center">
  <a href="README.md">简体中文</a> · <a href="README_EN.md">English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v1.0.0-orange" alt="version" />
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="license" />
  <img src="https://img.shields.io/badge/encryption-RSA--2048%20%2B%20AES--256-green" alt="encryption" />
</p>

<p align="center">
  <b>Lock down your optimized skills. Without your USB dongle, nobody can use them.</b>
</p>

## Architecture

```
┌─ Local skill directory ──────────────────────────────────────┐
│  SKILL.md              ← Bootloader shell (plaintext, always readable)
│  SKILL.body.enc        ← Encrypted skill body (AES-256 ciphertext)
│  SKILL.md.bak          ← Local backup of original
│  scripts/
│  ├── verify.py         ← USB validation (WMI + RSA signature check)
│  ├── decrypt_body.py   ← Verify → Decrypt → Output to stdout
│  └── public_key.pem    ← Public key (verification only, safe to share)
└──────────────────────────────────────────────────────────────┘

┌─ Master USB Dongle ─────────────────────────────────────────┐
│  private_key.pem       ← Signing authority (keep secure!)
│  license.dat           ← RSA signature (256 bytes, bound to this USB)
└──────────────────────────────────────────────────────────────┘

┌─ Backup USB Dongle ─────────────────────────────────────────┐
│  license.dat           ← Authorization only (cannot sign new licenses)
└──────────────────────────────────────────────────────────────┘

┌─ Off-site Backup (auto-created) ────────────────────────────┐
│  ~/skill-backup/<date>/<skill-name>/SKILL.md  ← Plaintext backup
└──────────────────────────────────────────────────────────────┘
```

## How It Works

1. **Generate keys** → RSA-2048 key pair, private key written directly to USB
2. **Sign license** → Private key signs USB serial number → `license.dat`
3. **Encrypt skills** → Original `SKILL.md` split into bootloader shell + `SKILL.body.enc` (AES-256)
4. **Use skills** → AI reads bootloader → runs `verify.py` (USB + RSA check) → asks for password → `decrypt_body.py` decrypts body → executes

The bootloader is always plaintext, so WorkBuddy's AI can always read the decryption protocol. The actual skill content is AES-256 encrypted and stored separately.

## Quick Start

### Prerequisites

```bash
pip install pyAesCrypt cryptography wmi
```

### One-time Setup

```bash
# 1. Read USB serial number
python scripts/read_serial.py

# 2. Generate RSA keys (private key → USB drive)
python scripts/gen_keys.py E

# 3. Sign license.dat to USB
python scripts/sign_license.py E AA0B1C2D3E4F
```

### Encrypt a Skill

```bash
# Single skill
python scripts/encrypt_skill.py

# Batch encrypt all skills
python scripts/batch_encrypt.py
```

### Use Encrypted Skills

Just use WorkBuddy normally. When AI loads an encrypted skill, it will:
1. Read the bootloader shell
2. Auto-run `verify.py` to check USB
3. Ask for password if authorized
4. Decrypt body and execute

## Security

| Layer | Mechanism | Purpose |
|---|---|---|
| Hardware binding | USB serial + RSA-2048 signature | Only authorized USB drives pass verification |
| Content encryption | AES-256 (pyAesCrypt) | Skill body is ciphertext without password |
| Bootloader isolation | Shell (plaintext) / Body (encrypted) | AI can always read the protocol, never the content |
| Private key custody | USB-only storage | Signing authority lives on physical dongle |
| Off-site backup | Auto-copy before encryption | Disaster recovery independent of skill directory |
| Multi-dongle | sign_multi.py | Redundancy — one USB lost doesn't lock you out |

## File Structure

```
workbuddy-skills-encrypt/
├── SKILL.md              # WorkBuddy skill definition (can encrypt itself)
└── scripts/
    ├── read_serial.py    # Read USB serial (with abnormal char cleaning)
    ├── gen_keys.py       # Generate RSA-2048 key pair (private → USB)
    ├── sign_license.py   # Sign license.dat to USB (reads private key from USB)
    ├── sign_multi.py     # Multi-USB redundancy signing
    ├── verify.py         # USB RSA verification (WMI association query)
    ├── encrypt_skill.py  # Encrypt single skill (shell + body separation + off-site backup)
    ├── decrypt_body.py   # Verify + decrypt → stdout
    ├── batch_encrypt.py  # Batch encrypt all skills (with off-site backup)
    └── public_key.pem    # Public key for verification
```

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=alpsmonkey/workbuddy-skills-encrypt&type=Date)](https://star-history.com/#alpsmonkey/workbuddy-skills-encrypt&Date)

## License

This project is provided for educational and personal use. Use at your own risk. The private key is your responsibility — if you lose both the USB dongle and all backups, encrypted skills cannot be recovered.
