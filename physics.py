import numpy as np

class SuspensionPhysics:
    @staticmethod
    def solve_damping(vel, k_stack, geo, oil_visc_cst, clicker_clicks):
        """
        Calcola la forza in base ai dati geometrici reali inseriti.
        """
        # 1. Recupero Geometria (con valori sicuri se vuoti)
        d_piston = geo.get('d_piston', 24.0) / 1000.0  # mm -> metri
        d_rod    = geo.get('d_rod', 12.0) / 1000.0     # mm -> metri
        n_port   = geo.get('n_port', 4)
        w_port   = geo.get('w_port', 8.0) / 1000.0     # mm -> metri
        
        # 2. Calcolo Aree di lavoro
        area_piston = np.pi * (d_piston/2)**2
        area_rod    = np.pi * (d_rod/2)**2
        
        # Area che spinge l'olio (Compression)
        area_eff = area_piston - area_rod
        if area_eff <= 0: area_eff = area_piston * 0.1 # Protezione matematica

        # 3. Flusso (Portata)
        Q = area_eff * vel # m^3/s

        # 4. Clicker (Bypass)
        # Ogni click apre un po' di passaggio (simulazione spillo)
        area_bleed = (clicker_clicks * 0.5) * (1e-6) 
        
        # 5. Lamelle (Stack)
        # Più è rigido lo stack (k_stack), meno si apre (lift)
        force_factor = 600.0 # Costante idraulica
        lift_mm = (vel * force_factor) / (k_stack + 0.1)
        
        # Limite fisico apertura (non si piegano all'infinito)
        if lift_mm > 2.5: lift_mm = 2.5 
        
        # Area laterale aperta dalle lamelle (Curtain Area)
        area_curtain = n_port * w_port * (lift_mm / 1000.0)
        
        # Area Totale di passaggio (Clicker + Lamelle)
        total_area = area_curtain + area_bleed

        # 6. Pressione (Bernoulli)
        rho_oil = 850.0 
        # La viscosità abbassa il coefficiente di scarico (Cd)
        Cd = 0.7 - (oil_visc_cst / 2000.0)
        if Cd < 0.2: Cd = 0.2
        
        try:
            # Formula Bernoulli: Delta P = 0.5 * rho * (Q / (Cd * A))^2
            dp = 0.5 * rho_oil * (Q / (Cd * total_area + 1e-9))**2
        except:
            dp = 0.0

        # Forza = Pressione * Area
        force = dp * area_eff
        
        # Aggiungo un po' di attrito viscoso puro
        force += vel * (oil_visc_cst * 0.2)

        return force, lift_mm
