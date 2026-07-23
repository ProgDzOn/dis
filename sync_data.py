#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكربت مزامنة تلقائي: يجلب البيانات من رابط ERP (cruds.php)
ويحوّلها لنفس صيغة data.js المستخدمة في المشروع، ثم يحفظها محليًا.
يُشغَّل عبر GitHub Actions (انظر .github/workflows/sync-data.yml).
"""

import re
import sys
import time
import urllib.error
import urllib.request

SOURCE_URL = "http://105.96.0.195:2023/erp/include/cruds.php"
OUTPUT_FILE = "data.js"
TIMEOUT_SECONDS = 30

# إعدادات إعادة المحاولة عند فشل الاتصال (مؤقت شبكة، انقطاع مؤقت...)
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

# حد أدنى تقريبي لحجم المحتوى (بالحروف) — أي رد أصغر من هذا يُعتبر مشبوهًا
# (صفحة خطأ، رد فارغ، انقطاع منتصف النقل...) ولا يُعتمد لتحديث data.js
MIN_CONTENT_LENGTH = 1000


def fetch_source(url: str) -> str:
    """يجلب محتوى الرابط مع إعادة محاولة عند فشل الشبكة."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (sync-bot)"})

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                raw = resp.read()
                # نحاول استخدام الترميز المُعلَن من السيرفر إن وُجد، وإلا نفترض UTF-8
                # (المتوقع لصفحات تحتوي نص عربي)
                charset = resp.headers.get_content_charset() or "utf-8"
                status = resp.status

            if status != 200:
                raise RuntimeError(f"استجابة غير متوقعة من الرابط: HTTP {status}")

            text = raw.decode(charset, errors="replace")
            print(f"ℹ️ تم الجلب بنجاح (status={status}, encoding={charset}, حجم={len(raw)} بايت)")
            return text

        except urllib.error.HTTPError as e:
            last_error = RuntimeError(f"HTTP {e.code} عند جلب {url}: {e.reason}")
        except urllib.error.URLError as e:
            last_error = RuntimeError(f"فشل الاتصال بـ {url}: {e.reason}")
        except TimeoutError:
            last_error = RuntimeError(f"انتهت مهلة الاتصال ({TIMEOUT_SECONDS}s) عند جلب {url}")
        except Exception as e:  # أي خطأ غير متوقع آخر أثناء القراءة/الفك
            last_error = RuntimeError(f"خطأ غير متوقع أثناء جلب {url}: {e}")

        if attempt < MAX_RETRIES:
            print(f"⚠️ محاولة {attempt}/{MAX_RETRIES} فشلت: {last_error}. إعادة المحاولة خلال {RETRY_DELAY_SECONDS}s...")
            time.sleep(RETRY_DELAY_SECONDS)

    # كل المحاولات فشلت
    raise last_error


def transform(content: str) -> str:
    if len(content) < MIN_CONTENT_LENGTH:
        raise ValueError(
            f"المحتوى المستلم قصير جدًا ({len(content)} حرف) — يبدو غير مكتمل أو صفحة خطأ. "
            "تم إيقاف التحديث حماية للبيانات الحالية."
        )

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
