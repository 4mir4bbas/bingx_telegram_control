from collections.abc import Sized
import time
import requests
import hmac
from hashlib import sha256
import json
import telebot


APIURL = "https://open-api-vst.bingx.com";
APIKEY = input("Please enter your API key: ")
SECRETKEY = input("Please enter your API secret: ")



def make_riskfree(symbol):
    positions = json.loads(get_positions())['data']
    for pos in positions:
        if pos['symbol'] == symbol:
            # we have open position in this symbol
            total_orders = json.loads(get_orders())['data']['orders']
            n_total_orders_for_symbol = 0
            for order in total_orders:
                if order['symbol'] == symbol:
                    n_total_orders_for_symbol += 1
            if n_total_orders_for_symbol < 6: # first tp touched
                # first we should delete sl orders
                sl_order_ids = []
                for order in total_orders:
                    if order['symbol'] == symbol and order['type'] == 'STOP_MARKET':
                        sl_order_ids.append(order['orderId'])
                for order_id in sl_order_ids:
                    delete_order(symbol, order_id)
                # now we should set riskfree sl order
                entry_price = pos['avgPrice']
                available_quantity = pos['availableAmt']
                side = ''
                if pos['positionSide'] == 'LONG':
                    side = 'BUY'
                else:
                    side = 'SELL'
                response = send_stop_loss_order(symbol, side, pos['positionSide'], entry_price, available_quantity)
                return response
    return -1



def delete_order(symbol, order_id):
    payload = {}
    path = '/openApi/swap/v2/trade/order'
    method = "DELETE"
    paramsMap = {
    "symbol": symbol,
    "orderId": order_id,
    "recvWindow": 0
    }
    paramsStr = praseParam(paramsMap)
    return send_request(method, path, paramsStr, payload)


def send_limit_order(symbol, side, positionside, price, quantity, tp, sl):
    payload = {}
    path = '/openApi/swap/v2/trade/order'
    method = "POST"
    paramsMap = {
    "symbol": symbol,
    "side": side,
    "positionSide": positionside,
    "type": "LIMIT",
    "price": price,
    "quantity": quantity,
    "takeProfit": "{\"type\": \"TAKE_PROFIT_MARKET\", \"quantity\": %s,\"stopPrice\": %s,\"price\": %s,\"workingType\":\"MARK_PRICE\"}" % (str(quantity), str(tp), str(tp)),
    "stopLoss": "{\"type\": \"STOP_MARKET\", \"quantity\": %s,\"stopPrice\": %s,\"price\": %s,\"workingType\":\"MARK_PRICE\"}" % (str(quantity), str(sl), str(sl))
    }
    paramsStr = praseParam(paramsMap)
    return send_request(method, path, paramsStr, payload)


def send_stop_loss_order(symbol, side, positionside, stopPrice, quantity):
    payload = {}
    path = '/openApi/swap/v2/trade/order'
    method = "POST"
    paramsMap = {
    "symbol": symbol,
    "side": side,
    "positionSide": positionside,
    "type": "STOP_MARKET",
    "quantity": quantity,
    "stopPrice": stopPrice,
    "price": stopPrice,
    "workingType":"MARK_PRICE"}
    paramsStr = praseParam(paramsMap)
    return send_request(method, path, paramsStr, payload)


def send_take_profit_order(symbol, side, positionside, stopPrice, quantity):
    payload = {}
    path = '/openApi/swap/v2/trade/order'
    method = "POST"
    paramsMap = {
    "symbol": symbol,
    "side": side,
    "positionSide": positionside,
    "type": "TAKE_PROFIT_MARKET",
    "quantity": quantity,
    "stopPrice": stopPrice,
    "price": stopPrice,
    "workingType":"MARK_PRICE"}
    paramsStr = praseParam(paramsMap)
    return send_request(method, path, paramsStr, payload)


def send_trigger_market_order(symbol, side, positionside, stopPrice, quantity):
    payload = {}
    path = '/openApi/swap/v2/trade/order'
    method = "POST"
    paramsMap = {
    "symbol": symbol,
    "side": side,
    "positionSide": positionside,
    "type": 'TRIGGER_MARKET',
    "stopPrice": stopPrice,
    "quantity": quantity
    }
    paramsStr = praseParam(paramsMap)
    return send_request(method, path, paramsStr, payload)


def send_market_order(symbol, side, positionside, price, quantity, tp, sl):
    payload = {}
    path = '/openApi/swap/v2/trade/order'
    method = "POST"
    paramsMap = {
    "symbol": symbol,
    "side": side,
    "positionSide": positionside,
    "type": "MARKET",
    "price": price,
    "quantity": quantity,
    "takeProfit": "{\"type\": \"TAKE_PROFIT_MARKET\", \"quantity\": %s,\"stopPrice\": %s,\"price\": %s,\"workingType\":\"MARK_PRICE\"}" % (str(quantity), str(tp), str(tp)),
    "stopLoss": "{\"type\": \"STOP_MARKET\", \"quantity\": %s,\"stopPrice\": %s,\"price\": %s,\"workingType\":\"MARK_PRICE\"}" % (str(quantity), str(sl), str(sl))
    }
    paramsStr = praseParam(paramsMap)
    return send_request(method, path, paramsStr, payload)


def get_balance():
    payload = {}
    path = '/openApi/swap/v2/user/balance'
    method = "GET"
    paramsMap ={}
    paramsStr = praseParam(paramsMap)
    balance_str = send_request(method, path, paramsStr, payload)
    balance_dic = json.loads(balance_str)
    if balance_dic['code'] == 0:
        return float(balance_dic['data']['balance']['balance'])
    else:
        return -1 #balance_dic['msg']


def get_price(symbol):
    payload = {}
    path = '/openApi/swap/v2/quote/price'
    method = "GET"
    paramsMap = {
    "symbol": symbol
    }
    paramsStr = praseParam(paramsMap)
    price_str = send_request(method, path, paramsStr, payload)
    price_dic = json.loads(price_str)
    if price_dic['code'] == 0:
        return float(price_dic['data']['price'])
    else:
        return -1


def get_orders():
    payload = {}
    path = '/openApi/swap/v2/trade/openOrders'
    method = "GET"
    paramsMap = {}
    paramsStr = praseParam(paramsMap)
    return send_request(method, path, paramsStr, payload)


def get_positions():
    payload = {}
    path = '/openApi/swap/v2/user/positions'
    method = "GET"
    paramsMap = {}
    paramsStr = praseParam(paramsMap)
    return send_request(method, path, paramsStr, payload)


def find_tp1_price(entry, side, change):
    result = -1
    if side.lower() == 'buy':
        result = entry + entry*change*0.01
    else:
        result = entry - entry*change*0.01
    return result


def get_sign(api_secret, payload):
    signature = hmac.new(api_secret.encode("utf-8"), payload.encode("utf-8"), digestmod=sha256).hexdigest()
    #print("sign=" + signature)
    return signature


def send_request(method, path, urlpa, payload):
    url = "%s%s?%s&signature=%s" % (APIURL, path, urlpa, get_sign(SECRETKEY, urlpa))
    #print(url)
    headers = {
        'X-BX-APIKEY': APIKEY,
    }
    response = requests.request(method, url, headers=headers, data=payload)
    return response.text

def praseParam(paramsMap):
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    return paramsStr+"&timestamp="+str(int(time.time() * 1000))

def message_hash(txt):
    return hmac.new(txt.encode('utf8'), digestmod=sha256).hexdigest()

def find_n_tps(txt):
    lines = txt.split()
    if len(lines) < 12:
        return -1
    n_tps = 0
    if lines[7] != '0':
        n_tps += 1
    if lines[9] != '0':
        n_tps += 1
    if lines[11] != '0':
        n_tps += 1
    return n_tps


def read_message(txt):
    lines = txt.split()
    if len(lines) > 13 and len(lines) != 2:
        return -1
    dic = {}
    if len(lines) == 2 and lines[0].lower() == 'risk:':
        dic['risk'] = float(lines[1]) * 0.01
        return dic
    elif len(lines) == 13 or len(lines) == 12:
        dic['type'] = 'LIMIT'
        dic['symbol'] = lines[0][1:].replace('/', '-')[:-1]
        dic['side'] = lines[1]
        if dic['side'].lower() == 'buy':
            dic['positionside'] = "LONG"
        elif dic['side'].lower() == "sell":
            dic['positionside'] = "SHORT"
        try:
            dic['price'] = float(lines[3])
            dic['sl'] = float(lines[5])
            dic['tp2'] = float(lines[7])
            dic['tp3'] = float(lines[9])
        except:
            return -1
        return dic
    else:
        return -1


bot_token = input("Please enter your Telegram bot token: ")
bot = telebot.TeleBot(bot_token)
chat_id = int(input("Please enter your chat ID: "))
orders_dic = {}
while len(bot.get_updates()) == 0:
    bot.send_message(chat_id, "Please send a random message to initialize the bot")
    time.sleep(5)
bot.send_message(chat_id, "the bot initialized successfully")
offset = bot.get_updates()[-1].update_id+1
print(offset)
#offset = 141038786
last_offset = offset
risk = 0.01
tps = {}
sls = {}
n_orders = 0
n_orders_last = 0
trigger_orders = set()
trigger_orders_orderId = set()
symbols = set()
while True:
    print("in while loop")
    # make riskfree
    symbol_list = list(symbols)
    i = 0
    while i < len(symbol_list):
        res = make_riskfree(symbol_list[i])
        if res != -1:
            res_dic = json.loads(res)
            if res_dic['code'] == 0:
                symbols.remove(symbol_list[i])
                bot.send_message(chat_id, 'The positions in %s is now risk free' % symbol_list[i])
        i += 1

    # for sym in symbols:
    #     res = make_riskfree(sym)
    #     if res != -1:
    #         res_dic = json.loads(res)
    #         if res_dic['code'] == 0:
    #             symbols.remove(sym)
    #             bot.send_message(chat_id, 'The positions in %s is now risk free' % sym)

    # check all orders in orders_dic to see if one of them closed by tp or sl


    updates = []
    if bot.get_updates()[-1].update_id == offset:
        print("get new updates")
        updates = bot.get_updates(offset)
    if len(updates) > 0:
        print("updates length is grater than 0")
        offset += 1
        print(offset)
        #print(offset)
        for msg in updates:
            #print(read_message(msg.channel_post.json['text']))
            dic = read_message(msg.channel_post.json['text'])
            if dic == -1:
                bot.send_message(chat_id, "The message is not in correct format!")
                continue
            elif len(dic.keys()) == 1:
                risk = dic['risk']
                bot.send_message(chat_id, "The risk of orders is set to: %s percent" % str(risk*100))
                # elif dic.keys()[0] == 'leverage:':
                #     pass
            else:
                if 'reply_to_message' in msg.channel_post.json.keys(): #message is a reply to older message
                    old_msg_txt = msg.channel_post.json['reply_to_message']['text']
                    old_msg_hash = message_hash(old_msg_txt)
                    old_msg_orderId = orders_dic[old_msg_hash]
                    # close the order here
                else: #message is not a reply to older message
                    balance = get_balance()
                    if balance != -1:
                        quoteorderqty = risk*balance
                        price = get_price(dic['symbol'])
                        quantity = quoteorderqty / price
                        #print(quantity)
                    else:
                        bot.send_message('Cannot fetch account balance from the server!')
                        continue
                    responses = []
                    if dic['type'] == 'LIMIT':
                        tp1_price = find_tp1_price(entry=dic['price'], side=dic['side'], change=0.01)###################################################
                        tp1_quantity = quantity/2
                        tp2_quantity = quantity/4
                        tp3_quantity = quantity/4
                        sl_quantity = quantity
                        responses.append(send_limit_order(dic['symbol'], dic['side'], dic['positionside'], dic['price'], tp1_quantity, tp1_price, dic['sl']))
                        responses.append(send_limit_order(dic['symbol'], dic['side'], dic['positionside'], dic['price'], tp2_quantity, dic['tp2'], dic['sl']))
                        responses.append(send_limit_order(dic['symbol'], dic['side'], dic['positionside'], dic['price'], tp3_quantity, dic['tp3'], dic['sl']))
                        symbols.add(dic['symbol'])

                    elif dic['type'] == 'MARKET':
                        print('reached here')
                        n_tps = find_n_tps(msg.channel_post.json['text'])

                        if n_tps == 1:
                            responses.append(send_market_order(dic['symbol'], dic['side'], dic['positionside'], dic['price'], quantity, dic['tp1'], dic['sl']))
                        elif n_tps == 2:
                            quantity /= 2
                            responses.append(send_market_order(dic['symbol'], dic['side'], dic['positionside'], dic['price'], quantity, dic['tp1'], dic['sl']))
                            responses.append(send_market_order(dic['symbol'], dic['side'], dic['positionside'], dic['price'], quantity, dic['tp2'], dic['sl']))
                        elif n_tps == 3:
                            quantity /= 3
                            print('here')
                            responses.append(send_market_order(dic['symbol'], dic['side'], dic['positionside'], dic['price'], quantity, dic['tp1'], dic['sl']))
                            responses.append(send_market_order(dic['symbol'], dic['side'], dic['positionside'], dic['price'], quantity, dic['tp2'], dic['sl']))
                            responses.append(send_market_order(dic['symbol'], dic['side'], dic['positionside'], dic['price'], quantity, dic['tp3'], dic['sl']))
                    elif dic['type'] == 'TRIGGER_MARKET':
                        responses.append(send_trigger_market_order(dic['symbol'], dic['side'], dic['positionside'], dic['price'], quantity))
                        #trigger_orders_orderId.add(json.loads(get_orders())['data']['orders'][-1]['orderId'])
                        #trigger_orders.add(json.loads(get_orders())['data']['orders'][-1])
                        sls[dic['symbol']] = [(quantity, dic['sl'])]
                        if n_tps == 1:
                            tps[dic['symbol']] = [(quantity, dic['tp1'])]
                        elif n_tps == 2:
                            tps[dic['symbol']] = [(quantity/2, dic['tp1']), (quantity/2, dic['tp2'])]
                        elif n_tps == 3:
                            tps[dic['symbol']] = [(quantity/3, dic['tp1']), (quantity/3, dic['tp2']), (quantity/3, dic['tp3'])]



                    for res in responses:
                        res_dic = json.loads(res)
                        if res_dic['code'] == 0: #order placed successfully
                            bot.send_message(chat_id, "Order successfully placed. order_id: %s" % res_dic['data']['order']['orderId'])
                            orders_dic[message_hash(msg.channel_post.json['text'])] = res_dic['data']['order']['orderId']
                        else:
                            bot.send_message(chat_id, res_dic['msg'])
                #print('info: ', send_order(dic['symbol'], dic['side'], dic['positionside'], dic['type'], dic['price'], dic['leverage'], dic['quantity'], dic['tp1'], dic['sl']))
                #demo(symbol, side, positionside, type1, price, quoteotderqty, leverage, quantity, tp, sl)
                #send_order(symbol, side, positionside, type1, price, quantity, tp, sl)
    time.sleep(2)
    print('after sleep')