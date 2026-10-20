"""Corrector de inglés para correos que funciona sin internet.

Combina:
- ortografía con diccionario incluido (pyspellchecker) y una lista de errores frecuentes;
- reglas de gramática habituales (a/an, concordancia, «didn't + pasado», «look forward to + -ing»…);
- errores típicos de hispanohablantes («explain me», «informations», «since 2 weeks», falsos amigos…);
- puntuación, mayúsculas, estilo de correo profesional y tono.

`check()` devuelve una lista de `Issue`; `apply()` aplica las sugerencias elegidas.
"""

import re
from dataclasses import dataclass, field
from functools import lru_cache

try:
    from spellchecker import SpellChecker
except ImportError:  # sin diccionario: solo reglas
    SpellChecker = None

KINDS = ("spelling", "grammar", "esl", "punctuation", "style", "tone", "clarity")


@dataclass
class Issue:
    start: int
    end: int
    kind: str
    rule: str
    text: str
    suggestions: list = field(default_factory=list)
    safe: bool = False  # se puede aplicar automáticamente con «Aplicar correcciones seguras»
    params: dict = field(default_factory=dict)


# ---------------------------------------------------------------- explicaciones (ES / EN / FR)

MESSAGES = {
    "spelling": ("Posible error ortográfico.", "Possible spelling mistake.", "Faute d'orthographe possible."),
    "misspelling": ("Error ortográfico frecuente.", "Common misspelling.", "Faute d'orthographe fréquente."),
    "contraction": ("Falta el apóstrofo en la contracción.", "The contraction is missing its apostrophe.",
                    "Il manque l'apostrophe de la contraction."),
    "a_an": ("Usa «an» delante de sonido vocálico y «a» delante de sonido consonántico.",
             "Use “an” before a vowel sound and “a” before a consonant sound.",
             "« an » devant un son voyelle, « a » devant un son consonne."),
    "repeated": ("Palabra repetida.", "Repeated word.", "Mot répété."),
    "pronoun_i": ("En inglés «I» (yo) siempre va en mayúscula.", "“I” is always capitalized in English.",
                  "En anglais, « I » (je) prend toujours une majuscule."),
    "sentence_case": ("La frase debería empezar con mayúscula.", "The sentence should start with a capital letter.",
                      "La phrase devrait commencer par une majuscule."),
    "proper_case": ("Días, meses, idiomas y nacionalidades van con mayúscula en inglés.",
                    "Days, months, languages and nationalities are capitalized in English.",
                    "En anglais, jours, mois, langues et nationalités prennent une majuscule."),
    "agreement": ("Concordancia entre sujeto y verbo.", "Subject–verb agreement.", "Accord sujet–verbe."),
    "aux_base": ("Después de un auxiliar (did, can, will…) el verbo va en forma base.",
                 "After an auxiliary (did, can, will…) use the base form of the verb.",
                 "Après un auxiliaire (did, can, will…), le verbe reste à la forme de base."),
    "participle": ("Después de have/has/had, y de be en pasiva, va el participio: «have sent», «was sent».",
                   "After have/has/had, and after be in the passive, use the past participle: “have sent”, “was sent”.",
                   "Après have/has/had, et après be au passif, on met le participe passé : « have sent », « was sent »."),
    "modal_to": ("Los verbos modales (can, must, should…) no llevan «to».",
                 "Modal verbs (can, must, should…) are not followed by “to”.",
                 "Les modaux (can, must, should…) ne sont pas suivis de « to »."),
    "modal_of": ("Se escribe «could/would/should have», no «of».", "Write “could/would/should have”, not “of”.",
                 "On écrit « could/would/should have », pas « of »."),
    "look_forward": ("«Look forward to» va seguido de -ing: «I look forward to hearing from you».",
                     "“Look forward to” takes -ing: “I look forward to hearing from you”.",
                     "« Look forward to » est suivi de -ing : « I look forward to hearing from you »."),
    "thanks_for": ("Después de «thank you for» el verbo va en -ing.", "After “thank you for”, use the -ing form.",
                   "Après « thank you for », le verbe prend -ing."),
    "double_negative": ("Doble negación: en inglés se usa «anything/anyone» tras un verbo negativo.",
                        "Double negative: use “anything/anyone” after a negative verb.",
                        "Double négation : utilisez « anything/anyone » après un verbe négatif."),
    "fewer": ("Con sustantivos contables en plural se usa «fewer», no «less».",
              "Use “fewer”, not “less”, with plural countable nouns.",
              "Avec un nom dénombrable au pluriel, on dit « fewer » et non « less »."),
    "number_of": ("Con sustantivos contables se usa «number of», no «amount of».",
                  "Use “number of”, not “amount of”, with countable nouns.",
                  "Avec un nom dénombrable, on dit « number of » et non « amount of »."),
    "confusion": ("Palabras que suelen confundirse.", "Commonly confused words.", "Mots souvent confondus."),
    "uncountable": ("Sustantivo incontable en inglés: no lleva plural.", "Uncountable noun in English: no plural.",
                    "Nom indénombrable en anglais : pas de pluriel."),
    "esl": ("Error frecuente de hispanohablantes en inglés.", "Common mistake for Spanish speakers.",
            "Erreur fréquente des hispanophones en anglais."),
    "false_friend": ("Falso amigo: la palabra no significa lo mismo que en español.",
                     "False friend: the word does not mean what it means in Spanish.",
                     "Faux ami : le mot n'a pas le même sens qu'en espagnol."),
    "since_for": ("Para duraciones se usa «for» (for 2 weeks); «since» es para un punto en el tiempo.",
                  "Use “for” with durations (for 2 weeks); “since” is for a point in time.",
                  "Pour une durée on dit « for » (for 2 weeks) ; « since » indique un point de départ."),
    "missing_subject": ("En inglés la frase necesita sujeto: «it is possible», «is it possible…?».",
                        "English needs a subject here: “it is possible”, “is it possible…?”.",
                        "L'anglais exige un sujet : « it is possible », « is it possible… ? »."),
    "space_before": ("Sobra el espacio antes del signo de puntuación.", "Remove the space before the punctuation mark.",
                     "Supprimez l'espace avant la ponctuation."),
    "space_after": ("Falta un espacio después del signo de puntuación.", "Add a space after the punctuation mark.",
                    "Ajoutez une espace après la ponctuation."),
    "multi_space": ("Espacios repetidos.", "Repeated spaces.", "Espaces répétées."),
    "spanish_marks": ("En inglés no se usan «¿» ni «¡».", "English does not use “¿” or “¡”.",
                      "L'anglais n'utilise pas « ¿ » ni « ¡ »."),
    "multi_marks": ("Varios signos seguidos pueden sonar exagerados o bruscos.",
                    "Several marks in a row can sound excessive or abrupt.",
                    "Plusieurs signes à la suite peuvent sembler excessifs."),
    "wordy": ("Expresión larga: hay una forma más directa.", "Wordy phrase: there is a more direct option.",
              "Formulation lourde : il existe plus simple."),
    "cliche": ("Fórmula anticuada o poco natural en correos.", "Old-fashioned or unnatural email phrase.",
               "Formule vieillie ou peu naturelle dans un e-mail."),
    "inclusive": ("Saludo poco inclusivo: mejor el nombre o un saludo neutro.",
                  "Non-inclusive greeting: better use the name or a neutral greeting.",
                  "Salutation peu inclusive : préférez le nom ou une formule neutre."),
    "shouting": ("Las mayúsculas sostenidas se leen como gritos.", "Sustained capitals read as shouting.",
                 "Les majuscules prolongées donnent l'impression de crier."),
    "demanding": ("Suena exigente: suaviza la petición.", "Sounds demanding: soften the request.",
                  "Ton exigeant : adoucissez la demande."),
    "abbreviation": ("Abreviatura informal o brusca en un correo profesional.",
                     "Informal or abrupt abbreviation in a professional email.",
                     "Abréviation familière ou abrupte dans un e-mail professionnel."),
    "passive": ("Voz pasiva: la activa suele ser más clara.", "Passive voice: the active voice is usually clearer.",
                "Voix passive : l'actif est souvent plus clair."),
    "long_sentence": ("Frase muy larga ({n} palabras): divídela.", "Very long sentence ({n} words): split it.",
                      "Phrase très longue ({n} mots) : coupez-la."),
    "no_greeting": ("El correo no tiene saludo (Hi/Hello/Dear…).", "The email has no greeting (Hi/Hello/Dear…).",
                    "L'e-mail n'a pas de salutation (Hi/Hello/Dear…)."),
    "no_closing": ("El correo no tiene despedida (Best regards, Thank you…).",
                   "The email has no closing (Best regards, Thank you…).",
                   "L'e-mail n'a pas de formule de politesse (Best regards, Thank you…)."),
    "subject_empty": ("El asunto está vacío.", "The subject is empty.", "L'objet est vide."),
    "subject_long": ("Asunto muy largo: se corta en el móvil.", "Very long subject: it gets cut off on phones.",
                     "Objet très long : il sera tronqué sur mobile."),
    "subject_caps": ("Asunto en mayúsculas: se lee como un grito.", "All-caps subject reads as shouting.",
                     "Objet en majuscules : effet de cri."),
    "subject_prefix": ("Prefijos repetidos (RE: RE: / FW: FW:).", "Repeated prefixes (RE: RE: / FW: FW:).",
                       "Préfixes répétés (RE: RE: / TR: TR:)."),
}

# ---------------------------------------------------------------- listas

MISSPELLINGS = {
    "recieve": "receive", "recieved": "received", "recieving": "receiving", "definately": "definitely",
    "definatly": "definitely", "seperate": "separate", "seperately": "separately", "occured": "occurred",
    "occurence": "occurrence", "untill": "until", "wich": "which", "accomodate": "accommodate", "adress": "address",
    "begining": "beginning", "beleive": "believe", "calender": "calendar", "comming": "coming", "commited": "committed",
    "comittee": "committee", "concious": "conscious", "existance": "existence", "foward": "forward",
    "goverment": "government", "grammer": "grammar", "independant": "independent", "maintainance": "maintenance",
    "neccessary": "necessary", "necesary": "necessary", "noticable": "noticeable", "occassion": "occasion",
    "persue": "pursue", "posession": "possession", "prefered": "preferred", "priviledge": "privilege",
    "publically": "publicly", "recomend": "recommend", "reccomend": "recommend", "refered": "referred",
    "relevent": "relevant", "responsable": "responsible", "responsability": "responsibility",
    "sucessful": "successful", "succesful": "successful", "tommorow": "tomorrow", "tomorow": "tomorrow",
    "truely": "truly", "wierd": "weird", "writting": "writing", "arguement": "argument", "buisness": "business",
    "bussiness": "business", "collegue": "colleague", "colleage": "colleague", "enviroment": "environment",
    "harrass": "harass", "immediatly": "immediately", "inmediately": "immediately", "liason": "liaison",
    "mispell": "misspell", "payed": "paid", "possesion": "possession", "refference": "reference",
    "sincerly": "sincerely", "thier": "their", "acknowledgment": "acknowledgment", "adresses": "addresses",
    "apologise": "apologize", "aproval": "approval", "aproved": "approved", "atached": "attached",
    "attatched": "attached", "attachement": "attachment", "availible": "available", "avaliable": "available",
    "cancelation": "cancellation", "comission": "commission", "confidencial": "confidential",
    "confirmated": "confirmed", "custumer": "customer", "costumer": "customer", "costumers": "customers",
    "custumers": "customers", "dissapointed": "disappointed", "doesnt": "doesn't", "eficient": "efficient",
    "fraudulant": "fraudulent", "fraudlent": "fraudulent", "guarentee": "guarantee", "garantee": "guarantee",
    "inconvinience": "inconvenience", "inconvenince": "inconvenience", "informaton": "information",
    "inquiery": "inquiry", "invesigation": "investigation", "managment": "management", "mantain": "maintain",
    "oportunity": "opportunity", "oppurtunity": "opportunity", "procces": "process", "proccess": "process",
    "recived": "received", "reimbursment": "reimbursement", "remainder": "remainder", "transfered": "transferred",
    "transfering": "transferring", "transaccion": "transaction", "transacction": "transaction",
    "unfortunatly": "unfortunately", "unfortunatelly": "unfortunately", "verifiy": "verify", "wether": "whether",
    "acount": "account", "accout": "account", "anual": "annual", "beggining": "beginning", "buget": "budget",
    "cheked": "checked", "comunication": "communication", "dicision": "decision", "familiar": "familiar",
    "finaly": "finally", "folowing": "following", "folow": "follow", "hapen": "happen", "hapened": "happened",
    "interesting": "interesting", "knowlege": "knowledge", "lenght": "length", "meeing": "meeting",
    "mesage": "message", "nessesary": "necessary", "ofice": "office", "pasword": "password", "paymet": "payment",
    "posible": "possible", "probem": "problem", "proyect": "project", "proyects": "projects", "realy": "really",
    "recomendation": "recommendation", "regardles": "regardless", "regulary": "regularly", "reponse": "response",
    "requeriment": "requirement", "requeriments": "requirements", "shedule": "schedule", "stablish": "establish",
    "succes": "success", "sumary": "summary", "suport": "support", "temperary": "temporary", "thru": "through",
    "usefull": "useful", "wellcome": "welcome", "aswell": "as well", "infact": "in fact",
}
MISSPELLINGS = {k: v for k, v in MISSPELLINGS.items() if k != v}

CONTRACTIONS = {
    "dont": "don't", "doesnt": "doesn't", "didnt": "didn't", "isnt": "isn't", "arent": "aren't", "wasnt": "wasn't",
    "werent": "weren't", "havent": "haven't", "hasnt": "hasn't", "hadnt": "hadn't", "couldnt": "couldn't",
    "wouldnt": "wouldn't", "shouldnt": "shouldn't", "im": "I'm", "ive": "I've", "youre": "you're",
    "theyre": "they're", "thats": "that's", "whats": "what's", "theres": "there's", "wouldve": "would've",
    "couldve": "could've", "shouldve": "should've", "youve": "you've", "weve": "we've", "theyve": "they've",
    "youll": "you'll", "theyll": "they'll", "hes": "he's", "shes": "she's", "cant": "can't", "wont": "won't",
}
UNSAFE_CONTRACTIONS = {"cant", "wont", "hes", "shes", "ill"}

ALLOW = {
    # banca, fraude y tecnología
    "chargeback", "chargebacks", "phishing", "vishing", "smishing", "quishing", "spoofing", "skimming", "skimmer",
    "kyc", "aml", "iban", "swift", "bic", "otp", "pin", "cvv", "cvc", "pan", "pci", "dss", "sla", "slas", "kpi",
    "kpis", "fyi", "asap", "eod", "eta", "ok", "okay", "email", "emails", "e-mail", "inbox", "outlook", "teams",
    "onboarding", "offboarding", "webinar", "fintech", "cybersecurity", "login", "logins", "logout", "username",
    "usernames", "dashboard", "dashboards", "workflow", "workflows", "backlog", "stakeholder", "stakeholders",
    "acquirer", "acquirers", "issuer", "issuers", "cardholder", "cardholders", "visa", "mastercard", "amex",
    "paypal", "zelle", "sepa", "ach", "fx", "covid", "pdf", "pdfs", "excel", "powerpoint", "powerbi", "sharepoint",
    "onedrive", "url", "urls", "it", "hr", "ceo", "cfo", "cto", "cio", "ciso", "ok'd", "inbound", "outbound",
    "recon", "reconciliations", "screenshot", "screenshots", "timeline", "timelines", "unblock", "unblocked",
    "reissue", "reissued", "refundable", "deepfake", "deepfakes", "malware", "ransomware", "cyberattack",
    # abreviaturas habituales en correos
    "approx", "etc", "vs", "attn", "ref", "dept", "mgmt", "info", "misc", "qty", "avg", "est", "ext", "tel",
    "encl", "bcc", "fwd", "pls", "thx", "regs", "admin", "admins", "dev", "ops", "biz",
    # ortografía británica
    "organise", "organised", "organising", "organisation", "organisations", "authorise", "authorised",
    "unauthorised", "authorisation", "recognise", "recognised", "realise", "realised", "analyse", "analysed",
    "colour", "favour", "favourite", "behaviour", "centre", "cheque", "cheques", "licence", "catalogue",
    "programme", "judgement", "prioritise", "prioritised", "finalise", "finalised", "summarise", "summarised",
    "apologise", "apologised", "minimise", "maximise", "emphasise", "utilise", "customise", "optimise",
}
ACRONYM_AN = set("AEFHILMNORSX")  # letras que «suenan» a vocal: an FBI, an SMS, an HR…
AN_EXCEPTIONS = ("hour", "honest", "honor", "honour", "heir", "herb")  # «an hour»
A_EXCEPTIONS = ("uni", "use", "usu", "uti", "euro", "eu", "one", "once", "ubiq", "ufo", "uk", "ura", "uro", "usa")
UNCOUNTABLE = {"informations": "information", "advices": "advice", "feedbacks": "feedback",
               "equipments": "equipment", "softwares": "software", "furnitures": "furniture",
               "knowledges": "knowledge", "evidences": "evidence", "researches": "research",
               "homeworks": "homework", "luggages": "luggage", "baggages": "baggage", "staffs": "staff"}
COUNTABLE_PLURALS = ("emails|customers|clients|people|cases|claims|transactions|mistakes|errors|calls|requests|items|"
                     "documents|cards|accounts|days|hours|steps|problems|issues|questions|complaints|employees|users|"
                     "payments|transfers|alerts|tickets|messages|files|meetings")
IRREGULAR_PAST = {
    "went": "go", "saw": "see", "sent": "send", "paid": "pay", "made": "make", "got": "get", "took": "take",
    "gave": "give", "came": "come", "knew": "know", "told": "tell", "said": "say", "thought": "think",
    "bought": "buy", "brought": "bring", "found": "find", "left": "leave", "felt": "feel", "kept": "keep",
    "wrote": "write", "spoke": "speak", "understood": "understand", "began": "begin", "chose": "choose",
    "forgot": "forget", "heard": "hear", "met": "meet", "ran": "run", "sold": "sell", "spent": "spend",
    "stole": "steal", "lost": "lose", "held": "hold", "did": "do", "had": "have", "was": "be", "were": "be",
    "taught": "teach", "caught": "catch", "built": "build", "drove": "drive", "ate": "eat", "fell": "fall",
    "forgave": "forgive", "grew": "grow", "hid": "hide", "led": "lead", "lent": "lend", "rose": "rise",
    "sought": "seek", "shook": "shake", "sang": "sing", "stood": "stand", "swore": "swear", "threw": "throw",
    "woke": "wake", "won": "win", "withdrew": "withdraw", "received": "receive",
}
# Verbos que tras have/has/had (o be en pasiva) suelen escribirse por error en forma base. Se excluyen los que
# también son sustantivos frecuentes en un banco («write access», «buy orders», «pay slips», «leave policy»…).
PERFECT_FIX = {"send": "sent", "make": "made", "do": "done", "give": "given", "take": "taken", "see": "seen",
               "tell": "told", "find": "found", "know": "known", "bring": "brought", "choose": "chosen",
               "eat": "eaten", "forget": "forgotten", "go": "gone", "hear": "heard", "lose": "lost", "meet": "met",
               "sell": "sold", "speak": "spoken", "spend": "spent", "teach": "taught", "think": "thought",
               "understand": "understood", "begin": "begun", "steal": "stolen", "receive": "received",
               "confirm": "confirmed", "approve": "approved", "inform": "informed", "notify": "notified",
               "explain": "explained"}
PASSIVE_FIX = {k: PERFECT_FIX[k] for k in ("send", "make", "give", "take", "tell", "find", "sell", "steal", "receive",
                                           "confirm", "approve", "inform", "notify")}
PASSIVE_FIX.update({"block": "blocked", "cancel": "cancelled", "attach": "attached", "resolve": "resolved",
                    "solve": "solved", "process": "processed", "refund": "refunded", "charge": "charged"})
PARTICIPLES = set(IRREGULAR_PAST) | {"done", "seen", "given", "taken", "written", "known", "shown", "chosen",
                                     "forgotten", "stolen", "spoken", "broken", "frozen", "driven", "eaten",
                                     "fallen", "hidden", "risen", "shaken", "thrown", "withdrawn", "sent", "paid"}
AUXILIARIES = ("didn't", "did not", "doesn't", "does not", "don't", "do not", "did", "does", "can't", "cannot", "can not",
               "couldn't", "could not", "won't", "will not", "wouldn't", "would not", "shouldn't", "should not",
               "mustn't", "must not", "can", "could", "will", "would", "should", "must", "may", "might")
AUX_WORDS = {"did", "does", "do", "can", "could", "will", "would", "should", "must", "may", "might", "let", "make",
             "makes", "help", "helps", "why", "didn't", "doesn't", "don't", "won't", "can't", "couldn't",
             "wouldn't", "shouldn't", "if"}
ING_VERBS = {"hear", "receive", "meet", "see", "work", "speak", "talk", "discuss", "collaborate", "get", "have",
             "answer", "help", "start", "review", "continue", "chat", "catch", "connect", "learn", "welcome",
             "visit", "join", "support", "resolve", "finalize", "sign", "attend", "read", "respond", "reply",
             "partner", "share", "hearing", "working", "assist", "send", "contact", "solve", "provide",
             "confirm", "explain", "clarify", "understand", "know", "reach", "set", "plan", "move", "build"}
DOUBLE_FINAL = {"get", "set", "put", "run", "sit", "stop", "plan", "chat", "shop", "begin", "swim", "drop",
                "ship", "prefer", "refer", "submit", "admit", "commit", "permit", "occur", "transfer", "forget"}
DAYS_MONTHS = ("monday tuesday wednesday thursday friday saturday sunday january february april june july "
               "september october november december").split()
NATIONALITIES = ("english spanish french portuguese german italian american european mexican colombian peruvian "
                 "chilean argentinian argentine canadian british chinese japanese brazilian venezuelan ecuadorian "
                 "bolivian uruguayan paraguayan guatemalan honduran salvadoran nicaraguan panamanian cuban "
                 "dominican latin").split()
WORDY = [
    (r"in order to", "to"), (r"due to the fact that", "because"), (r"owing to the fact that", "because"),
    (r"at this point in time", "now"), (r"at the present time", "now"), (r"in the event that", "if"),
    (r"with regard to", "regarding"), (r"with regards to", "regarding"), (r"in regards to", "regarding"),
    (r"a large number of", "many"), (r"in spite of the fact that", "although"), (r"for the purpose of", "to"),
    (r"prior to", "before"), (r"subsequent to", "after"), (r"in the near future", "soon"),
    (r"it is important to note that", "note that"), (r"at your earliest convenience", "as soon as you can"),
    (r"in a timely manner", "promptly"), (r"take into consideration", "consider"), (r"make a decision", "decide"),
    (r"provide assistance", "help"), (r"is able to", "can"), (r"are able to", "can"), (r"each and every", "every"),
]
CLICHES = [
    (r"please find attached", "I have attached"), (r"please find enclosed", "I have attached"),
    (r"please do not hesitate to contact (me|us)", r"please contact \1 if you have any questions"),
    (r"do not hesitate to contact (me|us)", r"feel free to contact \1"),
    (r"kindly be informed that", "please note that"), (r"please be informed that", "please note that"),
    (r"please be advised that", "please note that"), (r"do the needful", "take the necessary action"),
    (r"revert back", "reply"), (r"as per our conversation", "as we discussed"),
    (r"as per your request", "as you requested"), (r"\bpfa\b", "please see the attached file"),
    (r"thanking you in advance", "thank you in advance"), (r"hope this mail finds you well", "I hope you are well"),
]
CLOSINGS = ("regards", "best", "thanks", "thank you", "sincerely", "cheers", "kind regards", "best regards",
            "many thanks", "warm regards", "all the best", "yours", "respectfully", "saludos", "cordialement")
GREETINGS = ("hi", "hello", "dear", "good morning", "good afternoon", "good evening", "hey", "greetings",
             "to whom it may concern", "team", "all", "everyone", "hola", "bonjour", "buenos", "buenas", "estimad")

WORD_RE = re.compile(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’]*")
URLISH = re.compile(r"(https?://\S+|www\.\S+|\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+|\b[\w-]+\.(?:com|net|org|pdf|xlsx?|docx?|pptx?|csv|txt|zip)\b)",
                    re.I)
SENTENCE_RE = re.compile(r"[^.!?\n]+(?:[.!?]+|$)", re.M)


def match_case(original, replacement):
    if not replacement:
        return replacement
    if original.isupper() and len(original) > 1 and not replacement.startswith("I'"):
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def ing(verb):
    v = verb.lower()
    if v.endswith("ing"):
        return v
    if v.endswith("ie"):
        return v[:-2] + "ying"
    if v in DOUBLE_FINAL:
        return v + v[-1] + "ing"
    if v.endswith("e") and not v.endswith(("ee", "ye", "oe")):
        return v[:-1] + "ing"
    return v + "ing"


@lru_cache(maxsize=4)
def speller(lang="en"):
    if SpellChecker is None:
        return None
    try:
        return SpellChecker(language=lang)
    except Exception:  # idioma sin diccionario
        return None


def _base_form(word, sp):
    w = word.lower()
    if w in IRREGULAR_PAST:
        return IRREGULAR_PAST[w]
    if not w.endswith("ed") or len(w) < 5:
        return None
    candidates = [w[:-1], w[:-2]]
    if w.endswith("ied"):
        candidates.insert(0, w[:-3] + "y")
    if len(w) > 5 and w[-3] == w[-4]:
        candidates.append(w[:-3])
    known = [c for c in candidates if sp is not None and c not in ("need", "be") and sp.known([c])]
    return max(known, key=lambda c: sp.word_frequency[c]) if known else None


class Checker:
    def __init__(self, text, subject=None, lang="en", user_words=()):
        self.text = text
        self.subject = subject
        self.lang = lang
        self.user_words = {w.lower() for w in user_words}
        self.issues = []
        self.protected = [(m.start(), m.end()) for m in URLISH.finditer(text)]

    # -------- utilidades
    def _protected(self, start, end):
        return any(s < end and start < e for s, e in self.protected)

    def add(self, start, end, kind, rule, suggestions=(), safe=False, **params):
        if self._protected(start, end):
            return
        self.issues.append(Issue(start, end, kind, rule, self.text[start:end], list(suggestions), safe, params))

    def sub(self, pattern, replacement, kind, rule, safe=False, flags=re.I, group=0):
        for m in re.finditer(pattern, self.text, flags):
            start, end = m.span(group)
            original = m.group(group)
            new = m.expand(replacement) if "\\" in replacement else replacement
            self.add(start, end, kind, rule, [match_case(original, new)], safe)

    # -------- reglas
    def run(self):
        if self.lang == "en":
            self.misspellings()
            self.a_an()
            self.pronoun_i()
            self.agreement()
            self.aux_base()
            self.participles()
            self.patterns()
            self.capitals()
            self.style()
            self.tone()
            self.clarity()
            self.structure()
        self.repeated()
        self.punctuation()
        self.spelling()
        return self.resolve()

    def misspellings(self):
        for m in WORD_RE.finditer(self.text):
            w = m.group(0)
            low = w.lower().replace("’", "'")
            if low in MISSPELLINGS:
                self.add(m.start(), m.end(), "spelling", "misspelling", [match_case(w, MISSPELLINGS[low])], True)
            elif low in CONTRACTIONS and low not in ("ill",):
                if low == "im" and w == "IM":
                    continue
                self.add(m.start(), m.end(), "spelling", "contraction", [match_case(w, CONTRACTIONS[low])]
                         if low not in ("im", "ive") else [CONTRACTIONS[low]], low not in UNSAFE_CONTRACTIONS)
            elif low in UNCOUNTABLE:
                self.add(m.start(), m.end(), "esl", "uncountable", [match_case(w, UNCOUNTABLE[low])], True)

    def a_an(self):
        for m in re.finditer(r"\b(a|an)\s+([A-Za-z][\w'-]*)", self.text, re.I):
            art, word = m.group(1), m.group(2)
            low = word.lower()
            if word.isupper() and len(word) > 1 and word.isalpha():
                wants_an = word[0] in ACRONYM_AN
            elif low.startswith(AN_EXCEPTIONS):
                wants_an = True
            elif low[0] in "aeiou":
                wants_an = not low.startswith(A_EXCEPTIONS)
            else:
                wants_an = False
            if low in ("lot", "few", "little", "bit", "couple"):
                wants_an = False
            if art.lower() == "a" and wants_an:
                self.add(m.start(1), m.end(1), "grammar", "a_an", [match_case(art, "an")], True)
            elif art.lower() == "an" and not wants_an:
                self.add(m.start(1), m.end(1), "grammar", "a_an", [match_case(art, "a")], True)

    def repeated(self):
        for m in re.finditer(r"\b(\w+)(\s+)(\1)\b", self.text, re.I):
            if m.group(1).lower() in ("that", "had", "is", "do", "very", "so", "bye", "no", "ha", "la"):
                continue
            if m.group(1).isdigit():
                continue
            self.add(m.start(2), m.end(3), "grammar", "repeated", [""], True)

    def pronoun_i(self):
        for m in re.finditer(r"(?<![\w'’.-])i(?!\.e\b)(?=(\s|'m|'ve|'ll|'d|’m|’ve|’ll|’d)\b|\s*[,.!?]|$)", self.text):
            self.add(m.start(), m.end(), "grammar", "pronoun_i", ["I"], True)

    def agreement(self):
        tokens = [(m.group(0), m.start(), m.end()) for m in re.finditer(r"[A-Za-z']+", self.text)]
        third = {"he", "she", "it", "everyone", "everybody", "nobody", "somebody", "someone", "anyone", "anybody",
                 "nothing", "something", "everything"}
        others = {"i", "you", "we", "they", "people"}
        to_third = {"have": "has", "do": "does", "don't": "doesn't", "are": "is", "were": "was"}
        singular = {"customer", "client", "card", "account", "merchant", "bank", "manager", "user", "claim",
                    "transaction", "payment", "system", "company", "document", "email", "process", "person",
                    "cardholder", "supplier", "provider", "agent", "branch", "colleague", "department"}
        determiners = {"the", "this", "that", "a", "an", "my", "our", "your", "his", "her", "their", "each", "every"}
        to_other = {"has": "have", "does": "do", "doesn't": "don't", "is": "are", "was": "were"}
        for i in range(1, len(tokens)):
            subj, verb = tokens[i - 1][0].lower(), tokens[i][0].lower()
            prev = tokens[i - 2][0].lower() if i >= 2 else ""
            if (prev in AUX_WORDS or prev in ("that", "what", "which", "who", "to", "and", "than", "as", "like")) and \
                    subj not in singular:
                continue
            start, end = tokens[i][1], tokens[i][2]
            if self.text[tokens[i - 1][2]:start].strip():  # hay puntuación entre las palabras
                continue
            fix = None
            if subj in singular and prev in determiners and verb in to_third and verb != "were":
                fix = to_third[verb]
            elif subj in third and verb in to_third:
                if subj == "it" and verb == "were":
                    continue
                fix = to_third[verb]
            elif subj in others and verb in to_other:
                fix = to_other[verb]
                if subj == "i":
                    fix = {"is": "am", "has": "have", "does": "do", "doesn't": "don't", "was": None}.get(verb, fix)
                if fix is None:
                    continue
            if fix:
                self.add(start, end, "grammar", "agreement", [match_case(tokens[i][0], fix)], True)

    def aux_base(self):
        sp = speller("en")
        aux = "|".join(re.escape(a) for a in sorted(AUXILIARIES, key=len, reverse=True))
        subjects = r"(?:(?:you|he|she|it|we|they|i|the customer|the client)\s+)?"
        for m in re.finditer(rf"\b({aux})\s+{subjects}([a-z]+)\b", self.text, re.I):
            verb = m.group(2)
            if verb.lower() in ("be", "have", "been", "had", "used", "need", "not", "red", "bed", "feed", "seed",
                                "need", "speed", "proceed", "succeed", "exceed", "breed", "indeed"):
                continue
            if m.group(1).lower() in ("will", "would", "could", "should", "might", "may", "must") and \
                    verb.lower() in ("was", "were", "had"):
                continue
            base = _base_form(verb, sp)
            if base and base != verb.lower():
                self.add(m.start(2), m.end(2), "grammar", "aux_base", [match_case(verb, base)], True)

    def participles(self):
        """«have send» → «have sent»; «was send» → «was sent» (forma base en lugar del participio)."""
        found = [(m, PERFECT_FIX) for m in re.finditer(
            r"\b(?:have|has|had|haven't|hasn't|hadn't|have not|has not|had not)\s+(?:(?:you|we|they|he|she|it|i)\s+)?"
            r"(?:(?:already|just|ever|never|not|also|still|recently)\s+)?([a-z]+)\b(?![-'’])", self.text, re.I)]
        found += [(m, PASSIVE_FIX) for m in re.finditer(
            r"\b(?:be|been|being|is|are|was|were)\s+(?:(?:already|just|not|never|also|still)\s+)?([a-z]+)\b(?![-'’])",
            self.text, re.I)]
        for m, table in found:
            verb = m.group(1)
            if verb.lower() in table:
                self.add(m.start(1), m.end(1), "grammar", "participle", [match_case(verb, table[verb.lower()])], True)

    def missing_subject(self):
        """«Is very important for…» → «It is very important for…» (o «Is it…?» si es una pregunta)."""
        adjectives = ("possible|impossible|necessary|important|essential|mandatory|required|clear|true|urgent|better|"
                      "easier|difficult|hard|critical|normal|common|enough")
        tail = r"(?=\s*(?:to|for|because|if|when|since|and|but)\b|\s*[,.!?;:]|\s*$)"
        lead = r"(?:^|(?<=[.!?]\s)|(?<=\n)|\b(?:because|and|but|if|when|since|why)\s+)"
        pattern = (rf"{lead}(?P<verb>is|was)\s+(?P<rest>(?:(?:very|really|so|too|quite|extremely|absolutely|also)\s+)?"
                   rf"(?:{adjectives})){tail}")
        for m in re.finditer(pattern, self.text, re.I | re.M):
            verb, rest = m.group("verb"), m.group("rest")
            start = m.start("verb")
            end = re.search(r"[.!?\n]|$", self.text[m.end():])
            before = self.text[:start].rstrip(" \t")
            sentence_start = not before or before[-1] in ".!?\n"
            if end is not None and end.group(0) == "?":
                suggestion = f"{verb} it {rest}"
            else:
                suggestion = f"{'It' if sentence_start and verb[0].isupper() else 'it'} {verb.lower()} {rest}"
            self.add(start, m.end(), "esl", "missing_subject", [suggestion], True)

    def patterns(self):
        t = self.sub
        t(r"\b(can|could|must|should|will|would|may|might)\s+to\s+(?!some\b|a\s+certain\b|what\b|an?\s+extent\b)(?=[a-z])",
          r"\1 ", "grammar", "modal_to", True)
        t(r"\b(could|would|should|must|might)\s+of\b", r"\1 have", "grammar", "modal_of", True)
        for m in re.finditer(r"\b(look|looking|looks|looked)\s+forward\s+to\s+([a-z]+)\b", self.text, re.I):
            if m.group(2).lower() in ING_VERBS and not m.group(2).lower().endswith("ing"):
                self.add(m.start(2), m.end(2), "grammar", "look_forward", [ing(m.group(2))], True)
        for m in re.finditer(r"\bthanks?(?:\s+you)?(?:\s+so\s+much|\s+very\s+much)?\s+for\s+([a-z]+)\s+(me|us|him|her|them|the|our|my)\b",
                             self.text, re.I):
            if m.group(1).lower() in ING_VERBS:
                self.add(m.start(1), m.end(1), "grammar", "thanks_for", [ing(m.group(1))], True)
        neg = {"nothing": "anything", "nobody": "anybody", "no one": "anyone", "nowhere": "anywhere", "none": "any"}
        for m in re.finditer(r"\b(don't|doesn't|didn't|won't|can't|haven't|hasn't|isn't|aren't|wasn't|weren't|dont|"
                             r"doesnt|didnt|wont|cant|do not|does not|did not|will not|cannot|never)"
                             r"\s+((?:[\w']+\s+){0,5}?)(nothing|nobody|no one|nowhere)\b", self.text, re.I):
            if re.search(r"\b(why|that|because|if|when|where|who|what|how|since|but|and|or|whether)\b", m.group(2), re.I):
                continue  # «nobody» empieza otra oración: «I don't know why nobody called»
            self.add(m.start(3), m.end(3), "grammar", "double_negative", [match_case(m.group(3), neg[m.group(3).lower()])],
                     True)
        t(rf"\bless(?=\s+({COUNTABLE_PLURALS})\b)", "fewer", "grammar", "fewer", True)
        t(rf"\bamount(?=\s+of\s+({COUNTABLE_PLURALS})\b)", "number", "grammar", "number_of", True)
        # errores de hispanohablantes
        t(r"\bexplain\s+(me|us|him|her|them)\b", r"explain to \1", "esl", "esl", True)
        t(r"\bdiscuss(es|ed|ing)?\s+about\b", r"discuss\1", "esl", "esl", True)
        t(r"\b(depend|depends|depending|depended)\s+(of|from)\b", r"\1 on", "esl", "esl", True)
        t(r"\baccording\s+with\b", "according to", "esl", "esl", True)
        t(r"\bin\s+the\s+other\s+hand\b", "on the other hand", "esl", "esl", True)
        attend = {"assist": "attend", "assists": "attends", "assisted": "attended", "assisting": "attending"}
        for m in re.finditer(r"\b(assist|assists|assisted|assisting)\s+to\s+(the|a|an|our|my|this|that|your|tomorrow's)\s+"
                             r"(meeting|call|session|training|event|conference|class|webinar|workshop)\b", self.text, re.I):
            self.add(m.start(), m.end(), "esl", "false_friend",
                     [f"{match_case(m.group(1), attend[m.group(1).lower()])} {m.group(2)} {m.group(3)}"], True)
        t(r"\bmake\s+(a|the|some|any|more|few)\s+(question|questions)\b", r"ask \1 \2", "esl", "esl", True)
        do_make = {"do": "make", "did": "made", "doing": "making", "does": "makes", "done": "made"}
        for m in re.finditer(r"\b(do|did|doing|does|done)\s+(a|the|some|many|several|any|no)\s+"
                             r"(mistake|mistakes|error|errors)\b", self.text, re.I):
            self.add(m.start(1), m.end(1), "esl", "esl", [match_case(m.group(1), do_make[m.group(1).lower()])], True)
        t(r"\bsaid\s+me\b", "told me", "esl", "esl", True)
        t(r"\bsay\s+me\b", "tell me", "esl", "esl", True)
        t(r"\breturn\s+back\b", "return", "esl", "esl", True)
        t(r"\b(i|we|they|you)(\s+am|\s+are|'m|’m|'re|’re)\s+(agree|disagree)\b", r"\1 \3", "esl", "esl", True)
        t(r"\bare\s+you\s+agree\b", "do you agree", "esl", "esl", True)
        t(r"\bsince\s+(\d+|a|one|two|three|four|five|six|seven|eight|nine|ten|several|many|a few)\s+"
          r"(days?|weeks?|months?|years?|hours?|minutes?)\b", r"for \1 \2", "esl", "since_for", True)
        t(r"\bthe\s+most\s+of\b", "most of", "esl", "esl", True)
        t(r"\ban?\s+information\b", "some information", "esl", "uncountable", True)
        t(r"\ban?\s+advice\b", "a piece of advice", "esl", "uncountable", True)
        t(r"\b(would like|want|wanted|need|needed)\s+that\s+(you|he|she|they|we|it)\s+([a-z]+)", r"\1 \2 to \3",
          "esl", "esl", False)
        t(r"\bfor\s+to\b", "to", "esl", "esl", True)
        t(r"\bremember\s+(me|him|her|them|us)\s+to\b", r"remind \1 to", "esl", "false_friend", True)
        t(r"\bit'?s\s+depends\b", "it depends", "esl", "esl", True)
        self.missing_subject()
        t(r"\bdelay\s+in\s+(answer|respond)\b", "delay in replying", "esl", "esl", True)
        t(r"\b(is|are|was|were|be|being)\s+in\s+revision\b", r"\1 under review", "esl", "esl", True)
        t(r"\bin\s+the\s+next\s+days\b", "in the next few days", "esl", "esl", True)
        t(r"\b(?:received|receive|reviewing|review|regarding|about|with|for)\s+(you)(?=\s+(?:claim|account|card|"
          r"request|email|message|case|application|order|payment|transfer|reply|answer|documents?|statement|"
          r"complaint|query|question|details)\b)", "your", "grammar", "confusion", False, group=1)
        t(r"\bactually(?=,?\s+(?:the\s+(?:case|claim|account|card|process|status|investigation|request|transaction)|"
          r"we\s+are|it\s+is|is\s+in)\b)", "currently", "esl", "false_friend", False)
        t(r"\bin\s+this\s+moment\b", "at the moment", "esl", "esl", True)
        t(r"\bactual\s+(situation|status|balance|address|process|state|policy|version|account|procedure|"
          r"provider|system|manager)\b", r"current \1", "esl", "false_friend", False)
        t(r"\bsensible\s+(information|data|documents?|matters?|topics?|cases?|details)\b", r"sensitive \1", "esl",
          "false_friend", True)
        carry = {"realize": "carry out", "realizes": "carries out", "realized": "carried out",
                 "realizing": "carrying out", "realise": "carry out", "realised": "carried out"}
        for m in re.finditer(r"\b(realize|realizes|realized|realizing|realise|realised)\s+(a|the|an|this|our|your|some)\s+"
                             r"(transfer|payment|transaction|analysis|review|investigation|process|procedure|purchase|"
                             r"call|audit|deposit|withdrawal|refund|change)\b", self.text, re.I):
            self.add(m.start(1), m.end(1), "esl", "false_friend", [match_case(m.group(1), carry[m.group(1).lower()])],
                     False)
        t(r"\b(we|i|they)\s+pretend\s+to\b", r"\1 intend to", "esl", "false_friend", False)
        t(r"\b(in|to|the|shared|my|your|our|this|that)\s+carpet\b", r"\1 folder", "esl", "false_friend", False)
        t(r"\b(i|we|you|they)\s+advice\b", r"\1 advise", "grammar", "confusion", True)
        t(r"\bto\s+advice\b", "to advise", "grammar", "confusion", True)
        t(r"\b(an|your|the|my|our|his|her|their)\s+advise\b", r"\1 advice", "grammar", "confusion", True)
        t(r"\bloose\s+(the|my|your|our|their|access|money|data|time|it|them)\b", r"lose \1", "grammar", "confusion",
          True)
        t(r"\b(more|less|better|worse|rather|other|bigger|smaller|faster|slower|later|earlier|higher|lower|greater|"
          r"fewer|older|newer|easier|harder)\s+then\b", r"\1 than", "grammar", "confusion", True)
        t(r"\bits\s+(?=(a|an|the|not|been|very|time|possible|important|necessary|ok|okay|done|going|just|also|still|"
          r"already|clear|true|my|your|our|their|urgent|fine)\b)", "it's ", "grammar", "confusion", True)
        t(r"\bit['’]s\s+(?=(own|name|account|balance|status|team|value|data|owner|customers?|policy|policies|purpose|role|"
          r"use|contents?|address|location|website)\b)", "its ", "grammar", "confusion", True)
        t(r"\byour\s+(?=(going|not|the|a|an|so|doing|able|sure|aware|invited)\b)", "you're ", "grammar", "confusion",
          True)
        t(r"\byour\s+(?=welcome\s*([.!,]|$|to\s+(call|contact|join|ask|reach|email|attend|use|send|visit)\b))",
          "you're ", "grammar", "confusion", True, re.I | re.M)
        t(r"\byour\s+(?=(right|wrong)\b(?!\s+to\b))", "you're ", "grammar", "confusion", False)
        t(r"\btheir\s+(?=(is|are|was|were|will be|has been|have been)\b)", "there ", "grammar", "confusion", True)
        for m in re.finditer(r"\b(\w+\s+)?(there)\s+(own|account|accounts|team|teams|company|card|cards|email|emails|"
                             r"manager|bank|claim|claims|customers|clients|request|requests|documents|names?)\b",
                             self.text, re.I):
            if (m.group(1) or "").strip().lower() in ("is", "are", "was", "were", "be", "been", "any", "no", "isn't",
                                                       "aren't", "wasn't", "weren't"):
                continue
            self.add(m.start(2), m.end(2), "grammar", "confusion", [match_case(m.group(2), "their")], False)
        t(r"\bwho['’]s\s+(?=(account|card|email|name|turn|responsibility|claim|request|phone|job)\b)", "whose ",
          "grammar", "confusion", True)
        t(r"\b((?:more|less|fewer)\s+\w+)\s+then\b", r"\1 than", "grammar", "confusion", True)
        for m in re.finditer(r"\bthere\s+(is|was|'s)\s+(?=(?:many|several|few|fewer|more|some|two|three|four|five|\d+)"
                             r"\s+[a-z]+s\b)", self.text, re.I):
            fix = {"is": "are", "was": "were", "'s": " are"}[m.group(1).lower()]
            self.add(m.start(1), m.end(1), "grammar", "agreement", [fix.strip() if m.group(1) != "'s" else fix], True)
        t(r"\ban?\s+((?:\w+\s+)?)(information|advice|feedback|evidence|equipment|software|knowledge|furniture)\b",
          r"\1\2", "esl", "uncountable", True)
        t(r"\balot\b", "a lot", "spelling", "misspelling", True)
        t(r"\birregardless\b", "regardless", "grammar", "confusion", True)

    def capitals(self):
        for m in re.finditer(r"\b(" + "|".join(DAYS_MONTHS + NATIONALITIES) + r")\b", self.text):
            self.add(m.start(), m.end(), "grammar", "proper_case", [m.group(1).capitalize()], True)
        for m in re.finditer(r"\b(may|march)(?=\s+\d)", self.text):
            self.add(m.start(), m.end(), "grammar", "proper_case", [m.group(1).capitalize()], True)
        abbrev = ("e.g", "i.e", "etc", "vs", "mr", "mrs", "ms", "dr", "approx", "no", "inc", "ltd", "co", "jr", "sr")
        for m in re.finditer(r"(?:^|[.!?]\s+|\n\s*\n\s*)([a-z])", self.text):
            before = self.text[:m.start(1)].rstrip()
            last = re.findall(r"([A-Za-z.]+)\.$", before)
            if last and last[-1].lower().rstrip(".") in abbrev:
                continue
            if self.text[m.start(1):m.start(1) + 4].lower().startswith(("http", "www.")):
                continue
            self.add(m.start(1), m.end(1), "grammar", "sentence_case", [m.group(1).upper()], True)

    def punctuation(self):
        for m in re.finditer(r"(?<=\w)[ \t]+([,;:!?.])(?![\w/)(\-DPp3.])", self.text):
            if self.lang == "fr":
                continue
            self.add(m.start(), m.start(1), "punctuation", "space_before", [""], True)
        for m in re.finditer(r"(?<=[a-zA-Z\)])([,;])(?=[A-Za-z])", self.text):
            self.add(m.start(1), m.end(1), "punctuation", "space_after", [m.group(1) + " "], True)
        for m in re.finditer(r"(?<=[a-z]{3})\.(?=[A-Z][a-z])", self.text):
            self.add(m.start(), m.end(), "punctuation", "space_after", [". "], True)
        for m in re.finditer(r"(?<=\S)( {2,})(?=\S)", self.text):
            self.add(m.start(1), m.end(1), "punctuation", "multi_space", [" "], True)
        if self.lang == "en":
            for m in re.finditer(r"[¿¡]", self.text):
                self.add(m.start(), m.end(), "punctuation", "spanish_marks", [""], True)
        for m in re.finditer(r"([!?])[!?]+", self.text):
            self.add(m.start(), m.end(), "tone", "multi_marks", [m.group(1)], False)

    def style(self):
        for pattern, repl in WORDY:
            self.sub(r"\b" + pattern + r"\b", repl, "style", "wordy", False)
        for pattern, repl in CLICHES:
            self.sub(r"\b" + pattern.replace(r"\b", "") + r"\b", repl, "style", "cliche", False)
        self.sub(r"\bdear\s+(sir|sirs|madam|sir or madam|sir/madam)\b(?=\s*[,:])", "Dear [Name]", "style",
                 "inclusive", False)
        self.sub(r"\b(hi|hello|hey)\s+guys\b", r"\1 everyone", "style", "inclusive", False)

    def tone(self):
        acronyms = {w.upper() for w in ALLOW} | {"ASAP", "FYI", "URGENT"}
        closing = [m.end() for m in re.finditer(r"\b(" + "|".join(CLOSINGS) + r")\b", self.text, re.I)]
        signature = closing[-1] if closing else len(self.text) + 1
        for m in re.finditer(r"\b([A-Z]{4,}(?:\s+[A-Z]{2,}){1,})\b", self.text):
            if m.start() > signature:
                continue
            words = m.group(1).split()
            if all(w in acronyms for w in words):
                continue
            self.add(m.start(), m.end(), "tone", "shouting", [m.group(1).capitalize()], False)
        self.sub(r"\byou\s+(must|need to|have to)\s+(send|reply|answer|call|provide|confirm|fix|resolve|check|review|"
                 r"respond|update|complete|sign)\b", r"could you please \2", "tone", "demanding", False)
        self.sub(r"\bas I (said|mentioned|told you) (before|already|previously)\b", "as mentioned in my previous email",
                 "tone", "demanding", False)
        for m in re.finditer(r"\bASAP\b", self.text):
            self.add(m.start(), m.end(), "tone", "abbreviation", ["as soon as possible"], False)

    def clarity(self):
        for m in re.finditer(r"\b(am|is|are|was|were|be|been|being)\s+((?:\w+ly\s+)?)([a-z]+ed|"
                             + "|".join(sorted(PARTICIPLES - {"was", "were", "had", "did"})) + r")\b", self.text, re.I):
            if m.group(3).lower() in ("based", "located", "interested", "concerned", "pleased", "satisfied", "used",
                                      "supposed", "allowed", "married", "tired", "bored", "excited", "worried",
                                      "involved", "attached", "required", "needed", "related", "scheduled",
                                      "committed", "dedicated", "closed", "opened", "aware"):
                continue
            self.add(m.start(), m.end(), "clarity", "passive", [], False)
        for m in SENTENCE_RE.finditer(self.text):
            n = len(m.group(0).split())
            if n > 35:
                self.add(m.start(), m.end(), "clarity", "long_sentence", [], False, n=n)

    def structure(self):
        lines = [l.strip() for l in self.text.strip().splitlines() if l.strip()]
        if len(" ".join(lines).split()) >= 25:
            first = lines[0].lower() if lines else ""
            named = len(first.split()) <= 5 and first.endswith((",", ":"))  # «Ana,» o «Equipo de pagos:»
            if not first.startswith(GREETINGS) and not named:
                self.issues.append(Issue(0, 0, "style", "no_greeting", "", ["Hi [Name],"], False))
            tail = " ".join(lines[-4:]).lower()
            if not any(c in tail for c in CLOSINGS):
                end = len(self.text)
                self.issues.append(Issue(end, end, "style", "no_closing", "", ["\n\nBest regards,\n[Your name]"], False))
        if self.subject is None or not self.text.strip():
            return
        s = self.subject.strip()
        if not s:
            self.issues.append(Issue(-1, -1, "style", "subject_empty", "", [], False))
            return
        if len(s) > 78:
            self.issues.append(Issue(-1, -1, "style", "subject_long", s, [], False))
        letters = [c for c in s if c.isalpha()]
        if len(letters) > 8 and sum(c.isupper() for c in letters) / len(letters) > 0.8:
            self.issues.append(Issue(-1, -1, "tone", "subject_caps", s, [s.capitalize()], False))
        if re.match(r"^((re|fw|fwd|rv|tr)\s*:\s*){2,}", s, re.I):
            clean = re.sub(r"^((re|fw|fwd|rv|tr)\s*:\s*)+", lambda m: m.group(1), s, flags=re.I)
            self.issues.append(Issue(-1, -1, "style", "subject_prefix", s, [clean], False))

    def spelling(self):
        sp = speller(self.lang)
        if sp is None:
            return
        covered = [(i.start, i.end) for i in self.issues]
        sentence_starts = {m.start() for m in re.finditer(r"(?:^|[.!?]\s+|\n)\s*([A-Za-zÀ-ÿ])", self.text)}
        sentence_starts |= {m.start(1) for m in re.finditer(r"(?:^|[.!?]\s+|\n)\s*([A-Za-zÀ-ÿ])", self.text)}
        tokens = []
        for m in WORD_RE.finditer(self.text):
            w = m.group(0).strip("'’")
            if len(w) <= 2 or self._protected(m.start(), m.end()):
                continue
            low = w.lower()
            if low in ALLOW or low in self.user_words or low in MISSPELLINGS or low in CONTRACTIONS:
                continue
            if w.isupper() and len(w) <= 6:
                continue
            if w[0].isupper() and m.start() not in sentence_starts:
                continue  # nombre propio probable
            if w[0].isupper():
                line_start = self.text.rfind("\n", 0, m.start()) + 1
                line_end = self.text.find("\n", m.end())
                line = self.text[line_start:line_end if line_end >= 0 else len(self.text)]
                if len(line.split()) <= 4:
                    continue  # firma, nombre o cargo
            if any(s < m.end() and m.start() < e for s, e in covered):
                continue
            tokens.append((m, low))
        unknown = sp.unknown([low.replace("’", "'") for _, low in tokens])
        for m, low in tokens:
            key = low.replace("’", "'")
            if key not in unknown:
                continue
            if "'" in key and key.split("'")[0] in sp:
                continue
            cands = sp.candidates(key) if len(key) <= 14 else sp.known(sp.edit_distance_1(key))
            cands = sorted(cands or [], key=lambda c: -sp.word_frequency[c])[:3]
            self.add(m.start(), m.end(), "spelling", "spelling", [match_case(m.group(0), c) for c in cands], False)

    # -------- solapamientos
    def resolve(self):
        priority = {"spelling": 0, "grammar": 1, "esl": 1, "punctuation": 2, "tone": 3, "style": 4, "clarity": 5}
        out, taken = [], []
        for issue in sorted(self.issues, key=lambda i: (priority[i.kind], i.start, -(i.end - i.start))):
            if issue.end > issue.start and any(s < issue.end and issue.start < e for s, e in taken):
                if issue.kind not in ("clarity",):
                    continue
            out.append(issue)
            if issue.end > issue.start and issue.kind != "clarity":
                taken.append((issue.start, issue.end))
        return sorted(out, key=lambda i: (i.start, i.end))


def check(text, subject=None, lang="en", user_words=()):
    return Checker(text, subject, lang, user_words).run()


def apply(text, issues, subject=""):
    """Aplica la primera sugerencia de cada issue (sin solapes). Devuelve (texto, asunto)."""
    body_issues = sorted((i for i in issues if i.start >= 0 and i.suggestions), key=lambda i: i.start, reverse=True)
    last_start = len(text) + 1
    for issue in body_issues:
        if issue.end > last_start:
            continue
        text = text[:issue.start] + issue.suggestions[0] + text[issue.end:]
        last_start = issue.start
    for issue in issues:
        if issue.start < 0 and issue.suggestions:
            subject = issue.suggestions[0]
    return text, subject


def apply_safe(text, subject="", lang="en", user_words=(), rounds=3):
    """Aplica solo las correcciones seguras, repitiendo hasta que no queden (máximo `rounds`)."""
    for _ in range(rounds):
        issues = [i for i in check(text, subject, lang, user_words) if i.safe]
        if not issues:
            break
        text, subject = apply(text, issues, subject)
    return text, subject


def stats(text, lang="en"):
    from ..docpilot.logic import readability_level, text_stats

    st = text_stats(text, lang)
    passive = sum(1 for i in check(text, lang=lang) if i.rule == "passive")
    return {**st, "level": readability_level(st["score"]), "passive": passive}
