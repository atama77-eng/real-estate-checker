"""
【一度だけ実行するスクリプト】
N02-22_Station.geojson から駅名・駅コードの変換テーブル(station_codes.csv)を生成します。

使い方:
  python convert_station_geojson.py <GeoJSONのパス>

例:
  python convert_station_geojson.py "C:/Users/ntaga/Downloads/UTF-8/N02-22_Station.geojson"

生成されたstation_codes.csvをreal-estate-checkerフォルダに置いてください。
"""

import sys
import json
import csv
from pathlib import Path


def convert(geojson_path: str):
    path = Path(geojson_path)
    if not path.exists():
        print(f"エラー: ファイルが見つかりません → {geojson_path}")
        sys.exit(1)

    print(f"読み込み中: {path} ({path.stat().st_size // 1024} KB)")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    print(f"  フィーチャー数: {len(features)}")

    # 駅グループコード(N02_005g)と駅名(N02_005)を抽出・重複除去
    seen = set()
    rows = []
    for feat in features:
        props = feat.get("properties", {})
        name = props.get("N02_005") or props.get("N02_005e") or ""
        code = props.get("N02_005g") or ""
        if name and code and code not in seen:
            seen.add(code)
            rows.append({"station_name": name.strip(), "station_code": str(code).strip()})

    # 駅名でソート
    rows.sort(key=lambda r: r["station_name"])

    out_path = Path(__file__).parent / "station_codes.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["station_name", "station_code"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"  駅数(重複除去後): {len(rows)}")
    print(f"✅ 保存完了: {out_path}")
    print("  → このファイルをreal-estate-checkerフォルダに置いてください。")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python convert_station_geojson.py <GeoJSONのパス>")
        print('例: python convert_station_geojson.py "C:/Users/ntaga/Downloads/UTF-8/N02-22_Station.geojson"')
        sys.exit(1)
    convert(sys.argv[1])
