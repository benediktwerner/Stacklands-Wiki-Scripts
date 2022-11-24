#!/usr/bin/env python3

import os, re
from collections import Counter, defaultdict
from pprint import pprint
import yaml

BASE_PATH = (
    "/mnt/g/extracted/stacklands/v1.2.6/Stacklands/ExportedProject/Assets/Resources"
)
OUT_PATH = "equipment"
IDEA_OUT_PATH = "equipment_idea"
CAT_NAME = {"body": "Body", "head": "Head", "weapon": "Hand"}
ATTACK_TYPE = ["", "Melee", "Ranged", "Magic"]
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
ATTACK_SPEED = [
    3.5,
    2.5,
    1.5,
    1,
    0.75,
    0.5,
]
HIT_CHANCE = [
    0.5,
    0.6,
    0.7,
    0.8,
    0.85,
    0.95,
]

SPECIAL_HIT_TXT = {
    "bleeding": "[chance]% chance to [[Status Effects#Status:_Bleeding|Bleed]] [target]",
    "crit": "[chance]% chance to do a Critical Hit on [target]",
    "damage": "[chance]% chance to Damage [target]",
    "frenzy": "[chance]% chance to [[Status Effects#Status:_Frenzy|Frenzy]] [target] for 10s",
    "heal": "[chance]% chance to Heal [target] by 2",
    "heallowest": "[chance]% chance to Heal friendly with lowest health by 2",
    "invulnerable": "[chance]% chance to make [target] [[Status Effects#Status:_Invulnerable|Invulnerable]] for 10s",
    "lifesteal": "[chance]% chance to Lifesteal from [target]",
    "poison": "[chance]% chance to [[Status Effects#Status:_Poisoned|Poison]] [target]",
    "stun": "[chance]% chance to [[Status Effects#Status:_Stunned|Stun]] [target] for 5s",
}

equipped_by = defaultdict(list)
dropped_by = defaultdict(list)
can_drop_equipment = defaultdict(lambda: False)
blueprints = {None: None}
loc = {}


def loc_id(id):
    if id == "any_villager":
        return "Villager"
    return loc[f"card_{id}_name"]


def join(xs):
    assert xs, "trying to join empty list"
    if len(xs) == 1:
        return xs[0]
    elif len(xs) == 2:
        return f"{xs[0]} or {xs[1]}"
    return f"{', '.join(xs[:-1])}, or {xs[-1]}"


def signed(s):
    if s == 0:
        return ""
    if s > 0:
        return f"+{s}"
    return str(s)


def obtain(o, guid):
    result = []
    if o["Id"] == "spear":
        result.append("From [[Travelling Cart]]")
    if o["Id"] in dropped_by:
        droppers = dropped_by[o["Id"]]
        units = join([f"[[{loc_id(x)}]] ({c}%)" for x, c in droppers])
        r = f"Dropped when killing {units}"
        if any(can_drop_equipment[x] for x, _ in droppers):
            if len(droppers) == 1:
                r += " if it doesn't have droppable equipment"
            else:
                r += " if they don't have droppable equipment"
        result.append(r)
    if guid in equipped_by:
        units = join([f"[[{loc_id(x)}]]" for x in equipped_by[guid]])
        r = f"Dropped when killing {units} spawned with it"
        if "guid" in o["blueprint"]:
            r += " if this card hasn't been found found yet"
        result.append(r)

    return result


def clamp_stat(s):
    return min(5, max(0, s))

def calc_level(stats):
    dmg = clamp_stat(stats["AttackDamage"] + stats["AttackDamageIncrement"]) + 1
    chance = HIT_CHANCE[clamp_stat(stats["HitChance"] + stats["HitChanceIncrement"])]
    speed = ATTACK_SPEED[clamp_stat(stats["AttackSpeed"] + stats["AttackSpeedIncrement"])]
    dps = dmg / speed * chance
    lvl = dps * 5
    lvl += stats["MaxHealth"] * 0.5
    lvl += (stats["Defence"] + stats["DefenceIncrement"]) * 2
    for special in stats["SpecialHits"]:
        lvl += special["Chance"] / 5
    return round(lvl)


def summarize_special(s):
    target = loc["target_" + SPECIAL_HIT_TARGET[s["Target"]]]
    # txt = loc["specialhit_" + SPECIAL_HIT_TYPE[s["HitType"]] + "_long"]
    txt = SPECIAL_HIT_TXT[SPECIAL_HIT_TYPE[s["HitType"]]]
    return txt.replace("[chance]", str(s["Chance"])).replace("[target]", target)


def summarize_specials(stats):
    specials = [summarize_special(s) for s in stats["SpecialHits"]]
    if not specials:
        return ""
    if len(specials) == 1:
        return specials[0]
    return "*" + "\n*".join(specials)


def format_blueprint(obj):
    if obj is None:
        return ""
    assert len(obj["Subprints"]) == 1
    s = obj["Subprints"][0]
    cnt = Counter(s["RequiredCards"])
    return (
        ", ".join(f"{c}x [[{loc_id(x)}]]" for x, c in cnt.items())
        + f" for {s['Time']}s"
    )


os.makedirs(OUT_PATH, exist_ok=True)
os.makedirs(IDEA_OUT_PATH, exist_ok=True)

with open("loc.tsv") as f:
    for line in f:
        key, notes, eng, *_ = line.split("\t")
        loc[key] = eng

for path, _, files in os.walk(BASE_PATH):
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

            if "blueprint_" in file:
                blueprints[guid] = obj

            for equip in obj.get("PossibleEquipables", []):
                equipped_by[equip["guid"]].append(obj["Id"])
                can_drop_equipment[obj["Id"]] = True

            drops = obj.get("Drops", {}).get("Chances", [])
            total_chance = sum(d["Chance"] for d in drops)
            for drop in drops:
                dropped_by[drop["Id"]].append(
                    (obj["Id"], int(drop["Chance"] / total_chance * 100))
                )


for cat in ["body", "head", "weapon"]:
    catpath = os.path.join(BASE_PATH, "cards", "equipment", cat)

    for fname in os.listdir(catpath):
        if not fname.endswith(".prefab") or fname.startswith("blueprint_"):
            continue

        with open(os.path.join(catpath, fname + ".meta")) as f:
            guid = yaml.safe_load(f)["guid"]

        with open(os.path.join(catpath, fname)) as f:
            content = f.read()
            obj = yaml.safe_load(content[content.find("MonoBehaviour") :])[
                "MonoBehaviour"
            ]
            name = loc[obj["NameTerm"]]
            desc = loc[obj["DescriptionTerm"]]
            stats = obj["MyStats"]
            rec = format_blueprint(blueprints[obj["blueprint"].get("guid")])
            rec2 = f"==Recipe==\n*{rec}\n\n" if rec else ""
            obt = obtain(obj, guid)
            obt2 = (
                (
                    f"==Way{'s' if len(obt) > 1 else ''} to Obtain==\n*"
                    + "\n*".join(obt)
                    + "\n\n"
                )
                if obt
                else ""
            )
            used = (
                f"==Used For==\n*[[{loc_id(obj['VillagerTypeOverride'])}]]\n\n"
                if obj["VillagerTypeOverride"]
                else ""
            )
            see = f"==See also==\n*[[Idea: {name}]]\n\n" if rec else ""
            out = f"""\
{{{{Stacklands Equipment
|image = {name.replace(" ", "_")}.png
|caption = "{desc}"
|special = {summarize_specials(stats)}
|hp = {signed(stats['MaxHealth'])}
|attack_speed = {signed(stats['AttackSpeedIncrement'])}
|hit_chance = {signed(stats['HitChanceIncrement'])}
|damage = {signed(stats['AttackDamageIncrement'])}
|defense = {signed(stats['DefenceIncrement'])}
|slot = {CAT_NAME[cat]}
|attack_type = {ATTACK_TYPE[obj["AttackType"]]}
|level = {calc_level(stats)}
|sell_prize = {obj["Value"]}
}}}}
'''{name}''' is a [[:Category:Equipment|Gray]] [[Cards|Card]] in [[Stacklands]]. In the [[Cardopedia]], it is categorized as [[:Category:Equipment|Equipment]].

{obt2}\
{rec2}\
{used}\
{see}\
[[Category:Equipment]]
[[Category:Equipment/{CAT_NAME[cat]}]]"""

        with open(os.path.join(OUT_PATH, name.replace(" ", "_") + ".txt"), "w") as of:
            of.write(out)

        if rec:
            out = f"""\
{{{{Stacklands Idea
|image1 = Idea - {name}.png
|caption1 = {desc}
|sell_price = 1
}}}}
'''Idea: {name}''' is a blue [[Cards|Card]] in [[Stacklands]]. In the [[Cardopedia]], it is categorized as an [[:Category:Ideas|Idea]]. It explains how to create a [[{name}]].

==See also==
*[[{name}]]

[[Category:Ideas]]"""

            with open(
                os.path.join(IDEA_OUT_PATH, name.replace(" ", "_") + ".txt"), "w"
            ) as of:
                of.write(out)
