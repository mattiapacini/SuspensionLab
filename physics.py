import numpy as np

class SuspensionPhysics:
    @staticmethod
    def solve_damping(vel, k_stack, geo, oil_visc_cst, clicker_clicks):
        """
        Calcola la forza di smorzamento basata su:
        - Velocità stelo (vel)
        - Rigidità Stack Lamelle (k_stack)
        - Geometria (Pistone, Asta, Port, Throat)
        - Viscosità Olio (cSt)
        - Clicker (Bleed bypass)
        """
        # --- 1. GEOMETRIA (Dati dal Manuale/Excel) ---
        d_piston = geo.get('d_piston', 24.0) / 1000.0  # mm -> m
        d_rod    = geo.get('d_rod', 12.0) / 1000.0     # mm -> m
        n_port   = geo.get('n_port', 4)
        w_port   = geo.get('w_port', 8.0) / 1000.0     # mm -> m
        d_throat = geo.get('d_throat', 4.0) / 1000.0   # mm -> m (diametro passaggio fisso)
        
        # --- 2. AREE IDRAULICHE ---
        area_piston = np.pi * (d_piston/2)**2
        area_rod    = np.pi * (d_rod/2)**2
        
        # In compressione sposti l'olio pari al volume dell'asta (se mono) o pistone intero (cartuccia chiusa)
        # Qui usiamo un modello generico: Area Effettiva = Piston - Rod
        area_eff = area_piston - area_rod
        if area_eff <= 0: area_eff = area_piston * 0.1 # Fallback sicurezza

        # Portata (Q)
        Q = area_eff * vel # m^3/s

        # --- 3. BLEED (CLICKER) ---
        # Più click aperti = più area di bypass = meno forza
        # 1 click = approx 0.1mm diametro eq.
        area_bleed = (clicker_clicks * 0.5) * (1e-6) # m^2 semplificato
        
        # Sottraiamo la portata che passa dal bleed
        Q_stack = Q # Inizialmente tutto
        
        # --- 4. APERTURA LAMELLE (LIFT) ---
        # La pressione dell'olio piega le lamelle.
        # Approx: Forza fluido ~ Pressione * AreaPort
        # Resistenza molla = k_stack * lift
        # Lift approssimato (non lineare)
        force_factor = 500.0 # Fattore conversione idrodinamico
        lift_mm = (vel * force_factor) / (k_stack + 0.1)
        
        # Saturazione fisica (le lamelle non si aprono all'infinito, c'è il piattello)
        max_lift = 2.0 # mm
        if lift_mm > max_lift: lift_mm = max_lift
        
        # --- 5. AREA DI PASSAGGIO VARIABILE (CURTAIN AREA) ---
        # Area laterale aperta dal sollevamento della lamella
        area_curtain = n_port * w_port * (lift_mm / 1000.0)
        
        # Area fissa del passaggio (throat)
        area_port_fix = n_port * (np.pi * (d_throat/2)**2)
        
        # Somma aree (Parallelo tra Bleed e Stack)
        # Resistenza totale equivalente
        area_flow_stack = 1.0 / np.sqrt((1/(area_curtain**2 + 1e-9)) + (1/(area_port_fix**2 + 1e-9)))
        total_area = area_flow_stack + area_bleed

        # --- 6. CALCOLO PRESSIONE (BERNOULLI) ---
        rho_oil = 850.0 # kg/m^3
        # Coefficiente di scarico (Cd) dipendente dalla viscosità
        # Più viscoso = Cd più basso = più forza
        Cd = 0.75 - (oil_visc_cst / 500.0)
        if Cd < 0.3: Cd = 0.3
        
        try:
            dp = 0.5 * rho_oil * (Q / (Cd * total_area + 1e-9))**2
        except:
            dp = 0.0

        # --- 7. FORZA TOTALE ---
        damping_force = dp * area_eff
        
        # Aggiunta componente attrito/viscosità pura a bassa velocità
        damping_force += vel * (oil_visc_cst * 0.5)

        return damping_force, lift_mm
