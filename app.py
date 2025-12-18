import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from physics import SuspensionPhysics
from db_manager import SuspensionDB

# --- CONFIGURAZIONE UI ---
st.set_page_config(layout="wide", page_title="SuspensionLab", page_icon="⚙️")

# CSS
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #2b2b2b; border-radius: 5px; color: white; font-weight: bold;}
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: #e74c3c; color: white; }
    div[data-testid="stExpander"] { background-color: #1e1e1e; border: 1px solid #444; }
    .stMetric { background-color: #111; padding: 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- INIZIALIZZAZIONE ROBUSTA (Fix Crash) ---
# Controlliamo ogni singola chiave. Se manca, la creiamo.
if "fork_bv_df" not in st.session_state:
    st.session_state["fork_bv_df"] = pd.DataFrame([{"qty": 5, "od": 24.0, "th": 0.15}, {"qty": 1, "od": 18.0, "th": 0.10}])

if "fork_mv_df" not in st.session_state:
    st.session_state["fork_mv_df"] = pd.DataFrame([{"qty": 3, "od": 20.0, "th": 0.10}])

if "shock_comp_df" not in st.session_state:
    st.session_state["shock_comp_df"] = pd.DataFrame([{"qty": 8, "od": 44.0, "th": 0.20}, {"qty": 1, "od": 30.0, "th": 0.15}])

if "shock_reb_df" not in st.session_state:
    st.session_state["shock_reb_df"] = pd.DataFrame([{"qty": 4, "od": 40.0, "th": 0.15}])

# Ecco le chiavi che ti davano errore: le forziamo qui.
if "geo_f" not in st.session_state:
    st.session_state["geo_f"] = {
        'd_piston': 24.0, 'd_rod': 12.0, 'n_port': 4, 'w_port': 8.0, 
        'd_throat': 4.0, 'oil_visc': 15.0, 'clicks': 12
    }

if "geo_s" not in st.session_state:
    st.session_state["geo_s"] = {
        'd_piston': 50.0, 'd_rod': 18.0, 'n_port': 4, 'w_port': 12.0, 
        'd_throat': 6.0, 'oil_visc': 12.0, 'clicks': 15
    }

if "current_pilot_id" not in st.session_state:
    st.session_state["current_pilot_id"] = None

if "current_bike_id" not in st.session_state:
    st.session_state["current_bike_id"] = None

# --- FUNZIONI ---
def render_stack(key, label):
    st.markdown(f"**{label}**")
    return st.data_editor(
        st.session_state[f"{key}_df"],
        num_rows="dynamic",
        column_config={
            "qty": st.column_config.NumberColumn("Q.tà", min_value=1, format="%d"),
            "od": st.column_config.NumberColumn("Ø Est", format="%.1f"),
            "th": st.column_config.NumberColumn("Spess", format="%.2f")
        },
        use_container_width=True,
        key=f"editor_{key}"
    )

def calc_k(df):
    k = 0.0
    try:
        for _, r in df.iterrows(): k += (r['th']**3) * r['qty'] * 1000
    except: pass
    return max(k, 0.1)

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.title("🗂️ ARCHIVIO")
    
    # 1. PILOTI
    df_p = SuspensionDB.get_piloti()
    opt_p = ["SELEZIONA PILOTA..."] + df_p.apply(lambda x: f"{x['Nome']} (ID:{x['ID']})", axis=1).tolist()
    sel_p = st.selectbox("Pilota", opt_p)
    
    if sel_p != "SELEZIONA PILOTA...":
        # Gestione sicura dell'indice
        try:
            pid = df_p.iloc[opt_p.index(sel_p)-1]["ID"]
            st.session_state["current_pilot_id"] = pid
            
            # 2. MOTO
            df_m = SuspensionDB.get_garage(pid)
            opt_m = ["SELEZIONA MOTO..."]
            if not df_m.empty: opt_m += df_m.apply(lambda x: f"{x['marca']} {x['modello']}", axis=1).tolist()
            sel_m = st.selectbox("Garage", opt_m)
            
            if sel_m != "SELEZIONA MOTO...":
                mid = df_m.iloc[opt_m.index(sel_m)-1]["id_mezzo"]
                st.session_state["current_bike_id"] = mid
                
                # 3. SESSIONI
                st.divider()
                st.write("📂 **Storico Sessioni**")
                df_s = SuspensionDB.get_sessioni(mid)
                if not df_s.empty:
                    opt_s = df_s.apply(lambda x: f"{x['data']} | {x['pista_luogo']}", axis=1).tolist()
                    sel_s = st.selectbox("Carica Setup:", opt_s)
                    
                    if st.button("CARICA DATI", type="primary", use_container_width=True):
                        row = df_s.iloc[opt_s.index(sel_s)]
                        dati = SuspensionDB.parse_json(row['dati_tecnici_json'])
                        
                        # Ripristino Stack
                        if 'f_bv' in dati: st.session_state["fork_bv_df"] = pd.DataFrame(dati['f_bv'])
                        if 'f_mv' in dati: st.session_state["fork_mv_df"] = pd.DataFrame(dati['f_mv'])
                        if 's_comp' in dati: st.session_state["shock_comp_df"] = pd.DataFrame(dati['s_comp'])
                        if 's_reb' in dati: st.session_state["shock_reb_df"] = pd.DataFrame(dati['s_reb'])
                        
                        # Ripristino Geometrie (Importante!)
                        if 'geo_f' in dati: st.session_state["geo_f"] = dati['geo_f']
                        if 'geo_s' in dati: st.session_state["geo_s"] = dati['geo_s']
                        
                        st.toast("Setup Caricato con Successo!", icon="✅")
                        st.rerun()

                # SALVA
                with st.expander("💾 Salva Sessione Corrente"):
                    pista = st.text_input("Pista")
                    cond = st.selectbox("Condizione", ["Secco", "Fango", "Sabbia", "Duro"])
                    feed = st.text_area("Feedback")
                    if st.button("SALVA"):
                        pack = {
                            "f_bv": st.session_state["fork_bv_df"].to_dict('records'),
                            "f_mv": st.session_state["fork_mv_df"].to_dict('records'),
                            "s_comp": st.session_state["shock_comp_df"].to_dict('records'),
                            "s_reb": st.session_state["shock_reb_df"].to_dict('records'),
                            "geo_f": st.session_state["geo_f"],
                            "geo_s": st.session_state["geo_s"]
                        }
                        SuspensionDB.save_session(mid, pista, cond, feed, 3, pack)
                        st.success("Salvato!")
        except Exception as e:
            st.error(f"Errore nel caricamento dati: {e}")

# ==============================================================================
# MAIN: TAB E SIMULATORE
# ==============================================================================

if not st.session_state["current_bike_id"]:
    st.info("👈 Seleziona Pilota e Moto dal menu laterale per iniziare.")
else:
    t_fork, t_shock, t_setup = st.tabs(["🔹 FORCELLA", "🔸 MONO", "⚖️ TELAIO / SAG"])

    # --- TAB 1: FORCELLA ---
    with t_fork:
        col_L, col_R = st.columns([1, 1.3])
        
        with col_L:
            st.subheader("🛠️ Taratura")
            st.session_state["fork_bv_df"] = render_stack("fork_bv", "Base Valve (BV)")
            st.divider()
            st.session_state["fork_mv_df"] = render_stack("fork_mv", "Mid Valve (MV)")
            
        with col_R:
            st.subheader("⚙️ Parametri Tecnici")
            # GEOMETRIA FORCELLA EDITABILE
            gf = st.session_state["geo_f"]
            with st.expander("📐 GEOMETRIA INTERNA (Manuale/Excel)", expanded=True):
                c1, c2 = st.columns(2)
                gf['d_piston'] = c1.number_input("Ø Pistone (mm)", 10.0, 50.0, float(gf['d_piston']), key="f_dp")
                gf['d_rod'] = c2.number_input("Ø Asta (mm)", 5.0, 20.0, float(gf['d_rod']), key="f_dr")
                c3, c4 = st.columns(2)
                gf['n_port'] = c3.number_input("N° Luci", 1, 10, int(gf['n_port']), key="f_np")
                gf['w_port'] = c4.number_input("Larghezza Luce (mm)", 1.0, 20.0, float(gf['w_port']), key="f_wp")
                
            with st.expander("🛢️ OLIO & CLICKER"):
                c5, c6 = st.columns(2)
                gf['oil_visc'] = c5.number_input("Viscosità (cSt)", 5.0, 50.0, float(gf['oil_visc']), key="f_oil")
                gf['clicks'] = c6.slider("Clicker Comp (Aperti)", 0, 30, int(gf['clicks']), key="f_clk")
            
            st.session_state["geo_f"] = gf # Save state

            # CALCOLO FISICO
            st.markdown("### 📈 Analisi")
            k_bv = calc_k(st.session_state["fork_bv_df"])
            vels = np.linspace(0.01, 5.0, 50)
            forces, lifts = [], []
            
            for v in vels:
                f, l = SuspensionPhysics.solve_damping(v, k_bv, gf, gf['oil_visc'], gf['clicks'])
                forces.append(f)
                lifts.append(l)
                
            # GRAFICO FORZA
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=vels, y=forces, line=dict(color='#3498db', width=3), name="Forza"))
            fig.update_layout(title="Curva Forza / Velocità", xaxis_title="Velocità (m/s)", yaxis_title="Forza (N)", height=300, template="plotly_dark", margin=dict(l=20,r=20,t=40,b=20))
            st.plotly_chart(fig, use_container_width=True)
            
            # VISUALIZER LAMELLA
            max_lift = max(lifts)
            st.info(f"Rigidezza Stack: **{k_bv:.2f}** | Apertura Max Lamella: **{max_lift:.2f} mm**")

    # --- TAB 2: MONO ---
    with t_shock:
        col_SL, col_SR = st.columns([1, 1.3])
        
        with col_SL:
            st.subheader("🛠️ Taratura Mono")
            st.session_state["shock_comp_df"] = render_stack("shock_comp", "Compressione")
            st.divider()
            st.session_state["shock_reb_df"] = render_stack("shock_reb", "Ritorno")
            
        with col_SR:
            st.subheader("⚙️ Parametri Mono")
            gs = st.session_state["geo_s"]
            with st.expander("📐 GEOMETRIA MONO", expanded=True):
                c1, c2 = st.columns(2)
                gs['d_piston'] = c1.number_input("Ø Pistone (mm)", 30.0, 60.0, float(gs['d_piston']), key="s_dp")
                gs['d_rod'] = c2.number_input("Ø Asta (mm)", 10.0, 25.0, float(gs['d_rod']), key="s_dr")
                c3, c4 = st.columns(2)
                gs['n_port'] = c3.number_input("N° Luci", 1, 10, int(gs['n_port']), key="s_np")
                gs['w_port'] = c4.number_input("Larghezza Luce (mm)", 5.0, 25.0, float(gs['w_port']), key="s_wp")
                
            with st.expander("🛢️ OLIO & REGOLAZIONI"):
                c5, c6 = st.columns(2)
                gs['oil_visc'] = c5.number_input("Viscosità (cSt)", 5.0, 50.0, float(gs['oil_visc']), key="s_oil")
                gs['clicks'] = c6.slider("Clicker Comp (Aperti)", 0, 30, int(gs['clicks']), key="s_clk")
            
            st.session_state["geo_s"] = gs

            # GRAFICO MONO
            k_sc = calc_k(st.session_state["shock_comp_df"])
            forces_s = []
            for v in vels:
                f, _ = SuspensionPhysics.solve_damping(v, k_sc, gs, gs['oil_visc'], gs['clicks'])
                forces_s.append(f)
                
            fig_s = go.Figure()
            fig_s.add_trace(go.Scatter(x=vels, y=forces_s, line=dict(color='#e74c3c', width=3), name="Mono"))
            fig_s.update_layout(title="Curva Compressione Mono", xaxis_title="Velocità (m/s)", yaxis_title="Forza (N)", height=300, template="plotly_dark", margin=dict(l=20,r=20,t=40,b=20))
            st.plotly_chart(fig_s, use_container_width=True)

    # --- TAB 3: TELAIO ---
    with t_setup:
        st.header("⚖️ Calcolo Sag e Molle")
        c1, c2, c3 = st.columns(3)
        
        # Recupera peso pilota dal DB se possibile
        w_default = 80.0
        if st.session_state["current_pilot_id"]:
            # Piccola query per prendere il peso fresco
            piloti = SuspensionDB.get_piloti()
            p_row = piloti[piloti["ID"] == str(st.session_state["current_pilot_id"])]
            if not p_row.empty and p_row.iloc[0]["Peso"]:
                try: w_default = float(p_row.iloc[0]["Peso"])
                except: pass

        p_pilota = c1.number_input("Peso Pilota (kg)", 40.0, 150.0, w_default)
        k_molla = c2.number_input("Molla Mono Attuale (N/mm)", 30.0, 80.0, 45.0)
        preload = c3.number_input("Precarico (mm)", 0.0, 20.0, 8.0)
        
        st.markdown("---")
        
        # Calcolo approssimativo Sag
        peso_totale_kg = 105 + p_pilota # Moto + Pilota
        carico_post_N = (peso_totale_kg * 0.65) * 9.81
        
        linkage_ratio = 3.0
        force_shock = carico_post_N * linkage_ratio
        
        sag_rider_calc = (force_shock / k_molla) - preload
        
        c_res1, c_res2 = st.columns(2)
        c_res1.metric("Rider Sag Stimato", f"{sag_rider_calc:.1f} mm", delta="Target: 105mm", delta_color="normal")
        
        if sag_rider_calc > 115:
            c_res2.error("⚠️ SAG ECCESSIVO: La molla è troppo morbida o serve più precarico.")
        elif sag_rider_calc < 95:
            c_res2.warning("⚠️ SAG RIDOTTO: La molla è troppo dura.")
        else:
            c_res2.success("✅ MOLLE OK: Il Sag è nel range corretto.")
