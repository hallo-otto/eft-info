import asyncio

from aiohttp import ClientSession
from api.api import AnkerSolixApi
import streamlit as st
from datetime import date, datetime, timedelta
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import math
import pandas as pd
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
    self.data    = []
    self.total1  = []
    self.total2  = []
    self.total3  = []
    self.total4  = []
    self.erzeugt = 0
    self.ph1     = st.empty()
    self.ph2     = st.empty()
    self.ph3     = st.empty()
    self.ph401   = st.empty()
    self.ph402   = st.empty()
    self.ph411   = st.empty()
    self.ph412   = st.empty()
    self.ph421   = st.empty()
    self.ph422   = st.empty()
    self.ph431   = st.empty()
    self.ph432   = st.empty()
    self.ph441   = st.empty()
    self.ph442   = st.empty()
    self.api     = AnkerSolixApi(user, pw, country, session)  # einmalig speichern

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
      self.erzeugt = items[0][1]["statistics"][0]["total"]
      site, site_data = items[0]
      await self.hist(site_data)
      self.api.sites.clear()
    else:
       st.warning("Keine Standorte verfügbar.")
       #print("Keine Standorte verfügbar.")

  # ----------------
  # Hist Daten
  # ----------------
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

      self.total1 = ([{"Titel": "erzeugt", "Daten": self.erzeugt}])

      # "device_type": ["solar_production", "solarbank", "home_usage", "grid"]
      resp = await self.api.energy_analysis(siteId=siteId, deviceSn="", rangeType="week", startDay=startDay, endDay=endDay,  devType="solar_production")
      self.data.extend([{"type": "solar production", "color": "#84bd00", "data": resp.get("power")}])

      self.total2 = ([{"Titel": "solar_total", "Daten": resp["solar_total"]},
                      {"Titel": "solar_to_battery_total", "Daten": resp["solar_to_battery_total"]},
                      {"Titel": "solar_to_home_total", "Daten": resp["solar_to_home_total"]},
                      {"Titel": "solar_to_grid_total", "Daten": resp["solar_to_grid_total"]}
      ])

      resp = await self.api.energy_analysis(siteId=siteId, deviceSn="", rangeType="week", startDay=startDay, endDay=endDay,  devType="home_usage")
      self.data.extend([{"type": "home usage", "color": "#0085ad", "data": resp.get("power")}])

      self.total3 = ([{"Titel": "home_usage_total", "Daten": resp["home_usage_total"]},
                      {"Titel": "battery_to_home_total", "Daten": resp["battery_to_home_total"]},
                      {"Titel": "solar_to_home_total", "Daten": resp["solar_to_home_total"]},
                      {"Titel": "grid_to_home_total", "Daten": resp["grid_to_home_total"]}
      ])

      resp = await self.api.energy_analysis(siteId=siteId, deviceSn="", rangeType="week", startDay=startDay, endDay=endDay,  devType="solarbank")
      self.data.extend([{"type": 'solarbank', "color": "#e1e000", "data": resp.get("power")}])

      resp = await self.api.energy_analysis(siteId=siteId, deviceSn="", rangeType="week", startDay=startDay, endDay=endDay,  devType="grid")
      self.data.extend([{"type": "grid export", "color": "#e4002b", "data": resp.get("power")}])

      self.total4 = ([{"Titel": "solar_to_grid_total", "Daten": resp["solar_to_grid_total"]},
                      {"Titel": "grid_imported_total", "Daten": resp["grid_imported_total"]}
      ])

      """
      proz = round(100 * float(100 - resp["solar_to_grid_total"]) / float(self.erzeugt),2)
      self.total =([
         {"Tilel": "erzeugt",               "Daten" : self.erzeugt},
         {"Tilel": "solar_to_grid_total",   "Daten" : resp["solar_to_grid_total"]},
         {"Tilel": "grid_to_home_total",    "Daten" : resp["grid_to_home_total"]},
         {"Tilel": "grid_imported_total",   "Daten" : resp["grid_imported_total"]},
         {"Tilel": "grid_to_battery_total", "Daten" : resp["grid_to_battery_total"]},
         {"Tilel": "prozent eigennutzung",  "Daten" : proz}
      ])
      """
  # ----------------
  # Grafik
  # ----------------
  async def ausgabe_graph(self):
    selected = ["all"]
    if "selected_curves" in st.session_state:
      selected = st.session_state.selected_curves
    self.ph1.empty()
    self.ph2.empty()
    self.ph3.empty()
    self.ph401.empty()
    self.ph402.empty()
    self.ph411.empty()
    self.ph412.empty()
    self.ph421.empty()
    self.ph422.empty()
    self.ph431.empty()
    self.ph432.empty()
    self.ph441.empty()
    self.ph442.empty()
    graph_container = st.container()

    with graph_container:
      if len(selected) == 0:
          self.ph1.error("keine Kurve ausgewählt!")
          self.ph2.write("")
          self.ph3.write("")
          return
      # Ausgabe
      werte = []
      arr_type = []
      arr_avg = []
      arr_color = []

      # Grafik ph1
      for d in self.data:
        dd = d.get("data")
        type = d["type"]
        # Selektion Grafiken
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

      # Grafik anzeigen ph1
      fig.tight_layout()
      self.ph1.pyplot(fig)
      # Überschreitung 2.7kWk ph2
      prz = round(100 * anz_th / n, 2)
      self.ph2.markdown(
        f"<p style='font-size:13px;padding-left:20px'>🔹Überschreitung Einspeisung {th} kWh Tage: {anz_th} ({prz}%)</p>", unsafe_allow_html=True)

      # Durchscnitt ph3
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

      # Statistik ph4
      self.ph401.markdown("<style>table th {text-align: left !important;</style>",  unsafe_allow_html=True)
      self.ph402.markdown(f"**Statistik**")

      df1 = pd.DataFrame(self.total1)
      self.ph411.markdown(f"**Erzeugt**")
      self.ph412.markdown(df1.to_html(escape=False, index=False), unsafe_allow_html=True)

      df2 = pd.DataFrame(self.total2)
      self.ph421.markdown(f"**solar_production**")
      self.ph422.markdown(df2.to_html(escape=False, index=False), unsafe_allow_html=True)

      df3 = pd.DataFrame(self.total3)
      self.ph431.markdown(f"**home_usage**")
      self.ph432.markdown(df3.to_html(escape=False, index=False), unsafe_allow_html=True)

      df4 = pd.DataFrame(self.total4)
      self.ph441.markdown(f"**grid**")
      self.ph442.markdown(df4.to_html(escape=False, index=False), unsafe_allow_html=True)
  # ----------------
  # Create Session
  # ----------------
async def create_session_and_update(user, pw, country, numdays):
  async with ClientSession() as session:
      a = AnkerSolixInfo(user, pw, country, numdays, session)
      # Async-Funktion synchron ausführen
      await a.update_sites()
      #await a.ausgabe_graph()
      return a

# 🔁 Definition einer synchronen Wrapper-Funktion für Streamlit, für multiselect
def draw_graph():
  if "a" not in st.session_state:
    return
  a = st.session_state["a"]
  asyncio.run(a.ausgabe_graph())

# --- Login-Status initialisieren (einmalig beim Start) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "a" not in st.session_state:
    st.session_state.a = None

# Platzhalter nur für Diagramme
if "ph1" not in st.session_state:
  st.session_state.ph1 = st.empty()
  st.session_state.ph2 = st.empty()
  st.session_state.ph3 = st.empty()

# Kurven Auswahl, muss mit data.type übereinstimmen
kurven = ["solar production", "home usage", "solarbank", "grid export"]
# -------------
# --- Start ---
# -------------
if not st.session_state.logged_in:
  user     = st.text_input("User")
  pw       = st.text_input("Passwort", type="password")
  country  = "DE"
  numdaysx = st.text_input("Anzahl Tage", value="100")

  if numdaysx.isdigit():
      numdays = int(numdaysx)
  else:
      numdays = 10

  if st.button("Anmelden"):
    try:
      a = asyncio.run(create_session_and_update(user, pw, country, numdays))
      st.session_state["a"] = a  # <--- WICHTIG: speichern
      st.success("Login erfolgreich!")
      st.session_state.logged_in = True
      # Neustart nach Anmeldung
      st.rerun()
    except Exception as e:
      st.error(f"Anmeldefehler: {e}")
else:
  # ----------------------
  # --- Nach Anmeldung ---
  # ----------------------
  st.multiselect(label="Kurve auswählen:",options=kurven,default=kurven,key="selected_curves",on_change=draw_graph)
  a = st.session_state["a"]
  asyncio.run(a.ausgabe_graph())
