import MetaTrader5 as mt5
import time
import pandas as pd

# ===== CONFIGURAÇÕES - VERSÃO FINAL H4 2x1 =====
LOTE = 1.0
PERIODO_CURTA = 10
PERIODO_LONGA = 35
ALVO_PONTOS = 210
STOP_PONTOS = 105
SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_H4

# ===== CONECTA NO METATRADER 5 =====
if not mt5.initialize():
    print("Falha ao conectar no MT5")
    quit()

print("RoboMediaMovel H4 2x1 rodando...")

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
    return df['media_curta'].iloc[-2], df['media_longa'].iloc[-2], df['media_curta'].iloc[-3], df['media_longa'].iloc[-3]

def abrir_ordem(tipo, lote, comentario):
    tick = mt5.symbol_info_tick(SYMBOL)
    info = mt5.symbol_info(SYMBOL)
    point = info.point
    preco = tick.ask if tipo == mt5.ORDER_TYPE_BUY else tick.bid

    # Calcula STOP e ALVO 2x1 já na abertura
    if tipo == mt5.ORDER_TYPE_BUY:
        sl = preco - STOP_PONTOS * point
        tp = preco + ALVO_PONTOS * point
    else:
        sl = preco + STOP_PONTOS * point
        tp = preco - ALVO_PONTOS * point

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": lote,
        "type": tipo,
        "price": preco,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 123456,
        "comment": comentario,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    print(f"Ordem enviada: {comentario} | SL: {sl:.5f} TP: {tp:.5f} -> {result.retcode}")
    return result

def fechar_posicao(pos):
    tick = mt5.symbol_info_tick(SYMBOL)
    tipo_fechamento = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    preco = tick.bid if tipo_fechamento == mt5.ORDER_TYPE_SELL else tick.ask
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": pos.volume,
        "type": tipo_fechamento,
        "position": pos.ticket,
        "price": preco,
        "deviation": 20,
        "magic": 123456,
        "comment": "Fechamento por sinal contrario",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    print(f"Posicao fechada -> {result.retcode}")
    return result

while True:
    if is_new_bar():
        tick = mt5.symbol_info_tick(SYMBOL)
        media_curta_1, media_longa_1, media_curta_2, media_longa_2 = pegar_medias()

        sinal_compra = False
        sinal_venda = False

        if media_curta_1 > media_longa_1 and media_curta_2 < media_longa_2:
            sinal_compra = True
            print(f"NOVA VELA H4 - Sinal COMPRA | Curta: {media_curta_1:.5f} Longa: {media_longa_1:.5f}")
        if media_curta_1 < media_longa_1 and media_curta_2 > media_longa_2:
            sinal_venda = True
            print(f"NOVA VELA H4 - Sinal VENDA | Curta: {media_curta_1:.5f} Longa: {media_longa_1:.5f}")

        # Verifica posição aberta
        posicoes = mt5.positions_get(symbol=SYMBOL)
        comprado = False
        vendido = False
        pos_atual = None

        if posicoes:
            pos_atual = posicoes[0]
            if pos_atual.type == mt5.POSITION_TYPE_BUY:
                comprado = True
            if pos_atual.type == mt5.POSITION_TYPE_SELL:
                vendido = True

        if not comprado and not vendido:
            if sinal_compra:
                print("Abrindo COMPRA H4 - SL 105 / TP 210")
                abrir_ordem(mt5.ORDER_TYPE_BUY, LOTE, "Compra H4 2x1")
            if sinal_venda:
                print("Abrindo VENDA H4 - SL 105 / TP 210")
                abrir_ordem(mt5.ORDER_TYPE_SELL, LOTE, "Venda H4 2x1")
        else:
            # Se tem posição e veio sinal contrário, só fecha. Sem virada x2.
            if comprado and sinal_venda:
                print("Sinal de VENDA com compra aberta - Fechando sem virar")
                fechar_posicao(pos_atual)
            elif vendido and sinal_compra:
                print("Sinal de COMPRA com venda aberta - Fechando sem virar")
                fechar_posicao(pos_atual)
            else:
                print(f"Aguardando... Posicao aberta, SL/TP ja na corretora. Preco atual: {tick.bid:.5f}")

    time.sleep(1)