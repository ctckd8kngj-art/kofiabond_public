"""
kofia_history.csv 읽어서
- 통계 계산 (전일/전주대비, YTD/Rolling 고저 퍼센타일)
- 차트 이미지 생성 (최근 60일)
결과를 dict 로 반환
"""
import os
import io
import base64
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib import rcParams

rcParams["font.family"] = "DejaVu Sans"

CSV_PATH   = os.path.join(os.path.dirname(__file__), "data", "kofia_history.csv")
CHART_PATH = os.path.join(os.path.dirname(__file__), "data", "chart.png")

KTB_COLS = ["국고1Y","국고2Y","국고3Y","국고5Y","국고10Y","국고20Y","국고30Y"]
CB_COLS  = ["AA공모1Y","AA공모2Y","AA공모3Y","AA공모5Y"]
SP_COLS  = ["spread_credit_3Y","spread_credit_5Y","spread_kt_10_3","spread_kt_30_10"]
SP_LABELS = {
    "spread_credit_3Y": "Credit 3Y (bp)",
    "spread_credit_5Y": "Credit 5Y (bp)",
    "spread_kt_10_3":   "KTB 10-3Y (bp)",
    "spread_kt_30_10":  "KTB 30-10Y (bp)",
}


def load() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)


def pct_rank(series: pd.Series, value) -> float:
    valid = series.dropna()
    if len(valid) == 0 or pd.isna(value):
        return np.nan
    return round((valid < value).sum() / len(valid) * 100, 1)


def calc_stats(df: pd.DataFrame) -> dict:
    today      = df.iloc[-1]
    date_str   = today["date"].strftime("%Y-%m-%d")
    year_start = pd.Timestamp(f"{today['date'].year}-01-01")
    one_yr_ago = today["date"] - pd.DateOffset(years=1)

    cols = [c for c in KTB_COLS + CB_COLS + SP_COLS if c in df.columns]
    result = {"date": date_str, "columns": {}}

    def chg(a, b, is_spread):
        if pd.isna(a) or pd.isna(b): return np.nan
        delta = (a - b) * (1 if is_spread else 100)
        return round(float(delta), 1)

    for col in cols:
        cur   = today[col]
        is_sp = col in SP_COLS
        prev1 = df.iloc[-2][col] if len(df) >= 2 else np.nan
        prev5 = df.iloc[-6][col] if len(df) >= 6 else np.nan

        ytd  = df[df["date"] >= year_start][col]
        r1y  = df[df["date"] >= one_yr_ago][col]

        result["columns"][col] = {
            "current":  round(float(cur), 3) if not pd.isna(cur) else None,
            "unit":     "bp" if is_sp else "%",
            "d1":       chg(cur, prev1, is_sp),
            "d5":       chg(cur, prev5, is_sp),
            "ytd_high": round(float(ytd.max()), 3) if not pd.isna(ytd.max()) else None,
            "ytd_low":  round(float(ytd.min()), 3) if not pd.isna(ytd.min()) else None,
            "ytd_pct":  pct_rank(ytd, cur),
            "r1y_high": round(float(r1y.max()), 3) if not pd.isna(r1y.max()) else None,
            "r1y_low":  round(float(r1y.min()), 3) if not pd.isna(r1y.min()) else None,
            "r1y_pct":  pct_rank(r1y, cur),
        }
    return result


def make_chart(df: pd.DataFrame) -> str:
    recent = df.tail(60).copy()
    cur_year = recent["date"].iloc[-1].year

    fig, axes = plt.subplots(3, 1, figsize=(12, 14), facecolor="#f8f9fa")
    fig.suptitle("KOFIA 금리 추이 (최근 60일)", fontsize=14, fontweight="bold", y=0.98)

    def add_ytd_lines(ax, col, color):
        ytd = df[df["date"].dt.year == cur_year][col].dropna()
        if ytd.empty: return
        ax.axhline(ytd.max(), color=color, linewidth=0.6, linestyle="--", alpha=0.45)
        ax.axhline(ytd.min(), color=color, linewidth=0.6, linestyle=":",  alpha=0.45)

    # 국고채
    ax1, colors1 = axes[0], ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b","#e377c2"]
    for col, c in zip(["국고1Y","국고2Y","국고3Y","국고5Y","국고10Y","국고20Y","국고30Y"], colors1):
        if col in recent.columns:
            ax1.plot(recent["date"], recent[col], label=col, color=c, linewidth=1.5)
            add_ytd_lines(ax1, col, c)
    ax1.set_title("국고채 수익률 (%)", fontsize=11)
    ax1.legend(loc="upper left", fontsize=8, ncol=3)
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))

    # 공모AA
    ax2, colors2 = axes[1], ["#1f77b4","#ff7f0e","#2ca02c","#d62728"]
    for col, c in zip(CB_COLS, colors2):
        if col in recent.columns:
            ax2.plot(recent["date"], recent[col], label=col, color=c, linewidth=1.5)
            add_ytd_lines(ax2, col, c)
    ax2.set_title("공모AA 수익률 (%)", fontsize=11)
    ax2.legend(loc="upper left", fontsize=8, ncol=2)
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))

    # 스프레드
    ax3, colors3 = axes[2], ["#e41a1c","#377eb8","#4daf4a","#984ea3"]
    for col, c in zip(SP_COLS, colors3):
        if col in recent.columns:
            ax3.plot(recent["date"], recent[col], label=SP_LABELS[col], color=c, linewidth=1.5)
    ax3.set_title("스프레드 (bp)", fontsize=11)
    ax3.legend(loc="upper left", fontsize=8, ncol=2)
    ax3.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))

    for ax in axes:
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis="x", rotation=30, labelsize=8)
        ax.tick_params(axis="y", labelsize=9)
        ax.set_facecolor("white")

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    os.makedirs(os.path.dirname(CHART_PATH), exist_ok=True)
    fig.savefig(CHART_PATH, dpi=150, bbox_inches="tight")
    plt.close(fig)

    with open(CHART_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()


def run() -> dict:
    df = load()
    return {
        "stats":      calc_stats(df),
        "chart_b64":  make_chart(df),
        "chart_path": CHART_PATH,
    }


if __name__ == "__main__":
    r = run()
    print("date:", r["stats"]["date"])
    for col, v in r["stats"]["columns"].items():
        d1 = v["d1"]
        print(f"  {col}: {v['current']} {v['unit']}  전일{d1:+.1f}  YTD pct {v['ytd_pct']}")
