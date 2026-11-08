import MetaTrader5 as mt5
import time
import pandas as pd

# ===== CONFIGURAÇÕES - IGUAIS AO SEU MQL5 =====
LOTE = 1.0
PERIODO_CURTA = 10
PERIODO_LONGA = 35
PONTOS = 210
SYMBOL = "EURUSD"  # troca aqui pro ativo que você quiser, ex: XAUUSD
TIMEFRAME = mt5.TIMEFRAME_M15

# ===== CONECTA NO METATRADER 5 =====
if not mt5.initialize():
    print("Falha ao conectar no MT5")
    quit()

# ===== FUNÇÃO PARA VER SE É VELA NOVA =====
ultima_vela = 0

def is_new_bar():
    global ultima_vela
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 1)
    if rates is None:
        return False
    tempo_atual = rates[0]['time']
    if ultima_vela == 0:
        ultima_vela = tempo_atual
        return False
    if ultima_vela != tempo_atual:
        ultima_vela = tempo_atual
        return True
    return False

# ===== FUNÇÃO PARA PEGAR AS MÉDIAS =====
def pegar_medias():
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 50)
    df = pd.DataFrame(rates)
    df['media_curta'] = df['close'].rolling(PERIODO_CURTA).mean()
    df['media_longa'] = df['close'].rolling(PERIODO_LONGA).mean()
    # [1] = vela anterior fechada, [2] = 2 velas atrás, igual ao seu MQL
    return df['media_curta'].iloc[-2], df['media_longa'].iloc[-2], df['media_curta'].iloc[-3], df['media_longa'].iloc[-3]

def abrir_ordem(tipo, lote, comentario):
    tick = mt5.symbol_info_tick(SYMBOL)
    preco = tick.ask if tipo == mt5.ORDER_TYPE_BUY else tick.bid
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": lote,
        "type": tipo,
        "price": preco,
        "deviation": 20,
        "magic": 123456,
        "comment": comentario,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    print(f"Ordem enviada: {comentario} -> {result.retcode}")
    return result

print("RoboMediaMovel em Python rodando...")

while True:
    if is_new_bar():
        tick = mt5.symbol_info_tick(SYMBOL)
        bid = tick.bid
        ask = tick.ask
        point = mt5.symbol_info(SYMBOL).point

        media_curta_1, media_longa_1, media_curta_2, media_longa_2 = pegar_medias()

        sinal_compra = False
        sinal_venda = False

        if media_curta_1 > media_longa_1 and media_curta_2 < media_longa_2:
            sinal_compra = True
        if media_curta_1 < media_longa_1 and media_curta_2 > media_longa_2:
            sinal_venda = True

        # Verifica posição aberta
        posicoes = mt5.positions_get(symbol=SYMBOL)
        comprado = False
        vendido = False
        preco_entrada = 0

        if posicoes:
            pos = posicoes[0]
            preco_entrada = pos.price_open
            if pos.type == mt5.POSITION_TYPE_BUY:
                comprado = True
            if pos.type == mt5.POSITION_TYPE_SELL:
                vendido = True

        if not comprado and not vendido:
            if sinal_compra:
                print("Abrindo posição de COMPRA a mercado.")
                abrir_ordem(mt5.ORDER_TYPE_BUY, LOTE, "Compra a Mercado")
            if sinal_venda:
                print("Abrindo posição de VENDA a mercado.")
                abrir_ordem(mt5.ORDER_TYPE_SELL, LOTE, "Venda a Mercado")
        else:
            if comprado:
                # Fecha por target de 210 pontos
                if (bid - preco_entrada) >= PONTOS * point:
                    print("Fechando comprada por atingir o target.")
                    mt5.Close(SYMBOL)
                # Virada de mão
                elif sinal_venda:
                    print("Virada de mão (compra -> venda)")
                    abrir_ordem(mt5.ORDER_TYPE_SELL, LOTE * 2, "Virada de mão")

            elif vendido:
                if (preco_entrada - ask) >= PONTOS * point:
                    print("Fechando vendida por atingir o target.")
                    mt5.Close(SYMBOL)
                elif sinal_compra:
                    print("Virada de mão (venda -> compra)")
                    abrir_ordem(mt5.ORDER_TYPE_BUY, LOTE * 2, "Virada de mão")

    time.sleep(1)