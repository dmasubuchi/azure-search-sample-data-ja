"""hotels/ja の試験。Python 3.11 以上の標準ライブラリだけで動く。

Repo 直下から次のように流す。
    python3 -m unittest hotels/ja/test_build.py -v
このフォルダーの中からでも流せる（build.py はファイルの場所から読み込む）。
"""

import contextlib
import importlib.util
import io
import json
import re
import tempfile
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
UPSTREAM_PATH = HERE.parent / "HotelsData_toAzureBlobs.json"
OUTPUT_PATH = HERE / "HotelsData_toAzureBlobs_ja.json"
TRANSLATIONS_PATH = HERE / "translations.json"

NEW_HOTEL_FIELDS = ("HotelName_ja", "Description_ja", "Category_ja", "Tags_ja")
NEW_ROOM_FIELDS = ("Description_ja", "Type_ja")


def load_build_module():
    """build.py を、置いてある場所から読み込む（同名の別モジュールと取り違えない）。"""
    spec = importlib.util.spec_from_file_location("hotels_ja_build", HERE / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class GeneratedFileTest(unittest.TestCase):
    """生成物（HotelsData_toAzureBlobs_ja.json）を元のファイルと突き合わせる。"""

    @classmethod
    def setUpClass(cls):
        cls.upstream = load_json(UPSTREAM_PATH)
        cls.output = load_json(OUTPUT_PATH)
        cls.upstream_by_id = {h["HotelId"]: h for h in cls.upstream}
        cls.output_by_id = {h["HotelId"]: h for h in cls.output}

    def test_all_hotels_translated(self):
        self.assertEqual(len(self.upstream), 50)
        self.assertEqual(len(self.output), 50)
        self.assertEqual(set(self.output_by_id), set(self.upstream_by_id))
        for hotel in self.output:
            for field in NEW_HOTEL_FIELDS:
                with self.subTest(hotel=hotel["HotelId"], field=field):
                    self.assertIn(field, hotel)
                    self.assertTrue(hotel[field], "空です")
            self.assertIsInstance(hotel["Tags_ja"], list)
            self.assertEqual(len(hotel["Tags_ja"]), len(hotel["Tags"]))
            self.assertTrue(all(isinstance(t, str) and t for t in hotel["Tags_ja"]))

    def test_upstream_fields_unchanged(self):
        for up in self.upstream:
            out = self.output_by_id[up["HotelId"]]
            for key, value in up.items():
                if key == "Rooms":
                    continue
                with self.subTest(hotel=up["HotelId"], field=key):
                    self.assertEqual(out[key], value)
            for i, up_room in enumerate(up["Rooms"]):
                for key, value in up_room.items():
                    with self.subTest(hotel=up["HotelId"], room=i, field=key):
                        self.assertEqual(out["Rooms"][i][key], value)

    def test_only_expected_fields_added(self):
        for up in self.upstream:
            out = self.output_by_id[up["HotelId"]]
            self.assertEqual(set(out) - set(up), set(NEW_HOTEL_FIELDS))
            for up_room, out_room in zip(up["Rooms"], out["Rooms"]):
                self.assertEqual(set(out_room) - set(up_room), set(NEW_ROOM_FIELDS))

    def test_rooms_translated(self):
        total = 0
        for up in self.upstream:
            out = self.output_by_id[up["HotelId"]]
            self.assertEqual(len(out["Rooms"]), len(up["Rooms"]), up["HotelId"])
            for i, room in enumerate(out["Rooms"]):
                total += 1
                for field in NEW_ROOM_FIELDS:
                    with self.subTest(hotel=up["HotelId"], room=i, field=field):
                        self.assertIn(field, room)
                        self.assertTrue(room[field], "空です")
        self.assertEqual(total, 757)

    def test_numbers_preserved(self):
        for up in self.upstream:
            out = self.output_by_id[up["HotelId"]]
            en = Counter(re.findall(r"\d+", up["Description"]))
            ja = Counter(re.findall(r"\d+", out["Description_ja"]))
            with self.subTest(hotel=up["HotelId"]):
                self.assertEqual(en - ja, Counter(), "英語の数字が訳に出てこない")

    def test_room_numbers_preserved(self):
        for up in self.upstream:
            out = self.output_by_id[up["HotelId"]]
            for i, room in enumerate(up["Rooms"]):
                en = Counter(re.findall(r"\d+", room["Description"]))
                ja = Counter(re.findall(r"\d+", out["Rooms"][i]["Description_ja"]))
                with self.subTest(hotel=up["HotelId"], room=i):
                    self.assertEqual(en - ja, Counter())

    def test_no_latin_in_name_ja(self):
        for hotel in self.output:
            with self.subTest(hotel=hotel["HotelId"]):
                self.assertIsNone(
                    re.search(r"[A-Za-zＡ-Ｚａ-ｚ]", hotel["HotelName_ja"]),
                    hotel["HotelName_ja"],
                )

    def test_translated_fields_contain_japanese(self):
        kana_or_kanji = re.compile(r"[぀-ヿ一-鿿]")
        for hotel in self.output:
            fields = [hotel["HotelName_ja"], hotel["Description_ja"], hotel["Category_ja"]]
            fields += hotel["Tags_ja"]
            for room in hotel["Rooms"]:
                fields += [room["Description_ja"], room["Type_ja"]]
            for text in fields:
                with self.subTest(hotel=hotel["HotelId"], text=text):
                    self.assertTrue(kana_or_kanji.search(text))

    def test_same_english_same_japanese(self):
        """同じ英語には、どのホテルでも同じ訳が付く。"""
        pairs = {"Category": {}, "Type": {}, "Tag": {}, "RoomDescription": {}}
        for hotel in self.output:
            pairs["Category"].setdefault(hotel["Category"], set()).add(hotel["Category_ja"])
            for en, ja in zip(hotel["Tags"], hotel["Tags_ja"]):
                pairs["Tag"].setdefault(en, set()).add(ja)
            for room in hotel["Rooms"]:
                pairs["Type"].setdefault(room["Type"], set()).add(room["Type_ja"])
                pairs["RoomDescription"].setdefault(room["Description"], set()).add(
                    room["Description_ja"]
                )
        self.assertEqual(
            {k: len(v) for k, v in pairs.items()},
            {"Category": 6, "Type": 4, "Tag": 12, "RoomDescription": 80},
        )
        for kind, mapping in pairs.items():
            for en, ja_set in mapping.items():
                with self.subTest(kind=kind, en=en):
                    self.assertEqual(len(ja_set), 1, ja_set)

    def test_different_english_different_japanese(self):
        """違う英語に同じ訳を当てない（検索で区別がつかなくなる）。"""
        for kind, key_en, key_ja in (
            ("Category", "Category", "Category_ja"),
            ("Type", "Type", "Type_ja"),
            ("RoomDescription", "Description", "Description_ja"),
        ):
            seen = {}
            for hotel in self.output:
                rows = [hotel] if kind == "Category" else hotel["Rooms"]
                for row in rows:
                    seen.setdefault(row[key_ja], set()).add(row[key_en])
            for ja, en_set in seen.items():
                with self.subTest(kind=kind, ja=ja):
                    self.assertEqual(len(en_set), 1, en_set)
        tag_seen = {}
        for hotel in self.output:
            for en, ja in zip(hotel["Tags"], hotel["Tags_ja"]):
                tag_seen.setdefault(ja, set()).add(en)
        for ja, en_set in tag_seen.items():
            with self.subTest(kind="Tag", ja=ja):
                self.assertEqual(len(en_set), 1, en_set)

    def test_suite_is_not_translated_as_sweets(self):
        text = OUTPUT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("スイーツ", text)
        for hotel in self.output:
            for room in hotel["Rooms"]:
                if room["Type"] == "Suite":
                    self.assertEqual(room["Type_ja"], "スイート")
                    self.assertTrue(room["Description_ja"].startswith("スイート、"))

    def test_output_is_up_to_date(self):
        """生成物が、いまの translations.json と build.py から作り直したものと同じ。"""
        build = load_build_module()
        self.assertEqual(self.output, build.build(self.upstream, load_json(TRANSLATIONS_PATH)))


class BuildFunctionTest(unittest.TestCase):
    """build.py の動き（訳が足りないときに、黙って英語や空欄を出さない）。"""

    @classmethod
    def setUpClass(cls):
        cls.build = load_build_module()
        cls.upstream = load_json(UPSTREAM_PATH)
        cls.translations = load_json(TRANSLATIONS_PATH)

    def test_build_does_not_mutate_inputs(self):
        before = json.dumps(self.upstream, sort_keys=True)
        self.build.build(self.upstream, self.translations)
        self.assertEqual(json.dumps(self.upstream, sort_keys=True), before)

    def test_missing_hotel_translation_raises(self):
        broken = json.loads(json.dumps(self.translations))
        del broken["hotels"]["1"]
        with self.assertRaises(self.build.MissingTranslation) as ctx:
            self.build.build(self.upstream, broken)
        self.assertIn("1", str(ctx.exception))

    def test_missing_room_description_translation_raises(self):
        broken = json.loads(json.dumps(self.translations))
        del broken["room_descriptions"]["Suite, 1 King Bed (Amenities)"]
        with self.assertRaises(self.build.MissingTranslation) as ctx:
            self.build.build(self.upstream, broken)
        self.assertIn("Suite, 1 King Bed (Amenities)", str(ctx.exception))

    def test_missing_tag_category_type_raise(self):
        for section, key in (
            ("tags", "free wifi"),
            ("categories", "Luxury"),
            ("room_types", "Deluxe Room"),
        ):
            with self.subTest(section=section):
                broken = json.loads(json.dumps(self.translations))
                del broken[section][key]
                with self.assertRaises(self.build.MissingTranslation) as ctx:
                    self.build.build(self.upstream, broken)
                self.assertIn(key, str(ctx.exception))

    def test_unused_translations_raise(self):
        """元にないホテルや英文の訳が残っていたら、気づけるようにする。"""
        extra_hotel = json.loads(json.dumps(self.translations))
        extra_hotel["hotels"]["999"] = {"HotelName_ja": "あ", "Description_ja": "い"}
        with self.assertRaises(self.build.UnusedTranslation):
            self.build.build(self.upstream, extra_hotel)
        extra_room = json.loads(json.dumps(self.translations))
        extra_room["room_descriptions"]["Suite, 3 Cots (View)"] = "スイート"
        with self.assertRaises(self.build.UnusedTranslation):
            self.build.build(self.upstream, extra_room)

    def test_main_writes_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.json"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(self.build.main(["--output", str(out)]), 0)
            self.assertEqual(
                load_json(out), self.build.build(self.upstream, self.translations)
            )


if __name__ == "__main__":
    unittest.main()
