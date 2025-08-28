import asyncio
import pandas as pd
import matplotlib.pyplot as plt
import justetf_scraping  # ← stelle sicher, dass dieses Modul verfügbar ist
import streamlit as st
import numpy as np
import matplotlib.dates as mdates
import math
import pdb

class ETFVergleich:
  def __init__(self,last_days, input_type):
    self.etfs = {
      "FR0010655712": "Amundi DAX UCITS ETF DR (V)",
      "IE00BD4TXV59": "UBS Core MSCI World UCITS (V)",
      "DE0005190003": "BAY.MOTOREN WERKE AG ST",
      "IE00B43HR379": "ISHSV-S+P500H.CA.SECT.DLA",
      "IE00BMYDM794": "LGUE-HYDR.ECO. DLA",
      "IE00BYZK4552": "ISHS IV-AUTO.+ROBOTIC.ETF",
      "IE00BM67HT60": "X(IE)-MSCI WO.IN.TE. 1CDL",
      "LU2611732046": "AIS AMUNDI DAX ETF DIST",
      "LU0171307068": "BGF-WLD HEALTHSC.NA.A2EO",
      "DE0008486655": "DWS CONCEPT GS+P FOOD LD",
      "DE0008481763": "ALL.NEBENW.D A (EUR)",
      "FR0010135103": "CARMIGN.PATRIMOI. AEO ACC",
      "LU0055631609": "BGF-WORLD GOLD A2DL",
      "LU0323578657": "FLOSSB.V.STORCH-MUL.OPP.R",
      "DE000SH9VRM6": "SGIS AKTANL PL 24/26 NVDA"
      "IE0001UQQ933": "Kommer Fond"
    }

    self.last_days  = last_days
    self.input_type = input_type

    # Leeres DataFrame zur Zusammenführung
    self.df_comparison = pd.DataFrame()
    self.stats         = {}
    self.fehler_isin   = []
    self.title         = ""

  def getEtfList(self):
      return self.etfs

  # ETF Durchlauf
  async def etf_read(self, selected):
    n = 0
    #st.write(f"  selected {type(selected)} {selected}")
    for isin, name in self.etfs.items():
        suche = f"{isin} – {name}"
        #if (suche in selected):
        if (suche not in selected and "Alle" not in selected):
            continue

        try:
            df = justetf_scraping.load_chart(isin)
            # Datumsbereich
            current_day = df.index.max()
            last_day = current_day - pd.DateOffset(days=self.last_days)
            # Filter
            df_filtered = df[(df.index >= last_day) & (df.index <= current_day)].copy()
            if df_filtered.empty:
               print(f"⚠️  Keine Daten im Zeitraum für {isin} {name}{name}")
               continue
            df.index = pd.to_datetime(df.index)
            df_sort  = df_filtered.sort_index()
            # Berechnen der Quote
            await self.etf_quote(isin, name, df_sort)
            n += 1
        except RuntimeError:
            #st.write(f"⚠️ Fehler bei ISIN {isin} {name}")
            arr = [[isin, name]]
            self.fehler_isin.extend(arr)
            continue

    # Ausgabe
    # kein justETF
    if n == 0:
       self.input_type = "F"
    await  self.etf_output()

  # Brechnen der Quoten und Performance
  async def etf_quote(self, isin, name, df):
    if self.input_type == "K":
        series      = df["quote"]
        start_value = series.iloc[0]
        end_value   = series.iloc[-1]
        quote       = series
        performance = (end_value / start_value - 1) * 100
        self.title  = "Kurs"
    elif self.input_type == "R":
        series = df["quote"]
        start_value = series.iloc[0]
        end_value = series.iloc[-1]
        quote = series.pct_change()*100
        #sval = series.values
        #temp_quote = [(sval[i] - sval[i - 1]) / sval[i - 1] * 100 for i in range(1, len(sval))]
        #quote = np.array(temp_quote, dtype=float)
        performance = (end_value / start_value - 1) * 100
        self.title = "Kurs zum Vortag%"
    elif self.input_type == "P":
        series      = df["quote"]
        start_value = series.iloc[0]
        end_value   = series.iloc[-1]
        quote       = series / start_value * 100
        performance = (end_value / start_value - 1) * 100
        self.title  = "Performance [%]"
    elif self.input_type == "V":
        # Bereite die Preisreihe vor (z. B. Total Return Kurs)
        series      = df["quote_with_reinvested_dividends"]
        # Berechne tägliche logarithmische Renditen .dropna() für NaN
        quote       = np.log(series / series.shift(1)).dropna()
        # Performance
        vol_window  = 30
        performance = quote[-vol_window:].std() * np.sqrt(252)
        # Label
        self.title  = "Volatilität (%)"
    elif self.input_type == "F":
        return

    # Zusammenführen der Daten
    self.df_comparison[isin] = quote.astype(float)
    self.stats[isin]         = {"name":name, "performance": round(performance, 2)}
    #st.write(f"ETF: {isin} {name}")

  # Ausgaben
  async def etf_output(self):
    # Ausgabe der Fehlerliste
    if self.input_type == "F":
      # In DataFrame umwandeln (mit Spaltennamen)
      dfl = pd.DataFrame(self.fehler_isin, columns=['ISIN', 'Name'])
      # In Streamlit anzeigen
      # st.subheader("In justETF nicht gefunden")
      st.markdown("<div style='font-size:15px;font-weight: bold;text-align: center;'>nicht in justETF vorhanden</div>", unsafe_allow_html=True)
      st.dataframe(dfl)
    # Ausgabe Grafik
    else:
      fig, ax = plt.subplots(figsize=(16, 10))
      max_len = 0
      for col in self.df_comparison.columns:
          label   = f"{col} - {self.etfs[col]}"
          max_len = max(max_len, len(label))
          ax.plot(self.df_comparison.index, self.df_comparison[col], label=label)
          # ax.set_ylim(0, 200)  # engerer Bereich
          # letzen Wert ausgeben
          if input_type == "K":
            ind = self.df_comparison.index[-1]
            val = round(self.df_comparison[col][-1], 2)
            ax.text(ind, val + 0.2, f"{val}", ha="center", va="bottom", fontsize=16)

      #round_performance = round(performance, 2)
      round_days = round(last_days)
      #ax.set_title(f"ETF-{ylabel}  {round_performance} – der letzten {round_days} Tage", fontsize=18)
      ax.set_title(f"ETF-{self.title} – der letzten {round_days} Tage", fontsize=18)
      if self.last_days <= 25:
         rot=0
      else:
         rot=15
      ax.tick_params(axis='x', labelsize=16, rotation=rot)  # Schriftgröße x-Achsenwerte
      ax.tick_params(axis='y', labelsize=16)  # Schriftgröße y-Achsenwerte
      ax.set_xlabel("Datum", fontsize=16)
      ax.set_ylabel(self.title, fontsize=16)
      iv = math.ceil(self.last_days/15)
      ax.xaxis.set_major_locator(mdates.DayLocator(interval=iv))
      # st.write(max_len)
      ncol=2
      if max_len >= 40:
         ncol=1
      ax.legend(loc='upper left', bbox_to_anchor=(0, -0.10), fontsize=18, ncol=ncol)
      ax.grid(True)
      #fig.tight_layout()
      plt.tight_layout()
      st.pyplot(fig)


async def create_session(last_days, input_type):
    e = ETFVergleich(last_days, input_type)
    etf_list = e.getEtfList()
    # Streamlit Selectbox mit voreingestelltem Wert
    keys = [f"{k} – {v}" for k, v in etf_list.items()]
    keys.insert(0,"Alle")
    selected = st.multiselect("Wähle einen ETF:", keys)

    #st.button("Programm starten")
    # Ausgabe
    #st.write(f"Du hast gewählt: {choice[:12]}")
    if len(selected) > 0:
       await e.etf_read(selected)

#asyncio.run(create_session(100,"R"))
# ----------------
# --- Eingaben ---
# ----------------
input_days = st.text_input("Anzahl Tage", value="100")
last_days=float(input_days)

#["Performance", "Annualisierte Rendite", "Volatilität","Maximaler Drawdown","Fehler Liste"],
input_type_radio = st.radio(
    "Kennzahl",
    ["Kurs", "Relativert Kurs%", "Performance", "Volatilität","Fehler Liste"],
    index=1,
    horizontal=True
)
input_type = input_type_radio[0]
asyncio.run(create_session(last_days, input_type))
