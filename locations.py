#!/usr/bin/env python3

import os, re
from collections import Counter, defaultdict
from pprint import pprint
import yaml
from itertools import chain

BASE_PATH = (
    "/mnt/g/extracted/stacklands/v1.2.6/Stacklands/ExportedProject/Assets/Resources"
)


def loc_id(id):
    if id == "any_villager":
        return "Villager"
    id = id.replace("smelting", "smelter")
    if id.startswith("blueprint_"):
        return "Idea: " + loc[f"card_{id.replace('blueprint_', '')}_name"]
    return loc[f"card_{id}_name"]


loc = {}

with open("loc.tsv") as f:
    for line in f:
        key, notes, eng, *_ = line.split("\t")
        loc[key] = eng

with open("enemy_bags.yaml") as f:
    enemy_bags = {}
    for index, enemies in yaml.safe_load(f).items():
        total = sum(enemies.values())
        enemy_bags[index] = [(c / total, e) for e, c in enemies.items()]

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

            # Locations
            if obj["MyCardType"] == 6:
                name = loc[obj["NameTerm"]]
                print(name)
                spawns = defaultdict(int)
                for bag in obj["MyCardBag"]["Chances"]:
                    if bag["IsEnemy"]:
                        for c, enemy in enemy_bags[bag["EnemyBag"]]:
                            spawns[enemy] += c * bag["PercentageChance"]
                    else:
                        spawns[bag["Id"]] += bag["PercentageChance"]
                for spawn, chance in sorted(spawns.items(), key=lambda x: -x[1]):
                    print(
                        "*[[" + loc_id(spawn) + "]] (" + str(round(chance * 100)) + "%)"
                    )
                print()
