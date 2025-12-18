import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from physics import SuspensionPhysics
from db_manager import SuspensionDB

# --- CONFIGURAZIONE ---
st.set_page_config(layout="wide", page_title="SuspensionLab PRO", page_icon="⚙️")

# --- INIZIALIZZAZIONE SICURA (IL FIX PER LA MEMORIA) ---
# Questo blocco viene eseguito PRIMA di tutto il resto.
# Se mancano le chiavi, le crea. Non darà mai più KeyError.
if "init_done" not in st.session_state:
    # Tabelle Default
    st.session_state["fork_bv_df"] = pd.DataFrame([{"qty": 5, "od": 24.0, "th": 0.15}, {"qty": 1, "od": 18.0, "th": 0.10}])
    st.session_state["fork_mv_df"] = pd.DataFrame([{"qty": 3, "od": 20.0, "th": 0.10}])
    st.session_state["shock_comp_df"] = pd.DataFrame([{"qty": 8, "od": 44.0, "th": 0.20}, {"qty": 1, "od": 30.0, "th": 0.15}])
    st.session_state["shock_reb_df"] = pd.DataFrame([{"qty": 4, "od": 40.0, "th": 0.15}])
    
    # Geometrie Default (Queste sono quelle che mancavano prima)
    st.session_state["geo_f"] = {
        'd_piston': 24.0, 'd_rod': 12.0, 'n_port': 4, 'w_port': 8.0, 
        'oil_visc': 15.0, 'clicks': 10
    }
    st.session_state["geo_s"] = {
        'd_piston': 50.0, 'd_rod': 18.0, 'n_port': 4, 'w_port': 12.0, 
        'oil_visc': 12.0, 'clicks': 12
    }
    
    st.session_state["current_pilot_id"] = None
    st.session_state["current_bike_id"] = None
    st.session_state["init_done"] = True

# Funzione helper per calcolo rigidezza stack (semplificata)
def calc_k(df):
    k = 0.0
    try:
        for _, r in df.iterrows(): k += (r['th']**3) * r['qty'] * 1000
    except: pass
    return max(k, 0.1)

# Funzione helper per disegnare le tabelle
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
        key=f"edt_{key}"
    )

# ==============================================================================
# SIDEBAR - ARCHIVIO
# ==============================================================================
with st.sidebar:
    st.title("🗂️ ARCHIVIO")
    
    # 1. PILOTA
    df_p = SuspensionDB.get_piloti()
    opt_p = ["SELEZIONA..."] + df_p.apply(lambda x: f"{x['Nome']} (ID:{x['ID']})", axis=1).tolist()
    sel_p = st.selectbox("Pilota", opt_p)
    
    if sel_p != "SELEZIONA...":
        pid = df_p.iloc[opt_p.index(sel_p)-1]["ID"]
        st.session_state["current_pilot_id"] = pid
        
        # 2. MOTO
        df_m = SuspensionDB.get_garage(pid)
        opt_m = ["SELEZIONA..."]
        if not df_m.empty: opt_m += df_m.apply(lambda x: f"{x['marca']} {x['modello']}", axis=1).tolist()
        sel_m = st.selectbox("Moto", opt_m)
        
        if sel_m != "SELEZIONA...":
            mid = df_m.iloc[opt_m.index(sel_m)-1]["id_mezzo"]
            st.session_state["current_bike_id"] = mid
            
            st.divider()
            
            # 3. CARICA SESSIONE (Recupera anche la GEOMETRIA)
            df_s = SuspensionDB.get_sessioni(mid)
            if not df_s.empty:
                st.write("**Storico Setup**")
                opt_s = df_s.apply(lambda x: f"{x['data']} | {x['pista_luogo']}", axis=1).tolist()
                sel_s = st.selectbox("Seleziona:", opt_s)
                
                if st.button("📥 CARICA DATI", type="primary", use_container_width=True):
                    row = df_s.iloc[opt_s.index(sel_s)]
                    dati = SuspensionDB.parse_json(row['dati_tecnici_json'])
                    
                    # Recupero Tabelle Lamelle
                    if 'f_bv' in dati: st.session_state["fork_bv_df"] = pd.DataFrame(dati['f_bv'])
                    if 'f_mv' in dati: st.session_state["fork_mv_df"] = pd.DataFrame(dati['f_mv'])
                    if 's_comp' in dati: st.session_state["shock_comp_df"] = pd.DataFrame(dati['s_comp'])
                    if 's_reb' in dati: st.session_state["shock_reb_df"] = pd.DataFrame(dati['s_reb'])
                    
                    # Recupero Parametri Geometria (CRUCIALE)
                    if 'geo_f' in dati: st.session_state["geo_f"] = dati['geo_f']
                    if 'geo_s' in dati: st.session_state["geo_s"] = dati['geo_s']
                    
                    st.toast("Setup Caricato Completo!", icon="✅")
                    st.rerun()

            # 4. SALVA SESSIONE
            with st.expander("💾 Salva Setup Corrente"):
                pista = st.text_input("Pista")
                note = st.text_area("Note")
                if st.button("SALVA"):
                    pack = {
                        "f_bv": st.session_state["fork_bv_df"].to_dict('records'),
                        "f_mv": st.session_state["fork_mv_df"].to_dict('records'),
                        "s_comp": st.session_state["shock_comp_df"].to_dict('records'),
                        "s_reb": st.session_state["shock_reb_df"].to_dict('records'),
                        "geo_f": st.session_state["geo_f"], # Salviamo la geo forcella
                        "geo_s": st.session_state["geo_s"]  # Salviamo la geo mono
                    }
                    SuspensionDB.save_session(mid, pista, "Test", note, 3, pack)
                    st.success("Salvato nel DB!")

# ==============================================================================
# MAIN - TAB E GRAFICI
# ==============================================================================

if not st.session_state["current_bike_id"]:
    st.info("👈 Seleziona Pilota e Moto dal menu a sinistra.")
else:
    t_f, t_s, t_k = st.tabs(["🔹 FORCELLA", "🔸 MONO", "⚖️ TELAIO"])

    # --- TAB FORCELLA ---
    with t_f:
        c1, c2 = st.columns([1, 1.2])
        with c1:
            st.subheader("Lamelle (Shims)")
            st.session_state["fork_bv_df"] = render_stack("fork_bv", "Base Valve")
            st.session_state["fork_mv_df"] = render_stack("fork_mv", "Mid Valve")
            
        with c2:
            st.subheader("Geometria & Simulazione")
            # BOX GEOMETRIA FORCELLA (Modificabile)
            gf = st.session_state["geo_f"]
            with st.expander("📐 PARAMETRI TECNICI (Excel Input)", expanded=True):
                col_a, col_b = st.columns(2)
                gf['d_piston'] = col_a.number_input("Ø Pistone (mm)", 10.0, 50.0, float(gf['d_piston']), key="f_dp")
                gf['d_rod'] = col_b.number_input("Ø Asta (mm)", 5.0, 20.0, float(gf['d_rod']), key="f_dr")
                
                col_c, col_d = st.columns(2)
                gf['n_port'] = col_c.number_input("N° Port", 2, 8, int(gf['n_port']), key="f_np")
                gf['w_port'] = col_d.number_input("Largh. Port (mm)", 2.0, 20.0, float(gf['w_port']), key="f_wp")

                st.markdown("---")
                col_e, col_f = st.columns(2)
                gf['oil_visc'] = col_e.number_input("Olio (cSt)", 2.5, 50.0, float(gf['oil_visc']), key="f_oil")
                gf['clicks'] = col_f.slider("Clicker Aperti", 0, 30, int(gf['clicks']), key="f_clk")
            
            st.session_state["geo_f"] = gf # Aggiorna lo stato

            # CALCOLO E GRAFICO
            k_val = calc_k(st.session_state["fork_bv_df"])
            vels = np.linspace(0, 5, 50)
            forces = []
            for v in vels:
                f, _ = SuspensionPhysics.solve_damping(v, k_val, gf, gf['oil_visc'], gf['clicks'])
                forces.append(f)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=vels, y=forces, line=dict(color='#00CC96', width=3), name='Forza'))
            fig.update_layout(title="Curva Forza Forcella", xaxis_title="m/s", yaxis_title="Newton", height=350, margin=dict(l=20,r=20,t=40,b=20))
            st.plotly_chart(fig, use_container_width=True)

    # --- TAB MONO ---
    with t_s:
        c1s, c2s = st.columns([1, 1.2])
        with c1s:
            st.subheader("Lamelle Mono")
            st.session_state["shock_comp_df"] = render_stack("shock_comp", "Compressione")
            st.session_state["shock_reb_df"] = render_stack("shock_reb", "Ritorno")
            
        with c2s:
            st.subheader("Geometria Mono")
            # BOX GEOMETRIA MONO (Modificabile)
            gs = st.session_state["geo_s"]
            with st.expander("📐 PARAMETRI TECNICI MONO", expanded=True):
                col_a, col_b = st.columns(2)
                gs['d_piston'] = col_a.number_input("Ø Pistone (mm)", 30.0, 60.0, float(gs['d_piston']), key="s_dp")
                gs['d_rod'] = col_b.number_input("Ø Asta (mm)", 10.0, 25.0, float(gs['d_rod']), key="s_dr")
                
                col_c, col_d = st.columns(2)
                gs['n_port'] = col_c.number_input("N° Port", 2, 8, int(gs['n_port']), key="s_np")
                gs['w_port'] = col_d.number_input("Largh. Port (mm)", 5.0, 30.0, float(gs['w_port']), key="s_wp")

                st.markdown("---")
                col_e, col_f = st.columns(2)
                gs['oil_visc'] = col_e.number_input("Olio (cSt)", 2.5, 50.0, float(gs['oil_visc']), key="s_oil")
                gs['clicks'] = col_f.slider("Clicker Aperti", 0, 30, int(gs['clicks']), key="s_clk")
            
            st.session_state["geo_s"] = gs

            # CALCOLO MONO
            k_val_s = calc_k(st.session_state["shock_comp_df"])
            forces_s = []
            for v in vels:
                f, _ = SuspensionPhysics.solve_damping(v, k_val_s, gs, gs['oil_visc'], gs['clicks'])
                forces_s.append(f)
            
            fig_s = go.Figure()
            fig_s.add_trace(go.Scatter(x=vels, y=forces_s, line=dict(color='#EF553B', width=3), name='Mono'))
            fig_s.update_layout(title="Curva Forza Mono", xaxis_title="m/s", yaxis_title="Newton", height=350, margin=dict(l=20,r=20,t=40,b=20))
            st.plotly_chart(fig_s, use_container_width=True)

    # --- TAB TELAIO ---
    with t_k:
        st.header("Calcolatore SAG e Molle")
        
        # Recupero peso pilota dal DB
        w_def = 80.0
        if st.session_state["current_pilot_id"]:
            try:
                p_row = SuspensionDB.get_piloti()
                w_val = p_row[p_row["ID"] == str(st.session_state["current_pilot_id"])].iloc[0]["Peso"]
                if w_val: w_def = float(w_val)
            except: pass

        c_w, c_k, c_p = st.columns(3)
        w_pilota = c_w.number_input("Peso Pilota (kg)", 40.0, 150.0, w_def)
        k_molla = c_k.number_input("K Molla Mono (N/mm)", 30.0, 90.0, 52.0)
        preload = c_p.number_input("Precarico Ghiera (mm)", 0.0, 25.0, 8.0)
        
        st.divider()
        
        # Calcolo Sag
        peso_tot = 105 + w_pilota
        forza_leva = (peso_tot * 0.65 * 9.81) * 3.0 # Approx Leva 1:3
        sag_calc = (forza_leva / k_molla) - preload
        
        cm1, cm2 = st.columns(2)
        cm1.metric("SAG RIDER CALCOLATO", f"{sag_calc:.1f} mm")
        
        if sag_calc > 115:
            cm2.error("❌ Troppo Morbida / Poco Precarico")
        elif sag_calc < 95:
            cm2.warning("❌ Troppo Dura / Troppo Precarico")
        else:
            cm2.success("✅ Setup Molla OK")
