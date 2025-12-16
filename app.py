import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import os
from datetime import datetime

# ==============================================================================
# 1. MOTORE FISICO (Logica Pressioni)
# ==============================================================================
class SuspensionSystem:
    def __init__(self):
        self.general = {
            "d_rod": 16.0,      # Diametro stelo standard mono
            "d_piston": 50.0,   # Diametro pistone standard
            "oil_visc": 14.0,
            "gas_pressure": 10.0, # Bar
            "comp_sys": "Bladder"
        }
        self.inputs = {} # Qui salveremo tutti i dati delle valvole

    def calcola_aree(self):
        # Calcolo aree idrauliche fondamentali
        d_rod = self.general['d_rod']
        d_pist = self.general['d_piston']
        
        area_rod = np.pi * (d_rod/2)**2            # Area che sposta olio verso la BVC
        area_pist = np.pi * (d_pist/2)**2          # Area totale pistone
        area_annulus = area_pist - area_rod        # Area anulare (dove lavora la Mid in estensione)
        
        return area_rod, area_pist, area_annulus

    def simulazione_pressioni(self, v_max=5.0):
        """
        Simula il bilancio delle PRESSIONI per la cavitazione.
        """
        v = np.linspace(0, v_max, 50)
        area_rod, area_pist, area_annulus = self.calcola_aree()
        
        # Recuperiamo fattori di rigidezza (simulati per ora, poi saranno reali dal calcolo lamelle)
        # Nota: Questi valori verrebbero dal calcolo dello Stack tab per tab
        k_bvc = 1500 # Resistenza BVC (Adjuster)
        k_mvc = 1200 # Resistenza MVC (Main Piston)
        
        # 1. PRESSIONE BASE (Back Pressure)
        # La BVC crea pressione perché l'asta entra e spinge olio.
        # P_base = P_gas + (Forza_BVC / Area_Rod)
        # Più l'asta è grossa, più olio sposta, più la BVC lavora.
        flow_bvc = v * area_rod 
        force_bvc = flow_bvc * k_bvc / 10000 # Scaling factor fittizio
        p_base = self.general['gas_pressure'] + (force_bvc / area_rod * 10) # Convert approx to Bar
        
        # 2. CADUTA DI PRESSIONE MID VALVE (Pressure Drop)
        # La MVC crea una caduta di pressione dietro al pistone.
        # Delta_P_mid = Forza_MVC / Area_Pistone_Netta
        flow_mvc = v * area_annulus
        force_mvc = flow_mvc * k_mvc / 10000
        delta_p_mvc = force_mvc / (area_pist - area_rod) * 10
        
        # 3. PRESSIONE RISULTANTE (Dietro il pistone)
        # P_rebound_chamber = P_base - Delta_P_mid
        # Se questo valore va < 0, stiamo cavitando.
        p_result = p_base - delta_p_mvc
        
        return v, p_base, delta_p_mvc, p_result

# Init Session
if 'system' not in st.session_state:
    st.session_state['system'] = SuspensionSystem()
sys = st.session_state['system']

# ==============================================================================
# 2. UI SETUP
# ==============================================================================
st.set_page_config(page_title="Suspension Lab V5", layout="wide", page_icon="⚙️")
st.title("🔧 Suspension Lab V5 - Pressure Analysis")

# --- HEADER GEOMETRIA CRITICA ---
st.markdown("### 1. Dati Generali Componente")
c1, c2, c3, c4 = st.columns(4)
sys.general['d_rod'] = c1.number_input("Ø Stelo (Rod) mm", value=sys.general['d_rod'], step=1.0)
sys.general['d_piston'] = c2.number_input("Ø Pistone (Valve) mm", value=sys.general['d_piston'], step=1.0)
sys.general['gas_pressure'] = c3.number_input("Pressione Gas (Bar)", value=10.0, step=1.0)
comp_type = c4.selectbox("Tipo Sospensione", ["MONO (Shock)", "FORCELLA (Fork)"])

st.markdown("---")

# ==============================================================================
# 3. GESTIONE VALVOLE (La struttura a 3 Blocchi)
# ==============================================================================
st.markdown("### 2. Configurazione Valvole")

# Funzione per disegnare una valvola generica
def render_valve_tab(label, key_prefix, has_hsc=False):
    c_geo, c_stack = st.columns([1, 2])
    
    with c_geo:
        st.markdown(f"**Geometria {label}**")
        st.number_input("r.port", value=12.0, key=f"{key_prefix}_r")
        st.number_input("d.thrt (Gola)", value=9.0, key=f"{key_prefix}_th")
        st.number_input("d.bleed (Clicker)", value=0.0, key=f"{key_prefix}_bl")
        
        if has_hsc:
            st.warning("🔴 HSC Configuration")
            st.selectbox("Sistema HSC", ["Molla (Spring)", "Lamelle (Stack)"], key=f"{key_prefix}_hsct")
            st.number_input("Precarico / Gap", value=0.0, step=0.1, key=f"{key_prefix}_hscp")

    with c_stack:
        st.markdown(f"**Stack {label}**")
        df = pd.DataFrame([{"Qty":1, "OD":30, "Thk":0.20}, {"Qty":1, "OD":28, "Thk":0.20}])
        st.data_editor(df, num_rows="dynamic", key=f"{key_prefix}_stack", use_container_width=True)

# LOGICA TAB
if comp_type == "MONO (Shock)":
    # Qui applichiamo la logica che hai chiesto: BVC (Adjuster) + Main Piston (MVC/MVR)
    tab1, tab2, tab3 = st.tabs(["BVC (Adjuster/Reservoir)", "MVC (Main Piston)", "MVR (Main Piston)"])
    
    with tab1:
        st.info("Configurazione 'Bombolino' - Base Valve Compression")
        render_valve_tab("BVC", "bvc", has_hsc=True) # Solo qui c'è HSC
        
    with tab2:
        st.success("Configurazione Pistone - Lato Compressione")
        render_valve_tab("MVC", "mvc", has_hsc=False)
        
    with tab3:
        st.success("Configurazione Pistone - Lato Ritorno")
        render_valve_tab("MVR", "mvr", has_hsc=False)

else: # FORCELLA
    tab1, tab2, tab3 = st.tabs(["BVC (Base Valve)", "MVC (Mid Valve)", "MVR (Rebound)"])
    with tab1: render_valve_tab("BVC", "fork_bvc")
    with tab2: render_valve_tab("MVC", "fork_mvc")
    with tab3: render_valve_tab("MVR", "fork_mvr")

st.markdown("---")

# ==============================================================================
# 4. ANALISI PRESSIONI E CAVITAZIONE
# ==============================================================================
if st.button("🚀 LANCIA TEST PRESSIONI", type="primary", use_container_width=True):
    
    # Esegui simulazione
    v, p_base, delta_p_mvc, p_result = sys.simulazione_pressioni()
    
    col_chart, col_data = st.columns([3, 1])
    
    with col_chart:
        st.subheader("Grafico Bilancio Pressioni (Cavitation Check)")
        fig = go.Figure()
        
        # 1. Pressione di Base (Quella che ci protegge)
        fig.add_trace(go.Scatter(x=v, y=p_base, mode='lines', 
                                 name='Pressione Totale Disponibile (Gas + BVC)',
                                 line=dict(color='green', width=3)))
        
        # 2. Pressione Dietro al Pistone (Il risultato critico)
        # Se questa linea va sotto lo 0, stiamo cavitando
        fig.add_trace(go.Scatter(x=v, y=p_result, mode='lines', 
                                 name='Pressione Reale (Dietro Pistone)',
                                 line=dict(color='blue', width=3)))
        
        # 3. Linea Zero (Pericolo)
        fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="LIMITE CAVITAZIONE (Vuoto)")
        fig.add_hline(y=sys.general['gas_pressure'], line_dash="dot", line_color="gray", annotation_text="Pressione Statica Gas")

        # Riempimento zona pericolo
        fig.add_trace(go.Scatter(x=v, y=np.zeros_like(v), fill=None, mode='lines', line_color='red', showlegend=False))
        
        # Se cavita, colora l'area sotto zero
        fig.update_layout(xaxis_title="Velocità Stelo (m/s)", yaxis_title="Pressione (Bar)", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    
    with col_data:
        st.subheader("Esito")
        min_p = np.min(p_result)
        
        st.metric("Pressione Gas Statica", f"{sys.general['gas_pressure']} Bar")
        st.metric("Minima Pressione Raggiunta", f"{min_p:.2f} Bar", delta_color="normal" if min_p > 0 else "inverse")
        
        if min_p < 0:
            st.error(f"⚠️ CAVITAZIONE! Scendiamo a {min_p:.2f} Bar.")
            st.markdown("""
            **Soluzioni Possibili:**
            1. Aumentare Pressione Gas.
            2. Indurire BVC (Adjuster).
            3. Ammorbidire MVC (Pistone).
            """)
        else:
            st.success("✅ SISTEMA OK. Nessuna cavitazione rilevata.")

    # --- WEIGHT SCALING (Solo dopo calcolo) ---
    st.divider()
    with st.expander("⚖️ Adattamento Peso (Post-Process)"):
        st.write("Funzione disponibile ora che la taratura base è calcolata.")
        c_w1, c_w2 = st.columns(2)
        w_old = c_w1.number_input("Peso Attuale", 75)
        w_new = c_w2.number_input("Peso Target", 85)
        if w_new != w_old:
            factor = (w_new/w_old)
            st.info(f"Target Rigidità: +{(factor-1)*100:.1f}%")
