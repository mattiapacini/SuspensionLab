import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import os
from datetime import datetime

# ==========================================
# 1. MOTORE FISICO (Simulatore Python)
# ==========================================
class PhysicsEngine:
    """
    Simula la logica di ReStackor usando equazioni fluidodinamiche semplificate
    per permettere il rendering in tempo reale senza EXE esterno.
    """
    
    @staticmethod
    def calc_flow_area(r_port, d_port, w_seat):
        # Calcola l'area della faccia della valvola (Curtain Area approx)
        # Semplificazione: Area = Perimetro * Lift (qui usiamo area fissa per stima base)
        perimeter = 2 * np.pi * r_port 
        return perimeter * d_port # Approx area frontale

    @staticmethod
    def calc_throat_area(d_thrt, n_thrt):
        # Calcola l'area della gola interna (Restrizione)
        return n_thrt * np.pi * (d_thrt / 2)**2

    @staticmethod
    def validate_stack(stack_df, d_port, r_port):
        """Controlla errori comuni nell'assemblaggio"""
        errors = []
        warnings = []
        
        if stack_df.empty:
            errors.append("Il pacco lamellare è vuoto.")
            return errors, warnings

        # 1. Controllo Copertura Porta (Face Shim)
        first_shim = stack_df.iloc[0]
        min_required_od = (r_port * 2) + 2 # Margine di sicurezza
        if first_shim['OD'] < min_required_od:
            errors.append(f"⛔ ERRORE GRAVE: La prima lamella ({first_shim['OD']}mm) è troppo piccola per coprire la porta del pistone (serve > {min_required_od:.1f}mm). L'olio passerà diretto!")

        # 2. Controllo Piramide (Reverse Stack)
        current_od = first_shim['OD']
        for index, row in stack_df.iloc[1:].iterrows():
            if row['OD'] > current_od:
                # Se la lamella sopra è più grande, è un crossover o un errore?
                # Se la differenza è grande, probabile errore
                if row['OD'] > current_od + 2:
                    warnings.append(f"⚠️ Avviso Lamella #{index+1}: Lamella da {row['OD']}mm sopra una da {current_od}mm. Verifica che sia un crossover intenzionale.")
            current_od = row['OD']
            
        return errors, warnings

    @staticmethod
    def simulate_curve(inputs, v_max=5.0, steps=50, clicker_override=None):
        """
        Genera la curva Forza vs Velocità.
        """
        v = np.linspace(0, v_max, steps)
        
        # Recupera parametri
        clicks = inputs.get('clicks', 12) if clicker_override is None else clicker_override
        visc = inputs.get('visc', 14.0)
        r_port = inputs.get('r_port', 12.0)
        h_deck = inputs.get('h_deck', 0.0) # Precarico piatto
        
        # Calcolo Rigidità Stack (Metodo Cubico Semplificato)
        stack_data = pd.DataFrame(inputs['stack'])
        # Rigidità = Sum(Thickness^3 * Diameter) / Leva
        stack_stiffness = 0
        if not stack_data.empty:
            stack_stiffness = sum((row['Thk']**3) * row['OD'] for _, row in stack_data.iterrows())
        
        # Effetto Precarico (h.deck)
        preload_force = stack_stiffness * h_deck * 50 # Fattore arbitrario di scala fisica
        
        # Idraulica
        # Basse velocità: dominate dal bleed (clicker)
        # Alta velocità: dominate dallo stack + gola
        
        # Più click aperti = meno forza low speed
        # d.bleed approx factor
        bleed_factor = (30 - clicks) * 0.5 
        
        damping_low = v * (stack_stiffness * 2 + bleed_factor) * (visc/10)
        damping_high = v * (stack_stiffness * 0.8) + preload_force
        
        # Blend curve (Bernoulli transition)
        force = np.where(v < 0.3, damping_low, damping_high + (damping_low[10] if len(damping_low)>10 else 0))
        
        # Aggiungi turbolenza quadratica (High speed blow-off limitato dalla gola)
        # Se d.thrt è piccolo, la forza schizza in alto
        d_thrt = inputs.get('d_thrt', 99.0)
        n_thrt = inputs.get('n_thrt', 3)
        area_thrt = PhysicsEngine.calc_throat_area(d_thrt, n_thrt)
        
        # Restrizione quadratica
        restriction = (v**2) * (1000 / (area_thrt + 1)) 
        
        return v, force + restriction

# ==========================================
# 2. GESTIONE DB
# ==========================================
class SuspensionDB:
    def __init__(self, db_file="suspension_db.json"):
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

    def get_list(self, type_filter=None):
        if type_filter:
            return [k for k,v in self.data.items() if v['meta']['type'] == type_filter]
        return list(self.data.keys())
        
    def get(self, setup_id):
        return self.data.get(setup_id)

db = SuspensionDB()

# ==========================================
# 3. UI PRINCIPALE
# ==========================================
st.set_page_config(page_title="Suspension Lab V3", layout="wide", page_icon="⚙️")

# CSS per rendere le tabelle più compatte
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("🗂️ Gestione")
    mode = st.radio("Modalità", ["Nuovo / Modifica", "Confronto Curve"])
    
    if mode == "Nuovo / Modifica":
        st.markdown("---")
        st.subheader("Carica Setup")
        history = db.get_list()
        load_sel = st.selectbox("Seleziona:", ["-- Nuovo --"] + history)
        if st.button("Carica"):
            st.session_state['setup'] = db.get(load_sel) if load_sel != "-- Nuovo --" else {}
            st.experimental_rerun()

# Recupera dati sessione
curr = st.session_state.get('setup', {})
c_meta = curr.get('meta', {})
c_inp = curr.get('inputs', {})

# ==========================================
# MODALITÀ: NUOVO / MODIFICA
# ==========================================
if mode == "Nuovo / Modifica":
    st.title("🛠️ Progettazione Valvola")
    
    # Header Info
    col1, col2, col3 = st.columns([1,2,2])
    with col1:
        comp_type = st.selectbox("Componente", ["Fork", "Shock"], index=0 if c_meta.get('type')!="Shock" else 1)
    with col2:
        bike = st.text_input("Moto", value=c_meta.get('bike', ''))
    with col3:
        track = st.text_input("Pista/Cliente", value=c_meta.get('track', ''))

    # TABS
    tab1, tab2, tab3, tab4 = st.tabs(["1. Geometria Valvola", "2. Shim Stack", "3. Idraulica", "4. Simulazione & Weight"])

    # --- TAB 1: GEOMETRIA AVANZATA ---
    with tab1:
        col_face, col_internal = st.columns(2)
        
        with col_face:
            st.markdown("### 🔵 Faccia Pistone (Face)")
            st.caption("Dove appoggiano le lamelle")
            r_port = st.number_input("r.port (Raggio Porta)", value=c_inp.get('r_port', 12.0))
            d_port = st.number_input("d.port (Largh. Porta)", value=c_inp.get('d_port', 14.0))
            w_seat = st.number_input("w.seat (Largh. Sede)", value=c_inp.get('w_seat', 1.5))
            h_deck = st.number_input("h.deck (Dish/Precarico)", value=c_inp.get('h_deck', 0.0), step=0.05, help="Se > 0, le lamelle sono precaricate (pistone concavo)")

        with col_internal:
            st.markdown("### 🔴 Interno (Throat)")
            st.caption("Restrizioni di flusso interne")
            d_thrt = st.number_input("d.thrt (Diametro Gola)", value=c_inp.get('d_thrt', 9.0))
            n_thrt = st.number_input("n.thrt (Numero Fori)", value=c_inp.get('n_thrt', 3))
            d_leak = st.number_input("d.leak (Bleed Fisso)", value=c_inp.get('d_leak', 0.0))
            
            # Calcolo automatico verifica strozzatura
            area_face = PhysicsEngine.calc_flow_area(r_port, d_port, w_seat)
            area_thrt = PhysicsEngine.calc_throat_area(d_thrt, n_thrt)
            
            st.markdown("---")
            st.markdown(f"**Verifica Aree:**")
            st.text(f"Area Faccia (Face): {area_face:.1f} mm²")
            st.text(f"Area Gola (Throat): {area_thrt:.1f} mm²")
            
            if area_thrt < area_face * 0.8:
                st.error("⚠️ ATTENZIONE: La valvola è strozzata internamente (Throat < Face). Modificare le lamelle potrebbe non avere effetto sulle alte velocità!")
            else:
                st.success("✅ Flusso ottimale: La restrizione principale sono le lamelle.")

    # --- TAB 2: SHIM STACK ---
    with tab2:
        st.subheader("Configurazione Lamelle")
        
        default_stack = pd.DataFrame([
            {"Qty": 1, "OD": 30.0, "Thk": 0.15}, 
            {"Qty": 1, "OD": 28.0, "Thk": 0.15},
            {"Qty": 1, "OD": 26.0, "Thk": 0.15},
            {"Qty": 1, "OD": 18.0, "Thk": 0.10}
        ])
        
        stack_df = st.data_editor(
            pd.DataFrame(c_inp.get('stack', default_stack.to_dict('records'))),
            num_rows="dynamic",
            use_container_width=True
        )
        
        # Validazione Live
        errs, warns = PhysicsEngine.validate_stack(stack_df, d_port, r_port)
        for e in errs: st.error(e)
        for w in warns: st.warning(w)

    # --- TAB 3: IDRAULICA ---
    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Olio & Clicker")
            visc = st.number_input("Viscosità (cSt @ 40°)", value=c_inp.get('visc', 14.0))
            clicks = st.slider("Click Aperti", 0, 30, c_inp.get('clicks', 12))
            st.caption("0 = Tutto Chiuso, 30 = Tutto Aperto")
            
        with c2:
            st.subheader("Compensazione")
            p_gas = st.number_input("Pressione Gas/Bladder (bar)", value=c_inp.get('p_gas', 10.0))

    # --- TAB 4: SIMULAZIONE & WEIGHT SCALING ---
    with tab4:
        st.markdown("### ⚖️ Weight Scaling & Analisi")
        
        sw_col1, sw_col2 = st.columns([1,3])
        
        with sw_col1:
            st.markdown("**Adattamento Peso**")
            w_curr = st.number_input("Peso Pilota Attuale (kg)", value=75.0)
            w_targ = st.number_input("Peso Pilota Target (kg)", value=75.0)
            
            scaling_factor = 1.0
            if w_targ != w_curr and w_curr > 0:
                scaling_factor = w_targ / w_curr
                st.info(f"Target Forza: {scaling_factor*100:.0f}%")
            
            v_max_sim = st.slider("Vel. Max Grafico", 1.0, 10.0, 4.0)

        with sw_col2:
            if st.button("🚀 CALCOLA CURVE", type="primary"):
                # Raccogli input per il motore
                inputs = {
                    "r_port": r_port, "d_port": d_port, "d_thrt": d_thrt, 
                    "n_thrt": n_thrt, "h_deck": h_deck, "stack": stack_df.to_dict('records'),
                    "clicks": clicks, "visc": visc
                }
                
                # 1. Calcola Curva Attuale
                v, f_curr = PhysicsEngine.simulate_curve(inputs, v_max=v_max_sim)
                
                # 2. Calcola Range Clicker (Clicker Map)
                _, f_closed = PhysicsEngine.simulate_curve(inputs, v_max=v_max_sim, clicker_override=0)
                _, f_open = PhysicsEngine.simulate_curve(inputs, v_max=v_max_sim, clicker_override=30)
                
                # 3. Creazione Grafico
                fig = go.Figure()
                
                # Area Clicker (Grigia)
                fig.add_trace(go.Scatter(
                    x=np.concatenate([v, v[::-1]]),
                    y=np.concatenate([f_open, f_closed[::-1]]),
                    fill='toself',
                    fillcolor='rgba(200,200,200,0.3)',
                    line=dict(color='rgba(255,255,255,0)'),
                    name='Range Clicker (Min/Max)',
                    hoverinfo="skip"
                ))
                
                # Curva Attuale
                fig.add_trace(go.Scatter(x=v, y=f_curr, mode='lines', name='Setup Attuale', line=dict(color='red', width=3)))
                
                # Ghost Curve (Weight Scaled)
                if scaling_factor != 1.0:
                    f_target = f_curr * scaling_factor
                    fig.add_trace(go.Scatter(x=v, y=f_target, mode='lines', name=f'Target ({w_targ}kg)', line=dict(color='black', dash='dash')))

                # Zone colori
                
                fig.add_vrect(x0=0, x1=0.3, fillcolor="green", opacity=0.05, annotation_text="Low Speed", annotation_position="top left")
                
                fig.update_layout(
                    title="Analisi Forza Smorzamento",
                    xaxis_title="Velocità Stelo (m/s)",
                    yaxis_title="Forza (kgf)",
                    hovermode="x unified",
                    height=600
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
        # Pulsante salvataggio
        st.divider()
        if st.button("💾 SALVA NEL DB"):
            if bike:
                inputs_save = {
                    "r_port": r_port, "d_port": d_port, "d_thrt": d_thrt, 
                    "n_thrt": n_thrt, "h_deck": h_deck, "w_seat": w_seat,
                    "stack": stack_df.to_dict('records'),
                    "clicks": clicks, "visc": visc, "p_gas": p_gas
                }
                meta_save = {"bike": bike, "track": track, "type": comp_type}
                
                sid = db.save(meta_save, inputs_save)
                st.success(f"Salvato: {sid}")
            else:
                st.error("Inserisci nome Moto.")

# ==========================================
# MODALITÀ: CONFRONTO
# ==========================================
elif mode == "Confronto Curve":
    st.header("📊 Comparativa")
    
    # Filtro
    ftype = st.radio("Filtra:", ["Fork", "Shock"], horizontal=True)
    opts = db.get_list(ftype)
    sels = st.multiselect("Scegli Setup (Max 3):", opts)
    
    if sels:
        fig = go.Figure()
        for sid in sels:
            rec = db.get(sid)
            # Ricalcola al volo
            v, f = PhysicsEngine.simulate_curve(rec['inputs'], v_max=4.0)
            fig.add_trace(go.Scatter(x=v, y=f, name=sid))
            
        fig.update_layout(title="Confronto Diretto", xaxis_title="Vel (m/s)", yaxis_title="Forza (kgf)")
        st.plotly_chart(fig, use_container_width=True)
