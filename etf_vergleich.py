import pandas as pd
import matplotlib.pyplot as plt
import justetf_scraping  # ← stelle sicher, dass dieses Modul verfügbar ist
import streamlit as st
import numpy as np

@st.cache_data
def load_fvs_data(url):
  try:
      dfx = pd.read_excel(url, skiprows=3)
      dfx.columns = ["Datum", "Kurs"]
      dfx.dropna(inplace=True)
      dfx["Datum"] = pd.to_datetime(dfx["Datum"])
      dfx.set_index("Datum", inplace=True)
      dfx.sort_index(inplace=True)
      return dfx
  except Exception as e:
      #st.error(f"Fehler beim Laden der Kursdaten: {url}")
      print(f"⚠️ Fehler bei URL {url}")
      return pd.DataFrame()

# ETFs: ISIN → Anzeigename
etfs = {
    "DE0005190003": "(DE0005190003) BAY.MOTOREN WERKE AG ST",
    "IE00B43HR379": "(IE00B43HR379) ISHSV-S+P500H.CA.SECT.DLA",
    "IE00BMYDM794": "(IE00BMYDM794) LGUE-HYDR.ECO. DLA",
    "IE00BYZK4552": "(IE00BYZK4552) ISHS IV-AUTO.+ROBOTIC.ETF",
    "IE00BM67HT60": "(IE00BM67HT60) X(IE)-MSCI WO.IN.TE. 1CDL",
    "LU2611732046": "(LU2611732046) AIS AMUNDI DAX ETF DIST",
    "LU0171307068": "(LU0171307068) BGF-WLD HEALTHSC.NA.A2EO",
    "DE0008486655": "(DE0008486655) DWS CONCEPT GS+P FOOD LD",
    "DE0008481763": "(DE0008481763) ALL.NEBENW.D A (EUR)",
    "FR0010135103": "(FR0010135103) CARMIGN.PATRIMOI. AEO ACC",
    "LU0055631609": "(LU0055631609) BGF-WORLD GOLD A2DL",
    "LU0323578657": "(LU0323578657) FLOSSB.V.STORCH-MUL.OPP.R",
    "DE000SH9VRM6": "(DE000SH9VRM6) SGIS AKTANL PL 24/26 NVDA"
}

# ----------------
# --- Eingaben ---
# ----------------
input_days = st.text_input("Anzahl Tage", value="100")
last_days=float(input_days)

#["Performance", "Annualisierte Rendite", "Volatilität","Maximaler Drawdown","Fehler Liste"],
input_type_radio = st.radio(
    "Kennzahl",
    ["Kurs", "Performance", "Volatilität","Fehler Liste"],
    horizontal=True
)
input_type = input_type_radio[0]
#input_type = "K"

# Leeres DataFrame zur Zusammenführung
comparison_df = pd.DataFrame()
stats = {}
fehler_isin = []

for isin, name in etfs.items():
    try:
      df = justetf_scraping.load_chart(isin)
    except RuntimeError:
      print(f"⚠️ Fehler bei ISIN {isin} {name}")
      arr = [[isin,name]]
      fehler_isin.extend(arr)
      continue

    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    current_year = df.index.max()
    last_year = current_year - pd.DateOffset(days=last_days)

    df_filtered = df[(df.index >= last_year) & (df.index <= current_year)].copy()

    if df_filtered.empty:
        print(f"⚠️  Keine Daten im Zeitraum für {name}")
        continue

    if input_type == "K":
        series = df_filtered["quote"]
        start_value = series.iloc[0]
        end_value = series.iloc[-1]
        quote = series
        performance = (end_value / start_value - 1) * 100
        ylabel = "Kurs"
    elif input_type == "P":
        series      = df_filtered["quote"]
        start_value = series.iloc[0]
        end_value   = series.iloc[-1]
        quote = series / start_value * 100
        performance = (end_value / start_value - 1) * 100
        ylabel = "Performance [%]"
    elif input_type == "A":
        series = df_filtered["quote_with_reinvested_dividends"]
        start_value = series.iloc[0]
        end_value   = series.iloc[-1]
        n_days = (series.index[-1] - series.index[0]).days
        # Berechne für jeden Tag die annualisierte Rendite seit Start
        quote       = (series / start_value) ** (365 / (n_days + 1)) - 1
        performance = ((end_value / start_value) ** (365 / n_days) - 1) * 100
        ylabel = "Annualisierte Rendite"
    elif input_type == "V":
        # Bereite die Preisreihe vor (z. B. Total Return Kurs)
        series      = df_filtered["quote_with_reinvested_dividends"]
        start_value = series.iloc[0]
        end_value   = series.iloc[-1]
        n_days = (series.index[-1] - series.index[0]).days

        # Berechne tägliche logarithmische Renditen .dropna() für NaN
        quote = np.log(series / series.shift(1)).dropna()
        # Berechne rollierende Volatilität (30 Tage Fenster), 30 Tage ≈ 1 Monat an Handelstagen

        vol_window = 30
        performance = quote[-vol_window:].std() * np.sqrt(252)

        ylabel  = "Volatilität (%)"
    elif input_type == "M":
        series = df_filtered["quote_with_reinvested_dividends"]
        running_max = series.cummax()
        quote = (series / running_max - 1) * 100
        performance =quote.min()
        ylabel  = "Maximaler Drawdown (%)"
    else:
        x = "x"

    if input_type != "F":
       comparison_df[name] = quote.astype(float)
       stats[name] = {ylabel : round(performance, 2)}

# Ausgabe der Kennzahlen
if input_type == "F":
    # In DataFrame umwandeln (mit Spaltennamen)
    dfl = pd.DataFrame(fehler_isin, columns=['ISIN', 'Name'])
    # In Streamlit anzeigen
    #st.subheader("In justETF nicht gefunden")
    st.markdown("<div style='font-size:15px;font-weight: bold;text-align: center;'>nicht in justETF vorhanden</div>", unsafe_allow_html=True)
    st.dataframe(dfl)
else:
    comparison_df[name] = quote.astype(float)
    stats[name] = {ylabel : round(performance, 2)}
    #st.write(comparison_df)
    # Plot
    # figsize=(9, 6) ist die Figur 9 Zoll breit und 6 Zoll hoch.
    fig, ax = plt.subplots(figsize=(16, 10))
    for col in comparison_df.columns:
        ax.plot(comparison_df.index, comparison_df[col], label=col)
        #ax.set_ylim(0, 200)  # engerer Bereich
        # letzen Wert ausgeben
        if input_type == "K":
          ind = comparison_df.index[-1]
          val = int(round(comparison_df[col][-1],0))
          ax.text(ind, val + 0.2, f"{val}", ha="center", va="bottom" ,fontsize=16)

    round_performance = round(performance,2)
    round_days        = round(last_days)
    ax.set_title(f"ETF-{ylabel}  {round_performance} – der letzten {round_days } Tage",fontsize=18)
    ax.tick_params(axis='x', labelsize=16)  # Schriftgröße x-Achsenwerte
    ax.tick_params(axis='y', labelsize=16)  # Schriftgröße y-Achsenwerte
    ax.set_xlabel("Datum",fontsize=16)
    ax.set_ylabel(ylabel,fontsize=16)
    ax.legend(loc='upper left', bbox_to_anchor=(0, -0.10),fontsize=18, ncol=2,)
    ax.grid(True)
    fig.tight_layout()
    st.pyplot(fig)
