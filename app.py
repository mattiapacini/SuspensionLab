import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import os
from datetime import datetime

# ==============================================================================
# 1. MOTORE FISICO & VALIDATORI (Il cervello)
# ==============================================================================
class PhysicsEngine:
    
    @staticmethod
    def validate_stack(stack_df, d_port, r_port):
        """Controlla errori comuni nell'assemblaggio lamelle"""
        if stack_df is None or stack_df.empty:
            return [], [] # Nessun dato, nessun errore
            
        errors = []
        warnings = []
        
        # 1. Controllo Copertura Porta (Face Shim)
        try:
            first_shim = stack_df.iloc[0]
            # La prima lamella deve essere più grande della porta + tenuta
            min_required = (r_port * 2) + 2.0 
            if first_shim['OD'] < min_required:
                errors.append(f"⛔ ERRORE: La prima lamella ({first_shim['OD']}mm) è troppo piccola! La porta è larga e serve almeno {min_required:.1f}mm.")
        except:
            pass

        # 2. Controllo Piramide Invertita (Lamella grande sopra piccola)
        try:
            prev_od = stack_df.iloc[0]['OD']
            for i, row in stack_df.iloc[1:].iterrows():
                curr_od = row['OD']
                if curr_od > prev_od + 2.0: # Tolleranza per ring/crossover
                    warnings.append(f"⚠️ AVVISO: Lamella #{i+1} ({curr_od}mm) è più grande di quella sotto ({prev_od}mm). Verifica se è corretto.")
                prev_od = curr_od
        except:
            pass
            
        return errors, warnings

    @staticmethod
    def calc_areas(inputs):
        """Calcola le aree di passaggio per avvisi di strozzatura"""
        # Area Faccia (Curtain Area approx)
        perimeter = 2 * np.pi * inputs.get('r_port', 12)
        area_face = perimeter * inputs.get('d_port', 14) * 0.5 # Stima apertura media
        
        # Area Gola (Throat - Restrizione Interna)
        n_thrt = inputs.get('n_thrt', 3)
        d_thrt = inputs.get('d_thrt', 9)
        area_thrt = n_thrt * np.pi * (d_thrt / 2)**2
        
        return area_face, area_thrt

# ==============================================================================
# 2. GESTIONE DATABASE (Salvataggio)
# ==============================================================================
class SuspensionDB:
    def __init__(self, db_file="suspension_master_db.json"):
        self.db_file = db_file
        self.load()

    def load(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = {}

    def save(self, meta, inputs):
        date_str = datetime.now().strftime("%Y-%m-%d")
        setup_id = f"{meta['bike']} - {meta['track']} ({date_str})"
        self.data[setup_id] = {"meta": meta, "inputs": inputs}
        with open(self.db_file, 'w') as f:
            json.dump(self.data, f, indent=4)
        return setup_id

    def get_list(self, filter_type=None):
        if filter_type:
            return [k for k,v in self.data.items() if v['meta']['type'] == filter_type]
        return list(self.data.keys())

    def get(self, setup_id):
        return self.data.get(setup_id)

db = SuspensionDB()

# ==============================================================================
# 3. INTERFACCIA UTENTE (UI)
# ==============================================================================
st.set_page_config(page_title="Suspension Lab MASTER", layout="wide", page_icon="🔧")

# CSS per compattare
st.markdown("""<style>.stTabs [data-baseweb="tab-list"] { gap: 8px; }</style>""", unsafe_allow_html=True)

# --- SIDEBAR: GESTIONE ---
with st.sidebar:
    st.title("🗂️ Archivio")
    mode = st.radio("Azione:", ["📝 Nuovo / Modifica", "📊 Confronta Storico"])
    
    if mode == "📝 Nuovo / Modifica":
        st.markdown("---")
        st.subheader("Carica Setup")
        history = db.get_list()
        load_sel = st.selectbox("Seleziona:", ["-- Vuoto --"] + history)
        if st.button("📥 Carica"):
            st.session_state['active_setup'] = db.get(load_sel) if load_sel != "-- Vuoto --" else {}
            st.rerun()

# Recupera dati sessione
act_rec = st.session_state.get('active_setup', {})
meta = act_rec.get('meta', {})
data = act_rec.get('inputs', {})

# ==============================================================================
# FUNZIONE GENERATORE VALVOLE (Questa contiene TUTTI i tuoi campi)
# ==============================================================================
def render_valve_detailed(label, key, has_hsc=False, is_mid=False):
    """Genera la scheda completa per una singola valvola"""
    st.markdown(f"#### 🔩 {label}")
    
    t_geo, t_stack = st.tabs(["📐 Geometria & Port", "🥞 Shim Stack"])
    
    # --- TAB GEOMETRIA (Tutti i campi che volevi) ---
    with t_geo:
        c1, c2, c3 = st.columns(3)
        
        # COL 1: Faccia Pistone
        with c1:
            st.caption("Faccia Pistone")
            r_port = st.number_input(f"r.port (Raggio)", value=data.get(f'{key}_r', 12.0), key=f'{key}_r')
            d_port = st.number_input(f"d.port (Largh. Porta)", value=data.get(f'{key}_d', 14.0), key=f'{key}_d')
            w_seat = st.number_input(f"w.seat (Largh. Sede)", value=data.get(f'{key}_w', 1.5), key=f'{key}_w', help="Larghezza della battuta di tenuta")
            h_deck = st.number_input(f"h.deck (Dish/Precarico)", value=data.get(f'{key}_h', 0.0), step=0.05, key=f'{key}_h', help="Concavità pistone")

        # COL 2: Interno (Throat) & Leak
        with c2:
            st.caption("Interno & Leak")
            d_thrt = st.number_input(f"d.thrt (Gola)", value=data.get(f'{key}_dt', 9.0), key=f'{key}_dt')
            n_thrt = st.number_input(f"n.thrt (N. Fori)", value=data.get(f'{key}_nt', 3), key=f'{key}_nt')
            d_leak = st.number_input(f"d.leak (Bleed Fisso)", value=data.get(f'{key}_dl', 0.0), key=f'{key}_dl')
            
            # Verifica Strozzatura Live
            a_face, a_thrt = PhysicsEngine.calc_areas({
                'r_port':r_port, 'd_port':d_port, 'd_thrt':d_thrt, 'n_thrt':n_thrt
            })
            if a_thrt < a_face * 0.9:
                st.warning(f"⚠️ Strozzatura Interna: Gola ({a_thrt:.1f}) < Faccia ({a_face:.1f})")

        # COL 3: Registri & HSC
        with c3:
            st.caption("Registri")
            st.number_input(f"d.bleed (Spillo)", value=data.get(f'{key}_bl', 0.0), key=f'{key}_bl')
            clicks = st.slider(f"Clicker", 0, 30, data.get(f'{key}_clk', 12), key=f'{key}_clk')
            
            if has_hsc:
                st.error("🔴 HSC Setup")
                st.selectbox("Tipo HSC", ["Molla", "Stack"], key=f'{key}_hsct')
                st.number_input("Precarico HSC", value=data.get(f'{key}_hscp', 0.0), step=0.1, key=f'{key}_hscp')

    # --- TAB STACK (Editor + Validatore) ---
    with t_stack:
        col_ed, col_val = st.columns([3, 1])
        
        with col_ed:
            # Recupera lo stack salvato o usa default
            saved_stack = data.get(f'{key}_stack')
            if saved_stack:
                df_start = pd.DataFrame(saved_stack)
            else:
                df_start = pd.DataFrame([{"Qty":1, "OD":30.0, "Thk":0.20}, {"Qty":1, "OD":28.0, "Thk":0.20}])
                
            edited_df = st.data_editor(df_start, num_rows="dynamic", use_container_width=True, key=f'{key}_df')
            
            if is_mid:
                st.number_input("Float / Gioco (mm)", value=data.get(f'{key}_float', 0.3), step=0.05, key=f'{key}_float')

        with col_val:
            # Esegue il validatore in tempo reale
            errs, warns = PhysicsEngine.validate_stack(edited_df, d_port, r_port)
            if errs: 
                for e in errs: st.error(e)
            elif warns:
                for w in warns: st.warning(w)
            else:
                st.success("✅ Stack OK")
                
    return {
        "stack": edited_df.to_dict('records'),
        "r_port": r_port, "d_port": d_port, "w_seat": w_seat, "h_deck": h_deck,
        "d_thrt": d_thrt, "n_thrt": n_thrt, "d_leak": d_leak, 
        "clicks": clicks
    }


# ==============================================================================
# MAIN PAGE LOGIC
# ==============================================================================

if mode == "📝 Nuovo / Modifica":
    st.title("🛠️ Suspension Lab Master")
    
    # 1. HEADER GENERALE
    c_gen1, c_gen2, c_gen3, c_gen4 = st.columns(4)
    comp_type = c_gen1.selectbox("Tipo Componente", ["FORCELLA (Fork)", "MONO (Shock)"], index=0 if meta.get('type')!="Shock" else 1)
    d_rod = c_gen2.number_input("Ø Stelo (Rod)", value=data.get('d_rod', 16.0))
    d_pist = c_gen3.number_input("Ø Pistone (Valve)", value=data.get('d_pist', 50.0))
    p_gas = c_gen4.number_input("Pressione Gas (Bar)", value=data.get('p_gas', 10.0))
    
    # Input Cliente
    c_cli1, c_cli2 = st.columns(2)
    bike = c_cli1.text_input("Moto", value=meta.get('bike', ''))
    track = c_cli2.text_input("Pista/Cliente", value=meta.get('track', ''))

    st.markdown("---")

    # 2. CONFIGURAZIONE VALVOLE (Dinamica)
    inputs_collected = {} # Qui raccogliamo tutto per il salvataggio

    if "Fork" in comp_type:
        # Struttura Forcella: BVc + MVc + MVr
        tab_bv, tab_mv_c, tab_mv_r = st.tabs(["🟦 BASE VALVE (Comp)", "🟧 MID VALVE (Comp)", "🟨 MID VALVE (Reb)"])
        
        with tab_bv: 
            inputs_collected['bvc'] = render_valve_detailed("Base Valve Comp", "bvc", has_hsc=False)
        with tab_mv_c: 
            inputs_collected['mvc'] = render_valve_detailed("Mid Valve Comp", "mvc", has_hsc=False, is_mid=True)
        with tab_mv_r: 
            inputs_collected['mvr'] = render_valve_detailed("Mid Valve Reb", "mvr", has_hsc=False)
            
    else: # SHOCK
        # Struttura Mono: Adjuster (HSC) + Main (Comp/Reb)
        tab_adj, tab_main_c, tab_main_r = st.tabs(["🎛️ ADJUSTER (BVC+HSC)", "🟧 MAIN PISTON (Comp)", "🟨 MAIN PISTON (Reb)"])
        
        with tab_adj:
            inputs_collected['bvc'] = render_valve_detailed("Adjuster / BVC", "bvc", has_hsc=True)
        with tab_main_c:
            inputs_collected['mvc'] = render_valve_detailed("Main Piston Comp", "mvc", has_hsc=False, is_mid=True)
        with tab_main_r:
            inputs_collected['mvr'] = render_valve_detailed("Main Piston Reb", "mvr", has_hsc=False)

    st.markdown("---")

    # 3. AZIONI & SIMULAZIONE
    col_act1, col_act2 = st.columns([1, 3])
    
    with col_act1:
        st.write("### 🏁 Azioni")
        if st.button("💾 SALVA PROGETTO", type="primary", use_container_width=True):
            if bike:
                final_inputs = {**inputs_collected, "d_rod":d_rod, "d_pist":d_pist, "p_gas":p_gas}
                final_meta = {"bike": bike, "track": track, "type": "Fork" if "Fork" in comp_type else "Shock"}
                db.save(final_meta, final_inputs)
                st.success("✅ Salvato nel Database!")
            else:
                st.error("Inserisci almeno il nome della Moto.")

        # Bottone per calcolare (simulazione)
        calc_clicked = st.button("🚀 CALCOLA TARATURA", use_container_width=True)

    with col_act2:
        # 4. RISULTATI SIMULAZIONE
        if calc_clicked:
            st.subheader("📊 Analisi Risultati")
            
            # Simulazione Dati (Placeholder basato su input reali)
            v = np.linspace(0, 4, 50)
            
            # Recuperiamo rigidità (simbolica) dagli stack inseriti per rendere il grafico vivo
            k_base = len(inputs_collected['bvc']['stack']) * 5
            k_mid = len(inputs_collected['mvc']['stack']) * 5
            
            # Forze Totali
            f_tot = v * (k_base + k_mid)
            f_click_min = f_tot * 1.2 # Tutto chiuso
            f_click_max = f_tot * 0.8 # Tutto aperto
            
            # Pressioni (Logica Cavitazione Semplificata per display)
            # Pressione Base = P_gas + resistenza BVC
            p_base = p_gas + (v * k_base / 10) 
            # Depressione Mid = P_base - caduta MVC
            p_mid_cham = p_base - (v * k_mid / 15)

            # --- GRAFICO 1: Clicker Map ---
            fig1 = go.Figure()
            # Area Grigia Range
            fig1.add_trace(go.Scatter(
                x=np.concatenate([v, v[::-1]]),
                y=np.concatenate([f_click_max, f_click_min[::-1]]),
                fill='toself', fillcolor='rgba(180,180,180,0.3)', 
                line=dict(color='rgba(255,255,255,0)'), name='Range Regolazioni'
            ))
            fig1.add_trace(go.Scatter(x=v, y=f_tot, line=dict(color='red', width=3), name='Attuale'))
            
            # Zone Velocità
            
            fig1.add_vrect(x0=0, x1=0.3, fillcolor="green", opacity=0.1, annotation_text="Low Speed")
            
            st.plotly_chart(fig1, use_container_width=True)
            
            # --- GRAFICO 2: Pressioni (Cavitazione) ---
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=v, y=p_base, name='Pressione Base (BV)', line=dict(color='green')))
            fig2.add_trace(go.Scatter(x=v, y=p_mid_cham, name='Pressione Mid (Reb Chamber)', line=dict(color='blue')))
            fig2.add_hline(y=0, line_color="red", line_dash="dash", annotation_text="CAVITAZIONE")
            
            if np.min(p_mid_cham) < 0:
                st.error("⚠️ ALLARME: Rischio Cavitazione! (Linea blu sotto zero)")
            else:
                st.success("✅ Pressioni Sicure")
                
            st.plotly_chart(fig2, use_container_width=True)

            # --- 5. WEIGHT SCALING (Appare solo ORA) ---
            st.divider()
            st.write("### ⚖️ Adattamento Peso (Post-Process)")
            cw1, cw2 = st.columns(2)
            w_start = cw1.number_input("Peso Attuale", 75.0)
            w_target = cw2.number_input("Peso Target", 85.0)
            
            if w_target != w_start:
                factor = w_target / w_start
                st.info(f"Per il nuovo peso serve il **{(factor-1)*100:+.1f}%** di forza in più.")
                # Proietta la curva target sul grafico (simulazione mentale)
                st.caption("Usa questa percentuale per indurire gli stack sopra.")

elif mode == "📊 Confronta Storico":
    st.header("Confronto Tarature")
    # Codice confronto (semplificato per brevità, usa db.get_list)
    opts = db.get_list()
    sels = st.multiselect("Scegli setup:", opts)
    if sels:
        st.write("Funzione confronto attiva...")
