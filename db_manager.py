import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import json

class SuspensionDB:
    @staticmethod
    def get_connection():
        return st.connection("gsheets", type=GSheetsConnection)
    # ... (Il resto del codice DB è identico alla versione precedente)
    # Se non ce l'hai, fammelo sapere che lo rincollo, ma dovresti averlo.
