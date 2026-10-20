"""Datos de ejemplo (deterministas) para probar las apps sin archivos propios."""

import random
from datetime import date, timedelta

import pandas as pd

from .i18n import LANGS


def _pick(lang, *variants):
    return variants[LANGS.index(lang)] if lang in LANGS else variants[0]


SALES_COLS = {
    "date": ("Fecha", "Date", "Date"),
    "region": ("Región", "Region", "Région"),
    "seller": ("Vendedor", "Salesperson", "Vendeur"),
    "product": ("Producto", "Product", "Produit"),
    "category": ("Categoría", "Category", "Catégorie"),
    "units": ("Unidades", "Units", "Unités"),
    "price": ("Precio", "Price", "Prix"),
    "total": ("Total", "Total", "Total"),
    "customer": ("Cliente", "Customer", "Client"),
}
REGIONS = [("Norte", "North", "Nord"), ("Sur", "South", "Sud"), ("Este", "East", "Est"),
           ("Oeste", "West", "Ouest"), ("Centro", "Central", "Centre")]
PRODUCTS = [
    (("Portátil Pro 14", "Laptop Pro 14", "Portable Pro 14"), ("Hardware", "Hardware", "Matériel"), 1250.0),
    (("Monitor 27\"", "Monitor 27\"", "Écran 27\""), ("Hardware", "Hardware", "Matériel"), 320.0),
    (("Teclado inalámbrico", "Wireless keyboard", "Clavier sans fil"), ("Accesorios", "Accessories", "Accessoires"), 45.0),
    (("Ratón ergonómico", "Ergonomic mouse", "Souris ergonomique"), ("Accesorios", "Accessories", "Accessoires"), 35.0),
    (("Licencia ERP", "ERP license", "Licence ERP"), ("Software", "Software", "Logiciel"), 890.0),
    (("Antivirus anual", "Annual antivirus", "Antivirus annuel"), ("Software", "Software", "Logiciel"), 60.0),
    (("Soporte premium", "Premium support", "Support premium"), ("Servicios", "Services", "Services"), 480.0),
    (("Formación online", "Online training", "Formation en ligne"), ("Servicios", "Services", "Services"), 150.0),
]
SELLERS = ["Ana Torres", "Luis Gómez", "Claire Martin", "John Smith", "Sofía Ruiz", "Marc Dubois"]
CUSTOMERS = ["Acme S.A.", "Globex", "Initech", "Umbrella Corp", "Stark Ind.", "Wayne Ent.", "Hooli", "Soylent",
             "Vandelay", "Pied Piper", "Cyberdyne", "Tyrell Corp"]


def sales(lang="es", rows=360, messy=True):
    rng = random.Random(42)
    c = {k: _pick(lang, *v) for k, v in SALES_COLS.items()}
    start = date(2025, 1, 1)
    records = []
    for _ in range(rows):
        names, category, price = rng.choice(PRODUCTS)
        units = rng.choice([1, 1, 2, 2, 3, 4, 5, 8, 10, 12])
        price = round(price * rng.uniform(0.9, 1.1), 2)
        records.append({
            c["date"]: pd.Timestamp(start + timedelta(days=rng.randint(0, 364))),
            c["region"]: _pick(lang, *rng.choice(REGIONS)),
            c["seller"]: rng.choice(SELLERS),
            c["product"]: _pick(lang, *names),
            c["category"]: _pick(lang, *category),
            c["units"]: units,
            c["price"]: price,
            c["total"]: round(units * price, 2),
            c["customer"]: rng.choice(CUSTOMERS),
        })
    df = pd.DataFrame(records).sort_values(c["date"]).reset_index(drop=True)
    if messy:
        df[c["units"]] = df[c["units"]].astype(object)
        for i in rng.sample(range(len(df)), 12):
            df.at[i, c["region"]] = f"  {df.at[i, c['region']].upper()} "
        for i in rng.sample(range(len(df)), 10):
            df.at[i, c["units"]] = str(df.at[i, c["units"]])
        dupes = df.sample(6, random_state=1)
        blank = pd.DataFrame([{col: None for col in df.columns}] * 3)
        df = pd.concat([df, dupes, blank], ignore_index=True)
    return df


def bi_model(lang="es"):
    rng = random.Random(7)
    t_sales = _pick(lang, "Ventas", "Sales", "Ventes")
    t_prod = _pick(lang, "Productos", "Products", "Produits")
    t_cust = _pick(lang, "Clientes", "Customers", "Clients")
    products = pd.DataFrame({
        "ProductID": [f"P{i:03d}" for i in range(1, len(PRODUCTS) + 1)],
        _pick(lang, "Producto", "Product", "Produit"): [_pick(lang, *p[0]) for p in PRODUCTS],
        _pick(lang, "Categoría", "Category", "Catégorie"): [_pick(lang, *p[1]) for p in PRODUCTS],
        _pick(lang, "Costo", "Cost", "Coût"): [round(p[2] * 0.62, 2) for p in PRODUCTS],
    })
    countries = [("México", "Mexico", "Mexique"), ("España", "Spain", "Espagne"), ("Francia", "France", "France"),
                 ("Colombia", "Colombia", "Colombie"), ("Canadá", "Canada", "Canada")]
    segments = [("Empresa", "Enterprise", "Entreprise"), ("PYME", "SMB", "PME"), ("Gobierno", "Government", "Public")]
    customers = pd.DataFrame({
        "CustomerID": [f"C{i:03d}" for i in range(1, len(CUSTOMERS) + 1)],
        _pick(lang, "Cliente", "Customer", "Client"): CUSTOMERS,
        _pick(lang, "País", "Country", "Pays"): [_pick(lang, *rng.choice(countries)) for _ in CUSTOMERS],
        _pick(lang, "Segmento", "Segment", "Segment"): [_pick(lang, *rng.choice(segments)) for _ in CUSTOMERS],
    })
    rows = []
    start = date(2024, 1, 1)
    for i in range(1, 901):
        p = rng.randrange(len(PRODUCTS))
        qty = rng.choice([1, 1, 2, 3, 5, 10])
        rows.append({
            "OrderID": 100000 + i,
            _pick(lang, "Fecha", "Date", "Date"): pd.Timestamp(start + timedelta(days=rng.randint(0, 729))),
            "ProductID": f"P{p + 1:03d}",
            "CustomerID": f"C{rng.randint(1, len(CUSTOMERS)):03d}",
            _pick(lang, "Cantidad", "Quantity", "Quantité"): qty,
            _pick(lang, "Importe", "Amount", "Montant"): round(qty * PRODUCTS[p][2] * rng.uniform(0.9, 1.05), 2),
        })
    fact = pd.DataFrame(rows).sort_values(_pick(lang, "Fecha", "Date", "Date")).reset_index(drop=True)
    fact.loc[[5, 77, 401], "ProductID"] = "P999"  # claves huérfanas para el control de calidad
    return {t_sales: fact, t_prod: products, t_cust: customers}


CLAIM_COLS = {
    "claim_id": ("ID reclamación", "Claim ID", "ID réclamation"),
    "customer_id": ("ID cliente", "Customer ID", "ID client"),
    "customer": ("Cliente", "Customer", "Client"),
    "claim_date": ("Fecha reclamación", "Claim date", "Date réclamation"),
    "txn_date": ("Fecha transacción", "Transaction date", "Date transaction"),
    "amount": ("Importe", "Amount", "Montant"),
    "channel": ("Canal", "Channel", "Canal"),
    "merchant": ("Comercio", "Merchant", "Commerçant"),
    "description": ("Descripción", "Description", "Description"),
}
CHANNELS = [("Tarjeta presente", "Card present", "Carte présente"),
            ("Compra en línea", "Online purchase", "Achat en ligne"),
            ("Banca en línea", "Online banking", "Banque en ligne"),
            ("Transferencia", "Transfer", "Virement"),
            ("Cajero", "ATM", "DAB")]
MERCHANTS = ["MegaShop Online", "TravelNow", "ElectroMax", "Café Central", "StreamPlus", "FarmaVida",
             "Super Ahorro", "GameZone", "Hotel Mirador", "TaxiGo", "Moda Express", "Libros & Co"]
DESCRIPTIONS = [
    ("No reconozco el cargo.", "I don't recognize the charge.", "Je ne reconnais pas le débit."),
    ("Recibí una llamada del supuesto banco y di un código.", "I got a call from the 'bank' and gave a code.",
     "J'ai reçu un appel de la « banque » et donné un code."),
    ("Perdí la tarjeta el fin de semana.", "I lost my card over the weekend.", "J'ai perdu ma carte ce week-end."),
    ("Cargos repetidos que no hice.", "Repeated charges I did not make.", "Débits répétés que je n'ai pas faits."),
    ("Transferencia que no autoricé.", "A transfer I did not authorize.", "Un virement que je n'ai pas autorisé."),
    ("El producto nunca llegó.", "The product never arrived.", "Le produit n'est jamais arrivé."),
]


def fraud_claims(lang="es", rows=220):
    rng = random.Random(11)
    c = {k: _pick(lang, *v) for k, v in CLAIM_COLS.items()}
    names = ["Laura Méndez", "Carlos Ruiz", "Emma Wilson", "Pierre Lefèvre", "Ana Castillo", "David Brown",
             "Lucía Navarro", "Hugo Bernard", "Marta Ortega", "James Taylor", "Sara Vidal", "Louis Moreau"]
    surnames = ["García", "Smith", "Martin", "López", "Dubois", "Pérez", "Johnson", "Bernard", "Sánchez", "Roux"]
    customers = [(f"C-{1000 + i}", names[i % len(names)] if i < len(names) else
                  f"{names[i % len(names)].split()[0]} {surnames[i % len(surnames)]}") for i in range(180)]
    start = date(2025, 1, 1)
    records = []
    for i in range(rows):
        cid, cname = rng.choice(customers)
        txn = start + timedelta(days=rng.randint(0, 270))
        records.append({
            c["claim_id"]: f"R-{25000 + i}",
            c["customer_id"]: cid,
            c["customer"]: cname,
            c["claim_date"]: pd.Timestamp(txn + timedelta(days=rng.choice([0, 1, 1, 2, 3, 5, 8, 15, 30]))),
            c["txn_date"]: pd.Timestamp(txn),
            c["amount"]: round(rng.choice([rng.uniform(5, 120), rng.uniform(50, 600), rng.uniform(300, 2500)]), 2),
            c["channel"]: _pick(lang, *rng.choice(CHANNELS)),
            c["merchant"]: rng.choice(MERCHANTS),
            c["description"]: _pick(lang, *rng.choice(DESCRIPTIONS)),
        })
    # Comercio comprometido: muchas tarjetas clonadas en la misma gasolinera en pocas semanas.
    for k in range(18):
        cid, cname = rng.choice(customers)
        txn = date(2025, 6, 2) + timedelta(days=rng.randint(0, 20))
        records.append({
            c["claim_id"]: f"R-{26000 + k}", c["customer_id"]: cid, c["customer"]: cname,
            c["claim_date"]: pd.Timestamp(txn + timedelta(days=rng.randint(1, 6))), c["txn_date"]: pd.Timestamp(txn),
            c["amount"]: round(rng.uniform(150, 900), 2), c["channel"]: _pick(lang, *CHANNELS[0]),
            c["merchant"]: "Gasolinera Ruta 9",
            c["description"]: _pick(lang, "Cargos que no hice; tengo la tarjeta conmigo.",
                                    "Charges I didn't make; I still have my card.",
                                    "Débits que je n'ai pas faits ; j'ai toujours ma carte."),
        })
    # Cliente recurrente y reclamaciones duplicadas.
    for k in range(5):
        txn = date(2025, 8, 1) + timedelta(days=k * 9)
        records.append({
            c["claim_id"]: f"R-{27000 + k}", c["customer_id"]: "C-1007", c["customer"]: customers[7][1],
            c["claim_date"]: pd.Timestamp(txn + timedelta(days=2)), c["txn_date"]: pd.Timestamp(txn),
            c["amount"]: 500.0, c["channel"]: _pick(lang, *CHANNELS[1]), c["merchant"]: "GameZone",
            c["description"]: _pick(lang, *DESCRIPTIONS[0]),
        })
    dup = dict(records[3])
    dup[c["claim_id"]] = "R-27999"
    records.append(dup)
    # Reclamación muy tardía.
    late = dict(records[10])
    late[c["claim_id"]] = "R-27998"
    late[c["claim_date"]] = late[c["txn_date"]] + pd.Timedelta(days=140)
    records.append(late)
    return pd.DataFrame(records)


MERGE_COLS = {
    "name": ("Nombre", "Name", "Nom"),
    "company": ("Empresa", "Company", "Entreprise"),
    "email": ("Email", "Email", "Email"),
    "product": ("Producto", "Product", "Produit"),
    "amount": ("Importe", "Amount", "Montant"),
    "due": ("FechaLimite", "DueDate", "DateLimite"),
}


def merge_data(lang="es"):
    c = {k: _pick(lang, *v) for k, v in MERGE_COLS.items()}
    people = [("Laura Méndez", "Acme S.A."), ("Emma Wilson", "Globex"), ("Pierre Lefèvre", "Initech"),
              ("Carlos Ruiz", "Hooli"), ("Sara Vidal", "Vandelay")]
    rows = []
    for i, (name, company) in enumerate(people):
        rows.append({
            c["name"]: name, c["company"]: company,
            c["email"]: name.split()[0].lower() + "@example.com",
            c["product"]: _pick(lang, *PRODUCTS[i][0]),
            c["amount"]: round(PRODUCTS[i][2] * (i + 1), 2),
            c["due"]: pd.Timestamp(date(2026, 11, 15) + timedelta(days=7 * i)),
        })
    return pd.DataFrame(rows)
