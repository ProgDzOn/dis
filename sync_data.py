#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكربت مزامنة تلقائي: يجلب البيانات من رابط ERP الداخلي (cruds.php)
ويحوّلها لنفس صيغة data.js المستخدمة في المشروع، ثم يحفظها محليًا.
يُشغَّل عبر GitHub Actions (انظر .github/workflows/sync-data.yml).
"""

import re
import sys
import urllib.request

SOURCE_URL = "http://105.96.0.195:2023/erp/include/cruds.php"
OUTPUT_FILE = "data.js"
TIMEOUT_SECONDS = 30


def fetch_source(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (sync-bot)"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        raw = resp.read()
    # الصفحة عادة UTF-8، مع احتمال وجود نص عربي
    return raw.decode("utf-8", errors="replace")


def transform(content: str) -> str:
    # تأكيد أساسي أن الصيغة لم تتغيّر بشكل غير متوقع قبل الاستبدال
    if "unite" not in content or "lieu" not in content or "distance" not in content:
        raise ValueError(
            "الصيغة المستلمة من الرابط غير متوقعة (لم أجد المتغيرات المعروفة). "
            "تم إيقاف التحديث حماية للبيانات الحالية."
        )

    # unite -> codeNamesArr (نفس البيانات، تسمية مختلفة فقط)
    content = re.sub(r"var\s+unite\s*=", "const codeNamesArr =", content, count=1)

    # إضافة السطر الذي يربط records بـ distance، كما في data.js الأصلي
    if "var records" not in content:
        content = content.rstrip() + "\n\nvar records = distance;\n"

    return content


def main():
    try:
        raw = fetch_source(SOURCE_URL)
        new_content = transform(raw)
    except Exception as e:
        print(f"❌ فشل التحديث: {e}", file=sys.stderr)
        sys.exit(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ تم تحديث {OUTPUT_FILE} بنجاح ({len(new_content)} حرف).")


if __name__ == "__main__":
    main()
