#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
אימות קובץ הנתונים של אתר הגיבוי כפי שהוא ב-main: קורא data.enc.txt מתיקייה (clone טרי),
משווה את ה-sha256 שלו לערך צפוי, מפענח עם הסיסמה וסופר תיקים, מועדים ומסמכים.

שימוש:
  python3 verify_site_data.py --dir <תיקיית ה-clone> --password <סיסמה>
                              [--expect-sha <sha256 מתוך data.enc.sha256 המקומי>] [--min-cases 300]
מדפיס שורת OK עם המספרים, או FAIL עם הסיבה, וקוד יציאה 1 בכישלון.
"""
import argparse, base64, gzip, hashlib, json, os, sys


def decrypt(enc_text: str, password: str) -> dict:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    d = json.loads(enc_text)
    key = PBKDF2HMAC(hashes.SHA256(), 32, base64.b64decode(d['salt']), int(d['iters'])).derive(password.encode('utf-8'))
    pt = AESGCM(key).decrypt(base64.b64decode(d['iv']), base64.b64decode(d['ct']), None)
    if d.get('gzip'):
        pt = gzip.decompress(pt)
    return json.loads(pt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--password', required=True)
    ap.add_argument('--expect-sha')
    ap.add_argument('--min-cases', type=int, default=300)
    a = ap.parse_args()
    try:
        p = os.path.join(a.dir, 'data.enc.txt')
        if not os.path.isfile(p):
            raise RuntimeError('data.enc.txt לא נמצא')
        text = open(p, encoding='utf-8').read().strip()
        sha = hashlib.sha256(text.encode('utf-8')).hexdigest()
        if a.expect_sha and sha != a.expect_sha.strip():
            raise RuntimeError(f'sha256 במאגר ({sha[:12]}) שונה מהצפוי ({a.expect_sha.strip()[:12]}): הפרסום ל-main עדיין לא בוצע או נכשל')
        j = decrypt(text, a.password)
        cases, dls, docs = len(j.get('cases', [])), len(j.get('deadlines', [])), len(j.get('docs', []))
        if cases < a.min_cases:
            raise RuntimeError(f'רק {cases} תיקים בקובץ, פחות מ-{a.min_cases}')
        print(f'OK: sha256 {sha[:12]}, exportedAt {j.get("exportedAt")}, {cases} תיקים, {dls} מועדים, {docs} מסמכים')
    except Exception as e:
        print(f'FAIL: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
