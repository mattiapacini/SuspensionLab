import numpy as np
import pandas as pd
from scipy.optimize import fsolve

class SuspensionPhysics:
    # --- COSTANTI BASE ---
    RHO_OIL = 870.0       # kg/m^3 (Default, sovrascritto da UI)
    P_ATM = 101325.0      # Pascal (1 atm)
    GAMMA_AIR = 1.3       # Esponente adiabatico per molle ad aria dinamiche

    # --- DATABASE VOLUMI TOKEN (cc approx) ---
    TOKEN_DB = {
        "Fox 32": 5.0, "Fox 34": 8.0, "Fox 36": 10.8, "Fox 38": 12.0, "Fox 40": 14.0,
        "RockShox 35mm": 8.0, "RockShox 32mm": 6.0,
        "WP AER 48": 15.0, # Spacer grosso
        "Öhlins": 9.0,
        "Generic/Oil (10ml)": 10.0
    }

    @staticmethod
    def calc_air_spring(travel_array, geometry, p_psi, tokens_type, num_tokens):
        """
        Calcola la curva forza (N) di una molla ad aria basandosi sulla geometria reale.
        """
        # 1. Geometria Base
        d_stelo = float(geometry.get('d_stelo', 48.0))
        corsa_tot = float(geometry.get('travel', 300.0))
        
        # Area Pistone Aria (Interno stelo approx - spessore pareti)
        d_inner = d_stelo - 4.0 # 2mm parete
        area_piston_mm2 = np.pi * (d_inner/2)**2
        area_piston_m2 = area_piston_mm2 / 1e6
        
        # 2. Volumi Iniziali (V0)
        # Volume geometrico cilindro
        # Assumiamo una camera leggermente più lunga della corsa (es. +30mm)
        l_camera = corsa_tot + 30.0 
        vol_total_cc = (area_piston_mm2 * l_camera) / 1000.0
        
        # 3. Riduzione Volume (Tuning)
        token_vol = SuspensionPhysics.TOKEN_DB.get(tokens_type, 0.0) * num_tokens
        vol_net_start_cc = vol_total_cc - token_vol
        if vol_net_start_cc < 10: vol_net_start_cc = 10 # Sicurezza
        
        vol_start_m3 = vol_net_start_cc / 1e6
        
        # 4. Pressione
        p_start_pa = (p_psi * 6894.76) + SuspensionPhysics.P_ATM # Assoluta
        
        forces = []
        for x_mm in travel_array:
            x_m = x_mm / 1000.0
            
            # Volume corrente (Adiabatico)
            # V_curr = V_start - (Area * x)
            vol_curr_m3 = vol_start_m3 - (area_piston_m2 * x_m)
            
            if vol_curr_m3 <= 1e-6: # Protezione divisione zero (pacchetto aria)
                vol_curr_m3 = 1e-6
                
            # Formula: P1 * V1^gamma = P2 * V2^gamma
            p_curr_pa = p_start_pa * (vol_start_m3 / vol_curr_m3)**SuspensionPhysics.GAMMA_AIR
            
            # Forza = (P_interna - P_atm) * Area
            f_gas = (p_curr_pa - SuspensionPhysics.P_ATM) * area_piston_m2
            forces.append(f_gas)
            
        return np.array(forces)

    @staticmethod
    def calculate_valve_area(lift, geo_data):
        """
        Calcola l'area di flusso considerando h.deck e throat.
        """
        # Geometria Porte
        n_port = int(geo_data.get('n_port', 4))
        w_port = float(geo_data.get('w_port', 10.0))
        l_port = float(geo_data.get('l_port', 8.0)) # Lunghezza radiale
        
        # Geometria Strozzature (Tue correzioni)
        h_deck = float(geo_data.get('h_deck', 2.0)) # Altezza canale ingresso
        d_throat = float(geo_data.get('d_throat', 100.0)) # Se enorme, non strozza
        
        # 1. Area Tenda (Curtain Area) - Variabile con il lift
        # A_curtain = Perimetro * lift
        a_curtain = (n_port * w_port) * lift
        
        # 2. Area Deck (Ingresso) - Fissa
        a_deck = n_port * (w_port * h_deck)
        
        # 3. Area Gola (Throat) - Fissa interna
        # Se d_throat è definito, calcoliamo l'area dei fori interni
        if d_throat < 90:
             a_throat = n_port * (np.pi * (d_throat/2)**2) # Approx circolare
        else:
             a_throat = 9999.0 # Infinito
             
        # L'area efficace è il minimo di tutte le restrizioni
        a_eff = min(a_curtain, a_deck, a_throat)
        
        return max(a_eff, 0.001)

    @staticmethod
    def solve_damping(velocity, stack_stiffness, geo_data, clicker_area, bleed_fixed_area):
        """
        Risolve l'equilibrio Idraulico vs Meccanico.
        Restituisce Forza (N) e Lift (mm).
        """
        # Dati Pistone
        d_piston = float(geo_data.get('d_piston', 50.0))
        d_rod = float(geo_data.get('d_rod', 16.0))
        
        # Area che spinge l'olio
        if geo_data.get('type') == 'compression':
            area_push = np.pi * ((d_piston/2)**2 - (d_rod/2)**2) # Annulus
        else:
            area_push = np.pi * (d_piston/2)**2 # Full (Rebound approx)
            
        q_target = (velocity * 1000) * area_push # mm^3/s
        
        def balance_eq(lift):
            if lift < 0: lift = 0
            
            # Aree Parallele: Bleed Fisso + Clicker + Valvola
            a_valve = SuspensionPhysics.calculate_valve_area(lift, geo_data)
            a_tot = a_valve + clicker_area + bleed_fixed_area
            
            # Bernoulli
            v_fluid = q_target / a_tot # mm/s
            v_fluid_ms = v_fluid / 1000.0
            
            # Delta P (Pascal)
            dp = 0.5 * SuspensionPhysics.RHO_OIL * (v_fluid_ms / 0.7)**2 # Cd=0.7
            dp_mpa = dp / 1e6
            
            # Forza Fluido sulla faccia lamelle (Port Area)
            # Approx: Area porte su cui preme l'olio
            port_ratio = 0.4 # 40% della faccia pistone è porta
            f_fluid = dp_mpa * (area_push * port_ratio)
            
            # Forza Molla Stack
            f_spring = stack_stiffness * lift
            
            # Preload (Gradino iniziale se presente)
            f_preload = float(geo_data.get('preload_shim', 0.0))
            
            return f_fluid - (f_spring + f_preload)

        # Solver
        try:
            lift_sol = fsolve(balance_eq, 0.1)[0]
        except:
            lift_sol = 0.0
            
        if lift_sol < 0: lift_sol = 0
        
        # Forza Smorzante Totale (Damping Force)
        # F = DeltaP * PistonArea
        # Ricalcolo DP esatto con il lift trovato
        a_final = SuspensionPhysics.calculate_valve_area(lift_sol, geo_data) + clicker_area + bleed_fixed_area
        v_final = (q_target / a_final) / 1000.0
        dp_final = 0.5 * SuspensionPhysics.RHO_OIL * (v_final / 0.7)**2
        
        f_damping = dp_final * (area_push / 1e6) # N
        
        return f_damping, lift_sol

    @staticmethod
    def calc_cavitation_limit(p_res_bar, d_rod, d_piston, type_res="bladder"):
        """
        Calcola la linea di cavitazione (Max forza estensione prima del vuoto).
        F_lim = P_abs * Area_annulus (semplificato)
        """
        p_abs = (p_res_bar * 100000) + SuspensionPhysics.P_ATM
        
        # Area su cui agisce la pressione di back-up
        # In compressione aiuta, in estensione limita.
        area_rod = np.pi * (d_rod/2)**2
        area_pist = np.pi * (d_piston/2)**2
        area_annulus = area_pist - area_rod
        
        # Forza limite (N)
        f_lim = (p_abs * area_annulus) / 1e6 # Conversione in N approx (semplificato)
        # Nota: La fisica vera richiede analisi pressioni camera C vs R. 
        # Questo è un limite "safe" conservativo.
        
        return f_lim * 1000 # Ritorna in Newton (da MPa * mm2)
