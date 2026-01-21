import base64
import io
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from PIL import Image
from matplotlib import pyplot as plt
from numpy.ma.extras import row_stack
import plotly.graph_objects as go

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

# Funktion für deutsche Zahlendarstellung
def format_de(x, decimals=2):
    if pd.isna(x):
        return ""
    return f"{x:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")

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
    except Exception as e:
        print(f"Fehler beim Abrufen von {url}: {e}")
        return None

# ---------- ID_NOTATION extrahieren ----------
def get_id_notation(html: str):
    import re
    match = re.search(r"ID_NOTATION=(\d+)", html)
    id_notation = match.group(1) if match else None

    # 1️⃣ Datum extrahieren
    pattern = r'<td class="table__column--right" data-label="Datum">\s*(.*?)\s*</td>'
    matches1 = re.findall(pattern, html, re.DOTALL)

    # 2️⃣ data-label extrahieren
    pattern = r'<td class="table__column--top hidden-lg hidden-md table__column-mobile-toggle" data-label="(.*?)">'
    matches2 = re.findall(pattern, html, re.DOTALL)

    # 3️⃣ Index von Gettex
    # index_gettex = [...] or [0] → wenn „Gettex“ nicht gefunden wird, nehmen wir Index 0.
    index_gettex = [i for i, m in enumerate(matches2) if m.lower() == "gettex"] or [0]

    # 4️⃣ Wert aus matches1 an diesem Index
    index  = index_gettex[0]
    stand  = matches1[index] if matches1 else None
    boerse = matches2[index] if matches2 else None

    #print(stand)
    #print(matches1)
    #print(matches2)

    return id_notation, stand, boerse

# ---------- Chart laden ----------
def load_chart(isin, time_span, id_notation):
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
        except Exception as e:
            print(f"Fehler beim Kurs von {kurs_span}: {e}")
            aktueller_kurs = None

        if "stueck"   in info: stueck = info["stueck"]
        if "kaufwert" in info: kaufwert = info["kaufwert"]
        # Berechnen diff, prz
        if aktueller_kurs is not None:
            diff = stueck * aktueller_kurs - kaufwert
            prz  = (100 * diff / kaufwert) if kaufwert != 0 else 0
            # Leere Zellen / fehlende Werte → NaN
            # NaN ist ein float
            # datetime.strptime() erwartet str
            raw  = info["date"][0]
            if isinstance(raw, str):
              ziel = datetime.strptime(raw, "%d.%m.%Y")
              days = (datetime.today() - ziel).days
              diffJahr = diff * 365 / days
              przJahr  = prz * 365 / days
            else:
              diffJahr = None
              przJahr  = None

            info["kurs"].append(aktueller_kurs)
            info["date"].append(datetime.today().strftime("%d.%m.%Y"))
    whg = whg_span.get_text(strip=True) if whg_span else ""
    return aktueller_kurs, whg, diff, diffJahr, prz, przJahr

# ---------- Sparkline ----------
def sparkline(dates, values, aktueller_kurs, width=80, height=20, line_color="#1f77b4", mark_last=True):
    # Datum konvertieren
    dates = [pd.to_datetime(d, format="%d.%m.%Y") for d in dates]

    # Farbe
    if values[0]   < values[-1]: line_color = "green"
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

# Funktion, um Balken zu generieren
#.bar {display: inline-block;height: 100%;background-color: steelblue;width: 15%;  /* Breite des Balkens */margin: 0 2px;}
# steelblue #4682B4
# Firebrick #B22222
def create_bar_chart(i, data):
    min_val, max_val = min(data), max(data)
    bars = ''
    max_height = 65
    # am Ende muss background-color: stehen
    bar = "display:inline-block;width:10px;margin: 0 1px;vertical-align: bottom;background-color:"
    # Vorgänger
    vvalue = 0
    for value in data:
        # Berechne die Breite jedes Balkens basierend auf dem Wert
        width_percentage = (value - min_val) / (max_val - min_val)
        height = max_height * width_percentage
        tvalue = value if i==2 else value / 100
        delta  = value - vvalue
        prz    = 100 * delta / vvalue  if vvalue != 0 else 0
        #bars += f'<div class="bar" style="width:{width_percentage}%;"></div>'
        #bars += f'<div style="{bar}width:{width_percentage}%;">&nbsp;</div>'
        color  = "steelblue" if vvalue <=  value else "firebrick"
        bars  += (f'<div title="{value} ({format_de(delta,2)} {format_de(prz)}%)" style="{bar}{color};height:{height}px;">'
                  f'<span style="position:relative;font-size: 9px;top:-20px">{tvalue:.0f}</span>'
                  '</div>')
        vvalue = value
    return bars

# ---------- Kurse App ----------
def kurse():
  st.title("Kurse Edelmetalle")
  url = "https://www.gold.de/kurse/"
  html = load_page(url)
  soup = BeautifulSoup(html, "html.parser")
  section = soup.find("section", class_="sonstigetabelle nobord right-first-left google-anno-skip")

  # Finde alle td-Tags mit data-sparkline
  td_tags = soup.find_all('td', attrs={'data-sparkline': True})
  i  = 0
  for td in td_tags:
    # Extrahiere die Daten aus dem data-sparkline Attribut
    data = list(map(float, td['data-sparkline'].split(',')))
    i += 1
    bars = create_bar_chart(i,data)
    #td['class'] = 'sparkline'  # Stelle sicher, dass das td die richtige Klasse hat
    td['style'] = "white-space: nowrap;margin:1px"
    td.clear()  # Lösche den bisherigen Inhalt
    td.append(BeautifulSoup(bars, 'html.parser'))  # Füge die Balken hinzu

  st.markdown(section, unsafe_allow_html=True)

# ---------- Main App ----------
def main():
    # ---------- Kurse ----------
    kurse()

    # ---------- Fonds / Aktien Übersicht ----------
    fonds_mapping = load_fonds_mapping()
    st.set_page_config(layout="wide")
    st.title("Fonds / Aktien Übersicht")
    liste = []

    for isin, info in fonds_mapping.items():
        #print(isin)
        typ, url = get_product_type(isin)
        if not typ:
            st.markdown(f"<span style='color:red'>ISIN {isin} nicht gefunden</span>", unsafe_allow_html=True)
            continue

        html = load_page(url)
        if not html:
            st.markdown(f"<span style='color:red'>Fehler beim Laden: {isin}</span>", unsafe_allow_html=True)
            continue

        kurs, whg, diff, diffJahr, prz, przJahr = load_kurs(html, info)
        id_notation, stand, boerse  = get_id_notation(html)

        if isinstance(info["stueck"], float) and isinstance(info["kaufwert"], float) and isinstance(info["date"][0], str):
          # Farbe für Gewinn
          color = "green" if diff >= 0 else "red"

          svg = sparkline(info["date"], info["kurs"], kurs) if kurs else ""
          text = " | ".join([
            f"{d} ({format_de(k,2)})" for d, k in zip(info["date"], info["kurs"])
          ])

          st.markdown(
            f"## <div style='display: inline-block;white-space: nowrap;font-size: 22px'>"
            f"{info['name']} (<a href='{url}' target='_blank'>{isin}</a>) "
            f"<br><span style='font-size:17px;color:#555;font-weight: normal;'>"
            f"<b>Stand:</b>{stand} ({boerse}) &nbsp; &nbsp; <b>Diff:</b> <span style='color:{color}'>{format_de(diff,2)}</span> {whg} "
            f"({format_de(prz,2)}%) &nbsp; &nbsp; <b>Kurse:</b> {text}</span>{svg}</div>",
            unsafe_allow_html=True)

        else:
          st.markdown(
            f"## <div style='display: inline-block;white-space: nowrap;font-size: 22px'>"
            f"{info['name']} (<a href='{url}' target='_blank'>{isin}</a>) "
            f"<br><span style='font-size:17px;color:#555;font-weight: normal;'>"
            f"<b>Kurs:</b>{stand} ({boerse}) &nbsp; &nbsp; {format_de(kurs,2)} {whg}</span></div>",
            unsafe_allow_html = True)

        # Charts
        time_spans = [("10 Tage","10D"),("3 Monate","3M"),("6 Monate","6M"),("1 Jahr","1Y")]
        cols = st.columns(4)
        for col, (label, span) in zip(cols, time_spans):
            with col:
                st.caption(label)
                img = load_chart(isin, span, id_notation)
                if img:
                    st.image(img, use_container_width=True)

        st.divider()

        # Liste speichern, Diff/Prz für Tabelle farbig
        # Nie f"{wert:.2f}" beim Befüllen des DataFrames für Zahlen verwenden.
        # Stattdessen .format() oder .applymap() im Styler verwenden.
        liste.append([isin, url,
                      info['name'], diff, diffJahr, prz, przJahr,
                      info["date"][0] if len(info["date"]) >0 else None,
                      info["kurs"][0] if len(info["kurs"]) >0 else None,
                      info["date"][1] if len(info["date"]) >1 else None,
                      info["kurs"][1] if len(info["kurs"]) >1 else None,
                      info["date"][2] if len(info["date"]) >2 else None,
                      info["kurs"][2] if len(info["kurs"]) >2 else None
                     ])
    return liste

# ---------- Tabelle ----------
def liste_table(liste):
    if not liste: return
    df = pd.DataFrame(liste, columns=["ISIN","URL", "Name","Gewinn","Gewinn je Jahr","Prozent","Prozent je Jahr","Datum1","Kurs1","Datum2","Kurs2","Datum3","Kurs3"])

    # Farbe für Gewinn / Verlust in Tabelle
    def color_diff(val):
        v = to_float(val)
        color = 'green' if v > 0 else ('red' if v < 0 else '')
        return f'color: {color}; font-weight:bold'

    st.markdown("## Übersichtstabelle")

    # Ensure numeric type (important!), funktioniert nicht
    df["Gewinn"] = pd.to_numeric(df["Gewinn"], errors="coerce")

    df_sorted = df.sort_values(
      by="Gewinn",
      ascending=False,
      na_position="last"  # <-- das sorgt dafür, dass None/NaN am Ende stehen
    )

    # Style einmal mit dict für alle Spalten
    # Streamlit anzeigen mit deutschem Zahlenformat
    #df_sorted["URL"] = df_sorted.apply(
    #  lambda row: f"<a href=""{row['URL']}"" target='_blank'>{row['ISIN']}</a>", axis=1
    #)
    st.dataframe(
      df_sorted.style
      .format({
        "Gewinn":  lambda x: format_de(x, 0),          # keine Dezimalstellen
        "Gewinn je Jahr": lambda x: format_de(x, 0),   # 2 Dezimalstellen
        "Prozent": lambda x: format_de(x, 2),          # 2 Dezimalstellen
        "Prozent je Jahr": lambda x: format_de(x, 2),  # 2 Dezimalstellen
        "Kurs1":   lambda x: format_de(x, 2),
        "Kurs2":   lambda x: format_de(x, 2),
        "Kurs3":   lambda x: format_de(x, 2)
      })
      .applymap(color_diff, subset=["Gewinn"]),
      column_config = {
         "URL": None,  # <-- Spalte komplett versteckt
         #"URL": st.column_config.LinkColumn(
         #  label="Seite"
         #  #display_text=f"🔗 öffnen {row_stack}"
         #),
      },hide_index=True
    )
# ---------- App starten ----------
if __name__ == "__main__":
    l = main()
    liste_table(l)
