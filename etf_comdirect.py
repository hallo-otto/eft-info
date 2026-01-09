# pip install playwright pandas matplotlib
# playwright install
#pip install requests beautifulsoup4 pillow streamlit
#https://www.comdirect.de/inf/fonds/LI1381606980?CIF_Check=true
#https://charts.comdirect.de/charts/rebrush/design_small.ewf.chart?DENSITY=2&ID_NOTATION=486784471&TIME_SPAN=10D&TYPE=MOUNTAIN&WIDTH=800&HEIGHT=400
#https://charts.comdirect.de/charts/rebrush/design_small.ewf.chart?DENSITY=2&ID_NOTATION=486784471&TIME_SPAN=3M&TYPE=MOUNTAIN&WIDTH=800&HEIGHT=400

import base64
from urllib.parse import parse_qs, urlparse

import streamlit as st
import requests
import pandas as pd
import io
import re
from datetime import datetime
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import html

from fontTools.unicodedata import block
from matplotlib import pyplot as plt

HEADERS = {"User-Agent": "Mozilla/5.0"}
# --- Mapping ISIN → {Name, ID_NOTATION} --- 506766981
fonds_mapping = {"LI1381606980": {"name": "PI Physical Gold Fund",   "ST":40, "CHF": 5509.37 , "EUR": 5940.91 , "date":["03.11.25", "07.01.26"], "kurs":[132.91, 142.55]},
                 "LI1439616825": {"name": "PI Physical Silver Fund", "ST":46, "CHF": 7654.12 , "EUR": 8252.73 , "date":["03.11.25", "07.01.26"], "kurs":[128.43, 195.59]},
                 "LU2611732046": {"name": "Amundi Core DAX - UCITS ETF"},
                 "IE00BM67HT60": {"name": "Xtrackers MSCI World"},
                 "IE00B43HR379": {"name": "iShares S&P 500 Health"},
                 "LU0323578657": {"name": "Flossbach von Storch"},
}

# --- HTML einmal laden pro ISIN ---
def load_fonds_page(isin: str) -> str:
    url = f"https://www.comdirect.de/inf/fonds/{isin}"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return res.text

# Ermitteln der id_notation
# id_notation ist nicht konstant, wird aus der Html Seite ermittelt
def get_id_notation(html: str) -> str:
  # ID_NOTATION per Regex suchen
  match = re.search(r"ID_NOTATION=(\d+)", html)
  if match:
    #print(match.group(1))
    return match.group(1)
  else:
    raise ValueError("ID_NOTATION nicht gefunden")

# --- Funktion: Chart laden ---
def load_chart(isin, time_span, html):
  """
  Lädt das Chart-Bild für eine ISIN und Zeitraum.
  time_span: "10D", "3M", "6M" etc.
  """
  info = fonds_mapping.get(isin)
  if not info:
    raise ValueError(f"ISIN {isin} nicht im Mapping gefunden")

  id_notation=get_id_notation(html)
  #print(id_notation)

  # charts
  url = (
    f"https://charts.comdirect.de/charts/rebrush/design_small.ewf.chart"
    f"?DENSITY=2"
    f"&ID_NOTATION={id_notation}"
    f"&TIME_SPAN={time_span}"
    f"&TYPE=MOUNTAIN"
    f"&WIDTH=800"
    f"&HEIGHT=400"
  )

  r = requests.get(url, headers=HEADERS)
  r.raise_for_status()

  return Image.open(BytesIO(r.content))

# --- Funktion: Chart laden ---
def load_kurs(html,info):
  # kurs
  soup = BeautifulSoup(html, "html.parser")

  # Aktueller Kurs                            text-size--xxlarge text-weight--medium
  kurs_span = soup.find("span", class_="text-size--xxlarge text-weight--medium")
  whg_span = soup.find("span", class_="text-size--medium outer-spacing--small-top")
  #print(isin)
  #print(kurs_span)
  aktueller_kurs = None
  st,chf,diff,prz,whg = 0,0,0,0,""
  if kurs_span:
    aktueller_kurs = kurs_span.get_text(strip=True)

    if "ST"  in info : st  = info["ST"]
    if "CHF" in info : chf = info["CHF"]
    diff = st * float(aktueller_kurs) - chf
    if chf!=0: prz  = (100 * diff / chf)
    #print("Aktueller Kurs:", aktueller_kurs)
  else:
    print("Kurs nicht gefunden")
  if whg_span:
    whg = whg_span.get_text(strip=True)
  else:
    whg = ""

  return aktueller_kurs, whg, f"{diff:,.0f}CHF", f"{prz:,.2f}%"

# Sparline
def sparkline(xdates, kurs, aktueller_kurs, width=80, height=20, line_color="#1f77b4", mark_last=True):
  """
  Erzeugt eine Mini-Sparkline als SVG Base64 für Streamlit.

  - xdates: Liste von Datumsstrings im Format 'dd.mm.yy'
  - kurs: Liste von Kurswerten
  - aktueller_kurs: letzter Kurswert
  - width, height: Größe der Mini-Sparkline in Pixel
  - line_color: Farbe der Linie
  - mark_last: ob der letzte Punkt markiert werden soll
  """
  # Konvertiere Datum
  dates = [pd.to_datetime(d, format="%d.%m.%y") for d in xdates]
  dates.append(datetime.today())

  # Werte kopieren, um Original-Liste nicht zu ändern
  values = kurs.copy()
  values.append(float(aktueller_kurs))

  # Trendfarbe bestimmen
  if values[-1] > values[-2]:
        color = "green"
  elif values[-1] < values[-2]:
        color = "red"
  else:
        color = "#1f77b4"  # neutral/Blau

  # Mini-Chart erzeugen
  fig, ax = plt.subplots(figsize=(width / 80, height / 80))
  ax.plot(dates, values, linewidth=1.1, color=line_color)

  # Optional letzten Punkt markieren
  if mark_last:
    ax.scatter(dates[-1], values[-1], s=10, color=line_color, zorder=5)

  ax.axis('off')
  plt.tight_layout(pad=0)

  # SVG in Base64 kodieren
  buf = io.BytesIO()
  fig.savefig(buf, format="svg", bbox_inches='tight')
  plt.close(fig)
  svg_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

  # Inline HTML für Streamlit
  svg_inline = f'<object data="data:image/svg+xml;base64,{svg_base64}" type="image/svg+xml" ' \
               f'style="display:inline-block; vertical-align:middle; width:{width}px; height:{height}px; margin:0; padding:0"></object>'

  return svg_inline

# --- Streamlit-App ---
st.set_page_config(layout="wide")
st.title("Fonds-Übersicht")

isins = list(fonds_mapping.keys())
time_spans = [("10 Tage", "10D"), ("3 Monate", "3M"), ("6 Monate", "6M"), ("1 Jahr", "1Y")]

for isin in isins:
  info = fonds_mapping[isin]
  # html Seite nur einmal laden
  html = load_fonds_page(isin)

  kurs, whg, diff, prz = load_kurs(html,info)
  #print(info["kurs"])

  if "date" in info:
    text  = f"{info["date"][0]} ({info["kurs"][0]})"
    text += f"&nbsp;&nbsp; {info["date"][1]} ({info["kurs"][1]})"
    svg   = sparkline(info["date"], info["kurs"], kurs)
    st.markdown(f"## <div style='display: inline-block;white-space: nowrap;font-size: 22px'>{info['name']} (<a target='_blank' href='https://www.comdirect.de/inf/fonds/{isin}'>{isin}</a>) <span style='margin-left:10px;color: #888; font-size: 17px;'>Kurs: {kurs}{whg}{svg}Diff: {diff} ({prz})  &nbsp;&nbsp;&nbsp; Info: {text}</span></div>", unsafe_allow_html=True)
  else:
    st.markdown(f"## <div style='display: inline-block;white-space: nowrap;font-size: 22px'>{info['name']} (<a target='_blank' href='https://www.comdirect.de/inf/fonds/{isin}'>{isin}</a>) <span style='margin-left:10px;color: #888; font-size: 17px;'>Kurs: {kurs}{whg}</span></div>", unsafe_allow_html=True)

  # 4 Charts nebeneinander
  cols = st.columns(4)
  for col, (label, span) in zip(cols, time_spans):
    with col:
      st.caption(label)
      img = load_chart(isin, span, html)
      st.image(img, use_container_width=True)

  st.divider()
