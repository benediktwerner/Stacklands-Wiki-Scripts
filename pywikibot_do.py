import os, re, yaml
import pywikibot

site = pywikibot.Site()
site.login()

# page.move("newtitle", reason="Can't delete", noredirect=True)

PATH = "/mnt/d/dev/wiki/stacklands/enemies"
PATH_OLD = "/mnt/d/dev/wiki/stacklands/enemies_old"

for fname in os.listdir(PATH):
    if not fname.endswith(".txt"):
        continue

    name = fname.removesuffix(".txt")
    page = pywikibot.Page(site, name)

    with open(os.path.join(PATH_OLD, fname)) as f:
        if page.text != f.read():
            print(name, "changed =========================")
            continue

    with open(os.path.join(PATH, fname)) as f:
        new = f.read()
        if new == page.text:
            print(name, "already new")
            continue

        page.text = new

    page.save("update spawn chances after Structure & Order update")
