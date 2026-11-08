import MetaTrader5 as mt5
import pandas as pd

# ===== AQUI VOCÊ TESTA O QUE QUISER =====
SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_H4  # <--- TROCA AQUI: M15, M30, H1, H4, D1
DIAS = 120  # quantos dias pra trás você quer testar
PERIODO_CURTA = 10 # período da média curta
PERIODO_LONGA = 35 # período da média longa
ALVO_PONTOS = 210 # pontos de alvo
STOP_PONTOS = 105 # pontos de stop
LOTE = 0.10 # lote da operação
CAPITAL_INICIAL = 10000.0 
# ========================================

if not mt5.initialize():
    print("Abre o MT5 e deixa logado antes de rodar!")
    quit()

# Pega os dados do MT5
# H4 = 6 velas por dia, H1 = 24, M15 = 96
velas_por_dia = {
    mt5.TIMEFRAME_M15: 96,
    mt5.TIMEFRAME_M30: 48,
    mt5.TIMEFRAME_H1: 24,
    mt5.TIMEFRAME_H4: 6,
    mt5.TIMEFRAME_D1: 1,
}
qtd_velas = DIAS * velas_por_dia.get(TIMEFRAME, 24)

rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, qtd_velas)
if rates is None:
    print("Sem dados. Abre o gráfico do EURUSD no MT5 primeiro.")
    quit()

df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')
df['media_curta'] = df['close'].rolling(PERIODO_CURTA).mean()
df['media_longa'] = df['close'].rolling(PERIODO_LONGA).mean()
df = df.dropna().reset_index(drop=True)

print(f"\n=== BACKTEST {SYMBOL} ===")
print(f"Tempo gráfico: {TIMEFRAME} | Velas testadas: {len(df)} | Dias: {DIAS}")
print(f"Médias: {PERIODO_CURTA} x {PERIODO_LONGA} | Alvo: {ALVO_PONTOS} | Stop: {STOP_PONTOS}")

# ===== SIMULAÇÃO IGUAL AO ROBÔ REAL =====
point = mt5.symbol_info(SYMBOL).point
# Para EURUSD, 1 lote = $10 por pip. Ajusta se for XAUUSD etc
VALOR_POR_PONTO = 100000 * LOTE  

saldo = CAPITAL_INICIAL
pos = 0  # 1 = comprado, -1 = vendido, 0 = fora
entrada = 0
wins = 0
losses = 0
trades = 0
maior_drawdown = 0
pico = CAPITAL_INICIAL
curva = []

for i in range(2, len(df)):
    # Sinal igual ao robô: compara vela anterior com 2 atrás
    sinal_compra = df['media_curta'].iloc[i-1] > df['media_longa'].iloc[i-1] and df['media_curta'].iloc[i-2] < df['media_longa'].iloc[i-2]
    sinal_venda = df['media_curta'].iloc[i-1] < df['media_longa'].iloc[i-1] and df['media_curta'].iloc[i-2] > df['media_longa'].iloc[i-2]
    
    preco = df['close'].iloc[i]
    alvo = ALVO_PONTOS * point
    stop = STOP_PONTOS * point

    if pos == 0:
        if sinal_compra:
            pos = 1
            entrada = preco
            print(f"{df['time'].iloc[i].date()} COMPRA a {preco:.5f}")
        elif sinal_venda:
            pos = -1
            entrada = preco
            print(f"{df['time'].iloc[i].date()} VENDA a {preco:.5f}")

    elif pos == 1:
        if (preco - entrada) >= alvo:
            lucro = (preco - entrada) * VALOR_POR_PONTO
            saldo += lucro
            wins += 1; trades += 1
            print(f"  -> TP COMPRA +${lucro:.2f} | Saldo: ${saldo:.2f}")
            pos = 0
        elif (entrada - preco) >= stop:
            lucro = (preco - entrada) * VALOR_POR_PONTO
            saldo += lucro
            losses += 1; trades += 1
            print(f"  -> STOP COMPRA ${lucro:.2f} | Saldo: ${saldo:.2f}")
            pos = 0
        elif sinal_venda:
            lucro = (preco - entrada) * VALOR_POR_PONTO
            saldo += lucro
            trades += 1
            if lucro > 0: wins += 1
            else: losses += 1
            print(f"  -> FECHA por sinal contrário ${lucro:.2f} | Saldo: ${saldo:.2f}")
            pos = 0

    elif pos == -1:
        if (entrada - preco) >= alvo:
            lucro = (entrada - preco) * VALOR_POR_PONTO
            saldo += lucro
            wins += 1; trades += 1
            print(f"  -> TP VENDA +${lucro:.2f} | Saldo: ${saldo:.2f}")
            pos = 0
        elif (preco - entrada) >= stop:
            lucro = (entrada - preco) * VALOR_POR_PONTO
            saldo += lucro
            losses += 1; trades += 1
            print(f"  -> STOP VENDA ${lucro:.2f} | Saldo: ${saldo:.2f}")
            pos = 0
        elif sinal_compra:
            lucro = (entrada - preco) * VALOR_POR_PONTO
            saldo += lucro
            trades += 1
            if lucro > 0: wins += 1
            else: losses += 1
            print(f"  -> FECHA por sinal contrário ${lucro:.2f} | Saldo: ${saldo:.2f}")
            pos = 0

    curva.append(saldo)
    if saldo > pico: pico = saldo
    dd = pico - saldo
    if dd > maior_drawdown: maior_drawdown = dd

# Fecha posição aberta no final
if pos != 0:
    preco_final = df['close'].iloc[-1]
    lucro = (preco_final - entrada) * VALOR_POR_PONTO if pos == 1 else (entrada - preco_final) * VALOR_POR_PONTO
    saldo += lucro
    print(f"Fechamento final: ${lucro:.2f}")

# ===== RESULTADO FINAL =====
lucro_total = saldo - CAPITAL_INICIAL
win_rate = (wins / trades * 100) if trades > 0 else 0
print("\n" + "="*40)
print(f"RESULTADO FINAL - {SYMBOL}")
print(f"Capital inicial: ${CAPITAL_INICIAL:.2f}")
print(f"Capital final:   ${saldo:.2f}")
print(f"Lucro/Prejuízo:  ${lucro_total:.2f} ({lucro_total/CAPITAL_INICIAL*100:.1f}%)")
print(f"Trades: {trades} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%")
print(f"Maior Drawdown: ${maior_drawdown:.2f}")
print("="*40)
