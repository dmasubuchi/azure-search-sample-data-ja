# hotels/ja ホテルのデータの日本語版

Microsoft の公式サンプル [Azure-Samples/azure-search-sample-data](https://github.com/Azure-Samples/azure-search-sample-data) の `hotels` に、日本語の欄を足したものです。日本語で検索や RAG を試すために作りました。

この Repo の `main` は、元の `main` に、この `hotels/ja/` を足しただけです。元のファイルは変えていません。

## 足したもの

`HotelsData_toAzureBlobs_ja.json` は、元の `hotels/HotelsData_toAzureBlobs.json`（50 ホテル・757 客室）の全項目をそのまま残し、次の欄を足したものです。

- ホテル：`HotelName_ja`（ホテル名）、`Description_ja`（説明）、`Category_ja`（カテゴリ）、`Tags_ja`（タグ。`Tags` と同じ順・同じ数の配列）
- 客室（`Rooms[]` の各要素）：`Description_ja`（客室の説明）、`Type_ja`（客室の種類）

英語の欄、フランス語の欄（`Description_fr`）、数値、住所、位置情報などは、元のままです。

## 元のデータとライセンス

元のホテルのデータは Community Data License Agreement - Permissive, Version 2.0（CDLA-Permissive 2.0）で提供されています。契約の全文は、元の Repo にある [`hotels/LICENSE.md`](../LICENSE.md) です。このフォルダーの日本語版も、同じ契約の条件に従って共有します（共有するときは契約の文を添えます）。

## 日本語は AI で作りました

日本語の欄は、AI で作った訳です。Microsoft の公式の訳ではありません。誤訳や不自然な言い回しが残っているかもしれません。

訳すときに決めたこと：

- 元の英文にない事実（設備、距離、数字）を足さず、削りません。数字は元の英文と同じ数字を使います（`24/7` もそのまま残しています）
- 同じ英語には、どのホテルでも同じ訳を当てます。カテゴリ、タグ、客室の種類、客室の説明は、英語から日本語への対応表（`translations.json`）で引いています
- `Suite` は「スイート」です。ホテル名はカタカナで書きます
- 客室の説明（`Budget Room, 1 King Bed (City View)` など）は、種類・ベッド・眺めの組み合わせ 80 通りです。「バジェットルーム、キングベッド1台（市街の眺め）」のように訳しています。元の `(Amenities)` は「（設備）」、`(Cityside)` は「（市街側）」です
- ホテルの名前と説明は、作ってあった訳（`translations.json` の `hotels`）をそのまま使っています。文体はそろえ直していません

## 作り方

訳は `translations.json` にあります。

- `hotels`：HotelId ごとの `HotelName_ja` と `Description_ja`
- `categories`、`tags`、`room_types`、`room_descriptions`：英語の文から日本語への対応表

`build.py` が、元のファイルに訳を足して `HotelsData_toAzureBlobs_ja.json` を作ります。訳が足りないときや、元にない英語・HotelId の訳が残っているときは、止まってどれかを知らせます。

Python 3.11 以上の標準ライブラリだけで動きます。Repo の直下で流します。

```
python3 hotels/ja/build.py
```

訳を直したら、同じコマンドで作り直します。

## 試験

```
python3 -m unittest hotels/ja/test_build.py -v
```

確かめていること：

- 50 ホテルすべてに 4 つの欄があり、空でない。全客室に 2 つの欄がある
- 元の項目の値が、すべて同じ
- ホテルの説明と客室の説明で、元の英文の数字が日本語にも出てくる
- `HotelName_ja` に英字がない。`Suite` は「スイート」で、「スイーツ」になっていない
- 同じ英語には同じ訳、違う英語には違う訳が付いている
- 生成物が、いまの `translations.json` と `build.py` から作り直したものと同じ

## 使うとき

別の Repo から使うときは、コミットを固定した raw の URL で参照します。

```
https://raw.githubusercontent.com/<組織>/<Repo>/<コミット>/hotels/ja/HotelsData_toAzureBlobs_ja.json
```
