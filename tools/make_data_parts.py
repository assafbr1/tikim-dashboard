#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
בניית קובץ הנתונים המוצפן של אתר הגיבוי (data.enc.txt) ופיצולו לפרוסות קטנות
(data.enc.part-00.txt, data.enc.part-01.txt, ...) שהריצה הלילית דוחפת לענף build-* פרוסה אחת
בכל קריאה של push_files. הפעולה .github/workflows/publish-build.yml מאחה את הפרוסות ל-data.enc.txt
ב-main רק אם ה-sha256 של החיבור זהה לזה שבקובץ data.enc.sha256.

שימוש:
  python3 make_data_parts.py --payload payload.json --password <סיסמה> --out <תיקיית פלט>
      בונה data.enc.txt מתוך payload.json (gzip ואז AES-256-GCM עם מפתח PBKDF2-SHA256,
      300000 איטרציות, salt של 16 בתים ו-iv של 12 בתים אקראיים) ואז מפצל.
  python3 make_data_parts.py --from-enc data.enc.txt --out <תיקיית פלט>
      רק מפצל קובץ מוצפן קיים.

פלט: data.enc.txt (שורה אחת, בלי ירידת שורה בסוף), data.enc.sha256 (sha256 של הטקסט ואחריו
ירידת שורה), והפרוסות data.enc.part-NN.txt (עד CHUNK תווים כל אחת, בלי ירידת שורה).
"""
import argparse, base64, gzip, hashlib, json, os

CHUNK = 10000


def encrypt(payload_text: str, password: str) -> str:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    payload = json.loads(payload_text)
    exported_at = payload.get('exportedAt')
    if not exported_at:
        raise SystemExit('ה-payload חייב לכלול exportedAt')
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(hashes.SHA256(), 32, salt, 300000).derive(password.encode('utf-8'))
    ct = AESGCM(key).encrypt(iv, gzip.compress(payload_text.encode('utf-8'), 9), None)
    enc = {
        'salt': base64.b64encode(salt).decode(), 'iv': base64.b64encode(iv).decode(),
        'ct': base64.b64encode(ct).decode(), 'iters': 300000, 'gzip': True, 'exportedAt': exported_at,
    }
    return json.dumps(enc, separators=(',', ':'))


def split(enc_text: str, out_dir: str):
    enc_text = enc_text.strip()
    json.loads(enc_text)
    sha = hashlib.sha256(enc_text.encode('utf-8')).hexdigest()
    chunks = [enc_text[i:i + CHUNK] for i in range(0, len(enc_text), CHUNK)]
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'data.enc.txt'), 'w', encoding='utf-8', newline='') as f:
        f.write(enc_text)
    with open(os.path.join(out_dir, 'data.enc.sha256'), 'w', encoding='utf-8', newline='') as f:
        f.write(sha + '\n')
    names = []
    for i, c in enumerate(chunks):
        name = f'data.enc.part-{i:02d}.txt'
        with open(os.path.join(out_dir, name), 'w', encoding='utf-8', newline='') as f:
            f.write(c)
        names.append(name)
    print(f'data.enc.txt: {len(enc_text)} תווים, sha256 {sha}')
    print(f'פרוסות: {len(chunks)} (עד {CHUNK} תווים כל אחת): ' + ', '.join(names))
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--payload')
    ap.add_argument('--password')
    ap.add_argument('--from-enc')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if a.from_enc:
        enc_text = open(a.from_enc, encoding='utf-8').read()
    elif a.payload and a.password:
        enc_text = encrypt(open(a.payload, encoding='utf-8').read(), a.password)
    else:
        ap.error('נדרש --from-enc, או --payload יחד עם --password')
    split(enc_text, a.out)


if __name__ == '__main__':
    main()
