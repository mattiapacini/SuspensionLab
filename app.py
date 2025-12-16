import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import os
from datetime import datetime

# ==========================================
# 1. GESTORE DATABASE (Predisposto per Google Drive)
# ==========================================
class SuspensionDB:
    def __init__(self):
        # Per ora usiamo un file locale JSON. 
        # Nel prossimo step lo collegheremo a Google Sheets.
        self.db_file = "suspension_db.json"
        self.load_db()

    def load_db(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = {}

    def save_setup(self, meta, inputs):
        # Genera ID univoco: "Honda CRF250 - Pista Sabbia (2023-12-16)"
        date_str = datetime.now().strftime("%Y-%m-%d")
        setup_id = f"{meta['bike']} - {meta['track']} ({date_str})"
        
        record = {
            "meta": meta,     # Info cliente/moto
            "inputs": inputs, # Tutti i dati tecnici (lamelle, clicker...)
            "timestamp": str(datetime.now())
        }
        
        self.data[setup_id] = record
        
        # Salvataggio fisico
        with open(self.db_file, 'w') as f:
            json.dump(self.data, f, indent=4)
            
        return setup_id

    def get_list(self, filter_type=None):
        # Restituisce la lista dei setup salvati
        if filter_type:
            # Filtra per "Fork" o "Shock"
            return [k for k, v in self.data.items() if v['meta']['type'] == filter_type]
        return list(self.data.keys())

    def get_record(self, setup_id):
        return self.data.get(setup_id)

# Inizializza il Database
db = SuspensionDB()

# ==========================================
# 2. CONFIGURAZIONE PAGINA E SIDEBAR
# ==========================================
st.set_page_config(page_title="Suspension Lab Cloud", layout="wide", page_icon="🔧")

with st.sidebar:
    st.title("🔧 Suspension Lab")
    st.markdown("---")
    
    # MODALITÀ DI LAVORO
    work_mode = st.radio("Modalità:", ["📝 Nuovo / Modifica", "📊 Confronta Storico"])
    
    st.markdown("---")
    
    # GESTIONE CARICAMENTO (Se siamo in modifica)
    if work_mode == "📝 Nuovo / Modifica":
        st.subheader("📂 Carica Setup")
        history = db.get_list()
        selected_load = st.selectbox("Seleziona dallo storico:", ["-- Nuovo (Vuoto) --"] + history)
        
        if st.button("📥 Carica Dati"):
            if selected_load != "-- Nuovo (Vuoto) --":
                rec = db.get_record(selected_load)
                st.session_state['active_setup'] = rec
                st.success(f"Caricato: {selected_load}")
                st.rerun()
            else:
                st.session_state['active_setup'] = {}
                st.rerun()

# Recupera dati attivi dalla sessione (se caricati)
active_rec = st.session_state.get('active_setup', {})
act_meta = active_rec.get('meta', {})
act_inp = active_rec.get('inputs', {})

# ==========================================
# 3. INTERFACCIA PRINCIPALE
# ==========================================

if work_mode == "📝 Nuovo / Modifica":
    st.header("🛠️ Configurazione Sospensione")

    # --- DATI CLIENTE / MOTO ---
    col1, col2, col3 = st.columns([1, 2, 2])
    with col1:
        # Selettore fondamentale che cambia tutta l'interfaccia
        comp_type = st.selectbox("Componente", ["FORCELLA (Fork)", "MONO (Shock)"], 
                                 index=0 if act_meta.get('type') != 'Shock' else 1)
        is_fork = "Fork" in comp_type
    with col2:
        in_bike = st.text_input("Moto / Modello", value=act_meta.get('bike', ''))
    with col_3:
        in_track = st.text_input("Pista / Cliente", value=act_meta.get('track', ''))

    st.markdown("---")

    # --- TABBED INTERFACE (Il flusso di lavoro) ---
    tab_geo, tab_shim, tab_hyd, tab_sim = st.tabs([
        "📐 1. Geometria Valvola", 
        "🥞 2. Shim Stack", 
        "🛢️ 3. Idraulica & Housing",
        "🚀 4. Simulazione"
    ])

    # ---------------- TAB 1: GEOMETRIA ----------------
    with tab_geo:
        c_g1, c_g2 = st.columns(2)
        with c_g1:
            st.subheader("Geometria Pistone")
            r_port = st.number_input("r.port (Raggio Porta mm)", value=act_inp.get('r_port', 12.0))
            d_port = st.number_input("d.port (Largh. Porta mm)", value=act_inp.get('d_port', 14.0))
            w_seat = st.number_input("w.seat (Largh. Sede mm)", value=act_inp.get('w_seat', 1.5), help="Fondamentale per calcolo apertura")
            d_thrt = st.number_input("d.thrt (Gola Interna mm)", value=act_inp.get('d_thrt', 9.0))
        
        with c_g2:
            st.subheader("Bypass & Clicker")
            if is_fork:
                st.info("Sistema Cartuccia Forcella")
                d_bleed = st.number_input("d.bleed (Diametro Spillo)", value=act_inp.get('d_bleed', 2.5))
            else:
                st.info("Sistema Albero Mono")
                d_bleed = st.number_input("d.bleed (Diametro Spillo Ritorno)", value=act_inp.get('d_bleed', 3.0))
            
            clicks = st.slider("Click Aperti (da tutto chiuso)", 0, 30, act_inp.get('clicks', 12))

    # ---------------- TAB 2: SHIM STACK ----------------
    with tab_shim:
        st.subheader("Composizione Pacco Lamellare")
        st.caption("Inserire le lamelle partendo dalla faccia del pistone.")
        
        # Editor Lamelle
        default_stack = pd.DataFrame([
            {"Qty": 1, "OD": 30.0, "Thk": 0.15}, 
            {"Qty": 1, "OD": 28.0, "Thk": 0.15},
            {"Qty": 1, "OD": 26.0, "Thk": 0.15},
            {"Qty": 1, "OD": 18.0, "Thk": 0.10}
        ])
        
        # Se abbiamo caricato dati, usiamo quelli
        if 'stack' in act_inp:
            start_df = pd.DataFrame(act_inp['stack'])
        else:
            start_df = default_stack

        edited_stack = st.data_editor(start_df, num_rows="dynamic", use_container_width=True)

    # ---------------- TAB 3: IDRAULICA ----------------
    with tab_hyd:
        c_h1, c_h2 = st.columns(2)
        with c_h1:
            st.subheader("Fluido")
            visc = st.number_input("Viscosità (cSt @ 40°C)", value=act_inp.get('visc', 14.0))
        with c_h2:
            st.subheader("Compensazione (Cavitazione)")
            if is_fork:
                # Logica specifica Forcella
                h_type = st.selectbox("Tipo Compensazione", ["Molla ICS", "Cartuccia Chiusa (Aria)", "Aperta"], 
                                      index=0)
                if h_type == "Molla ICS":
                    k_ics = st.number_input("K Molla ICS (N/mm)", value=2.0)
                    
            else:
                # Logica specifica Mono
                h_type = st.selectbox("Tipo Compensazione", ["Bladder", "Pistone Separatore"], index=0)
                p_gas = st.number_input("Pressione Gas (bar)", value=act_inp.get('p_gas', 10.0))
                

    # ---------------- TAB 4: SIMULAZIONE & SAVE ----------------
    with tab_sim:
        st.success("Configurazione pronta.")
        
        if st.button("💾 SALVA NEL CLOUD", type="primary"):
            if in_bike and in_track:
                # 1. Raccogli Dati
                new_meta = {"type": "Fork" if is_fork else "Shock", "bike": in_bike, "track": in_track}
                new_inp = {
                    "r_port": r_port, "d_port": d_port, "w_seat": w_seat, "d_thrt": d_thrt,
                    "d_bleed": d_bleed, "clicks": clicks,
                    "stack": edited_stack.to_dict('records'), # Converte DF in lista
                    "visc": visc, "p_gas": p_gas if not is_fork else 0
                }
                
                # 2. Salva nel DB
                saved_id = db.save_setup(new_meta, new_inp)
                st.balloons()
                st.success(f"Salvato correttamente: {saved_id}")
            else:
                st.error("Inserisci almeno Nome Moto e Pista per salvare.")

elif work_mode == "📊 Confronta Storico":
    st.header("📈 Analisi Comparativa")
    
    # FILTRO: Mostra solo forcelle o solo mono
    filter_choice = st.radio("Filtra componente:", ["Fork", "Shock"], horizontal=True)
    available = db.get_list("Fork" if filter_choice=="Fork" else "Shock")
    
    selected_compare = st.multiselect("Scegli setup da sovrapporre (Max 3):", available)
    
    if selected_compare:
        fig = go.Figure()
        
        # CICLO SUI SETUP SELEZIONATI
        for setup_id in selected_compare:
            rec = db.get_record(setup_id)
            inputs = rec['inputs']
            
            # --- QUI VA IL MOTORE DI CALCOLO IDRAULICO ---
            # (Per ora simuliamo una curva basata sulla rigidità dello stack per dimostrazione)
            
            # Calcolo finto rigidità stack (somma spessori al cubo)
            stack_stiffness = sum([row['Thk']**3 * row['OD'] for row in inputs['stack']]) * 100
            clicker_flow = inputs['clicks'] * 2
            
            v = np.linspace(0, 4, 100)
            # Formula fisica simulata: Forza = (Vel * Rigidità) - (Bypass Clicker)
            force = (v * stack_stiffness) / (1 + clicker_flow * 0.1) 
            
            fig.add_trace(go.Scatter(x=v, y=force, mode='lines', name=setup_id))
        
        fig.update_layout(title="Confronto Curve (Forza vs Velocità)", 
                          xaxis_title="Velocità Stelo (m/s)", yaxis_title="Forza (kgf)",
                          hovermode="x unified")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabella differenze
        st.write("#### 📋 Dati a confronto")
        comp_data = []
        for sid in selected_compare:
            i = db.get_record(sid)['inputs']
            comp_data.append({
                "Setup": sid,
                "Clicker": i['clicks'],
                "Olio (cSt)": i['visc'],
                "r.port": i['r_port']
            })
        st.table(pd.DataFrame(comp_data))

    else:
        st.info("Seleziona i setup dal menu sopra per vedere il confronto.")
