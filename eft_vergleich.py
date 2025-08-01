import pandas as pd
import matplotlib.pyplot as plt
import justetf_scraping  # ← stelle sicher, dass dieses Modul verfügbar ist
import streamlit as st
import numpy as np

# ETFs: ISIN → Anzeigename
etfs = {
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
}

# ----------------
# --- Eingaben ---
# ----------------

input_days = st.text_input("Anzahl Tage", value="100")
last_days=float(input_days)

input_type_radio = st.radio(
    "Vergleich/Absolut",
    ["Vergleich", "Absolut"],
    horizontal=True
)
if input_type_radio == "Absolut":
   input_type = "a"
else:
   input_type = "v"

# Leeres DataFrame zur Zusammenführung
comparison_df = pd.DataFrame()
stats = {}

for isin, name in etfs.items():
    try:
        df = justetf_scraping.load_chart(isin)
    except RuntimeError:
        print(f"⚠️ Fehler bei ISIN {isin} {name}")
        continue

    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    current_year = df.index.max()
    last_year = current_year - pd.DateOffset(days=last_days)

    df_filtered = df[(df.index >= last_year) & (df.index <= current_year)].copy()

    if df_filtered.empty:
        print(f"⚠️  Keine Daten im Zeitraum für {name}")
        continue

    if input_type == "a":
        quote = df_filtered["quote"]
    else:
        quote = df_filtered["quote"] / df_filtered["quote"].iloc[0] * 100

    comparison_df[name] = quote.astype(float)

    # Nur die Performance berechnen und speichern
    performance = (quote.iloc[-1] / quote.iloc[0] - 1) * 100
    stats[name] = {'Performance [%]': round(performance, 2)}

# Ausgabe der Kennzahlen
stats_df = pd.DataFrame(stats).T
st.dataframe(stats_df)

# Plot
fig, ax = plt.subplots(figsize=(12, 6))
for col in comparison_df.columns:
    ax.plot(comparison_df.index, comparison_df[col], label=col)

ax.set_title(f"ETF-{'Absolute' if input_type=='a' else 'Vergleich (normalisiert)'} – der letzten {last_days} Tage")
ax.set_xlabel("Datum")
ax.set_ylabel("Performance [%]")
ax.legend()
ax.grid(True)
fig.tight_layout()
st.pyplot(fig)

