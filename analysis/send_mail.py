"""
analyze.py + gemini.py 결과를 받아 HTML 메일 발송
환경변수: GMAIL_USER, GMAIL_PASSWORD, MAIL_TO
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.image     import MIMEImage

KTB_COLS = ["국고1Y","국고2Y","국고3Y","국고5Y","국고10Y","국고20Y","국고30Y"]
CB_COLS  = ["AA공모1Y","AA공모2Y","AA공모3Y","AA공모5Y"]
SP_COLS  = ["spread_credit_3Y","spread_credit_5Y","spread_kt_10_3","spread_kt_30_10"]
SP_KO    = {
    "spread_credit_3Y": "신용스프레드 3Y",
    "spread_credit_5Y": "신용스프레드 5Y",
    "spread_kt_10_3":   "장단기 10-3Y",
    "spread_kt_30_10":  "장단기 30-10Y",
}


def _arrow(val):
    if val is None or val == 0: return "–"
    return f"▲{val:+.1f}" if val > 0 else f"▼{val:.1f}"


def _pct_bar(pct):
    """퍼센타일 시각화 바"""
    if pct is None: return ""
    filled = int(pct / 10)
    bar = "█" * filled + "░" * (10 - filled)
    color = "#c0392b" if pct >= 90 else ("#2980b9" if pct <= 10 else "#27ae60")
    return f'<span style="color:{color};font-family:monospace">{bar}</span> {pct:.0f}%'


def _row_color(d1):
    if d1 is None: return ""
    if d1 > 5:  return "background:#fff0f0"
    if d1 < -5: return "background:#f0f8ff"
    return ""


def _table_section(stats, cols, title, col_name_fn=None):
    col_name_fn = col_name_fn or (lambda c: c)
    rows_html = ""
    for col in cols:
        v = stats["columns"].get(col)
        if v is None: continue
        cur  = f"{v['current']}{v['unit']}" if v["current"] is not None else "–"
        d1   = _arrow(v["d1"])
        d5   = _arrow(v["d5"])
        ytd  = f"{v['ytd_high']} / {v['ytd_low']}" if v["ytd_high"] is not None else "–"
        r1y  = f"{v['r1y_high']} / {v['r1y_low']}" if v["r1y_high"] is not None else "–"
        ybar = _pct_bar(v["ytd_pct"])
        rbar = _pct_bar(v["r1y_pct"])
        rc   = _row_color(v["d1"])
        rows_html += f"""
        <tr style="{rc}">
          <td style="padding:6px 10px;font-weight:500">{col_name_fn(col)}</td>
          <td style="padding:6px 10px;text-align:right">{cur}</td>
          <td style="padding:6px 10px;text-align:right">{d1}</td>
          <td style="padding:6px 10px;text-align:right">{d5}</td>
          <td style="padding:6px 10px;text-align:right">{ytd}</td>
          <td style="padding:6px 10px">{ybar}</td>
          <td style="padding:6px 10px;text-align:right">{r1y}</td>
          <td style="padding:6px 10px">{rbar}</td>
        </tr>"""

    return f"""
    <h3 style="margin:20px 0 6px;color:#2c3e50">{title}</h3>
    <table style="border-collapse:collapse;width:100%;font-size:13px;background:#fff">
      <thead>
        <tr style="background:#34495e;color:#fff">
          <th style="padding:8px 10px;text-align:left">종목</th>
          <th style="padding:8px 10px">현재</th>
          <th style="padding:8px 10px">전일대비</th>
          <th style="padding:8px 10px">전주대비</th>
          <th style="padding:8px 10px">YTD 고/저</th>
          <th style="padding:8px 10px">YTD 퍼센타일</th>
          <th style="padding:8px 10px">1Y 고/저</th>
          <th style="padding:8px 10px">1Y 퍼센타일</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>"""


def build_html(stats: dict, gemini: dict) -> str:
    date = stats["date"]
    notable = gemini.get("notable", False)

    # 헤드라인: 국고10Y 현재값 + 전일대비
    ktb10 = stats["columns"].get("국고10Y", {})
    cur10 = ktb10.get("current")
    d1_10 = ktb10.get("d1")
    subject_suffix = ""
    if cur10 is not None and d1_10 is not None:
        subject_suffix = f"국고10Y {cur10}% ({_arrow(d1_10)}bp)"

    flag = "⚠️ 이상변동 감지" if notable else "✅ 정상범위"

    # 헤드라인 요약 (주요 3개)
    headlines = []
    for col in ["국고3Y", "국고10Y", "spread_kt_10_3", "spread_credit_3Y"]:
        v = stats["columns"].get(col)
        if v and v["current"] is not None:
            headlines.append(
                f"<b>{col}</b>: {v['current']}{v['unit']} ({_arrow(v['d1'])}bp 전일대비)"
            )

    headline_html = " &nbsp;|&nbsp; ".join(headlines[:4])

    # Gemini 코멘트 섹션
    comment_section = ""
    if notable and gemini.get("comment"):
        comment_section = f"""
        <div style="background:#fef9e7;border-left:4px solid #f39c12;padding:14px 16px;margin:18px 0;border-radius:4px">
          <b style="color:#d68910">📌 AI 분석 코멘트</b>
          <p style="margin:8px 0 0;line-height:1.7;color:#2c3e50">{gemini['comment'].replace(chr(10),'<br>')}</p>
        </div>"""

    # 테이블
    ktb_table = _table_section(stats, KTB_COLS, "국고채")
    cb_table  = _table_section(stats, CB_COLS,  "공모AA")
    sp_table  = _table_section(stats, SP_COLS,  "스프레드", col_name_fn=lambda c: SP_KO.get(c, c))

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:'Noto Sans KR',Arial,sans-serif;max-width:900px;margin:0 auto;padding:20px;color:#2c3e50">

  <div style="background:#2c3e50;color:#fff;padding:16px 20px;border-radius:6px 6px 0 0">
    <h2 style="margin:0">📊 금리 일간 브리핑</h2>
    <p style="margin:4px 0 0;opacity:.8">{date} &nbsp;|&nbsp; {subject_suffix}</p>
  </div>

  <div style="background:#ecf0f1;padding:12px 20px;border-radius:0 0 6px 6px;margin-bottom:16px">
    <span style="font-size:15px">{flag} &nbsp;&nbsp; {headline_html}</span>
  </div>

  {comment_section}

  {ktb_table}
  {cb_table}
  {sp_table}

  <div style="margin-top:24px">
    <h3 style="color:#2c3e50">추이 차트 (최근 60일)</h3>
    <img src="cid:chart" style="width:100%;border:1px solid #ddd;border-radius:4px">
  </div>

  <p style="margin-top:24px;font-size:11px;color:#999">
    본 메일은 GitHub Actions + KOFIA 데이터 기반으로 자동 생성됩니다.
    YTD 기준선: 점선(최고) / 점선(최저)
  </p>
</body></html>"""


def send(stats: dict, gemini: dict, chart_path: str):
    user = os.environ.get("GMAIL_USER")
    pw   = os.environ.get("GMAIL_PASSWORD")
    to   = os.environ.get("MAIL_TO")
    if not all([user, pw, to]):
        raise ValueError("[send_mail] 환경변수 누락 — GMAIL_USER / GMAIL_PASSWORD / MAIL_TO 확인")
    date    = stats["date"]

    ktb10  = stats["columns"].get("국고10Y", {})
    cur10  = ktb10.get("current")
    d1_10  = ktb10.get("d1")
    flag   = "⚠️" if gemini.get("notable") else "✅"
    suffix = f" | 국고10Y {cur10}% ({_arrow(d1_10)}bp)" if cur10 else ""
    subject = f"{flag} 금리 브리핑 {date}{suffix}"

    html = build_html(stats, gemini)

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"]    = user
    msg["To"]      = to

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alt)

    with open(chart_path, "rb") as f:
        img = MIMEImage(f.read(), _subtype="png")
        img.add_header("Content-ID", "<chart>")
        img.add_header("Content-Disposition", "inline", filename="chart.png")
        msg.attach(img)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.sendmail(user, to, msg.as_string())

    print(f"[send_mail] 발송 완료 → {to}")


if __name__ == "__main__":
    # 단독 테스트 (analyze + gemini 결과 필요)
    print("send_mail.py — analyze.py, gemini.py 와 함께 main.py 로 실행하세요")
