#!/usr/bin/env python3
"""Validate a Netscape-format cookies.txt for the Instagram/Facebook downloader.

Usage: python3 check_cookies.py [path/to/cookies.txt]
"""
import http.cookiejar
import sys
import time

REQUIRED_BY_DOMAIN = {
    "instagram.com": {"sessionid", "ds_user_id", "csrftoken"},
    "facebook.com": {"c_user", "xs"},
}


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "cookies.txt"

    jar = http.cookiejar.MozillaCookieJar(path)
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except FileNotFoundError:
        print(f"❌ Файл не найден: {path}")
        return 1
    except Exception as exc:
        print(f"❌ Не получилось разобрать файл как Netscape cookies.txt: {exc}")
        print("   Проверь, что экспортировал именно в этом формате (не JSON).")
        return 1

    if len(jar) == 0:
        print("❌ Файл прочитан, но кук в нём нет.")
        return 1

    print(f"Файл: {path}")
    print(f"Всего кук: {len(jar)}")

    now = time.time()
    by_domain: dict[str, list] = {}
    for cookie in jar:
        domain = cookie.domain.lstrip(".")
        by_domain.setdefault(domain, []).append(cookie)

    found_any_target = False
    ok = True
    for target_domain, required_names in REQUIRED_BY_DOMAIN.items():
        matching_domains = [
            d for d in by_domain if d == target_domain or d.endswith("." + target_domain)
        ]
        if not matching_domains:
            print(f"\n{target_domain}: куки не найдены")
            continue

        found_any_target = True
        present_names = set()
        expired_names = set()
        for d in matching_domains:
            for c in by_domain[d]:
                present_names.add(c.name)
                if c.expires and c.expires < now:
                    expired_names.add(c.name)

        total = sum(len(by_domain[d]) for d in matching_domains)
        print(f"\n{target_domain}: найдено {total} кук")

        missing = required_names - present_names
        if missing:
            ok = False
            print(f"  ⚠️  Не хватает ключевых кук авторизации: {', '.join(sorted(missing))}")
            print("     Скорее всего, при экспорте ты не был залогинен на этом сайте.")
        else:
            print(f"  ✅ Ключевые куки авторизации на месте: {', '.join(sorted(required_names))}")

        if expired_names:
            ok = False
            print(f"  ⚠️  Уже просрочены: {', '.join(sorted(expired_names))} — экспортируй куки заново.")

    if not found_any_target:
        print("\n❌ В файле нет кук ни для instagram.com, ни для facebook.com.")
        return 1

    print("\n" + ("✅ Файл выглядит рабочим." if ok else "⚠️  Файл частично рабочий, см. предупреждения выше."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
