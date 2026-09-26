"""
Secure Secrets Management for AI Video Factory

This module provides encryption and decryption functions for API secrets
stored in environment variables.
"""
import os
import base64
import hashlib
from cryptography.fernet import Fernet
from pathlib import Path
import json

# Encryption prefix to identify encrypted values
ENCRYPTION_PREFIX = "enc:"
ENCRYPTION_PREFIX_V2 = "encv2:"

# Master key environment variable name
MASTER_KEY_ENV = "SECRETS_MASTER_KEY"
MASTER_KEY_FILE = ".secrets_master_key"


def get_master_key():
    """
    Get or create the master encryption key.

    The master key is obtained from (in order of priority):
    1. Environment variable SECRETS_MASTER_KEY
    2. .secrets_master_key file in project root
    3. Create new key and save to file

    Returns:
        bytes: 32-byte encryption key
    """
    # 1. Check environment variable
    master_key_str = os.getenv(MASTER_KEY_ENV)
    if master_key_str:
        try:
            # Environment variable contains base64-encoded key as string
            return master_key_str.encode('utf-8')
        except Exception:
            pass

    # 2. Check for master key file
    project_root = Path(__file__).parent.parent
    key_file = project_root / MASTER_KEY_FILE

    if key_file.exists():
        try:
            with open(key_file, 'r') as f:
                stored_key = f.read().strip()
                if stored_key:
                    # File contains base64-encoded key as string
                    return stored_key.encode('utf-8')
        except Exception:
            pass

    # 3. Generate new master key
    master_key = Fernet.generate_key()

    # Save to file (restrictive permissions)
    try:
        # Decode bytes to string for file storage
        key_file.write_text(master_key.decode('utf-8'))
        # Try to set restrictive permissions (Unix-like systems)
        try:
            os.chmod(key_file, 0o600)
        except (AttributeError, OSError):
            pass  # Windows or permission change failed

        print(f"Generated new master key and saved to {key_file}")
        print("IMPORTANT: Back up this key securely. Without it, encrypted secrets cannot be decrypted!")
        print("You can also set the SECRETS_MASTER_KEY environment variable.")
    except Exception as e:
        print(f"Warning: Could not save master key to file: {e}")
        print("Set SECRETS_MASTER_KEY environment variable to persist the key.")

    return master_key


def get_fernet():
    """Get Fernet cipher instance with master key."""
    master_key = get_master_key()
    return Fernet(master_key)


def encrypt_value(value: str) -> str:
    """
    Encrypt a string value.

    Args:
        value: Plain text string to encrypt

    Returns:
        str: Encrypted value with prefix (format: encv2:<encrypted_string>)
    """
    if not value:
        return value

    try:
        fernet = get_fernet()
        encrypted_bytes = fernet.encrypt(value.encode('utf-8'))
        encrypted_str = base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
        return f"{ENCRYPTION_PREFIX_V2}{encrypted_str}"
    except Exception as e:
        raise ValueError(f"Failed to encrypt value: {e}")


def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypt an encrypted string value.

    Args:
        encrypted_value: Encrypted string (with or without prefix)

    Returns:
        str: Decrypted plain text
    """
    if not encrypted_value:
        return encrypted_value

    # Remove prefix if present
    if encrypted_value.startswith(ENCRYPTION_PREFIX_V2):
        encrypted_str = encrypted_value[len(ENCRYPTION_PREFIX_V2):]
    elif encrypted_value.startswith(ENCRYPTION_PREFIX):
        encrypted_str = encrypted_value[len(ENCRYPTION_PREFIX):]
    else:
        # Not encrypted, return as-is
        return encrypted_value

    try:
        fernet = get_fernet()
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_str.encode('utf-8'))
        decrypted_bytes = fernet.decrypt(encrypted_bytes)
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        # If decryption fails, return original value
        # This allows for mixed encrypted/unencrypted .env files
        return encrypted_value


def decrypt_env_var(env_var_name: str, default: str = "") -> str:
    """
    Get environment variable and decrypt if encrypted.

    Args:
        env_var_name: Name of environment variable
        default: Default value if variable not set

    Returns:
        str: Decrypted value or default
    """
    value = os.getenv(env_var_name, default)
    return decrypt_value(value)


def encrypt_env_file(input_file: str = None, output_file: str = None):
    """
    Encrypt API secrets in .env file.

    Args:
        input_file: Input .env file path (default: .env in project root)
        output_file: Output file path (default: overwrites input)
    """
    if input_file is None:
        project_root = Path(__file__).parent.parent
        input_file = project_root / ".env"

    if output_file is None:
        output_file = input_file

    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Fields to encrypt (API keys and secrets)
    sensitive_fields = [
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "ZHIPU_API_KEY",
        "QWEN_API_KEY",
        "KIMI_API_KEY",
        "ELEVENLABS_API_KEY",
        "SECRETS_MASTER_KEY",
    ]

    # Read input file
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Process each line
    encrypted_lines = []
    for line in lines:
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            encrypted_lines.append(line)
            continue

        # Check if this is a sensitive field
        for field in sensitive_fields:
            if stripped.startswith(f"{field}="):
                # Extract the value
                parts = stripped.split('=', 1)
                if len(parts) == 2:
                    key, value = parts
                    value = value.strip().strip('"').strip("'")

                    # Skip if already encrypted or empty
                    if not value or value.startswith(ENCRYPTION_PREFIX_V2) or value.startswith(ENCRYPTION_PREFIX):
                        encrypted_lines.append(line)
                        break

                    # Encrypt the value
                    try:
                        encrypted = encrypt_value(value)
                        # Preserve original quoting style
                        quote = '"' if '"' in line else "'" if "'" in line else ''
                        if quote:
                            new_line = f"{key}={quote}{encrypted}{quote}\n"
                        else:
                            new_line = f"{key}={encrypted}\n"
                        encrypted_lines.append(new_line)
                        print(f"[+] Encrypted {key}")
                    except Exception as e:
                        print(f"[!] Failed to encrypt {key}: {e}")
                        encrypted_lines.append(line)
                break
        else:
            # Not a sensitive field, keep as-is
            encrypted_lines.append(line)

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(encrypted_lines)

    print(f"\nEncrypted secrets saved to: {output_path}")


def decrypt_env_file(input_file: str = None, output_file: str = None):
    """
    Decrypt API secrets in .env file.

    Args:
        input_file: Input .env file path (default: .env in project root)
        output_file: Output file path (default: overwrites input)
    """
    if input_file is None:
        project_root = Path(__file__).parent.parent
        input_file = project_root / ".env"

    if output_file is None:
        output_file = input_file

    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Read input file
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Process each line
    decrypted_lines = []
    for line in lines:
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            decrypted_lines.append(line)
            continue

        # Check if this line contains an encrypted value
        if '=' in stripped:
            parts = stripped.split('=', 1)
            if len(parts) == 2:
                key, value = parts
                value = value.strip().strip('"').strip("'")

                # Try to decrypt
                decrypted = decrypt_value(value)
                if decrypted != value:  # Was encrypted
                    # Preserve original quoting style
                    quote = '"' if '"' in line else "'" if "'" in line else ''
                    if quote:
                        new_line = f"{key}={quote}{decrypted}{quote}\n"
                    else:
                        new_line = f"{key}={decrypted}\n"
                    decrypted_lines.append(new_line)
                    print(f"[+] Decrypted {key}")
                else:
                    decrypted_lines.append(line)
            else:
                decrypted_lines.append(line)
        else:
            decrypted_lines.append(line)

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(decrypted_lines)

    print(f"\nDecrypted secrets saved to: {output_path}")


def show_master_key():
    """Display the current master encryption key."""
    master_key = get_master_key()
    # Master key is already base64-encoded, just decode to string for display
    encoded_key = master_key.decode('utf-8')
    print("Master Encryption Key:")
    print(encoded_key)
    print("\nSet this as SECRETS_MASTER_KEY environment variable to share the key across systems.")


def rotate_master_key():
    """
    Rotate to a new master encryption key.

    WARNING: You must decrypt all secrets with the old key first,
    then re-encrypt with the new key.
    """
    # Decrypt current .env
    temp_file = Path(".env.decrypted.temp")
    decrypt_env_file(output_file=str(temp_file))

    # Generate new master key
    project_root = Path(__file__).parent.parent
    key_file = project_root / MASTER_KEY_FILE

    if key_file.exists():
        key_file.unlink()

    new_key = get_master_key()  # This will create a new key
    print(f"New master key generated: {new_key.decode('utf-8')}")

    # Re-encrypt with new key
    encrypt_env_file(input_file=str(temp_file))
    temp_file.unlink()

    print("Master key rotated successfully.")


# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Secrets Management Utility")
        print("Usage:")
        print("  python core/secrets.py encrypt          - Encrypt .env file")
        print("  python core/secrets.py decrypt          - Decrypt .env file")
        print("  python core/secrets.py show-key          - Show master key")
        print("  python core/secrets.py rotate-key        - Rotate master key")
        print("  python core/secrets.py encrypt <file>     - Encrypt specific file")
        print("  python core/secrets.py decrypt <file>    - Decrypt specific file")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "encrypt":
        if len(sys.argv) > 2:
            encrypt_env_file(input_file=sys.argv[2])
        else:
            encrypt_env_file()

    elif command == "decrypt":
        if len(sys.argv) > 2:
            decrypt_env_file(input_file=sys.argv[2])
        else:
            decrypt_env_file()

    elif command == "show-key":
        show_master_key()

    elif command == "rotate-key":
        rotate_master_key()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)