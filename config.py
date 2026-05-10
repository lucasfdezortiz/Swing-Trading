CAPITAL = 100_000           # Capital total en USD — ajustar según cuenta real
MAX_RISK_PCT = 0.01         # Riesgo máximo por operación (1%)
STOP_PCT = 0.073            # Stop por defecto 7.3% bajo el pivot
MIN_RS_RATING = 90          # Percentil mínimo de RS Rating
MIN_BASE_WEEKS = 5          # Semanas mínimas de base válida
MAX_PIVOT_DISTANCE = 0.05   # Máximo % sobre pivot para entrar (5%)
MIN_VOLUME_SPIKE = 1.40     # Volumen breakout vs media 50d (140%)
MIN_RR = 2.0                # R:R mínimo aceptable
EARNINGS_BUFFER_DAYS = 14   # Descartar si earnings en menos de X días

# Umbrales de detección de base
MAX_BASE_DEPTH_FLAT = 0.15   # Flat Base: máximo 15% de profundidad
MAX_BASE_DEPTH_CUP = 0.35    # Cup: máximo 35% de profundidad
VCP_CONTRACTION_THRESHOLD = 0.6  # VCP: cada swing ≤ 60% del anterior

# Condición de mercado
MAX_DISTRIBUTION_DAYS = 4   # Máximo distribution days permitidos en SPY/QQQ

# Universo
MIN_AVG_VOLUME = 500_000    # Volumen medio mínimo para incluir una acción
TOP_N_CANDIDATES = 5        # Número de candidatos a devolver

# Datos
LOOKBACK_DAYS = 300         # Días de histórico a descargar
