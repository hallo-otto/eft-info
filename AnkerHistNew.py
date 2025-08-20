import asyncio

from aiohttp import ClientSession
from api.api import AnkerSolixApi
import streamlit as st
from datetime import date, datetime, timedelta
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import math
from matplotlib.widgets import CheckButtons
from tornado.options import options


# @st.cache_resource

class AnkerSolixInfo:
  def __init__(self, user, pw, country, numdays, session):
    self.user = user
    self.pw = pw
    self.country = country
    self.numdays = numdays
    self.session = session
    self.data = []
    self.ph1 = st.empty()
    self.ph2 = st.empty()
    self.ph3 = st.empty()
    self.api = AnkerSolixApi(user, pw, country, session)  # einmalig speichern

  async def update_sites(self):
    # Beispiel: await irgendwas mit self.session
    # Du hast zu viele Anfragen in kurzer Zeit gesendet. Die API hat dich mit HTTP-Status 429 blockiert.
    await asyncio.sleep(1)  # Dummy async call
    await self.api.update_sites()
    await self.api.update_device_details()
    await self.api.update_device_energy()

    xitem = self.api.sites.items()
    items = list(xitem)
    if items:
      site, site_data = items[0]
      await self.hist(site_data)
      self.api.sites.clear()
    else:
       st.warning("Keine Standorte verfügbar.")
       #print("Keine Standorte verfügbar.")

  async def hist(self, site_data):
      # Historische Daten
      siteId    = site_data.get("site_id")
      #devices   = list(self.api.devices)
      #deviceSn1 = devices[0]
      #deviceSn2 = devices[1]
      numDays   = self.numdays

      # Datumsbereich
      endDay    = (date.today() - timedelta(days=1))
      startDay  = (endDay     - timedelta(days=numDays-1))
      if startDay < date(2025, 7, 11):
         startDay = date(2025, 7, 11)

      endDay   = datetime(endDay.year,endDay.month,endDay.day)
      startDay = datetime(startDay.year,startDay.month,startDay.day)
      #data = await self.api.energy_analysis(siteId=siteId, deviceSn="", rangeType="week", startDay=startDay, endDay=endDay,  devType="")
      #print(data)

      # "device_type": ["solar_production", "solarbank", "home_usage", "grid"]
      resp = await self.api.energy_analysis(siteId=siteId, deviceSn="", rangeType="week", startDay=startDay, endDay=endDay,  devType="solar_production")
      self.data.extend([{"type": "solar production", "color": "#84bd00", "data": resp.get("power")}])

      resp = await self.api.energy_analysis(siteId=siteId, deviceSn="", rangeType="week", startDay=startDay, endDay=endDay,  devType="home_usage")
      self.data.extend([{"type": "home usage", "color": "#0085ad", "data": resp.get("power")}])

      resp = await self.api.energy_analysis(siteId=siteId, deviceSn="", rangeType="week", startDay=startDay, endDay=endDay,  devType="solarbank")
      self.data.extend([{"type": 'solarbank', "color": "#e1e000", "data": resp.get("power")}])

      resp = await self.api.energy_analysis(siteId=siteId, deviceSn="", rangeType="week", startDay=startDay, endDay=endDay,  devType="grid")
      self.data.extend([{"type": "grid export", "color": "#e4002b", "data": resp.get("power")}])

  async def ausgabe_graph(self):
    selected = ["all"]
    if "selected_curves" in st.session_state:
      selected = st.session_state.selected_curves
    self.ph1.empty()
    self.ph2.empty()
    self.ph3.empty()
    graph_container = st.container()
    with graph_container:
      # Ausgabe
      werte = []
      arr_type = []
      arr_avg = []
      arr_color = []

      for d in self.data:
        dd = d.get("data")
        type = d["type"]
        # nur Selektierte Grafiken
        if type not in selected and "all" not in selected:
           continue

        arr_dd = []
        arr_ww = []
        arr_th = []
        d_sum = 0
        n = 0
        # Überstromgrenze
        anz_th = 0
        th = -1.8
        for w in dd:
          val = float(w.get("value"))
          arr_dd.extend([datetime.strptime(w.get("time"), '%Y-%m-%d')])
          arr_ww.extend([round(val, 2)])
          arr_th.extend([th])
          # wie oft wird der Schwellwert überschtritten
          if d.get("type") == "grid export" and val <= th:
            anz_th += 1

          d_sum += val
          n = n + 1

        werte.extend([[d.get("type"), arr_dd, arr_ww, d.get("color")]])
        arr_type.extend([d.get("type")])
        arr_color.extend([d.get("color")])
        arr_avg.extend([d_sum / n])

      # Grafik erstellen
      fig, ax = plt.subplots(figsize=(15, 7))

      for w in werte:
        label = w[0]
        ax.plot(w[1], w[2], label=label, marker="o", linestyle="-", color=w[3])
        for dd, v in zip(w[1], w[2]):
          color = w[3]
          # Markiering, wenn der Schwellwert unterschritten wurde
          if d.get("type") == "grid export" and v <= th:
            color = "#84bd00"
          ax.text(dd, v + 0.2, f"{v}", ha="center", va="bottom", fontsize=12, color=color)
      # Schwellwert
      plt.plot(w[1], arr_th, label=str(th) + "kWh", linestyle="-", color="#ffcc99", linewidth=3)

      if n <= 25:
        rot = 0
      else:
        rot = 15
      ax.tick_params(axis='x', labelsize=14, rotation=rot)  # Schriftgröße x-Achsenwerte
      ax.tick_params(axis='y', labelsize=14)  # Schriftgröße y-Achsenwerte
      # Achsenbeschriftung
      ax.set_xlabel("Datum", fontsize=14)
      ax.set_ylabel("kWh", fontsize=14)
      # Titel
      ax.set_title("Solaranlage", fontsize=16)
      # Legende anzeigen
      # ax.legend()
      ax.legend(loc='upper left', bbox_to_anchor=(0, -0.10), ncol=5, fontsize=14)
      # Raster aktivieren
      ax.grid(True)
      # X-Achse enger beschriften: z. B. alle 3 Tage
      iv = math.ceil(n / 15)
      ax.xaxis.set_major_locator(mdates.DayLocator(interval=iv))

      # Grafik anzeigen
      fig.tight_layout()
      self.ph1.pyplot(fig)
      # Überschreitung 2.7kWk
      prz = round(100 * anz_th / n, 2)
      self.ph2.markdown(
        f"<p style='font-size:13px;padding-left:20px'>🔹Überschreitung Einspeisung {th} kWh Tage: {anz_th} ({prz}%)</p>", unsafe_allow_html=True)

      # Durchscnitt
      fig, ax = plt.subplots(figsize=(12, 6))
      bars = ax.bar(arr_type, arr_avg, color=arr_color)
      # Beschriftungen über den Balken
      for bar in bars:
        y = round(bar.get_height(), 2)
        yb = y + 0.1
        if y < 0:
          yb = 0.1

        plt.text(bar.get_x() + bar.get_width() / 2, yb, f'{y}', ha='center', va='bottom', fontsize=12)

      ax.set_title(f"Solaranlage Durchscnitt ({n})", fontsize=13)
      ax.legend()
      ax.grid(True)
      ax.tick_params(axis='x', labelsize=12)  # Schriftgröße x-Achsenwerte
      ax.tick_params(axis='y', labelsize=12)  # Schriftgröße y-Achsenwerte
      ax.set_xlabel("Type", fontsize=12)
      ax.set_ylabel("kWh", fontsize=12)
      fig.tight_layout()
      self.ph3.pyplot(fig)

async def create_session_and_update(user, pw, country, numdays):
  async with ClientSession() as session:
      a = AnkerSolixInfo(user, pw, country, numdays, session)
      # Async-Funktion synchron ausführen
      await a.update_sites()
      await a.ausgabe_graph()
      return a

# 🔁 Definition einer synchronen Wrapper-Funktion für Streamlit

def draw_graph():
  if "a" not in st.session_state:
    return
  a = st.session_state["a"]
  asyncio.run(a.ausgabe_graph())

#asyncio.run(create_session_and_update("hallo.otto123.oo@gmail.com", "Anker3.oo#196", "DE",10))
# --- Login-Status initialisieren (einmalig beim Start) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.write(f"logged_in {st.session_state.logged_in}")

if "a" not in st.session_state:
    st.session_state.a = None

st.write(f"Durchlauf {st.session_state.logged_in}")
# Platzhalter nur für Diagramme
if "ph1" not in st.session_state:
  st.session_state.ph1 = st.empty()
  st.session_state.ph2 = st.empty()
  st.session_state.ph3 = st.empty()

kurven = ["solar production", "home usage", "solarbank", "grid export"]
if not st.session_state.logged_in:
  user     = st.text_input("User")
  pw       = st.text_input("Passwort", type="password")
  country  = "DE"
  numdaysx = st.text_input("Anzahl Tage", value="20")

  if numdaysx.isdigit():
      numdays = int(numdaysx)
  else:
      numdays = 10

  st.multiselect(label="Kurve auswählen0:", options=kurven, default=kurven, key="selected_curves", on_change=draw_graph)

  if st.button("Anmelden"):
    try:
      a = asyncio.run(create_session_and_update(user, pw, country, numdays))
      st.session_state["a"] = a  # <--- WICHTIG: speichern
      #st.success("Login erfolgreich!")
      st.session_state.logged_in = True
    except Exception as e:
      st.error(f"Anmeldefehler: {e}")
  else:
    st.write(f"Else user aussschalten {st.session_state.logged_in}")
else:
  st.multiselect(label="Kurve auswählen:",options=kurven,default=kurven,key="selected_curves",on_change=draw_graph)




