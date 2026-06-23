"""
不動産価格チェッカー
国土交通省「不動産情報ライブラリ」API (XIT001) を利用した
中古マンション等の取引価格チェック + 簡易利回り分析アプリ
"""

import os
import gzip
import json
from datetime import datetime
from io import BytesIO
from pathlib import Path

import requests
import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------
# 設定
# ----------------------------------------------------------------------

API_BASE_URL = "https://www.reinfolib.mlit.go.jp/ex-api/external/XIT001"
API_CITY_URL = "https://www.reinfolib.mlit.go.jp/ex-api/external/XIT002"

# st.secrets["REINFOLIB_API_KEY"] にAPIキーを設定すると本物のデータを使う。
# 未設定の場合は自動でダミーデータモードになる。
try:
    API_KEY = st.secrets.get("REINFOLIB_API_KEY", "") or os.environ.get("REINFOLIB_API_KEY", "")
except FileNotFoundError:
    API_KEY = os.environ.get("REINFOLIB_API_KEY", "")
USE_DUMMY_DATA = not bool(API_KEY)

CURRENT_YEAR = datetime.now().year

# 都道府県コード(よく使うものだけ。必要に応じて追加してください)
PREFECTURES = {
    "東京都": "13",
    "神奈川県": "14",
    "大阪府": "27",
    "愛知県": "23",
    "福岡県": "40",
}

QUARTERS = ["1", "2", "3", "4"]
YEARS = list(range(2015, CURRENT_YEAR + 1))

TYPE_OPTIONS = ["中古マンション等", "宅地(土地)", "宅地(土地と建物)", "農地", "林地"]

PRICE_CLASSIFICATION_MAP = {
    "取引価格+成約価格": None,
    "取引価格のみ": "01",
    "成約価格のみ": "02",
}


# ----------------------------------------------------------------------
# データ取得
# ----------------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_cities(pref_code):
    """XIT002 APIから都道府県内の市区町村一覧を取得する。結果は24時間キャッシュ。"""
    if USE_DUMMY_DATA:
        return {"指定なし": None}
    try:
        resp = requests.get(
            API_CITY_URL,
            params={"area": pref_code},
            headers={"Ocp-Apim-Subscription-Key": API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        try:
            data = json.loads(gzip.decompress(resp.content))
        except (gzip.BadGzipFile, OSError):
            data = resp.json()
        cities = {"指定なし": None}
        # デバッグ: 実際のレスポンスを表示
        raw_data = data.get("data", [])
        if raw_data:
            st.sidebar.write("🔍 APIレスポンス(先頭1件):", raw_data[0])
        else:
            st.sidebar.write("🔍 dataキーの中身が空です。キー一覧:", list(data.keys()))
        for item in data.get("data", []):
            name = item.get("Municipality") or item.get("municipality") or ""
            code = item.get("MunicipalityCode") or item.get("municipalityCode") or ""
            if name and code:
                cities[name] = code
        return cities
    except Exception as e:
        st.warning(f"市区町村リストの取得に失敗しました: {e}")
        return {"指定なし": None}


@st.cache_data(show_spinner=False)
def load_station_codes():
    """station_codes.csvから駅名→駅コードの辞書を返す。ファイルがなければ空dict。"""
    csv_path = Path(__file__).parent / "station_codes.csv"
    if not csv_path.exists():
        return {}
    df = pd.read_csv(csv_path, dtype=str)
    return dict(zip(df["station_name"], df["station_code"]))



def fetch_transactions(area_code, city_code, year_from, quarter_from, year_to, quarter_to,
                        price_classification, station_code=None):
    """国交省APIから取引価格情報を取得する。複数四半期にわたる場合は年×四半期分ループする。"""
    all_rows = []

    for year in range(year_from, year_to + 1):
        q_start = quarter_from if year == year_from else 1
        q_end = quarter_to if year == year_to else 4
        for quarter in range(q_start, q_end + 1):
            params = {"year": str(year), "quarter": str(quarter)}
            if station_code:
                params["station"] = station_code
            else:
                params["area"] = area_code
                if city_code:
                    params["city"] = city_code
            if price_classification:
                params["priceClassification"] = price_classification

            try:
                resp = requests.get(
                    API_BASE_URL,
                    params=params,
                    headers={"Ocp-Apim-Subscription-Key": API_KEY},
                    timeout=15,
                )
                if resp.status_code == 404:
                    continue  # データなし
                resp.raise_for_status()

                try:
                    data = json.loads(gzip.decompress(resp.content))
                except (gzip.BadGzipFile, OSError):
                    data = resp.json()

                rows = data.get("data", [])
                all_rows.extend(rows)
            except requests.RequestException as e:
                st.warning(f"{year}年第{quarter}四半期の取得に失敗しました: {e}")

    return pd.DataFrame(all_rows)


def generate_dummy_data():
    """APIキー未設定時に使うダミーデータ。実データと同じカラム構成にしてある。"""
    rows = [
        {"DistrictName": "日本橋小網町", "Period": "2024年第1四半期", "BuildingYear": "1998年",
         "FloorPlan": "３ＬＤＫ", "Area": "80", "TradePrice": "85000000",
         "UnitPrice": "1062500", "PricePerUnit": "3512000"},
        {"DistrictName": "勝どき", "Period": "2024年第2四半期", "BuildingYear": "2009年",
         "FloorPlan": "２ＬＤＫ", "Area": "55", "TradePrice": "61000000",
         "UnitPrice": "1109000", "PricePerUnit": "3667000"},
        {"DistrictName": "銀座", "Period": "2024年第3四半期", "BuildingYear": "2018年",
         "FloorPlan": "１Ｒ", "Area": "28", "TradePrice": "42300000",
         "UnitPrice": "1510000", "PricePerUnit": "4995000"},
        {"DistrictName": "月島", "Period": "2024年第4四半期", "BuildingYear": "2021年",
         "FloorPlan": "１ＬＤＫ", "Area": "40", "TradePrice": "49800000",
         "UnitPrice": "1245000", "PricePerUnit": "4117000"},
        {"DistrictName": "豊洲", "Period": "2025年第1四半期", "BuildingYear": "2015年",
         "FloorPlan": "２ＬＤＫ", "Area": "62", "TradePrice": "78000000",
         "UnitPrice": "1258000", "PricePerUnit": "4160000"},
    ]
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# データ加工
# ----------------------------------------------------------------------

def add_building_age(df):
    """BuildingYear (例: '1998年') から築年数を計算して列を追加する。"""
    def parse_year(s):
        try:
            return int(str(s).replace("年", "").strip())
        except (ValueError, TypeError):
            return None

    df = df.copy()
    df["建築年(数値)"] = df["BuildingYear"].apply(parse_year)
    df["築年数"] = df["建築年(数値)"].apply(
        lambda y: CURRENT_YEAR - y if y else None
    )
    return df


def to_numeric_safe(series):
    return pd.to_numeric(series, errors="coerce")


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------

st.set_page_config(page_title="不動産価格チェッカー", layout="wide")

st.title("不動産価格チェッカー")
st.caption("データ出典: 不動産情報ライブラリ (国土交通省)")

if USE_DUMMY_DATA:
    st.info("APIキーが未設定のため、ダミーデータで表示しています。"
            "st.secrets に REINFOLIB_API_KEY を設定すると実データに切り替わります。")

with st.sidebar:
    st.header("検索条件")

    pref_name = st.selectbox("都道府県", list(PREFECTURES.keys()))
    pref_code = PREFECTURES[pref_name]

    with st.spinner("市区町村を読み込み中..."):
        cities = fetch_cities(pref_code)
    city_name = st.selectbox("市区町村", list(cities.keys()))
    city_code = cities.get(city_name)

    station_codes = load_station_codes()
    if station_codes:
        station_options = ["指定なし"] + sorted(station_codes.keys())
        station_name = st.selectbox(
            "最寄り駅(任意)",
            station_options,
            help="駅名を入力して絞り込めます",
        )
        station_code = station_codes.get(station_name) if station_name != "指定なし" else None
    else:
        st.text_input("最寄り駅(任意)", disabled=True,
                      help="station_codes.csvが見つかりません。convert_station_geojson.pyを実行してください。")
        station_code = None
    property_type = st.selectbox("種別", TYPE_OPTIONS)

    price_classification_label = st.selectbox("価格情報区分", list(PRICE_CLASSIFICATION_MAP.keys()))
    st.caption(
        "取引価格情報: 実際の売買取引価格(2005年〜) / "
        "成約価格情報: 仲介(レインズ)経由の成約価格(2021年〜、仲介市場の実勢に近い)"
    )

    st.subheader("取引時期")
    col1, col2 = st.columns(2)
    with col1:
        year_from = st.selectbox("年(from)", YEARS, index=max(0, len(YEARS) - 3))
        quarter_from = st.selectbox("四半期(from)", QUARTERS, index=0)
    with col2:
        year_to = st.selectbox("年(to)", YEARS, index=len(YEARS) - 1)
        quarter_to = st.selectbox("四半期(to)", QUARTERS, index=3)

    st.subheader("範囲指定")
    age_range = st.slider("築年数", 0, 50, (0, 50))
    area_range = st.slider("面積(㎡)", 0, 200, (0, 200))
    price_range = st.slider("取引価格(円)", 0, 200_000_000, (0, 200_000_000), step=1_000_000)

    search_clicked = st.button("価格を検索", type="primary", use_container_width=True)

# ----------------------------------------------------------------------
# データ取得 & フィルタ
# ----------------------------------------------------------------------

if search_clicked or USE_DUMMY_DATA:
    if USE_DUMMY_DATA:
        df = generate_dummy_data()
    else:
        df = fetch_transactions(
            area_code=pref_code,
            city_code=city_code,
            year_from=year_from,
            quarter_from=int(quarter_from),
            year_to=year_to,
            quarter_to=int(quarter_to),
            price_classification=PRICE_CLASSIFICATION_MAP[price_classification_label],
            station_code=station_code or None,
        )

    if df.empty:
        st.warning("条件に一致する取引データが見つかりませんでした。条件を変えて再検索してください。")
    else:
        df = add_building_age(df)
        df["TradePrice"] = to_numeric_safe(df["TradePrice"])
        df["Area"] = to_numeric_safe(df["Area"])
        df["UnitPrice"] = to_numeric_safe(df["UnitPrice"])
        df["PricePerUnit"] = to_numeric_safe(df["PricePerUnit"])

        # 範囲フィルタ
        filtered = df[
            (df["築年数"].fillna(-1).between(age_range[0], age_range[1]) | df["築年数"].isna())
            & (df["Area"].between(area_range[0], area_range[1]))
            & (df["TradePrice"].between(price_range[0], price_range[1]))
        ].copy()

        # ----------------------------------------------------------------
        # サマリー
        # ----------------------------------------------------------------
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("該当件数", f"{len(filtered)} 件")
        avg_price = filtered["TradePrice"].mean()
        col_b.metric("平均取引価格", f"¥{avg_price:,.0f}" if pd.notna(avg_price) else "—")
        col_c.metric("対象期間", f"{year_from}Q{quarter_from} 〜 {year_to}Q{quarter_to}")

        # ----------------------------------------------------------------
        # 取引一覧
        # ----------------------------------------------------------------
        st.subheader("取引一覧")

        # 並び替えコントロール
        sort_col1, sort_col2 = st.columns([2, 1])
        with sort_col1:
            sort_by = st.selectbox(
                "並び替え",
                ["取引価格", "築年数", "面積(㎡)", "取引時点"],
                label_visibility="collapsed",
            )
        with sort_col2:
            sort_order = st.radio(
                "順序",
                ["降順 ↓", "昇順 ↑"],
                horizontal=True,
                label_visibility="collapsed",
            )

        sort_col_map = {
            "取引価格": "TradePrice",
            "築年数": "築年数",
            "面積(㎡)": "Area",
            "取引時点": "Period",
        }
        sort_key = sort_col_map[sort_by]
        ascending = sort_order == "昇順 ↑"
        if sort_key in filtered.columns:
            filtered = filtered.sort_values(sort_key, ascending=ascending, na_position="last")

        display_cols = {
            "DistrictName": "地区",
            "Period": "取引時点",
            "BuildingYear": "築年",
            "築年数": "築年数",
            "FloorPlan": "間取り",
            "Area": "面積(㎡)",
            "TradePrice": "取引価格",
        }
        available_cols = [c for c in display_cols if c in filtered.columns]
        display_df = filtered[available_cols].rename(columns=display_cols)
        if "取引価格" in display_df.columns:
            display_df["取引価格"] = display_df["取引価格"].apply(
                lambda v: f"¥{v:,.0f}" if pd.notna(v) else "—"
            )
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )

        # ----------------------------------------------------------------
        # 取引時点別 平均単価の推移
        # ----------------------------------------------------------------
        st.subheader("取引時点別 平均単価の推移")
        if "Period" in filtered.columns:
            summary = (
                filtered.groupby("Period")
                .agg(
                    **{
                        "㎡単価(平均)": ("UnitPrice", "mean"),
                        "坪単価(平均)": ("PricePerUnit", "mean"),
                        "件数": ("TradePrice", "count"),
                    }
                )
                .reset_index()
            )
            # Period文字列(例: "2024年第1四半期")でソートできるよう、補助列を作る
            try:
                summary["_sort"] = summary["Period"].str.extract(r"(\d{4})年第(\d)四半期").apply(
                    lambda r: int(r[0]) * 10 + int(r[1]), axis=1
                )
                summary = summary.sort_values("_sort").drop(columns="_sort")
            except Exception:
                pass

            chart_df = summary.set_index("Period")[["㎡単価(平均)", "坪単価(平均)"]]
            st.line_chart(chart_df)

            st.dataframe(
                summary.style.format({
                    "㎡単価(平均)": "¥{:,.0f}",
                    "坪単価(平均)": "¥{:,.0f}",
                }),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("取引時点データがありません。")
else:
    st.caption("左の検索条件を設定して「価格を検索」を押してください。")
