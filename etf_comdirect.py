# pip install playwright pandas matplotlib
# playwright install
#pip install requests beautifulsoup4 pillow streamlit
#https://www.comdirect.de/inf/fonds/LI1381606980?CIF_Check=true
#https://charts.comdirect.de/charts/rebrush/design_small.ewf.chart?DENSITY=2&ID_NOTATION=486784471&TIME_SPAN=10D&TYPE=MOUNTAIN&WIDTH=800&HEIGHT=400
#https://charts.comdirect.de/charts/rebrush/design_small.ewf.chart?DENSITY=2&ID_NOTATION=486784471&TIME_SPAN=3M&TYPE=MOUNTAIN&WIDTH=800&HEIGHT=400
import base64
import io
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from PIL import Image
from matplotlib import pyplot as plt

# ---------- HEADERS ----------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
    "Referer": "https://www.comdirect.de/"
}

# ---------- Fonds / Aktien Mapping ----------
fonds_mapping = {}

# ---------- Daten aus Google Sheet laden ----------
def to_float(value):
  if value is None:
     return 0.0
  return float(str(value).replace(".", "").replace(",", "."))

def load_fonds_mapping():
    SHEET_ID = "2PACX-1vQVWRS2FvPXn8JMnACaMeb4BRPGTdwrLQhl5K2-Y3Q1pkMoLNmrl3oKBjfkI2ceT0FYhu41MkA2x0Hk"
    url = f"https://docs.google.com/spreadsheets/d/e/{SHEET_ID}/pub?gid=0&single=true&output=csv"
    url_nocache = f"{url}&t={int(datetime.today().timestamp())}"
    # https://docs.google.com/spreadsheets/d/e/2PACX-1vQVWRS2FvPXn8JMnACaMeb4BRPGTdwrLQhl5K2-Y3Q1pkMoLNmrl3oKBjfkI2ceT0FYhu41MkA2x0Hk/pub?gid=0&single=true&output=csv

    #print("Lade Google Sheet von:")
    #print(url_nocache)

    df = pd.read_csv(url_nocache)

    #print("\n--- Rohdaten aus Google Sheet ---")
    #print(df)
    mapping = {}
    for _, row in df.iterrows():
      kz = row["KZ"]
      if kz != "ok": continue
      isin = str(row["ISIN"]).strip()
      try:
         mapping[isin] = {
          "name": row["Name"],
          "stueck": to_float(row.get("Stueck", None)),
          "kaufwert": to_float(row.get("Kaufwert")),
          "date": [row.get("Datum1", ""), row.get("Datum2", "")],
          "kurs": [to_float(row.get("Kurs1")), to_float(row.get("Kurs2"))],
          "EUR":  to_float(row.get("EUR"))
         }
      except (TypeError, ValueError):
         print("Error", row, TypeError, ValueError)

    return mapping

# ---------- Prüfen ob Fonds oder Aktie und html laden Html----------
def get_product_type(isin):
    url_fonds = f"https://www.comdirect.de/inf/fonds/{isin}"
    try:
        r = requests.get(url_fonds, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return "fonds", url_fonds
        url_aktie = f"https://www.comdirect.de/inf/aktien/{isin}"
        r2 = requests.get(url_aktie, headers=HEADERS, timeout=10)
        if r2.status_code == 200:
            return "aktie", url_aktie
    except requests.RequestException:
        pass
    return None, None

# ---------- HTML laden ----------
def load_page(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.text
    except:
        return None

# ---------- ID_NOTATION extrahieren ----------
def get_id_notation(html: str):
    import re
    match = re.search(r"ID_NOTATION=(\d+)", html)
    if match:
        return match.group(1)
    return None

# ---------- Chart laden ----------
def load_chart(isin, time_span, html):
    id_notation = get_id_notation(html)
    if not id_notation:
        return None
    url = (
        f"https://charts.comdirect.de/charts/rebrush/design_small.ewf.chart"
        f"?DENSITY=2"
        f"&ID_NOTATION={id_notation}"
        f"&TIME_SPAN={time_span}"
        f"&TYPE=MOUNTAIN"
        f"&WIDTH=800"
        f"&HEIGHT=400"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content))
    except:
        return None

# ---------- Kurs extrahieren ----------
def load_kurs(html, info):
    soup = BeautifulSoup(html, "html.parser")

    # Fonds / Standard
    kurs_span = soup.find("span", class_="text-size--xxlarge text-weight--medium")
    if not kurs_span:
        kurs_span = soup.find("span", class_="realtime-indicator--value")
    if not kurs_span:
        # Alternative für Aktien (z.B. BMW)
        kurs_span = soup.find("fin-streamer", {"data-field":"regularMarketPrice"})

    whg_span = soup.find("span", class_="text-size--medium outer-spacing--small-top")

    aktueller_kurs = None
    stueck, kaufwert, diff, prz, whg = 0, 0, 0, 0, ""
    if kurs_span:
        try:
            aktueller_kurs = float(kurs_span.get_text(strip=True).replace(",", "."))
        except:
            aktueller_kurs = None
        if "stueck"   in info: stueck = info["stueck"]
        if "kaufwert" in info: kaufwert = info["kaufwert"]
        # Berechnen diff, prz
        if aktueller_kurs is not None:
            diff = stueck * aktueller_kurs - kaufwert
            prz = (100 * diff / kaufwert) if kaufwert != 0 else 0
            info["kurs"].append(aktueller_kurs)
            info["date"].append(datetime.today().strftime("%d.%m.%Y"))
    whg = whg_span.get_text(strip=True) if whg_span else ""
    return aktueller_kurs, whg, diff, prz

# ---------- Sparkline ----------
def sparkline(dates, values, aktueller_kurs, width=80, height=20, line_color="#1f77b4", mark_last=True):
    # Datum konvertieren
    dates = [pd.to_datetime(d, format="%d.%m.%Y") for d in dates]

    # Farbe
    if values[0] < values[-1]: line_color = "green"
    elif values[0] > values[-1]: line_color = "red"

    # Grafik
    fig, ax = plt.subplots(figsize=(width/80, height/80))
    ax.plot(dates, values, linewidth=1.1, color=line_color)

    if mark_last:
        ax.scatter(dates[-1], values[-1], s=10, color=line_color, zorder=5)
    ax.axis('off')
    plt.tight_layout(pad=0)
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches='tight')
    plt.close(fig)

    svg_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f'<object data="data:image/svg+xml;base64,{svg_base64}" type="image/svg+xml" style="width:{width}px; height:{height}px"></object>'

# ---------- Main App ----------
def main():
    fonds_mapping = load_fonds_mapping()
    st.set_page_config(layout="wide")
    st.title("Fonds / Aktien Übersicht")
    liste = []

    for isin, info in fonds_mapping.items():
        typ, url = get_product_type(isin)
        if not typ:
            st.markdown(f"<span style='color:red'>ISIN {isin} nicht gefunden</span>", unsafe_allow_html=True)
            continue

        html = load_page(url)
        if not html:
            st.markdown(f"<span style='color:red'>Fehler beim Laden: {isin}</span>", unsafe_allow_html=True)
            continue

        kurs, whg, diff, prz = load_kurs(html, info)

        if isinstance(info["stueck"], float) and isinstance(info["kaufwert"], float) and isinstance(info["date"][0], str):
          # Farbe für Gewinn
          color = "green" if diff >= 0 else "red"

          svg = sparkline(info["date"], info["kurs"], kurs) if kurs else ""
          text = " | ".join([
            f"{d} ({k:.2f})" for d, k in zip(info["date"], info["kurs"])
          ])

          st.markdown(
            f"## {info['name']} (<a href='{url}' target='_blank'>{isin}</a>) "
            f"<span style='font-size:20px;color:#555'>"
            f"Diff: <span style='color:{color}; font-weight:bold'>{diff:.2f}</span>{whg} "
            f"({prz:.2f}%) | Kurse: {text}</span>{svg}",
            unsafe_allow_html=True)

        else:
          st.markdown(
            f"## {info['name']} (<a href='{url}' target='_blank'>{isin}</a>) "
            f"<span style='font-size:20px;color:#555'>"
            f"Kurs {whg}: <span style='font-weight:bold'>{kurs:,.2f}</span>",
            unsafe_allow_html = True)

        # Charts
        time_spans = [("10 Tage","10D"),("3 Monate","3M"),("6 Monate","6M"),("1 Jahr","1Y")]
        cols = st.columns(4)
        for col, (label, span) in zip(cols, time_spans):
            with col:
                st.caption(label)
                img = load_chart(isin, span, html)
                if img:
                    st.image(img, use_container_width=True)

        st.divider()

        # Liste speichern, Diff/Prz für Tabelle farbig
        liste.append([isin,
                      info['name'], f"{diff:.0f}", f"{prz:.2f}",
                      info["date"][0] if len(info["date"])>0 else None,
                      f"{info["kurs"][0]:.2f}" if len(info["kurs"]) > 0 else None,
                      info["date"][1] if len(info["date"])>1 else None,
                      f"{info["kurs"][1]:.2f}" if len(info["kurs"]) >1 else None,
                      info["date"][2] if len(info["date"])>2 else None,
                      f"{info["kurs"][2]:.2f}" if len(info["kurs"])>2 else None
                     ])
    return liste

# ---------- Tabelle ----------
def liste_table(liste):
    if not liste: return
    df = pd.DataFrame(liste, columns=["ISIN","Name","Gewinn","Prozent","Datum1","Kurs1","Datum2","Kurs2","Datum3","Kurs3"])

    # Farbe für Gewinn / Verlust in Tabelle
    def color_diff(val):
        v = to_float(val)
        color = 'green' if v > 0 else ('red' if v < 0 else '')
        return f'color: {color}; font-weight:bold'

    st.markdown("## Übersichtstabelle")
    st.dataframe(df.style.applymap(color_diff, subset=["Gewinn"]))

# ---------- App starten ----------
if __name__ == "__main__":
    l = main()
    liste_table(l)
