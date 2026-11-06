"""Synthetic waiter, extra sales and additional waste. No real staff records."""
import random
from datetime import datetime, timedelta

def enrich(orders, lines, products):
    r=random.Random(44)
    # Published September-2026 menu snapshot where available; other values assumed.
    catalog=[
      (101,"Cheddar Cheese",45,15,"Published menu snapshot","portion"),
      (102,"Spicy Mixed Olives",142,45,"Published menu snapshot; standalone starter","portion"),
      (103,"Chicken Strips",195,65,"Published menu snapshot; salad add-on","portion"),
      (104,"Grilled Pineapple",47,14,"Published menu snapshot","portion"),
      (105,"Mushroom",75,25,"Simulated price","portion"),
      (106,"PERinaise",47,12,"Published menu snapshot","portion"),
      (107,"Creamy Dip",45,12,"Simulated price","portion"),
      (108,"Pulled Chicken",152,50,"Published menu snapshot; salad add-on","portion"),
      (109,"Vodka",150,45,"Simulated price and availability","25 ml serving assumed"),
      (110,"Rhum",150,45,"Simulated price and availability","25 ml serving assumed"),
      (111,"Feta Cheese",95,30,"Published menu snapshot","portion"),
      (112,"Halloumi Cheese",162,55,"Published menu snapshot","portion")]
    staff=[(bid*100+j,bid,f"Demo Waiter {bid}-{j}") for bid in range(1,7) for j in range(1,5)]
    products=list(products)+[(pid,name,"Alcohol Extras" if pid in [109,110] else "Food Extras",price,cost)
                             for pid,name,price,cost,source,unit in catalog]
    lookup={o[0]:o for o in orders}
    neworders=[]
    extras=[]
    original_count=len(lines)
    for o in orders:
        paid=o[7]!="Not Captured"
        waiter=o[3]*100+r.randint(1,4) if o[4]=="Dine-in" else 0
        offered=int(bool(waiter) and paid and r.random()<.60)
        accepted=bool(offered) and r.random()<.42
        organic=paid and not accepted and r.random()<.12
        neworders.append((*o,waiter,offered))
        if not (accepted or organic): continue
        # Alcohol only as standalone add-on beverage in this model.
        choices=r.sample(catalog,r.choices([1,2,3],[.75,.20,.05])[0])
        for pid,name,price,cost,source,unit in choices:
            lid=original_count+len(extras)+1
            qty=1
            refund=price if o[6]=="Fully Refunded" else 0
            stamp=(datetime.fromisoformat(o[1])+timedelta(minutes=30)).isoformat(sep=" ") if refund else ""
            extras.append((lid,o[0],pid,qty,price,cost,0,price,0,price,cost,price-refund-cost,
                           "Sold",price,0,0,refund,price-refund,0,stamp,
                           "Full order refund" if refund else "","","",
                           "Extra",int(accepted),"Waiter suggested" if accepted else "Customer requested"))
    # Original menu lines are never retrospectively labelled waiter upsells.
    lines=[(*line,"Menu Item",0,"Standard basket") for line in lines]+extras
    # Separate waste ledger: incremental discarded ingredient cost only.
    # Existing cancellation waste stays in order_items; do not copy it here.
    waste=[]
    for line in lines[:original_count]:
        o=lookup[line[1]]
        if line[12]!="Sold" or o[6] not in ["Completed","Partially Refunded"]: continue
        if r.random()>=.006: continue
        reason=r.choice(["Wrong item prepared","Wrong PERi-PERi flavour","Incorrect extra added"])
        cost=round(line[3]*line[5],2)
        stamp=(datetime.fromisoformat(o[1])+timedelta(minutes=r.randint(3,20))).isoformat(sep=" ")
        waste.append((len(waste)+1,o[0],line[0],o[3],stamp,line[2],line[3],
                      cost,reason,"Remade; original sale retained","Kitchen/entry error unspecified"))
    return neworders,lines,products,staff,catalog,waste
