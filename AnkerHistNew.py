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
    self.total   = []
    self.erzeugt = 0
    self.api     = AnkerSolixApi(user, pw, country, session)  # einmalig speichern
    # Kurven Auswahl, muss mit data.type übereinstimmen
    self.kurven  = ["solar production", "home usage", "solarbank", "grid export"]

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

      #total1 = ([{"Titel": "erzeugt", "Daten": self.erzeugt}])

      # "device_type": ["solar_production", "solarbank", "home_usage", "grid"]
      resp = await self.api.energy_analysis(siteId=siteId, deviceSn="", rangeType="week", startDay=startDay, endDay=endDay,  devType="solar_production")
      self.data.extend([{"type": "solar production", "color": "#84bd00", "data": resp.get("power")}])

      total2 = ([{"Titel": "solar_total", "Daten": resp["solar_total"]},
                 {"Titel": "solar_to_battery_total", "Daten": resp["solar_to_battery_total"]},
                 {"Titel": "solar_to_home_total",    "Daten": resp["solar_to_home_total"]},
                 {"Titel": "solar_to_grid_total",    "Daten": resp["solar_to_grid_total"]}
      ])
      total1 = [total2[0]]

      resp = await self.api.energy_analysis(siteId=siteId, deviceSn="", rangeType="week", startDay=startDay, endDay=endDay,  devType="home_usage")
      self.data.extend([{"type": "home usage", "color": "#0085ad", "data": resp.get("power")}])

      total3 = ([{"Titel": "home_usage_total",      "Daten": resp["home_usage_total"]},
                 {"Titel": "battery_to_home_total", "Daten": resp["battery_to_home_total"]},
                 {"Titel": "solar_to_home_total",   "Daten": resp["solar_to_home_total"]},
                 {"Titel": "grid_to_home_total",    "Daten": resp["grid_to_home_total"]}
      ])
      total1.append(total3[0])

      resp = await self.api.energy_analysis(siteId=siteId, deviceSn="", rangeType="week", startDay=startDay, endDay=endDay,  devType="solarbank")
      self.data.extend([{"type": 'solarbank', "color": "#e1e000", "data": resp.get("power")}])

      resp = await self.api.energy_analysis(siteId=siteId, deviceSn="", rangeType="week", startDay=startDay, endDay=endDay,  devType="grid")
      self.data.extend([{"type": "grid export", "color": "#e4002b", "data": resp.get("power")}])

      total4 = ([{"Titel": "solar_to_grid_total", "Daten": resp["solar_to_grid_total"]},
                 {"Titel": "grid_imported_total", "Daten": resp["grid_imported_total"]}
      ])
      total1.append(total4[0])
      total1.append(total4[1])
      prz = 100 - round(100 * float(total4[1]["Daten"]) / float(total3[0]["Daten"]),2)
      total1.extend([{"Titel": "Eigenverbrauch%", "Daten": prz}])

      self.total = ([{"titel": "Gesamt",           "daten": total1},
                     {"titel": "Solar Production", "daten": total2},
                     {"titel": "Verbrauch",        "daten": total3},
                     {"titel": "Netz",             "daten": total4}
      ])
  # ----------------
  # Grafik
  # ----------------
  async def ausgabe_graph(self):
    selected = ["all"]
    try:
      if "selected_curves" in st.session_state:
          selected = st.session_state.selected_curves
    except Exception as e:
      selected = ["all"]

    ph1 = st.empty()
    ph2 = st.empty()
    ph3 = st.empty()

    graph_container = st.container()

    with graph_container:
      if len(selected) == 0:
         ph1.error("keine Kurve ausgewählt!")
         ph2.write("")
         ph3.write("")
         return

      # Ausgabe
      werte     = []
      arr_type  = []
      arr_avg   = []
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
          # wie oft wird der Schwellwert überschritten
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
      ph1.pyplot(fig)
      # Überschreitung 2.7kWk ph2
      prz = round(100 * anz_th / n, 2)
      ph2.markdown(
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

      ax.set_title(f"Solaranlage Durchschnitt ({n})", fontsize=13)
      ax.legend()
      ax.grid(True)
      ax.tick_params(axis='x',    labelsize=12)  # Schriftgröße x-Achsenwerte
      ax.tick_params(axis='y',    labelsize=12)  # Schriftgröße y-Achsenwerte
      ax.set_xlabel("Type", fontsize=12)
      ax.set_ylabel("kWh",  fontsize=12)
      fig.tight_layout()
      ph3.pyplot(fig)

      # Statistik
      phs = st.empty()
      phs.title("Statistik")

      for t in self.total:
        dfs  = pd.DataFrame(t["daten"])
        phs0 = st.empty()
        phs1 = st.empty()
        phs2 = st.empty()

        phs0.markdown("<style>table th {text-align: left !important} .dataframe td:first-child, th:first-child {width: 200px !important} .dataframe td:nth-child(even) {text-align: right !important}</style>", unsafe_allow_html=True)
        phs1.markdown(f"**{t["titel"]}**")
        phs2.markdown(dfs.to_html(escape=False, index=False), unsafe_allow_html=True)

# ----------------
# Test
# ----------------
async def test(user, pw, country, numdays):
  async with ClientSession() as session:
      a = AnkerSolixInfo(user, pw, country, numdays, session)
      # Async-Funktion synchron ausführen
      await a.update_sites()
      await a.ausgabe_graph()
      return a
#a = asyncio.run(test("user","pw", "DE", 100))

# -------------
# --- Session und Anmeldung nur beim ersten Mal
# -------------
async def create_session_and_update(user, pw, country, numdays):
  async with ClientSession() as session:
      a = AnkerSolixInfo(user, pw, country, numdays, session)
      # Async-Funktion synchron ausführen
      await a.update_sites()
      return a

# -------------
# --- Start ---
# -------------
async def start():
    # Anmeldung beim ersten Mal
    if not "a" in st.session_state:
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
          a = await create_session_and_update(user, pw, country, numdays)
          st.session_state["a"] = a  # <--- WICHTIG: speichern
          st.success("Login erfolgreich!")
          st.session_state.logged_in = True
          # Neustart nach Anmeldung
          st.rerun()
        except Exception as e:
          st.error(f"Anmeldefehler: {e}")
    else:
      # ----------------------
      # --- Nach der Anmeldung, Selektion Kurven,
      # --- wird beim ersten Mal durch st.rerun() aufgerufen
      # ----------------------
      a = st.session_state["a"]
      st.multiselect(label="Kurve auswählen:",options=a.kurven,default=a.kurven,key="selected_curves")
      await a.ausgabe_graph()

asyncio.run(start())
