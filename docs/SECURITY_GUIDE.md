# API Secrets Security Guide

## Overview

The AI Video Factory now includes a secure secrets management system that encrypts API keys and sensitive information in your `.env` file. This prevents plaintext secrets from being stored in your configuration files.

## How It Works

1. **Master Key**: A master encryption key is automatically generated on first use
2. **Encryption**: API secrets are encrypted using AES-128 (Fernet) before storing in `.env`
3. **Decryption**: Secrets are automatically decrypted when the application loads
4. **Fallback**: The system can handle both encrypted and plaintext values

## Quick Start

### 1. Install Dependencies

```bash
pip install cryptography>=41.0.0
```

### 2. Encrypt Your Current Secrets

```bash
# Encrypt API keys in .env file
python core/secrets.py encrypt
```

This will:
- Generate a master encryption key (saved to `.secrets_master_key`)
- Encrypt all API keys in your `.env` file
- Mark encrypted values with the `encv2:` prefix

### 3. Use Your Application Normally

The application will automatically decrypt secrets when loading. No code changes needed!

## CLI Commands

### Encrypt Secrets

```bash
# Encrypt .env file
python core/secrets.py encrypt

# Encrypt specific file
python core/secrets.py encrypt path/to/.env.production
```

### Decrypt Secrets

```bash
# Decrypt .env file
python core/secrets.py decrypt

# Decrypt specific file
python core/secrets.py decrypt path/to/.env.production
```

### Master Key Management

```bash
# Show current master key
python core/secrets.py show-key

# Rotate to new master key (decrypts with old key, re-encrypts with new)
python core/secrets.py rotate-key
```

## Environment Variables

### SECRETS_MASTER_KEY

Set the master key via environment variable to share across systems:

```bash
# Linux/Mac
export SECRETS_MASTER_KEY="your-base64-encoded-key"

# Windows
set SECRETS_MASTER_KEY=your-base64-encoded-key
```

### Priority Order

The master key is obtained from (in order):
1. `SECRETS_MASTER_KEY` environment variable
2. `.secrets_master_key` file in project root
3. Auto-generated key (saved to `.secrets_master_key`)

## Encrypted Format

Encrypted values in `.env` use this format:

```bash
GEMINI_API_KEY=encv2:gAAAAABl...
OPENAI_API_KEY=encv2:gAAAAABm...
```

The `encv2:` prefix indicates encrypted values (version 2).

## Supported Secrets

The following fields are automatically encrypted:

- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `ZHIPU_API_KEY`
- `QWEN_API_KEY`
- `KIMI_API_KEY`
- `ELEVENLABS_API_KEY`
- `SECRETS_MASTER_KEY`

## Security Best Practices

### 1. Backup Your Master Key

**CRITICAL**: Without the master key, encrypted secrets **cannot** be decrypted!

```bash
# Show and backup your master key
python core/secrets.py show-key

# Store it securely in a password manager or secrets manager
```

### 2. Don't Commit Secrets to Git

Add these lines to your `.gitignore`:

```
.env
.secrets_master_key
```

### 3. Use Different Keys for Different Environments

Generate different master keys for development, staging, and production:

```bash
# Development
export SECRETS_MASTER_KEY=$(python -c "from core.secrets import get_master_key; print(__import__('base64').urlsafe_b64encode(get_master_key()).decode())")

# Production (use separate key)
export SECRETS_MASTER_KEY="production-key-here"
```

### 4. Rotate Keys Periodically

```bash
# Rotate master key every 90 days
python core/secrets.py rotate-key
```

### 5. File Permissions

On Unix-like systems, the master key file is set to restrictive permissions (0600).

```bash
# Verify permissions
ls -la .secrets_master_key

# Should show: -rw------- (owner read/write only)
```

## Migration from Plain Text

### Step 1: Backup Your Current `.env`

```bash
cp .env .env.backup
```

### Step 2: Encrypt Secrets

```bash
python core/secrets.py encrypt
```

### Step 3: Test Your Application

```bash
# Test that everything still works
python core/main.py --idea "test"

# Or start web UI
python web_ui/start.py
```

### Step 4: Remove Backup

Once verified working:

```bash
# Remove plaintext backup
rm .env.backup
```

## Disaster Recovery

### If You Lose Your Master Key

**IMPORTANT**: Without the master key, encrypted secrets are **permanently lost**.

If you lose the master key but have a backup of your original `.env`:

1. Restore your `.env.backup` (plaintext version)
2. Generate a new master key: `rm .secrets_master_key && python -c "from core.secrets import get_master_key; get_master_key()"`
3. Re-encrypt: `python core/secrets.py encrypt`

### Decrypting for Migration

If you need to migrate secrets to another system:

```bash
# Option 1: Share master key via environment variable
python core/secrets.py show-key
# Set SECRETS_MASTER_KEY on new system

# Option 2: Copy master key file
cp .secrets_master_key /path/to/new/system/.secrets_master_key

# Option 3: Decrypt, copy, re-encrypt
python core/secrets.py decrypt
# Copy .env to new system
# On new system: python core/secrets.py encrypt
```

## Troubleshooting

### "Failed to decrypt" Errors

If you see decryption errors:

1. Check master key is accessible:
   ```bash
   python core/secrets.py show-key
   ```

2. Verify `.env` contains encrypted values (look for `encv2:` prefix)

3. Check master key hasn't changed:
   ```bash
   # Compare with backup
   diff .secrets_master_key .secrets_master_key.backup
   ```

### Mixed Encrypted/Unencrypted Values

The system handles mixed files automatically. Unencrypted values are passed through unchanged.

To encrypt all values:
```bash
python core/secrets.py encrypt
```

### Application Won't Start

If the application fails to load:

1. Temporarily decrypt to verify values:
   ```bash
   python core/secrets.py decrypt
   ```

2. Check API keys are valid

3. Re-encrypt if needed:
   ```bash
   python core/secrets.py encrypt
   ```

## API Integration

### For Developers

The secrets management is integrated into `config.py`. When loading API keys:

```python
# Old way (still works for backward compatibility)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# New way (automatic decryption)
GEMINI_API_KEY = decrypt_env_var("GEMINI_API_KEY", "")
```

### Manual Encryption/Decryption

```python
from core.secrets import encrypt_value, decrypt_value

# Encrypt a value
encrypted = encrypt_value("my-secret-key")
print(encrypted)  # encv2:gAAAAABl...

# Decrypt a value
decrypted = decrypt_value(encrypted)
print(decrypted)  # my-secret-key
```

## Technical Details

### Encryption Method

- **Algorithm**: Fernet (AES-128-CBC + HMAC)
- **Key Derivation**: PBKDF2-HMAC-SHA256
- **Encoding**: URL-safe base64
- **Version**: v2 (encv2: prefix)

### Security Properties

- **Confidentiality**: Secrets encrypted with AES
- **Integrity**: HMAC ensures data hasn't been tampered with
- **Key Management**: Master key stored securely or via environment variable
- **Fallback**: System can handle plaintext values for compatibility

### File Structure

```
project/
├── .env                      # Your environment variables (encrypted)
├── .secrets_master_key       # Master encryption key (auto-generated)
├── .gitignore               # Should exclude both files above
├── core/
│   └── secrets.py           # Secrets management module
└── config.py                # Updated to use decrypt_env_var()
```

## Summary

✅ **Automatic** - No code changes needed in your application  
✅ **Secure** - AES-128 encryption with integrity protection  
✅ **Flexible** - Handles mixed encrypted/unencrypted files  
✅ **Safe** - Master key never stored with encrypted secrets  
✅ **Compatible** - Works with existing `.env` files  

**Remember**: Always backup your master key in a secure location!