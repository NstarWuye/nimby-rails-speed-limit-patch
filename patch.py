"""Version-locked, reversible NIMBY Rails track speed loader patch."""
import argparse
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import sys

TARGET = None
BACKUP = None
PROFILES = [
    ('1.19 beta', '2668b2580d890c0c2b6d0b7befb8069891c15f39ea12917ac8fa26bd06a14eb9',
     0xAAD1A8, 0x4034DB, bytes.fromhex('F2 0F 10 35 C5 9C 6A 00')),
    ('1.20 beta', '244d41635e9b0f4126dbed6a943824c5b4576171f796d4dafe5343762d590e17',
     0xAE5F90, 0x40B8CB, bytes.fromhex('F2 0F 10 35 BD A6 6D 00')),
]
ORIGINAL_SHA = None
BUILD = None

def sha(data):
    return hashlib.sha256(data).hexdigest()

def offset(data, rva):
    if len(data) < 64:
        raise ValueError('Truncated PE executable')
    pe = struct.unpack_from('<I', data, 60)[0]
    if data[:2] != b'MZ' or data[pe:pe+4] != b'PE\0\0':
        raise ValueError('Not a PE executable')
    opt = pe + 24
    table = opt + struct.unpack_from('<H', data, pe+20)[0]
    for i in range(struct.unpack_from('<H', data, pe+6)[0]):
        _, va, size, raw = struct.unpack_from('<IIII', data, table+40*i+8)
        if va <= rva < va+size:
            return raw+rva-va
    raise ValueError('RVA outside file sections')

def variants(data):
    global ORIGINAL_SHA, BUILD
    for build, expected_sha, limit_rva, loader_rva, signature in PROFILES:
        try:
            loc = offset(data, limit_rva)
            code = offset(data, loader_rva)
        except (ValueError, struct.error, IndexError):
            continue
        if data[code:code+len(signature)] != signature:
            continue
        original = bytearray(data)
        original[loc:loc+8] = struct.pack('<d', 600.0)
        if sha(original) != expected_sha:
            continue
        patched = bytearray(original)
        patched[loc:loc+8] = struct.pack('<d', 1200.0)
        if bytes(data) not in (bytes(original), bytes(patched)):
            continue
        ORIGINAL_SHA, BUILD = expected_sha, build
        return bytes(original), bytes(patched), loc
    raise ValueError('Unsupported or modified game build; refusing to patch')


def ensure_closed():
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
        "if (Get-Process -Name NimbyRails -ErrorAction SilentlyContinue) { exit 7 }"],
        capture_output=True)
    if result.returncode:
        raise ValueError('Close NIMBY Rails before applying or restoring')

def replace(data):
    temp = TARGET.with_name('NimbyRails.exe.speedpatch.tmp')
    with temp.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    try:
        if temp.read_bytes() != data:
            raise ValueError('Temporary file verification failed')
        os.replace(temp, TARGET)
    finally:
        if temp.exists():
            temp.unlink()
    if TARGET.read_bytes() != data:
        raise ValueError('Final verification failed; original backup is retained')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['apply', 'restore', 'status', 'selftest'])
    parser.add_argument('--game-dir', type=Path, default=Path.cwd(), help='Directory containing NimbyRails.exe (default: current directory)')
    args = parser.parse_args()
    global TARGET, BACKUP
    TARGET = args.game_dir.resolve() / 'NimbyRails.exe'
    current = TARGET.read_bytes()
    original, patched, loc = variants(current)
    BACKUP = TARGET.with_name('NimbyRails.exe.speed-limit-' + ORIGINAL_SHA[:12] + '.bak')
    legacy = TARGET.with_name('NimbyRails.exe.speed-limit-original.bak')
    if not BACKUP.exists() and legacy.exists() and sha(legacy.read_bytes()) == ORIGINAL_SHA:
        BACKUP = legacy
    print('Recognized build: ' + BUILD)
    if args.action == 'selftest':
        assert len(original) == len(patched)
        assert original[:loc] == patched[:loc] and original[loc+8:] == patched[loc+8:]
        assert struct.unpack_from('<d', patched, loc)[0] == 1200.0
        assert variants(patched)[0] == original
        assert variants(original)[1] == patched
        bad = bytearray(original); bad[loc-1] ^= 1
        try:
            variants(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('Modified version accepted')
        print('PASS: precise patch, reversible conversion, incompatible-version rejection')
    elif args.action == 'status':
        print('Track loader cap: %d km/h' % struct.unpack_from('<d', current, loc)[0])
        print('SHA256: ' + sha(current))
        print('Original backup verified: ' + str(BACKUP.exists() and sha(BACKUP.read_bytes()) == ORIGINAL_SHA))
    else:
        ensure_closed()
        if BACKUP.exists():
            if sha(BACKUP.read_bytes()) != ORIGINAL_SHA:
                raise ValueError('Existing backup is invalid; refusing to overwrite')
        elif args.action == 'apply':
            with BACKUP.open('xb') as f:
                f.write(original)
            if sha(BACKUP.read_bytes()) != ORIGINAL_SHA:
                raise ValueError('Backup verification failed')
        else:
            raise ValueError('Original backup missing; refusing to restore')
        desired = patched if args.action == 'apply' else original
        if current != desired:
            replace(desired)
        print('SUCCESS: track loader cap = %d km/h' % (1200 if args.action == 'apply' else 600))
        print('SHA256: ' + sha(desired))

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(1)
