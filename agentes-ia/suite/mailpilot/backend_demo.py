"""Buzón de demostración en memoria: un analista de reclamaciones de fraude de un banco ficticio.

Sirve para probar MailPilot sin Outlook (y para las pruebas automáticas). Tiene un buzón propio, un buzón
compartido y un archivo .pst, con reclamaciones, contracargos, phishing, boletines, un número de tarjeta
enviado en claro y borradores en inglés con errores para el corrector.
"""

import random
import threading
from dataclasses import replace
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from ..i18n import LANGS
from .backend_base import BackendError, MailBackend, safe_filename, unique_path
from .edits import apply_changes, split_quoted
from .model import Category, Folder, Message, Store
from .query import fold

DOMAIN = "banco-demo.com"
USER = ("Ana Torres", "ana.torres@banco-demo.com")
SHARED_ADDRESS = "fraude@banco-demo.com"
EXTRA_SHARED = "pagos@banco-demo.com"

FOLDER_NAMES = {
    "inbox": ("Bandeja de entrada", "Inbox", "Boîte de réception"),
    "sent": ("Elementos enviados", "Sent Items", "Éléments envoyés"),
    "drafts": ("Borradores", "Drafts", "Brouillons"),
    "deleted": ("Elementos eliminados", "Deleted Items", "Éléments supprimés"),
    "junk": ("Correo no deseado", "Junk Email", "Courrier indésirable"),
    "archive": ("Archivo", "Archive", "Archives"),
    "claims": ("Reclamaciones", "Claims", "Réclamations"),
    "year": ("2026", "2026", "2026"),
    "chargebacks": ("Contracargos", "Chargebacks", "Rétrofacturations"),
    "vendors": ("Proveedores", "Vendors", "Fournisseurs"),
    "news": ("Boletines", "Newsletters", "Newsletters"),
    "pending": ("Pendientes", "Pending", "En attente"),
    "resolved": ("Resueltas", "Resolved", "Résolues"),
    "claims2025": ("Reclamaciones 2025", "Claims 2025", "Réclamations 2025"),
    "misc": ("Varios", "Misc", "Divers"),
}
STORE_NAMES = {"shared": ("Reclamaciones Fraude", "Fraud Claims", "Réclamations Fraude"),
               "payments": ("Pagos", "Payments", "Paiements"),
               "pst": ("Archivo 2025", "Archive 2025", "Archives 2025")}
CATEGORIES = {"urgent": (("Urgente", "Urgent", "Urgent"), 1), "followup": (("Seguimiento", "Follow-up", "Suivi"), 2),
              "chargeback": (("Contracargo", "Chargeback", "Rétrofacturation"), 8),
              "vendor": (("Proveedor", "Vendor", "Fournisseur"), 5),
              "phishing": (("Phishing", "Phishing", "Hameçonnage"), 9)}

CUSTOMERS = {
    "es": ["Laura Méndez", "Jorge Ramírez", "Lucía Fernández", "Carlos Gómez", "María José Ruiz", "Andrés Castillo",
           "Paula Herrera", "Diego Morales", "Sofía Navarro", "Javier Ortega"],
    "en": ["Emma Wilson", "James Carter", "Olivia Brown", "Liam Johnson", "Ava Martinez", "Noah Davis",
           "Mia Thompson", "Ethan Clark", "Grace Lewis", "Henry Walker"],
    "fr": ["Pierre Lefèvre", "Camille Martin", "Julien Bernard", "Chloé Dubois", "Lucas Moreau", "Léa Girard",
           "Hugo Lambert", "Manon Rousseau", "Louis Fontaine", "Inès Chevalier"],
}
COLLEAGUES = {
    "es": [("Marta Gil", "Analista de fraude"), ("Raúl Pardo", "Supervisor de reclamaciones"),
           ("Elena Soto", "Cumplimiento normativo")],
    "en": [("Mark Stevens", "Fraud analyst"), ("Sarah Lee", "Claims supervisor"), ("Tom Baker", "Compliance")],
    "fr": [("Sophie Laurent", "Analyste fraude"), ("Nicolas Petit", "Responsable réclamations"),
           ("Claire Moreau", "Conformité")],
}
MERCHANTS = ["Gasolinera Ruta 9", "TechStore Online", "Viajes Sol", "Marketplace Global", "StreamFlix", "RideNow",
             "Hotel Miramar", "ElectroHogar", "Farmacia Central", "GameZone"]
FREEMAIL = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com"]
IBANS = ["ES91 2100 0418 4502 0005 1332", "ES79 2100 0813 6101 2345 6789", "FR76 3000 6000 0112 3456 7890 189"]

# Plantillas en (español, inglés, francés).
T = {
    "claim_subject": ("Reclamación {claim} - cargo no reconocido", "Claim {claim} - unrecognized charge",
                      "Réclamation {claim} - débit non reconnu"),
    "claim_body": (
        "Buenos días:\n\nEn mi estado de cuenta aparece un cargo de {amount} en {merchant} del {date} que no "
        "reconozco. Mi tarjeta termina en {card4} y la tengo conmigo.\n\nAdjunto una captura del movimiento. "
        "Quedo atento a su respuesta.\n\nSaludos,\n{customer}\nTel. {phone}",
        "Hello,\n\nMy statement shows a charge of {amount} at {merchant} on {date} that I do not recognize. My "
        "card ends in {card4} and it is still in my possession.\n\nI attach a screenshot of the transaction. "
        "I look forward to your reply.\n\nKind regards,\n{customer}\nPhone {phone}",
        "Bonjour,\n\nMon relevé indique un débit de {amount} chez {merchant} le {date} que je ne reconnais pas. "
        "Ma carte se termine par {card4} et je l'ai toujours sur moi.\n\nJe joins une capture de l'opération. "
        "Dans l'attente de votre réponse.\n\nCordialement,\n{customer}\nTél. {phone}"),
    "claim_body_pan": (
        "Hola, me han cobrado {amount} en {merchant} y yo no hice esa compra. Les paso los datos de mi tarjeta "
        "para que lo revisen rápido: {pan}, vence 08/28.\n\nPor favor, devuelvan el dinero a mi cuenta {iban}."
        "\n\n{customer}",
        "Hi, I was charged {amount} at {merchant} and I did not make that purchase. Here are my card details so "
        "you can check it quickly: {pan}, expires 08/28.\n\nPlease refund the money to my account {iban}."
        "\n\n{customer}",
        "Bonjour, on m'a débité {amount} chez {merchant} et je n'ai pas fait cet achat. Voici les données de ma "
        "carte pour aller plus vite : {pan}, expire 08/28.\n\nMerci de rembourser sur mon compte {iban}."
        "\n\n{customer}"),
    "followup_subject": ("RE: Reclamación {claim}", "RE: Claim {claim}", "RE: Réclamation {claim}"),
    "followup_body": (
        "Hola de nuevo:\n\n¿Hay alguna novedad sobre mi reclamación {claim}? Ya pasaron {days} días y no he "
        "recibido respuesta.\n\nGracias,\n{customer}",
        "Hello again,\n\nIs there any update on my claim {claim}? It has been {days} days and I have not heard "
        "back.\n\nThanks,\n{customer}",
        "Bonjour,\n\nAvez-vous du nouveau sur ma réclamation {claim} ? Cela fait {days} jours sans réponse."
        "\n\nMerci,\n{customer}"),
    "credit_subject": ("Caso {claim}: abono provisional aprobado", "Case {claim}: provisional credit approved",
                       "Dossier {claim} : crédit provisoire approuvé"),
    "credit_body": (
        "Ana:\n\nApruebo el abono provisional de {amount} para el caso {claim}. Por favor, informa hoy al cliente "
        "y deja constancia en el expediente.\n\n{colleague}",
        "Ana,\n\nI approve the provisional credit of {amount} for case {claim}. Please let the customer know "
        "today and record it in the case file.\n\n{colleague}",
        "Ana,\n\nJ'approuve le crédit provisoire de {amount} pour le dossier {claim}. Merci d'informer le client "
        "aujourd'hui et de le noter dans le dossier.\n\n{colleague}"),
    "cpp_subject": ("Posible punto de compromiso: {merchant}", "Possible point of compromise: {merchant}",
                    "Point de compromission possible : {merchant}"),
    "cpp_body": (
        "Equipo:\n\nHemos recibido {n} reclamaciones con compras en {merchant} en los últimos 30 días. Propongo "
        "bloquear de forma preventiva las tarjetas afectadas. Os envío la lista en el adjunto.\n\n{colleague}",
        "Team,\n\nWe have received {n} claims with purchases at {merchant} in the last 30 days. I suggest a "
        "preventive block of the affected cards. The list is attached.\n\n{colleague}",
        "Équipe,\n\nNous avons reçu {n} réclamations avec des achats chez {merchant} sur les 30 derniers jours. "
        "Je propose un blocage préventif des cartes concernées. La liste est en pièce jointe.\n\n{colleague}"),
    "report_subject": ("Informe mensual de reclamaciones - {month}", "Monthly claims report - {month}",
                       "Rapport mensuel des réclamations - {month}"),
    "report_body": (
        "Adjunto el informe de {month}: {n} reclamaciones nuevas, {m} resueltas y {k} contracargos enviados."
        "\n\n{colleague}",
        "Attached is the {month} report: {n} new claims, {m} resolved and {k} chargebacks filed.\n\n{colleague}",
        "Ci-joint le rapport de {month} : {n} nouvelles réclamations, {m} résolues et {k} rétrofacturations "
        "envoyées.\n\n{colleague}"),
    "meeting_subject": ("Reunión de seguimiento de fraude", "Fraud follow-up meeting", "Réunion de suivi fraude"),
    "meeting_body": (
        "Hola a todos:\n\nOs convoco el jueves a las 10:30 en la sala 3 para revisar los casos abiertos y los "
        "plazos de respuesta.\n\n{colleague}",
        "Hi all,\n\nLet's meet on Thursday at 10:30 in room 3 to review open cases and response deadlines."
        "\n\n{colleague}",
        "Bonjour à tous,\n\nRéunion jeudi à 10h30 en salle 3 pour revoir les dossiers ouverts et les délais."
        "\n\n{colleague}"),
    "shift_subject": ("Turnos de guardia del próximo mes", "On-call rota for next month",
                      "Planning d'astreinte du mois prochain"),
    "shift_body": (
        "Os comparto el calendario de guardias. Si necesitáis cambiar algún turno, avisadme antes del viernes."
        "\n\n{colleague}",
        "Here is the on-call calendar. If you need to swap a shift, let me know before Friday.\n\n{colleague}",
        "Voici le planning d'astreinte. Pour échanger un créneau, prévenez-moi avant vendredi.\n\n{colleague}"),
    "reply_subject": ("RE: Reclamación {claim}", "RE: Claim {claim}", "RE: Réclamation {claim}"),
    "reply_body": (
        "Estimado/a {customer}:\n\nHemos recibido su reclamación {claim} y ya estamos analizando el cargo. Le "
        "responderemos en un plazo máximo de 10 días hábiles.\n\nUn saludo,\nAna Torres\nReclamaciones de fraude",
        "Dear {customer},\n\nWe have received your claim {claim} and are reviewing the charge. We will reply "
        "within 10 business days.\n\nBest regards,\nAna Torres\nFraud Claims",
        "Madame, Monsieur {customer},\n\nNous avons bien reçu votre réclamation {claim} et analysons le débit. "
        "Nous vous répondrons sous 10 jours ouvrés.\n\nCordialement,\nAna Torres\nRéclamations fraude"),
    "phish_update_subject": ("Actualice sus datos de seguridad", "Update your security details",
                             "Mettez à jour vos informations de sécurité"),
    "phish_update_body": (
        "Estimado colaborador:\n\nDetectamos accesos inusuales. Para evitar el bloqueo, verifique su cuenta "
        "inmediatamente e ingrese su contraseña en el siguiente enlace: http://bit.ly/3bdSecure\n\nSeguridad",
        "Dear employee,\n\nWe detected unusual sign-ins. To avoid a block, verify your account immediately and "
        "enter your password at this link: http://bit.ly/3bdSecure\n\nSecurity",
        "Cher collaborateur,\n\nNous avons détecté des connexions inhabituelles. Pour éviter le blocage, "
        "vérifiez votre compte immédiatement et saisissez votre mot de passe ici : http://bit.ly/3bdSecure"
        "\n\nSécurité"),
    "ceo_subject": ("Transferencia urgente y confidencial", "Urgent and confidential transfer",
                    "Virement urgent et confidentiel"),
    "ceo_body": (
        "Ana, necesito que hagas hoy mismo una transferencia urgente de 48.500,00 € a un proveedor nuevo. Es "
        "confidencial, no lo comentes con nadie. Esta es la nueva cuenta bancaria: {iban}.\n\nCarlos",
        "Ana, I need you to make an urgent transfer of $48,500.00 to a new supplier today. It is confidential, "
        "do not discuss it with anyone. This is the new bank account: {iban}.\n\nCarlos",
        "Ana, j'ai besoin que tu fasses aujourd'hui un virement urgent de 48 500,00 € à un nouveau fournisseur. "
        "C'est confidentiel, n'en parle à personne. Voici le nouveau RIB : {iban}.\n\nCarlos"),
    "translate_subject": ("Respuesta a la reclamación {claim}", "Reply to claim {claim}",
                          "Réponse à la réclamation {claim}"),
    "translate_body": (
        "Estimada Sra. Wilson:\n\nLe informamos que hemos aprobado un abono provisional de 320,00 € mientras "
        "terminamos la investigación de su reclamación. Por favor, no comparta nunca sus claves ni los códigos "
        "que recibe por SMS.\n\nAtentamente,\nAna Torres",
        "Dear Ms. Wilson,\n\nWe are pleased to inform you that we have approved a provisional credit of $320.00 "
        "while we finish investigating your claim. Please never share your passwords or the codes you receive "
        "by text message.\n\nSincerely,\nAna Torres",
        "Madame Wilson,\n\nNous vous informons que nous avons approuvé un crédit provisoire de 320,00 € le temps "
        "de terminer l'enquête sur votre réclamation. Ne communiquez jamais vos codes ni ceux reçus par SMS."
        "\n\nCordialement,\nAna Torres"),
    "payment_subject": ("Orden de pago {ref} rechazada", "Payment order {ref} rejected", "Ordre de paiement {ref} rejeté"),
    "payment_body": (
        "La orden de pago {ref} por {amount} fue rechazada por datos incompletos del beneficiario. Revise la "
        "cuenta {iban} y vuelva a enviarla.\n\nPagos",
        "Payment order {ref} for {amount} was rejected because of incomplete beneficiary details. Check account "
        "{iban} and resubmit it.\n\nPayments",
        "L'ordre de paiement {ref} de {amount} a été rejeté : données du bénéficiaire incomplètes. Vérifiez le "
        "compte {iban} et renvoyez-le.\n\nPaiements"),
}
MONTHS = {"es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
                 "noviembre", "diciembre"],
          "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                 "November", "December"],
          "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
                 "novembre", "décembre"]}

# Correos en inglés para cualquier idioma (redes de tarjetas, proveedores, boletines y phishing).
ENGLISH = {
    "visa": ("Visa Dispute Resolution", "disputes@visa.com", "Chargeback notification - case {claim}",
             "Dear Banco Demo team,\n\nPlease be advised that a chargeback has been filed for transaction {ref} "
             "({amount}). Supporting documentation must be submitted within 30 days through the dispute portal."
             "\n\nVisa Dispute Resolution"),
    "mastercard": ("Mastercard Fraud Alerts", "alerts@mastercard.com", "Fraud alert: compromised merchant {merchant}",
                   "Our monitoring identified {merchant} as a possible common point of purchase. We recommend "
                   "reviewing recent transactions and reissuing affected cards.\n\nMastercard Fraud Alerts"),
    "vendor": ("SecureDocs Support", "support@securedocs.io", "Your monthly invoice is available",
               "Hello,\n\nYour invoice for this month is available in the customer portal. No action is needed if "
               "you pay by direct debit.\n\nSecureDocs Support"),
    "it_phish": ("IT Service Desk", "it-support@banco-dem0.com", "URGENT: Your mailbox will be suspended",
                 "Your mailbox has exceeded its storage limit and will be suspended within 24 hours. Verify your "
                 "account now to keep receiving email.\n\nIT Service Desk"),
    "invoice_phish": ("Accounts Payable", "billing@vendor-payments.xyz", "Invoice #4471 overdue - final notice",
                      "Please review the attached invoice and confirm the payment today to avoid penalties."),
    "news_fraud": ("Fraud Insights", "newsletter@fraudinsights.com", "This week in payments fraud",
                   "New smishing campaigns are targeting bank customers with fake delivery messages. Read the full "
                   "analysis at https://fraudinsights.com/weekly\n\nUnsubscribe: https://fraudinsights.com/u"),
    "news_cyber": ("Cyber Security Bulletin", "noreply@cyberbulletin.org", "Weekly bulletin: new phishing kits",
                   "This week: phishing kits that copy bank login pages, and how to report them. "
                   "https://cyberbulletin.org/latest\n\nTo unsubscribe click here: https://cyberbulletin.org/u"),
}
IT_PHISH_HTML = ('<p>Your mailbox has exceeded its storage limit and will be suspended within 24 hours.</p>'
                 '<p><a href="http://banco-demo.com.mailbox-verify.top/login">https://outlook.banco-demo.com</a></p>')
INVOICE_HTML = '<p>Please review the attached invoice and confirm the payment today to avoid penalties.</p>'

# Borradores en inglés con errores típicos para probar el corrector (iguales en los tres idiomas).
DRAFTS = [
    ("disputes@visa.com", "Chargeback documentation for case {claim}",
     "Dear Sir,\n\ni am writting to informe you that we have send the documents since two weeks ago, but we "
     "didn't received any answer. Please find attached the informations about the transaction.\n\nCould you "
     "explain me what are the next steps? Is very important for our client.\n\nI look forward to hear from you."
     "\n\nBest regards,\nAna Torres\nFraud Claims Analyst\nBanco Demo"),
    ("emma.wilson@gmail.com", "your claim {claim}",
     "Hello Emma,\n\nThank you for contact us. We have received you claim and we are investigating it. Actually "
     "the case is in revision and we will send you an answer in the next days. Please dont share your PIN with "
     "nobody.\n\nRegards,\nAna"),
]


def _luhn_pan(rng):
    digits = [4] + [rng.randint(0, 9) for _ in range(14)]
    total = 0
    for i, d in enumerate(reversed(digits)):
        d = d * 2 if i % 2 == 0 else d
        total += d - 9 if d > 9 else d
    digits.append((10 - total % 10) % 10)
    text = "".join(map(str, digits))
    return " ".join(text[i:i + 4] for i in range(0, 16, 4))


def _money(value, lang):
    if lang == "en":
        return f"${value:,.2f}"
    text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "." if lang == "es" else " ")
    return f"{text} €"


def _day(value, lang):
    return value.strftime("%m/%d/%Y" if lang == "en" else "%d/%m/%Y")


def _email_of(name, domain):
    return ".".join(fold(name).replace("'", "").split()[:2]) + "@" + domain


class DemoBackend(MailBackend):
    kind = "demo"

    def __init__(self, lang="es", now=None, seed=7):
        self.lang = lang if lang in LANGS else "es"
        self.li = LANGS.index(self.lang)
        self.now = (now or datetime.now()).replace(microsecond=0)
        self.rng = random.Random(seed)
        self._lock = threading.RLock()
        self._stores = {}
        self._folders = {}  # id -> Folder (counts se calculan al listar)
        self._children = {}  # id -> [ids]
        self._messages = {}  # id -> Message completo (con cuerpo)
        self._categories = []
        self.rules = []
        self._seq = 0
        self._draft_turn = 0
        self._current = None
        self._build()

    # ------------------------------------------------------------ datos de ejemplo
    def tx(self, key, **kw):
        return T[key][self.li].format(**kw) if kw else T[key][self.li]

    def _new_store(self, key, name, kind, address=""):
        store = Store(id=f"demo-{key}", name=name, kind=kind, address=address)
        self._stores[store.id] = store
        root = Folder(id=f"{store.id}:root", store_id=store.id, name=name, path="", depth=0)
        self._folders[root.id] = root
        self._children[root.id] = []
        return store, root.id

    def _new_folder(self, parent_id, name, special=""):
        parent = self._folders[parent_id]
        self._seq += 1
        folder = Folder(id=f"{parent.store_id}:f{self._seq}", store_id=parent.store_id, name=name,
                        path=f"{parent.path}/{name}" if parent.path else name, parent_id=parent_id,
                        depth=parent.depth + 1, special=special)
        self._folders[folder.id] = folder
        self._children[folder.id] = []
        self._children[parent_id].append(folder.id)
        return folder.id

    def _std_folders(self, root_id, keys):
        return {k: self._new_folder(root_id, FOLDER_NAMES[k][self.li], k if k in (
            "inbox", "sent", "drafts", "deleted", "junk") else "") for k in keys}

    def _add(self, folder_id, sender, subject, body, received, html=None, categories=(), unread=None, flagged=False,
             importance=1, attachments=(), reply_to="", to="", cc=""):
        self._seq += 1
        folder = self._folders[folder_id]
        if unread is None:
            age = (self.now - received).days
            unread = self.rng.random() < (0.65 if age < 4 else 0.25 if age < 20 else 0.05)
        size = 6000 + len(body) * 2 + self.rng.randint(0, 25000)
        size += sum(self.rng.randint(60_000, 900_000) for _ in attachments)
        msg = Message(id=f"m{self._seq:05d}", store_id=folder.store_id, folder_id=folder_id, folder_path=folder.path,
                      subject=subject, sender_name=sender[0], sender_email=sender[1], to=to or USER[0], cc=cc,
                      received=received, categories=list(categories), unread=unread, flagged=flagged,
                      importance=importance, has_attachments=bool(attachments), size=size, body=body,
                      html=html, attachments=list(attachments), reply_to=reply_to)
        self._messages[msg.id] = msg
        return msg

    def _when(self, max_days, min_days=0):
        days = min_days + (max_days - min_days) * self.rng.random() ** 1.6  # más correos recientes
        moment = (self.now - timedelta(days=days)).replace(hour=self.rng.randint(8, 18),
                                                            minute=self.rng.randint(0, 59), second=0, microsecond=0)
        return moment if moment < self.now else moment - timedelta(days=1)

    def _claim_fields(self, year=2026):
        rng, lang = self.rng, self.lang
        customer = rng.choice(CUSTOMERS[lang])
        pan = _luhn_pan(rng)
        return dict(claim=f"R-{year}-{rng.randint(100, 999):04d}", customer=customer,
                    amount=_money(rng.choice([39.9, 89.5, 120, 249.99, 320, 480, 615.4, 1250, 2300]), lang),
                    merchant=rng.choice(MERCHANTS), date=_day(self.now - timedelta(days=rng.randint(3, 40)), lang),
                    card4=pan[-4:], pan=pan, iban=rng.choice(IBANS), phone=f"+34 6{rng.randint(10, 99)} "
                    f"{rng.randint(100, 999)} {rng.randint(100, 999)}", days=rng.randint(8, 25),
                    sender=(customer, _email_of(customer, rng.choice(FREEMAIL))))

    def _colleague(self, n=None):
        name, role = COLLEAGUES[self.lang][self.rng.randrange(3) if n is None else n]
        return (name, _email_of(name, DOMAIN)), f"{name}\n{role}"

    def _build(self):
        li, lang, rng, cat = self.li, self.lang, self.rng, self._cat
        for names, color in CATEGORIES.values():
            self._categories.append(Category(names[li], color))

        _, root = self._new_store("primary", USER[1], "primary", USER[1])
        f = self._std_folders(root, ("inbox", "sent", "drafts", "deleted", "junk", "archive"))
        f["claims"] = self._new_folder(f["inbox"], FOLDER_NAMES["claims"][li])
        f["year"] = self._new_folder(f["claims"], FOLDER_NAMES["year"][li])
        f["chargebacks"] = self._new_folder(f["claims"], FOLDER_NAMES["chargebacks"][li])
        f["vendors"] = self._new_folder(f["inbox"], FOLDER_NAMES["vendors"][li])
        f["news"] = self._new_folder(root, FOLDER_NAMES["news"][li])

        # Reclamaciones reenviadas, seguimientos y casos aprobados.
        for _ in range(22):
            c = self._claim_fields()
            folder = f["year"] if rng.random() < 0.6 else f["inbox"]
            msg = self._add(folder, c["sender"], self.tx("claim_subject", **c), self.tx("claim_body", **c),
                            self._when(110), attachments=["captura.png"] if rng.random() < 0.6 else (),
                            categories=[cat("urgent")] if rng.random() < 0.2 else ())
            if rng.random() < 0.4:
                later = msg.received + timedelta(days=c["days"])
                if later >= self.now:
                    later = self.now - timedelta(hours=rng.randint(1, 30))
                self._add(f["inbox"], c["sender"], self.tx("followup_subject", **c), self.tx("followup_body", **c),
                          later, categories=[cat("followup")])
            if rng.random() < 0.35:
                sender, signature = self._colleague(1)
                self._add(f["year"], sender, self.tx("credit_subject", **c),
                          self.tx("credit_body", colleague=signature, **c), self._when(60), unread=False)
            if rng.random() < 0.5:
                self._add(f["sent"], USER, self.tx("reply_subject", **c), self.tx("reply_body", **c),
                          self._when(100), unread=False, to=c["sender"][1])
        c = self._claim_fields()  # un cliente que manda el número completo de su tarjeta y su IBAN
        self._add(f["inbox"], c["sender"], self.tx("claim_subject", **c), self.tx("claim_body_pan", **c),
                  self.now - timedelta(hours=3), unread=True)

        # Contracargos y alertas de las redes de tarjetas (en inglés).
        for _ in range(9):
            c = self._claim_fields()
            name, email, subject, body = ENGLISH["visa"]
            ref = f"TX{rng.randint(10**7, 10**8 - 1)}"
            self._add(f["chargebacks"], (name, email), subject.format(**c), body.format(ref=ref, **c),
                      self._when(100), categories=[cat("chargeback")], importance=2 if rng.random() < 0.3 else 1)
        for merchant in rng.sample(MERCHANTS, 3):
            name, email, subject, body = ENGLISH["mastercard"]
            self._add(f["inbox"], (name, email), subject.format(merchant=merchant), body.format(merchant=merchant),
                      self._when(45), importance=2)

        # Equipo interno.
        sender, signature = self._colleague(0)
        self._add(f["inbox"], sender, self.tx("cpp_subject", merchant=MERCHANTS[0]),
                  self.tx("cpp_body", n=14, merchant=MERCHANTS[0], colleague=signature),
                  self.now - timedelta(days=1, hours=2), categories=[cat("urgent")], flagged=True, importance=2,
                  attachments=["tarjetas_afectadas.xlsx"])
        for months_ago in range(1, 4):
            month = MONTHS[lang][(self.now.month - months_ago - 1) % 12]
            sender, signature = self._colleague(1)
            self._add(f["inbox"], sender, self.tx("report_subject", month=month),
                      self.tx("report_body", month=month, n=rng.randint(140, 220), m=rng.randint(120, 200),
                              k=rng.randint(20, 45), colleague=signature),
                      self.now - timedelta(days=30 * months_ago - 2), attachments=[f"informe_{month}.xlsx"],
                      unread=False)
        for key in ("meeting", "shift"):
            sender, signature = self._colleague()
            self._add(f["inbox"], sender, self.tx(f"{key}_subject"), self.tx(f"{key}_body", colleague=signature),
                      self._when(20), cc=COLLEAGUES[lang][0][0])

        # Proveedores y boletines.
        for n in range(4):
            name, email, subject, body = ENGLISH["vendor"]
            self._add(f["vendors"], (name, email), subject, body, self.now - timedelta(days=30 * n + 5),
                      categories=[cat("vendor")], unread=False, attachments=["invoice.pdf"])
        for n in range(12):
            name, email, subject, body = ENGLISH["news_fraud" if n % 2 else "news_cyber"]
            html = "<p>" + body.replace("\n", "<br>") + "</p>"
            self._add(f["news"], (name, email), subject, body, self.now - timedelta(days=7 * n + 1), html=html)
        for n in range(3):
            name, email, subject, body = ENGLISH["news_cyber"]
            self._add(f["deleted"], (name, email), subject, body, self.now - timedelta(days=90 + 7 * n), unread=False)

        # Phishing: suplantación de TI, del propio banco, fraude del CEO y factura falsa.
        name, email, subject, body = ENGLISH["it_phish"]
        self._add(f["inbox"], (name, email), subject, body, self.now - timedelta(hours=5), html=IT_PHISH_HTML,
                  importance=2)
        bank_name = {"es": "Banco Demo Seguridad", "en": "Banco Demo Security", "fr": "Banco Demo Sécurité"}[lang]
        self._add(f["inbox"], (bank_name, "seguridad.bancodemo@gmail.com"), self.tx("phish_update_subject"),
                  self.tx("phish_update_body"), self.now - timedelta(days=2, hours=4))
        self._add(f["inbox"], ("Carlos Ruiz (CEO)", "carlos.ruiz.ceo@outlook.com"), self.tx("ceo_subject"),
                  self.tx("ceo_body", iban=IBANS[2]), self.now - timedelta(days=1, hours=7),
                  reply_to="c.ruiz.ceo@protonmail.com", importance=2)
        name, email, subject, body = ENGLISH["invoice_phish"]
        self._add(f["junk"], (name, email), subject, body, self.now - timedelta(days=3), html=INVOICE_HTML,
                  attachments=["Invoice_4471.html"])

        # Archivo y borradores.
        for _ in range(5):
            c = self._claim_fields()
            self._add(f["archive"], c["sender"], self.tx("claim_subject", **c), self.tx("claim_body", **c),
                      self._when(200, 120), unread=False)
        for n, (to, subject, body) in enumerate(DRAFTS):
            claim = f"R-2026-0{412 + n * 37}"
            self._add(f["drafts"], USER, subject.format(claim=claim), body, self.now - timedelta(hours=2 + n * 20),
                      unread=False, to=to)
        self._add(f["drafts"], USER, self.tx("translate_subject", claim="R-2026-0388"), self.tx("translate_body"),
                  self.now - timedelta(days=2), unread=False, to="emma.wilson@gmail.com")

        # Buzón compartido del equipo de reclamaciones.
        _, sroot = self._new_store("shared", STORE_NAMES["shared"][li], "shared", SHARED_ADDRESS)
        s = self._std_folders(sroot, ("inbox", "sent", "deleted"))
        s["pending"] = self._new_folder(s["inbox"], FOLDER_NAMES["pending"][li])
        s["resolved"] = self._new_folder(s["inbox"], FOLDER_NAMES["resolved"][li])
        for n in range(45):
            c = self._claim_fields()
            folder = s["inbox"] if n < 25 else s["pending"] if n < 33 else s["resolved"]
            body = self.tx("claim_body_pan" if n in (4, 17) else "claim_body", **c)
            self._add(folder, c["sender"], self.tx("claim_subject", **c), body,
                      self._when(30 if n < 25 else 100), to=STORE_NAMES["shared"][li],
                      unread=None if n < 33 else False, attachments=["estado_cuenta.pdf"] if n % 3 == 0 else ())
            if n < 25 and rng.random() < 0.3:
                self._add(s["inbox"], c["sender"], self.tx("followup_subject", **c), self.tx("followup_body", **c),
                          self.now - timedelta(hours=rng.randint(1, 120)), to=STORE_NAMES["shared"][li])

        # Archivo .pst con reclamaciones del año anterior.
        _, proot = self._new_store("pst", STORE_NAMES["pst"][li], "pst")
        p = {"claims2025": self._new_folder(proot, FOLDER_NAMES["claims2025"][li]),
             "misc": self._new_folder(proot, FOLDER_NAMES["misc"][li])}
        for n in range(24):
            c = self._claim_fields(2025)
            received = datetime(2025, 1 + n % 12, 3 + n, 10, 15)
            self._add(p["claims2025"], c["sender"], self.tx("claim_subject", **c), self.tx("claim_body", **c),
                      received, unread=False)
        sender, signature = self._colleague(2)
        self._add(p["misc"], sender, self.tx("shift_subject"), self.tx("shift_body", colleague=signature),
                  datetime(2025, 11, 4, 9, 30), unread=False)

    def _cat(self, key):
        return CATEGORIES[key][0][self.li]

    # ------------------------------------------------------------ conexión y carpetas
    def connect(self):
        return self.stores()

    def stores(self):
        with self._lock:
            return [replace(s) for s in self._stores.values()]

    def open_shared(self, address):
        address = (address or "").strip().lower()
        with self._lock:
            for store in self._stores.values():
                if store.address == address:
                    return replace(store)
            if address != EXTRA_SHARED:
                raise BackendError("shared_failed", address)
            store, root = self._new_store("payments", STORE_NAMES["payments"][self.li], "shared", EXTRA_SHARED)
            inbox = self._std_folders(root, ("inbox",))["inbox"]
            for n in range(8):
                ref = f"OP-{self.rng.randint(10000, 99999)}"
                self._add(inbox, ("Pagos" if self.lang == "es" else "Payments", EXTRA_SHARED),
                          self.tx("payment_subject", ref=ref),
                          self.tx("payment_body", ref=ref, amount=_money(1500 + 750 * n, self.lang),
                                  iban=IBANS[n % 3]), self._when(40), to=STORE_NAMES["payments"][self.li])
            return replace(store)

    def folders(self, store_id):
        with self._lock:
            counts = {}
            for msg in self._messages.values():
                total, unread = counts.get(msg.folder_id, (0, 0))
                counts[msg.folder_id] = (total + 1, unread + msg.unread)
            out = []

            def walk(fid):
                folder = self._folders[fid]
                total, unread = counts.get(fid, (0, 0))
                out.append(replace(folder, total=total, unread=unread))
                for child in self._children[fid]:
                    walk(child)

            walk(f"{store_id}:root")
            return out

    def _folder(self, folder_id):
        folder = self._folders.get(folder_id)
        if folder is None:
            raise BackendError("not_found", folder_id)
        return folder

    def _check_name(self, parent_id, name, own_id=None):
        name = (name or "").strip()
        if not name or any(c in name for c in "\\/"):
            raise BackendError("folder_name", name)
        for child in self._children[parent_id]:
            if child != own_id and self._folders[child].name.lower() == name.lower():
                raise BackendError("folder_exists", name)
        return name

    def _repath(self, folder_id):
        folder = self._folders[folder_id]
        parent = self._folders[folder.parent_id]
        folder.path = f"{parent.path}/{folder.name}" if parent.path else folder.name
        folder.depth = parent.depth + 1
        folder.store_id = parent.store_id
        for msg in self._messages.values():
            if msg.folder_id == folder_id:
                msg.folder_path, msg.store_id = folder.path, folder.store_id
        for child in self._children[folder_id]:
            self._repath(child)

    def _editable(self, folder_id):
        folder = self._folder(folder_id)
        if folder.depth == 0 or folder.special:
            raise BackendError("folder_special", folder.name)
        return folder

    def create_folder(self, parent_id, name):
        with self._lock:
            self._folder(parent_id)
            return replace(self._folders[self._new_folder(parent_id, self._check_name(parent_id, name))])

    def rename_folder(self, folder_id, name):
        with self._lock:
            folder = self._editable(folder_id)
            folder.name = self._check_name(folder.parent_id, name, folder_id)
            self._repath(folder_id)

    def move_folder(self, folder_id, parent_id):
        with self._lock:
            folder = self._editable(folder_id)
            parent = self._folder(parent_id)
            node = parent
            while node is not None:
                if node.id == folder_id:
                    raise BackendError("folder_loop", folder.name)
                node = self._folders.get(node.parent_id)
            self._check_name(parent_id, folder.name, folder_id)
            self._children[folder.parent_id].remove(folder_id)
            self._children[parent_id].append(folder_id)
            folder.parent_id = parent_id
            self._repath(folder_id)

    def delete_folder(self, folder_id):
        """Como Outlook: la carpeta pasa a Elementos eliminados (si ya estaba ahí, se borra del todo)."""
        with self._lock:
            folder = self._editable(folder_id)
            trash = self._special(folder.store_id, "deleted")
            node, inside = folder, False
            while node is not None:
                inside |= node.id == trash
                node = self._folders.get(node.parent_id)
            if trash and not inside:
                self._check_name(trash, folder.name, folder_id)
                self._children[folder.parent_id].remove(folder_id)
                self._children[trash].append(folder_id)
                folder.parent_id = trash
                self._repath(folder_id)
                return
            self._children[folder.parent_id].remove(folder_id)

            def drop(fid):
                for child in self._children.pop(fid):
                    drop(child)
                del self._folders[fid]
                for mid in [m.id for m in self._messages.values() if m.folder_id == fid]:
                    del self._messages[mid]

            drop(folder_id)

    def _special(self, store_id, kind):
        return next((f.id for f in self._folders.values() if f.store_id == store_id and f.special == kind), None)

    # ------------------------------------------------------------ correos
    def _iter_messages(self, folder_id, dasl, floor):
        with self._lock:
            self._folder(folder_id)
            # Como en Outlook, la lista no trae el cuerpo: se carga con `details` cuando hace falta.
            found = [replace(m, body=None, html=None, attachments=[], reply_to="", categories=list(m.categories))
                     for m in self._messages.values() if m.folder_id == folder_id]
        found.sort(key=lambda m: m.received or datetime.max, reverse=True)
        for msg in found:
            if floor and msg.received and msg.received < floor:
                break
            yield msg

    def messages(self, folder_id, since=None, limit=1000):
        out = []
        for msg in self._iter_messages(folder_id, "", since):
            if limit and len(out) >= limit:
                return out, True
            out.append(msg)
        return out, False

    def _load_details(self, msg, html=False):
        with self._lock:
            full = self._messages.get(msg.id)
        if full is None:
            msg.body, msg.html = msg.body or "", msg.html or ""
            return msg
        msg.body = full.body or ""
        msg.attachments = list(full.attachments)
        msg.reply_to = full.reply_to
        if html:
            msg.html = full.html or ""
        return msg

    def details(self, msg, html=False):
        return self._load_details(msg, html)

    def _each(self, messages):
        for msg in messages:
            full = self._messages.get(msg.id)
            if full is not None:
                yield full

    def move_messages(self, messages, folder_id):
        with self._lock:
            folder = self._folder(folder_id)
            n = 0
            for full in self._each(messages):
                full.folder_id, full.folder_path, full.store_id = folder.id, folder.path, folder.store_id
                n += 1
            return n

    def set_categories(self, messages, add=(), remove=()):
        with self._lock:
            n = 0
            drop = {c.lower() for c in remove}
            for full in self._each(messages):
                cats = [c for c in full.categories if c.lower() not in drop]
                cats += [c for c in add if c.lower() not in {x.lower() for x in cats}]
                if cats != full.categories:
                    full.categories = cats
                    n += 1
            return n

    def mark_read(self, messages, read=True):
        with self._lock:
            n = 0
            for full in self._each(messages):
                full.unread = not read
                n += 1
            return n

    def set_flag(self, messages, flagged=True):
        with self._lock:
            n = 0
            for full in self._each(messages):
                full.flagged = flagged
                n += 1
            return n

    def delete_messages(self, messages):
        with self._lock:
            n = 0
            for full in list(self._each(messages)):
                trash = self._special(full.store_id, "deleted")
                if trash and full.folder_id != trash:
                    full.folder_id, full.folder_path = trash, self._folders[trash].path
                else:
                    del self._messages[full.id]
                n += 1
            return n

    def save_messages(self, messages, folder):
        """En la demostración se guardan como .eml (Outlook los abre); con Outlook real, como .msg."""
        folder = Path(folder)
        paths = []
        with self._lock:
            items = [replace(m) for m in self._each(messages)]
        for full in items:
            mail = EmailMessage()
            mail["Subject"] = full.subject
            mail["From"] = f"{full.sender_name} <{full.sender_email}>"
            mail["To"] = full.to
            if full.received:
                mail["Date"] = full.received.strftime("%a, %d %b %Y %H:%M:%S +0000")
            mail.set_content(full.body or "")
            stamp = full.received.strftime("%Y-%m-%d") if full.received else ""
            path = unique_path(folder, safe_filename(f"{stamp} {full.subject}"), ".eml")
            path.write_bytes(bytes(mail))
            paths.append(path)
        return paths

    def save_attachments(self, messages, folder):
        folder = Path(folder)
        paths = []
        with self._lock:
            items = [replace(m) for m in self._each(messages)]
        for full in items:
            for name in full.attachments:
                stem, dot, ext = name.rpartition(".")
                path = unique_path(folder, safe_filename(stem or name), f".{ext}" if dot else "")
                path.write_text(f"MailPilot demo attachment: {name}\n{full.subject}\n", encoding="utf-8")
                paths.append(path)
        return paths

    def open_message(self, msg):
        return False  # no hay Outlook: la app muestra la vista previa

    # ------------------------------------------------------------ categorías, reglas y borradores
    def categories(self):
        with self._lock:
            return [replace(c) for c in self._categories]

    def _find_category(self, name):
        for cat in self._categories:
            if cat.name.lower() == (name or "").strip().lower():
                return cat
        return None

    def create_category(self, name, color):
        name = (name or "").strip()
        with self._lock:
            if not name or "," in name or ";" in name:
                raise BackendError("category_name", name)
            if self._find_category(name):
                raise BackendError("category_exists", name)
            self._categories.append(Category(name, int(color)))

    def update_category(self, name, new_name=None, color=None):
        with self._lock:
            cat = self._find_category(name)
            if cat is None:
                raise BackendError("not_found", name)
            if new_name and new_name.strip() != cat.name:
                new_name = new_name.strip()
                if "," in new_name or ";" in new_name:
                    raise BackendError("category_name", new_name)
                if self._find_category(new_name):
                    raise BackendError("category_exists", new_name)
                cat.name = new_name
            if color is not None:
                cat.color = int(color)

    def delete_category(self, name):
        with self._lock:
            cat = self._find_category(name)
            if cat is None:
                raise BackendError("not_found", name)
            self._categories.remove(cat)

    def create_rule(self, name, spec, store_id=None, folder_id=None, categories=(), flag=False):
        with self._lock:
            if folder_id:
                self._folder(folder_id)
            self.rules.append({"name": name, "spec": spec, "store_id": store_id, "folder_id": folder_id,
                               "categories": list(categories), "flag": flag})
        return name

    def create_draft(self, to, subject, body, cc=""):
        with self._lock:
            drafts = self._special("demo-primary", "drafts")
            return replace(self._add(drafts, USER, subject, body, self.now, unread=False, to=to, cc=cc))

    def current_draft(self):
        """En la demostración, cada llamada trae el siguiente borrador de la carpeta Borradores."""
        with self._lock:
            drafts = self._special("demo-primary", "drafts")
            items = sorted((m for m in self._messages.values() if m.folder_id == drafts),
                           key=lambda m: m.received or datetime.min, reverse=True)
            if not items:
                raise BackendError("no_current")
            msg = items[self._draft_turn % len(items)]
            self._draft_turn += 1
            own, _ = split_quoted(msg.body or "")
            self._current = (msg.id, own)
            return {"subject": msg.subject, "body": own, "to": msg.to, "editable": True}

    def apply_to_current(self, changes, subject=None):
        with self._lock:
            if not self._current or self._current[0] not in self._messages:
                raise BackendError("no_current")
            msg = self._messages[self._current[0]]
            text, applied, failed = apply_changes(msg.body or "", changes)
            msg.body = text
            if subject is not None:
                msg.subject = subject
            own = split_quoted(text)[0]
            self._current = (msg.id, own)
            return applied, failed, own
