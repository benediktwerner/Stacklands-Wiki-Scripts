#!/usr/bin/env python3

import os, re
from collections import Counter, defaultdict
from pprint import pprint
import yaml
from itertools import chain

BASE_PATH = (
    "/mnt/g/extracted/stacklands/v1.2.6/Stacklands/ExportedProject/Assets/Resources"
)
OUT_PATH = "enemies"
ATTACK_TYPE = ["", "Melee", "Ranged", "Magic"]
SLOT_NAME = ["Head", "Body", "Hand"]
SPECIAL_HIT_TARGET = [
    "self",
    "target",
    "randomfriendly",
    "randomenemy",
    "allfriendly",
    "allenemy",
]
SPECIAL_HIT_TARGET_CAT = [
    "Self",
    "Target",
    "Random Friendly",
    "Random Enemy",
    "All Friendly",
    "All Enemy",
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
SPECIAL_HIT_TYPE_CAT = [
    "none",
    "Poison",
    "Stun",
    "Heal",
    "Heal",
    "Lifesteal",
    "Bleed",
    "Frenzy",
    "Damage",
    "Invulnerable",
    "Critical Hit",
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

SPEED_TEXT = [
    "Very Slow",
    "Slow",
    "Normal",
    "Fast",
    "Very Fast",
    "Extremely Fast",
]
DMG_TEXT = [
    "Very Weak",
    "Weak",
    "Normal",
    "Strong",
    "Very Strong",
    "Extremely Strong",
]
CHANCE_TEXT = [
    "Very Small",
    "Small",
    "Normal",
    "High",
    "Very High",
    "Extremely High",
]

loc = {}
objs_by_guid = {}
objs_by_id = {}
dropped_by_booster = defaultdict(list)
dropped_by_location = defaultdict(lambda: defaultdict(int))
spawns_from_portal = {}
spawned_in_forest = {
    "elf",
    "elf_archer",
    "ghost",
    "giant_snail",
    "merman",
    "mosquito",
    "enchanted_shroom",
    "feral_cat",
}
spawned_in_forest_advanced = {
    "dark_elf",
    "ent",
    "mimic",
    "ogre",
    "orc_wizard",
    "pirate",
}


def loc_id(id):
    if id == "any_villager":
        return "Villager"
    return loc[f"card_{id}_name"]


def join(xs):
    xs = list(xs)
    assert xs, "trying to join empty list"
    if len(xs) == 1:
        return xs[0]
    elif len(xs) == 2:
        return f"{xs[0]} or {xs[1]}"
    return f"{', '.join(xs[:-1])}, or {xs[-1]}"


def clamp_stat(s):
    return min(5, max(0, s))


def calc_level(stats):
    dmg = clamp_stat(stats["AttackDamage"] + stats["AttackDamageIncrement"]) + 1
    chance = HIT_CHANCE[clamp_stat(stats["HitChance"] + stats["HitChanceIncrement"])]
    speed = ATTACK_SPEED[
        clamp_stat(stats["AttackSpeed"] + stats["AttackSpeedIncrement"])
    ]
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


def append_once(lst, val):
    if val not in lst:
        lst.append(val)


def special_hit_categories(stats):
    out = []
    for s in stats["SpecialHits"]:
        typ = SPECIAL_HIT_TYPE_CAT[s["HitType"]]
        target = SPECIAL_HIT_TARGET_CAT[s["Target"]]
        append_once(out, f"[[Category:Special Hit/{typ}]]")
        append_once(out, f"[[Category:Special Hit/{typ}/{target}]]")
        append_once(out, f"[[Category:Special Hit/{target}]]")
    if out:
        return "\n" + "\n".join(out)
    return ""


def attack_speed(stats):
    val = clamp_stat(stats["AttackSpeed"] + stats["AttackSpeedIncrement"])
    return f"{SPEED_TEXT[val]} ({ATTACK_SPEED[val]}s)"


def damage(stats):
    val = clamp_stat(stats["AttackDamage"] + stats["AttackDamageIncrement"])
    return f"{DMG_TEXT[val]} ({val+1})"


def defense(stats):
    val = clamp_stat(stats["Defence"] + stats["DefenceIncrement"])
    return f"{DMG_TEXT[val]} (Blocks {round((val+1)*0.5)})"


def hit_chance(stats):
    val = clamp_stat(stats["HitChance"] + stats["HitChanceIncrement"])
    return f"{CHANCE_TEXT[val]} ({int(HIT_CHANCE[val]*100)}%)"


def sum_gear_slot(eq, slot):
    eq = [e for e in eq if e["EquipableType"] == slot]
    if not eq:
        return ""
    eq = join([f"[[{loc[e['NameTerm']]}]]" for e in eq])
    return f"*'''{SLOT_NAME[slot]}''': {eq}\n"


def sum_gear(obj):
    eq = obj["PossibleEquipables"]
    if not eq:
        return ""
    eq = [objs_by_guid[e["guid"]] for e in eq]
    return f"""\
==Possible Equipment==
{sum_gear_slot(eq, 0)}{sum_gear_slot(eq, 2)}{sum_gear_slot(eq, 1)}
"""


def sum_chance(chance, drop):
    chance = round(chance * 100)
    out = ""
    if chance < 100:
        out = f"{chance}%"
    if drop:
        if out:
            out += ", "
        out += "only if no other equipment has been dropped yet in the current fight"
    if out:
        out = f" ({out})"
    return out


def sum_drops(obj, has_eq):
    bag = obj.get("Drops", {})
    drops = bag.get("Chances", [])
    if not drops:
        return ""

    count = bag["CardsInPack"]
    assert count == 1 or len(drops) <= 1, obj["Id"]
    assert bag["CardBagType"] == 0, obj["Id"]

    count = f"{count}x " if count > 1 else ""
    total_chance = sum(d["Chance"] for d in drops)
    always_drop = obj["AlwaysDrop"] == 1
    return (
        "==Drops==\n"
        + (
            "*If wearing equipment that is uncraftable or hasn't been found yet and no other mob has dropped any equipement in the current fight, one such worn equipment is dropped instead\n"
            if has_eq
            else ""
        )
        + "\n".join(
            f"*{count}[[{loc_id(drop['Id'])}]]{sum_chance(drop['Chance'] / total_chance, 'EquipableType' in objs_by_id[drop['Id']] and not always_drop )}"
            for drop in drops
        )
        + "\n\n"
    )


def sum_spawns(obj):
    rows = []
    id = obj["Id"]
    if dropped_by_location[id]:
        rows.append(
            f"By exploring "
            + join(
                f"[[{name}]] ({round(c*100)}%)"
                for name, c in dropped_by_location[id].items()
            )
        )
    if dropped_by_booster[id]:
        rows.append(
            "From "
            + join(f"''{pack}'' ({c})" for pack, c in dropped_by_booster[id])
            + " [[Card Packs]]"
        )
    if id in spawns_from_portal:
        rows.append(
            f"From [[Strange Portal]] or [[Rare Portal]] starting [[Moon]] {spawns_from_portal[id]}"
        )
    if id in spawned_in_forest:
        rows.append("By visiting the [[Dark Forest]]")
    if id in spawned_in_forest_advanced:
        rows.append("By visiting the [[Dark Forest]] (wave 4 or above)")

    if not rows:
        return ""
    return "==How to Spawn==\n" + "\n".join("*" + row for row in rows) + "\n\n"


os.makedirs(OUT_PATH, exist_ok=True)

with open("loc.tsv") as f:
    for line in f:
        key, notes, eng, *_ = line.split("\t")
        loc[key] = eng


with open("pack_drops.yaml") as f:
    for name, enemies in yaml.safe_load(f).items():
        for e, c in enemies.items():
            dropped_by_booster[e].append((name, c))

with open("portal.yaml") as f:
    for month, enemies in yaml.safe_load(f).items():
        for e in enemies:
            spawns_from_portal[e] = month

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
            objs_by_guid[guid] = obj
            objs_by_id[obj["Id"]] = obj

            # Locations
            if obj["MyCardType"] == 6:
                name = loc[obj["NameTerm"]]
                for bag in obj["MyCardBag"]["Chances"]:
                    if bag["IsEnemy"]:
                        for c, enemy in enemy_bags[bag["EnemyBag"]]:
                            dropped_by_location[enemy][name] += (
                                c * bag["PercentageChance"]
                            )
                    else:
                        dropped_by_location[bag["Id"]][name] += bag["PercentageChance"]


for guid, obj in objs_by_guid.items():
    if not obj.get("IsAggressive", False):
        continue

    name = loc[obj["NameTerm"]]
    desc = loc[obj["DescriptionTerm"]]
    stats = obj["BaseCombatStats"]
    spawn = sum_spawns(obj)
    gear = sum_gear(obj)
    drops = sum_drops(obj, bool(gear))
    out = f"""\
{{{{Stacklands Hostile Mob
|image1 = {name.replace(" ", "_")}.png
|caption1 = "{desc}"
|combat_level  = {calc_level(stats)}
|health_points = {stats['MaxHealth']}
|effect = {summarize_specials(stats)}
|attack_type = {ATTACK_TYPE[obj["BaseAttackType"]]}
|attack_speed = {attack_speed(stats)}
|hit_chance = {hit_chance(stats)}
|damage = {damage(stats)}
|defense = {defense(stats)}
}}}}
'''{name}''' is a [[:Category:Hostile Mobs|red]] [[Cards|Card]] in [[Stacklands]]. In the [[Cardopedia]], it is categorized as a [[:Category:Mobs|Mob]].

{spawn}\
{gear}\
{drops}\
[[Category:Mobs]]
[[Category:Hostile Mobs]]{special_hit_categories(stats)}"""

    with open(os.path.join(OUT_PATH, name.replace(" ", "_") + ".txt"), "w") as of:
        of.write(out)
