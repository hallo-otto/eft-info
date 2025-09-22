import asyncio
import pandas as pd
import matplotlib.pyplot as plt
import justetf_scraping
import streamlit as st
import numpy as np
import matplotlib.dates as mdates
import math

class ETFVergleich:
    def __init__(self):
        # Beispiel ETFs
        self.etfs = {
          "FR0010655712": {"name": "Amundi DAX UCITS ETF DR (V)"    , "ticker": ""        , "performance": -9999, "df": None},
          "IE00BD4TXV59": {"name": "UBS Core MSCI World UCITS (V)"  , "ticker": ""        , "performance": -9999, "df": None},
          "DE0005190003": {"name": "BAY.MOTOREN WERKE AG ST"        , "ticker": ""        , "performance": -9999, "df": None},
          "IE00B43HR379": {"name": "ISHSV-S+P500H.CA.SECT.DLA"      , "ticker": ""        , "performance": -9999, "df": None},
          "IE00BMYDM794": {"name": "LGUE-HYDR.ECO. DLA"             , "ticker": ""        , "performance": -9999, "df": None},
          "IE00BYZK4552": {"name": "ISHS IV-AUTO.+ROBOTIC.ETF"      , "ticker": ""        , "performance": -9999, "df": None},
          "IE00BM67HT60": {"name": "X(IE)-MSCI WO.IN.TE. 1CDL"      , "ticker": ""        , "performance": -9999, "df": None},
          "LU2611732046": {"name": "AIS AMUNDI DAX ETF DIST"        , "ticker": ""        , "performance": -9999, "df": None},
          "LU0171307068": {"name": "BGF-WLD HEALTHSC.NA.A2EO"       , "ticker": ""        , "performance": -9999, "df": None},
          "DE0008486655": {"name": "DWS CONCEPT GS+P FOOD LD"       , "ticker": ""        , "performance": -9999, "df": None},
          "DE0008481763": {"name": "ALL.NEBENW.D A (EUR)"           , "ticker": "ALND.DE" , "performance": -9999, "df": None},
          "FR0010135103": {"name": "CARMIGN.PATRIMOI. AEO ACC"      , "ticker": ""        , "performance": -9999, "df": None},
          "LU0055631609": {"name": "BGF-WORLD GOLD A2DL"            , "ticker": "MI9C.F"  , "performance": -9999, "df": None},
          "LU0323578657": {"name": "FLOSSB.V.STORCH-MUL.OPP.R"      , "ticker": ""        , "performance": -9999, "df": None},
          "DE000SH9VRM6": {"name": "SGIS AKTANL PL 24/26 NVDA"      , "ticker": ""        , "performance": -9999, "df": None},
          "IE0001UQQ933": {"name": "Kommer Fond"                    , "ticker": ""        , "performance": -9999, "df": None},
          "IE00B6R52259": {"name": "iShare MSCI ACWI"               , "ticker": ""        , "performance": -9999, "df": None}
        }
        self.df_comparison = pd.DataFrame()
        self.fehler_isin   = []
        self.input_type    = "P"
        self.last_days     = 100
        self.title         = ""

    async def etf_load_data(self, last_days: int):
        self.last_days = last_days
        tasks = []
        for isin, meta in self.etfs.items():
            # Lade in Thread, damit asynchrone Ausführung möglich
            tasks.append(asyncio.to_thread(self._load_single_etf, isin, meta))
        await asyncio.gather(*tasks)

        # Sortiere absteigend nach Performance, aufsteigend nach Name
        self.etfs = dict(sorted(self.etfs.items(),
                                key=lambda x: (-x[1].get("performance", -9999), x[1]["name"])))

    def _load_single_etf(self, isin, meta):
        try:
            df = justetf_scraping.load_chart(isin)
            df.index = pd.to_datetime(df.index)
            current_day = df.index.max()
            last_day = current_day - pd.DateOffset(days=self.last_days)
            df_filtered = df[(df.index >= last_day) & (df.index <= current_day)]
            if df_filtered.empty:
                self.fehler_isin.append([isin, meta["name"]])
                return
            meta["df"] = df_filtered.sort_index()
            meta["performance"] = self._calc_performance(meta["df"]["quote"])
        except Exception:
            self.fehler_isin.append([isin, meta["name"]])

    @staticmethod
    def _calc_performance(series: pd.Series) -> float:
        return (series.iloc[-1] / series.iloc[0] - 1) * 100

    async def etf_eingaben(self):
        # Kennzahlen auswählen
        input_type = st.radio(
            "Kennzahl",
            ["Kurs", "Relativert Kurs%", "Performance", "Volatilität", "Fehler Liste"],
            index=2,
            horizontal=True
        )
        mapping = {"Kurs": "K", "Relativert Kurs%": "R", "Performance": "P", "Volatilität": "V", "Fehler Liste": "F"}
        self.input_type = mapping[input_type]

        # ETF-Auswahl
        options = [f"{isin} – {meta['name']}" for isin, meta in self.etfs.items()]
        options.insert(0, "Alle")
        selected = st.multiselect("Wähle ETFs:", options, default="Alle")
        return selected

    async def etf_read(self, selected):
        for isin, meta in self.etfs.items():
            if meta["df"] is None:
                continue
            if "Alle" not in selected and f"{isin} – {meta['name']}" not in selected:
                continue
            self._prepare_series(isin, meta)

    def _prepare_series(self, isin, meta):
        df = meta["df"]
        if self.input_type == "K":
            series = df["quote"]
            self.title = "Kurs"
        elif self.input_type == "R":
            series = df["quote"].pct_change() * 100
            self.title = "Kurs zum Vortag %"
        elif self.input_type == "P":
            series = df["quote"] / df["quote"].iloc[0] * 100
            self.title = "Performance [%]"
        elif self.input_type == "V":
            series = np.log(df["quote_with_reinvested_dividends"] / df["quote_with_reinvested_dividends"].shift(1)).dropna()
            self.title = "Volatilität (%)"
        elif self.input_type == "F":
            return
        self.df_comparison[isin] = series.astype(float)

    async def etf_output(self):
        if self.input_type == "F":
            if self.fehler_isin:
                df_errors = pd.DataFrame(self.fehler_isin, columns=["ISIN", "Name"])
                st.markdown(
                    "<div style='font-size:15px;font-weight:bold;text-align:center;'>Nicht in justETF vorhanden</div>",
                    unsafe_allow_html=True
                )
                st.dataframe(df_errors)
            return

        fig, ax = plt.subplots(figsize=(16, 10))
        max_len = 0
        for isin, series in self.df_comparison.items():
            name = self.etfs[isin]["name"]
            label = f"{isin} – {name}"
            max_len = max(max_len, len(label))
            ax.plot(series.index, series, label=label)

            # Letzter Wert auf Grafik
            if self.input_type == "K" or self.input_type == "P":
                ax.text(series.index[-1], series.iloc[-1]+0.2, f"{series.iloc[-1]:.2f}", ha="center", va="bottom", fontsize=12)

        ax.set_title(f"ETF-{self.title} – der letzten {self.last_days} Tage", fontsize=16)
        rot = 0 if self.last_days <= 25 else 15
        ax.tick_params(axis='x', labelsize=12, rotation=rot)
        ax.tick_params(axis='y', labelsize=12)
        ax.set_xlabel("Datum", fontsize=14)
        ax.set_ylabel(self.title, fontsize=14)
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=math.ceil(self.last_days/15)))
        ncol = 2 if max_len < 40 else 1
        ax.legend(loc='upper left', bbox_to_anchor=(0, -0.10), fontsize=12, ncol=ncol)
        ax.grid(True)
        plt.tight_layout()
        st.pyplot(fig)


# ----------------
# Start Funktion
# ----------------
async def start():
    input_days = st.text_input("Anzahl Tage", value="100")
    last_days = int(input_days)
    e = ETFVergleich()
    await e.etf_load_data(last_days)
    selected = await e.etf_eingaben()
    await e.etf_read(selected)
    await e.etf_output()


asyncio.run(start())
