"""
crawler.py 실행 후 kofia.xlsx → analysis/data/kofia_history.csv 에 append
daily.yml 에서 크롤링 직후 호출
"""
import os
import sys
import pandas as pd
import numpy as np

XLSX_PATH = os.path.join(os.path.dirname(__file__), "..", "crawler", "kofia.xlsx")
CSV_PATH  = os.path.join(os.path.dirname(__file__), "data", "kofia_history.csv")

KTB_TENORS = ["1", "2", "3", "5", "10", "20", "30"]
CB_GRADES  = {"AA+", "AA0", "AA-", "AA"}
CB_TENORS  = ["1", "2", "3", "5"]


def extract_row(df: pd.DataFrame) -> dict | None:
    if df.empty:
        return None

    date = pd.to_datetime(df["date"].iloc[0]).strftime("%Y-%m-%d")
    row: dict = {"date": date}

    ktb = df[(df["largeCategoryMrk"] == "국채") &
             (df["typeNmMrk"]        == "국고채권")]
    for t in KTB_TENORS:
        val = ktb[t].mean() if not ktb.empty and t in ktb.columns else np.nan
        row[f"국고{t}Y"] = round(float(val), 3) if not pd.isna(val) else np.nan

    cb = df[(df["largeCategoryMrk"] == "회사채 I(공모사채)") &
            (df["typeNmMrk"]        == "무보증") &
            (df["creditRnkMrk"].isin(CB_GRADES))]
    for t in CB_TENORS:
        val = cb[t].mean() if not cb.empty and t in cb.columns else np.nan
        row[f"AA공모{t}Y"] = round(float(val), 3) if not pd.isna(val) else np.nan

    def sp(a, b):
        if pd.isna(a) or pd.isna(b):
            return np.nan
        return round((a - b) * 100, 1)

    row["spread_credit_3Y"] = sp(row.get("AA공모3Y"), row.get("국고3Y"))
    row["spread_credit_5Y"] = sp(row.get("AA공모5Y"), row.get("국고5Y"))
    row["spread_kt_10_3"]   = sp(row.get("국고10Y"),  row.get("국고3Y"))
    row["spread_kt_30_10"]  = sp(row.get("국고30Y"),  row.get("국고10Y"))

    return row


def main():
    if not os.path.exists(XLSX_PATH):
        print(f"[build_csv] xlsx 없음 — 스킵")
        sys.exit(0)

    raw = pd.read_excel(XLSX_PATH)
    row = extract_row(raw)
    if row is None:
        print("[build_csv] 유효 데이터 없음 — 스킵")
        sys.exit(0)

    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    new_df = pd.DataFrame([row])

    if os.path.exists(CSV_PATH):
        hist = pd.read_csv(CSV_PATH)
        hist = hist[hist["date"] != row["date"]]
        hist = pd.concat([hist, new_df], ignore_index=True)
    else:
        hist = new_df

    hist = hist.sort_values("date").reset_index(drop=True)
    hist.to_csv(CSV_PATH, index=False)
    print(f"[build_csv] {row['date']} 저장 완료 ({len(hist)}행)")


if __name__ == "__main__":
    main()
