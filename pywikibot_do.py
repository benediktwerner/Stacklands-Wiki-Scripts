import os, re, yaml
import pywikibot

site = pywikibot.Site()
site.login()

# page.move("newtitle", reason="Can't delete", noredirect=True)

PATH = "/mnt/d/dev/wiki/stacklands/enemies"

for fname in os.listdir(PATH):
    if not fname.endswith(".txt"):
        continue

    name = fname.removesuffix(".txt")

    if name not in ("Rat", "Seagull", "Skeleton", "Tiger"):
        continue

    page = pywikibot.Page(site, name)

    with open(os.path.join(PATH, fname)) as f:
        page.text = f.read()

    page.save("more detailed info")
