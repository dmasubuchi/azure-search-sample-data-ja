#!/usr/bin/env python3
"""元の hotels/HotelsData_toAzureBlobs.json に日本語の欄を足して、
hotels/ja/HotelsData_toAzureBlobs_ja.json を作る。

足す欄:
  ホテル  HotelName_ja, Description_ja, Category_ja, Tags_ja
  客室    Description_ja, Type_ja（Rooms[] の各要素）

訳は translations.json から引く。
  hotels             HotelId -> {HotelName_ja, Description_ja}
  categories         Category の英語 -> 日本語
  tags               Tags の英語 -> 日本語
  room_types         客室の Type の英語 -> 日本語
  room_descriptions  客室の Description の英語 -> 日本語
同じ英語には、どのホテルでも同じ訳が付く。

訳が足りないとき、また元にない英語・HotelId の訳が残っているときは、
黙って進まずに止まる。元の項目は変えない。

使い方（Repo 直下から）:
    python3 hotels/ja/build.py
Python 3.11 以上の標準ライブラリだけで動く。
"""

import argparse
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE.parent / "HotelsData_toAzureBlobs.json"
DEFAULT_TRANSLATIONS = HERE / "translations.json"
DEFAULT_OUTPUT = HERE / "HotelsData_toAzureBlobs_ja.json"


class MissingTranslation(Exception):
    """元のデータにあるのに、translations.json に訳がないもの。"""


class UnusedTranslation(Exception):
    """translations.json にあるのに、元のデータに出てこない訳。"""


def _insert_after(record, after_key, new_key, value):
    """record の項目順を保ったまま、after_key の次に new_key を入れた新しい dict を返す。
    after_key がなければ、いちばん最後に入れる。"""
    result = {}
    for key, current in record.items():
        result[key] = current
        if key == after_key:
            result[new_key] = value
    result.setdefault(new_key, value)
    return result


def build(hotels, translations):
    """元のホテルの一覧に日本語の欄を足した、新しい一覧を返す（引数は変えない）。"""
    missing = []
    used = {"hotels": set(), "categories": set(), "tags": set(), "room_types": set(), "room_descriptions": set()}

    def lookup(section, key, label):
        table = translations[section]
        if key not in table:
            missing.append(f"{label}: {key!r}")
            return None
        used[section].add(key)
        return table[key]

    result = []
    for hotel in hotels:
        hotel_id = hotel["HotelId"]
        entry = lookup("hotels", hotel_id, "ホテルの訳(hotels)")
        name_ja = description_ja = None
        if entry is not None:
            name_ja, description_ja = entry["HotelName_ja"], entry["Description_ja"]
        category_ja = lookup("categories", hotel["Category"], f"カテゴリの訳(categories) HotelId={hotel_id}")
        tags_ja = [lookup("tags", tag, f"タグの訳(tags) HotelId={hotel_id}") for tag in hotel["Tags"]]

        rooms = []
        for room in hotel["Rooms"]:
            room_ja = lookup("room_descriptions", room["Description"], f"客室の説明の訳(room_descriptions) HotelId={hotel_id}")
            type_ja = lookup("room_types", room["Type"], f"客室の種類の訳(room_types) HotelId={hotel_id}")
            new_room = _insert_after(copy.deepcopy(room), "Description_fr", "Description_ja", room_ja)
            new_room = _insert_after(new_room, "Type", "Type_ja", type_ja)
            rooms.append(new_room)

        new_hotel = copy.deepcopy(hotel)
        new_hotel = _insert_after(new_hotel, "HotelName", "HotelName_ja", name_ja)
        new_hotel = _insert_after(new_hotel, "Description_fr", "Description_ja", description_ja)
        new_hotel = _insert_after(new_hotel, "Category", "Category_ja", category_ja)
        new_hotel = _insert_after(new_hotel, "Tags", "Tags_ja", tags_ja)
        new_hotel["Rooms"] = rooms
        result.append(new_hotel)

    if missing:
        unique = list(dict.fromkeys(missing))
        raise MissingTranslation(f"訳が足りません（{len(unique)} 件）:\n  " + "\n  ".join(unique))

    unused = [
        f"{section}: {key!r}"
        for section, keys in used.items()
        for key in translations[section]
        if key not in keys
    ]
    if unused:
        raise UnusedTranslation(f"元のデータにない訳が残っています（{len(unused)} 件）:\n  " + "\n  ".join(unused))

    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="日本語の欄を足した HotelsData_toAzureBlobs_ja.json を作る")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="元の JSON")
    parser.add_argument("--translations", type=Path, default=DEFAULT_TRANSLATIONS, help="訳の表")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="出力先")
    args = parser.parse_args(argv)

    with open(args.source, encoding="utf-8") as f:
        hotels = json.load(f)
    with open(args.translations, encoding="utf-8") as f:
        translations = json.load(f)

    try:
        output = build(hotels, translations)
    except (MissingTranslation, UnusedTranslation) as error:
        print(f"エラー: {error}", file=sys.stderr)
        return 1

    with open(args.output, "w", encoding="utf-8", newline="\n") as f:  # Windows でも改行は LF
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")
    rooms = sum(len(h["Rooms"]) for h in output)
    print(f"{args.output} を作りました（ホテル {len(output)} 件、客室 {rooms} 件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
