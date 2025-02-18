//+------------------------------------------------------------------+
//| RoboMedialMovel.mq5                                             |
//| Copyright 2023, MetaQuotes Ltd.                                 |
//| https://www.mql5.com                                           |
//+------------------------------------------------------------------+
#property copyright "Copyright 2023, MetaQuotes Ltd."
#property link      "https://www.mql5.com"
#property version   "1.00"

#include <Trade/Trade.mqh>

input float lote = 1;
input int periodoCurta = 10;
input int periodoLonga = 35;
input int pontos = 210;

double bid, ask, precoEntrada;

int curtaHandle = INVALID_HANDLE;
int longaHandle = INVALID_HANDLE;

double mediaCurta[];
double mediaLonga[];

CTrade trade;

int OnInit() {
    ArraySetAsSeries(mediaCurta, true);
    ArraySetAsSeries(mediaLonga, true);
    
    curtaHandle = iMA(_Symbol, _Period, periodoCurta, 0, MODE_SMA, PRICE_CLOSE);
    longaHandle = iMA(_Symbol, _Period, periodoLonga, 0, MODE_SMA, PRICE_CLOSE);
    
    return INIT_SUCCEEDED;
}

void OnTick() {
    if (isNewBar()) {
        bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
        ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
        
        int copied1 = CopyBuffer(curtaHandle, 0, 0, 3, mediaCurta);
        int copied2 = CopyBuffer(longaHandle, 0, 0, 3, mediaLonga);
        
        bool sinalCompra = false;
        bool sinalVenda = false;
        
        if (copied1 == 3 && copied2 == 3) {
            if (mediaCurta[1] > mediaLonga[1] && mediaCurta[2] < mediaLonga[2]) {
                sinalCompra = true;
            }
            if (mediaCurta[1] < mediaLonga[1] && mediaCurta[2] > mediaLonga[2]) {
                sinalVenda = true;
            }
        }
        
        bool comprado = false;
        bool vendido = false;
        
        // Verifica se já existe uma posição aberta para o símbolo
        if (PositionSelect(_Symbol)) {
            precoEntrada = PositionGetDouble(POSITION_PRICE_OPEN);
            
            if (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) {
               comprado = true;
            }
            if (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_SELL) {
                vendido = true;
            }
        }
        
        if (!comprado && !vendido) {
            if (sinalCompra) {
                Print("Abrindo posição de COMPRA a mercado.");
                trade.Buy(lote, _Symbol, 0, 0, 0, "Compra a Mercado");
                // Marca a posição como comprada
                comprado = true;
            }
            if (sinalVenda) {
                Print("Abrindo posição de VENDA a mercado.");
                trade.Sell(lote, _Symbol, 0, 0, 0, "Venda a Mercado");
                // Marca a posição como vendida
                vendido = true;
            }
        } else {
            if (comprado) {
                // Verifica se atingiu o target de 210 pontos
                if ((bid - precoEntrada) >= pontos * _Point) {
                    Print("Fechando posição comprada por atingir o target.");
                    trade.PositionClose(_Symbol);
                    comprado = false;
                }

                // Verifica se há sinal de venda e realiza a virada de mão
                if (sinalVenda) {
                    Print("Executando virada de mão (compra --> venda)");
                    trade.Sell(lote * 2, _Symbol, 0, 0, 0, "Virada de mão (compra --> venda)");
                    // Marca a posição como vendida e cancela a compra
                    comprado = false;
                    vendido = true;
                }
            } else if (vendido) {
                // Verifica se atingiu o target de 210 pontos
                if ((precoEntrada - ask) >= pontos * _Point) {
                    Print("Fechando posição vendida por atingir o target.");
                    trade.PositionClose(_Symbol);
                    vendido = false;
                }

                // Verifica se há sinal de compra e realiza a virada de mão
                if (sinalCompra) {
                    Print("Executando virada de mão (venda --> compra)");
                    trade.Buy(lote * 2, _Symbol, 0, 0, 0, "Virada de mão (venda --> compra)");
                    // Marca a posição como comprada e cancela a venda
                    vendido = false;
                    comprado = true;
                }
            }
        }
    }
}

bool isNewBar() {
    static datetime last_time = 0;
    datetime lastBar_time = (datetime)SeriesInfoInteger(Symbol(), Period(), SERIES_LASTBAR_DATE);
    
    if (last_time == 0) {
        last_time = lastBar_time;
        return false;
    }
    if (last_time != lastBar_time) {
        last_time = lastBar_time;
        return true;
    }
    return false;
}
