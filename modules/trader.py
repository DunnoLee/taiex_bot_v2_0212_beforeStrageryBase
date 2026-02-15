import shioaji as sj
from shioaji import constant, account
from config.settings import Settings

class Trader:
    def __init__(self, api):
        self.api = api
        self.account = None
        
        print("💳 [Trader] 正在掃描可用帳號...")
        try:
            all_accounts = self.api.list_accounts()
        except Exception as e:
            print(f"❌ 無法取得帳號列表: {e}")
            all_accounts = []

        for acc in all_accounts:
            if isinstance(acc, account.FutureAccount):
                self.account = acc
                break
        
        if self.account:
            print(f"✅ [Trader] 成功綁定期貨帳號: {self.account.account_id}")
        else:
            print(f"❌ [Trader] 嚴重警告：找不到任何期貨帳號！")
            if self.api.stock_account:
                self.account = self.api.stock_account

    def place_order(self, contract_code, action, quantity=1, price=0):
        try:
            if not self.account:
                print("❌ [下單失敗] 無有效帳號")
                return None

            contract = self.api.Contracts.Futures.TMF[contract_code]
            if not contract:
                print(f"❌ [下單錯誤] 找不到合約: {contract_code}")
                return None

            action_enum = constant.Action.Buy if action == "Buy" else constant.Action.Sell
            
            # 🟢 修正點：如果價格是 0，改用 MKT (市價)；否則用 LMT (限價)
            if price <=0:
                p_type = constant.FuturesPriceType.MKT 
                input_price = 0 
            else:
                p_type = constant.FuturesPriceType.LMT
                input_price = price

            # 2. 🟢 關鍵修正：判斷委託條件
            # 市價單 (MKT) 必須搭配 IOC (立即成交否則取消)
            # 限價單 (LMT) 通常搭配 ROD (當日有效)
            if p_type == constant.StockPriceType.MKT:
                o_type = constant.OrderType.IOC
            else:
                o_type = constant.OrderType.ROD

            order = self.api.Order(
                price=input_price,
                quantity=quantity,
                action=action_enum,
                price_type=p_type,
                order_type=o_type, 
                
                # 👇 [修正] 使用使用者指定的正確參數
                oct_type=constant.FuturesOCType.Auto,
                
                account=self.account
            )

            if Settings.DRY_RUN:
                print(f"🚧 [演習模式] 攔截下單！")
                print(f"   📝 內容: {action} {contract_code} x {quantity} @ {input_price}")
                return "DryRun_Success_ID"
            else:
                print(f"⚡ [真實下單] 發送中... {action} {contract_code} x {quantity} @ {input_price}")
                trade = self.api.place_order(contract, order)
                print(f"✅ [Trader] 委託已送出: {action} {contract_code} x{quantity}")
                print(f"   👉 類型: {p_type}, 條件: {o_type}")
                return trade

        except Exception as e:
            print(f"❌ [下單失敗] {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_positions(self):
        """[查詢] 目前期貨倉位"""
        try:
            if not self.account: return []
            
            positions = self.api.list_positions(self.account)
            results = []
            for p in positions:
                if "TMF" in p.code: 
                    direction = "Buy" if p.direction == constant.Action.Buy else "Sell"
                    
                    # 👇 [關鍵修正] 強制轉 float，避免 Decimal 汙染後續運算
                    results.append({
                        "code": p.code,
                        "direction": direction,
                        "quantity": int(p.quantity),  # 強制轉 int
                        "price": float(p.price),      # 強制轉 float
                        "pnl": float(p.pnl)           # 強制轉 float
                    })
            return results
        except Exception as e:
            print(f"❌ [查詢倉位失敗] {e}")
            return []

    def get_account_balance(self):
        try:
            if not self.account: return None
            margin = self.api.margin(self.account)
            return {
                "equity": float(margin.equity),             # 強制轉 float
                "available": float(margin.available_margin),# 強制轉 float
                "total_pnl": float(margin.initial_margin)   # 強制轉 float
            }
        except Exception as e:
            print(f"❌ [查詢權益失敗] {e}")
            return None