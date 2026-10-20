"""Frases y plantillas de correo en inglés profesional, con su traducción al español y al francés como ayuda.

Las plantillas están pensadas para un equipo de reclamaciones de fraude; los datos van entre corchetes
([Name], [Claim number]…) para completarlos antes de enviar.
"""

# Cada frase: (inglés, español, francés).
PHRASES = {
    "greetings": [
        ("Dear Ms. [Surname],", "Estimada Sra. [Apellido]:", "Madame [Nom],"),
        ("Dear Mr. [Surname],", "Estimado Sr. [Apellido]:", "Monsieur [Nom],"),
        ("Hello [Name],", "Hola, [Nombre]:", "Bonjour [Prénom],"),
        ("Hi team,", "Hola, equipo:", "Bonjour à tous,"),
        ("Good morning [Name],", "Buenos días, [Nombre]:", "Bonjour [Prénom],"),
        ("Dear Customer Service team,", "Estimado equipo de atención al cliente:", "Madame, Monsieur,"),
    ],
    "openings": [
        ("Thank you for your email.", "Gracias por su correo.", "Merci pour votre e-mail."),
        ("Thank you for contacting us.", "Gracias por contactarnos.", "Merci de nous avoir contactés."),
        ("I am writing to let you know that…", "Le escribo para informarle de que…", "Je vous écris pour vous informer que…"),
        ("I am writing regarding claim [Claim number].", "Le escribo en relación con la reclamación [número].",
         "Je vous écris au sujet de la réclamation [numéro]."),
        ("Following our phone call today, …", "Tras nuestra llamada de hoy, …", "Suite à notre appel d'aujourd'hui, …"),
        ("I hope you are doing well.", "Espero que se encuentre bien.", "J'espère que vous allez bien."),
    ],
    "requests": [
        ("Could you please send me…?", "¿Podría enviarme…?", "Pourriez-vous m'envoyer… ?"),
        ("I would appreciate it if you could…", "Le agradecería que…", "Je vous serais reconnaissant(e) de…"),
        ("Please let me know if you have any questions.", "Avíseme si tiene alguna pregunta.",
         "N'hésitez pas à me contacter pour toute question."),
        ("Could you please confirm receipt of this email?", "¿Podría confirmar que recibió este correo?",
         "Pourriez-vous accuser réception de cet e-mail ?"),
        ("I have attached the requested documents.", "Adjunto los documentos solicitados.",
         "Vous trouverez ci-joint les documents demandés."),
        ("We would need the following information:", "Necesitaríamos la siguiente información:",
         "Nous aurions besoin des informations suivantes :"),
    ],
    "followup": [
        ("I am following up on my previous email about…", "Retomo mi correo anterior sobre…",
         "Je reviens vers vous au sujet de mon précédent e-mail concernant…"),
        ("Just a quick reminder that…", "Solo un breve recordatorio de que…", "Petit rappel : …"),
        ("Do you have any update on…?", "¿Tiene alguna novedad sobre…?", "Avez-vous du nouveau concernant… ?"),
        ("We have not received a reply yet.", "Todavía no hemos recibido respuesta.",
         "Nous n'avons pas encore reçu de réponse."),
        ("I look forward to hearing from you.", "Quedo a la espera de su respuesta.",
         "Dans l'attente de votre réponse."),
    ],
    "apologies": [
        ("I apologize for the delay in getting back to you.", "Disculpe la demora en responderle.",
         "Veuillez excuser le délai de réponse."),
        ("We are sorry for any inconvenience this may have caused.", "Lamentamos las molestias ocasionadas.",
         "Nous sommes désolés pour la gêne occasionnée."),
        ("Please accept our apologies for the error.", "Le pedimos disculpas por el error.",
         "Veuillez accepter nos excuses pour cette erreur."),
        ("Thank you for your patience.", "Gracias por su paciencia.", "Merci de votre patience."),
    ],
    "bad_news": [
        ("Unfortunately, we are unable to…", "Lamentablemente, no podemos…", "Malheureusement, nous ne pouvons pas…"),
        ("After careful review, …", "Tras una revisión detallada, …", "Après un examen attentif, …"),
        ("We understand this is not the outcome you expected.", "Entendemos que no es el resultado que esperaba.",
         "Nous comprenons que ce n'est pas le résultat attendu."),
        ("If you do not agree with this decision, you may…", "Si no está de acuerdo con esta decisión, puede…",
         "Si vous n'êtes pas d'accord avec cette décision, vous pouvez…"),
    ],
    "closings": [
        ("Best regards,", "Saludos cordiales,", "Cordialement,"),
        ("Kind regards,", "Un cordial saludo,", "Bien cordialement,"),
        ("Sincerely,", "Atentamente,", "Veuillez agréer mes salutations distinguées,"),
        ("Thank you in advance.", "Gracias de antemano.", "Merci d'avance."),
        ("Have a nice day.", "Que tenga un buen día.", "Bonne journée."),
    ],
    "claims": [
        ("We have received your claim and are reviewing it.", "Hemos recibido su reclamación y la estamos revisando.",
         "Nous avons bien reçu votre réclamation et l'étudions."),
        ("Your claim reference number is [Claim number].", "El número de referencia de su reclamación es [número].",
         "Le numéro de référence de votre réclamation est [numéro]."),
        ("We have issued a provisional credit of [Amount] to your account.",
         "Hemos abonado provisionalmente [importe] en su cuenta.",
         "Nous avons crédité provisoirement [montant] sur votre compte."),
        ("Your card has been blocked and a new one will be sent to you.",
         "Su tarjeta ha sido bloqueada y le enviaremos una nueva.",
         "Votre carte a été bloquée et une nouvelle vous sera envoyée."),
        ("Please never share your PIN, passwords or one-time codes with anyone.",
         "Nunca comparta su PIN, contraseñas ni códigos de un solo uso con nadie.",
         "Ne communiquez jamais votre code PIN, vos mots de passe ni vos codes à usage unique."),
        ("We will contact you within [number] business days.", "Le contactaremos en un plazo de [número] días hábiles.",
         "Nous vous contacterons sous [nombre] jours ouvrés."),
        ("We have opened a chargeback with the card network.", "Hemos iniciado un contracargo con la red de la tarjeta.",
         "Nous avons ouvert une rétrofacturation auprès du réseau de la carte."),
    ],
}

# Plantillas completas: (asunto, cuerpo), en inglés.
TEMPLATES = {
    "tpl_ack": (
        "Your claim [Claim number] has been received",
        "Dear [Name],\n\nThank you for contacting us. We have received your claim regarding the transaction of "
        "[Amount] at [Merchant] on [Date], and we have opened case [Claim number].\n\nOur team is reviewing it "
        "and we will contact you within [number] business days. In the meantime, your card has been blocked "
        "to protect your account.\n\nPlease never share your PIN, passwords or one-time codes with anyone.\n\n"
        "Kind regards,\n[Your name]\nFraud Claims Team"),
    "tpl_docs": (
        "Additional information needed for claim [Claim number]",
        "Dear [Name],\n\nTo continue reviewing your claim [Claim number], we need the following documents:\n\n"
        "- A copy of your account statement showing the transaction.\n- The signed claim form.\n"
        "- A copy of the police report, if available.\n\nPlease send them by replying to this email within 10 "
        "business days.\n\nThank you for your cooperation.\n\nBest regards,\n[Your name]\nFraud Claims Team"),
    "tpl_credit": (
        "Provisional credit for claim [Claim number]",
        "Dear [Name],\n\nWe would like to inform you that we have issued a provisional credit of [Amount] to your "
        "account while we complete the investigation of claim [Claim number].\n\nWe will let you know the final "
        "outcome as soon as possible.\n\nKind regards,\n[Your name]\nFraud Claims Team"),
    "tpl_favorable": (
        "Claim [Claim number] resolved in your favor",
        "Dear [Name],\n\nWe are pleased to inform you that claim [Claim number] has been resolved in your favor. "
        "The credit of [Amount] is now final.\n\nThank you for your patience during the investigation.\n\n"
        "Best regards,\n[Your name]\nFraud Claims Team"),
    "tpl_unfavorable": (
        "Outcome of claim [Claim number]",
        "Dear [Name],\n\nAfter careful review of claim [Claim number], we have concluded that the transaction of "
        "[Amount] was authorized with your card and credentials, so we are unable to refund it.\n\nIf you do not "
        "agree with this decision, you may reply to this email with any additional information within 15 "
        "business days.\n\nSincerely,\n[Your name]\nFraud Claims Team"),
    "tpl_chargeback": (
        "Chargeback documentation - case [Claim number]",
        "Dear Dispute Resolution team,\n\nI have attached the supporting documentation for the chargeback on "
        "transaction [Reference] ([Amount], [Date]) related to case [Claim number].\n\nThe cardholder states "
        "that they did not authorize or take part in this transaction, and the card was in their possession at "
        "all times.\n\nCould you please confirm receipt?\n\nBest regards,\n[Your name]\nFraud Claims Team"),
    "tpl_phishing": (
        "Security alert: fraudulent messages",
        "Dear [Name],\n\nWe have detected fraudulent emails and text messages that pretend to come from our "
        "bank. We will never ask you for your PIN, passwords or one-time codes by email, text message or phone."
        "\n\nIf you receive a suspicious message, do not click on any links and forward it to our security team."
        "\n\nKind regards,\n[Your name]\nSecurity Team"),
    "tpl_internal": (
        "Case [Claim number] - follow-up",
        "Hi [Name],\n\nI am following up on case [Claim number]. Could you please send me an update on the "
        "status of the investigation by [Date]?\n\nThank you in advance.\n\nBest regards,\n[Your name]"),
}
