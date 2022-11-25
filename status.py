#!/usr/bin/env python3

import os, re
from collections import Counter, defaultdict
from pprint import pprint
import yaml
from itertools import chain

BASE_PATH = (
    "/mnt/g/extracted/stacklands/v1.2.6/Stacklands/ExportedProject/Assets/Resources"
)
SPECIAL_HIT_TARGET = [
    "self",
    "target",
    "randomfriendly",
    "randomenemy",
    "allfriendly",
    "allenemy",
]
SPECIAL_HIT_TYPE = [
    "none",
    "poison",
    "stun",
    "heal",
    "heallowest",
    "lifesteal",
    "bleeding",
    "frenzy",
    "damage",
    "invulnerable",
    "crit",
]

loc = {}
objs_by_guid = {}
objs_by_id = {}


def loc_id(id):
    if id == "any_villager":
        return "Villager"
    return loc[f"card_{id}_name"]


with open("loc.tsv") as f:
    for line in f:
        key, notes, eng, *_ = line.split("\t")
        loc[key] = eng

status = defaultdict(list)

for path, _, files in chain(
    *(os.walk(os.path.join(BASE_PATH, x)) for x in ("cards", "island_cards"))
):
    for file in files:
        if not file.endswith(".prefab"):
            continue

        file = os.path.join(path, file)

        with open(file + ".meta") as f:
            guid = yaml.safe_load(f)["guid"]

        with open(file) as f:
            content = f.read()
            if content.count("MonoBehaviour") > 1:
                print(file)
                continue
            obj = yaml.safe_load(content[content.find("MonoBehaviour") :])[
                "MonoBehaviour"
            ]
            objs_by_guid[guid] = obj
            objs_by_id[obj["Id"]] = obj


# KEY = "BaseCombatStats"
KEY = "MyStats"

for guid, obj in objs_by_guid.items():
    if KEY not in obj:
        continue

    for hit in obj[KEY]["SpecialHits"]:
        status[SPECIAL_HIT_TYPE[hit["HitType"]]].append(loc[obj["NameTerm"]])

pprint(status)
