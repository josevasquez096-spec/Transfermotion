STRINGS = {
    "tagline": ("Agente IA de reclamaciones de fraude: registra, prioriza, investiga y responde",
                "AI agent for fraud claims: log, prioritize, investigate and respond",
                "Agent IA pour les réclamations de fraude : enregistrer, prioriser, enquêter et répondre"),
    "tab_claim": ("🆕 Reclamación", "🆕 Claim", "🆕 Réclamation"),
    "tab_cases": ("📋 Casos", "📋 Cases", "📋 Dossiers"),
    "tab_letters": ("✉ Cartas", "✉ Letters", "✉ Courriers"),
    "tab_batch": ("📊 Análisis masivo", "📊 Batch analysis", "📊 Analyse de masse"),
    # formulario
    "claim_data": ("Datos de la reclamación", "Claim details", "Détails de la réclamation"),
    "f_id": ("Nº de caso", "Case no.", "N° de dossier"),
    "f_received": ("Fecha de recepción", "Date received", "Date de réception"),
    "f_customer_name": ("Cliente", "Customer", "Client"),
    "f_customer_id": ("ID cliente", "Customer ID", "ID client"),
    "f_account": ("Cuenta / tarjeta (últimos 4)", "Account / card (last 4)", "Compte / carte (4 derniers)"),
    "f_product": ("Producto", "Product", "Produit"),
    "f_channel": ("Canal", "Channel", "Canal"),
    "f_txn_date": ("Fecha de la operación", "Transaction date", "Date de l'opération"),
    "f_amount": ("Importe reclamado", "Claimed amount", "Montant réclamé"),
    "f_currency": ("Moneda", "Currency", "Devise"),
    "f_n_txns": ("Nº de operaciones", "No. of transactions", "Nb d'opérations"),
    "f_merchant": ("Comercio / beneficiario", "Merchant / beneficiary", "Commerçant / bénéficiaire"),
    "f_prior_claims": ("Reclamaciones previas (12 meses)", "Prior claims (12 months)", "Réclamations antérieures (12 mois)"),
    "f_narrative": ("Relato del cliente", "Customer statement", "Déclaration du client"),
    "indicators": ("Indicadores (marca lo que aplique)", "Indicators (tick what applies)",
                   "Indicateurs (cochez ce qui s'applique)"),
    "prod_credit_card": ("Tarjeta de crédito", "Credit card", "Carte de crédit"),
    "prod_debit_card": ("Tarjeta de débito", "Debit card", "Carte de débit"),
    "prod_transfer": ("Transferencia", "Bank transfer", "Virement"),
    "prod_online_banking": ("Banca en línea", "Online banking", "Banque en ligne"),
    "prod_wallet": ("Billetera digital", "Digital wallet", "Portefeuille numérique"),
    "prod_check": ("Cheque", "Check", "Chèque"),
    "prod_other": ("Otro", "Other", "Autre"),
    "ch_card_present": ("Tarjeta presente (TPV)", "Card present (POS)", "Carte présente (TPE)"),
    "ch_card_not_present": ("Compra en línea / a distancia", "Online / card not present", "En ligne / à distance"),
    "ch_atm": ("Cajero automático", "ATM", "Distributeur (DAB)"),
    "ch_online_banking": ("Banca en línea", "Online banking", "Banque en ligne"),
    "ch_mobile_app": ("App móvil", "Mobile app", "Application mobile"),
    "ch_phone": ("Teléfono", "Phone", "Téléphone"),
    "ch_branch": ("Sucursal", "Branch", "Agence"),
    "ind_card_in_possession": ("El cliente conserva la tarjeta", "Customer still has the card",
                               "Le client a toujours sa carte"),
    "ind_card_lost_stolen": ("Tarjeta perdida o robada", "Card lost or stolen", "Carte perdue ou volée"),
    "ind_contacted_by_fraudster": ("Recibió llamada/SMS/correo haciéndose pasar por el banco",
                                   "Got a call/SMS/email impersonating the bank",
                                   "A reçu un appel/SMS/e-mail se faisant passer pour la banque"),
    "ind_shared_credentials": ("Compartió código, PIN o contraseña", "Shared a code, PIN or password",
                               "A communiqué un code, PIN ou mot de passe"),
    "ind_authorized_payment": ("El propio cliente hizo el pago, engañado", "Customer made the payment, deceived",
                               "Le client a fait le paiement lui-même, trompé"),
    "ind_sim_issue": ("Se quedó sin línea móvil / cambio de SIM", "Lost mobile service / SIM swap",
                      "Perte de ligne mobile / changement de SIM"),
    "ind_new_device": ("Acceso desde dispositivo o lugar nuevo", "Access from a new device or location",
                       "Accès depuis un nouvel appareil ou lieu"),
    "ind_foreign_txn": ("Operación en el extranjero", "Foreign transaction", "Opération à l'étranger"),
    "ind_recognizes_merchant": ("Reconoce al comercio", "Recognizes the merchant", "Reconnaît le commerçant"),
    "ind_goods_not_received": ("No recibió el producto/servicio", "Goods/services not received",
                               "Produit/service non reçu"),
    "ind_not_opened_by_customer": ("No abrió ese producto (suplantación)", "Did not open that product (impersonation)",
                                   "N'a pas ouvert ce produit (usurpation)"),
    "ind_new_account": ("Cuenta con menos de 90 días", "Account under 90 days old", "Compte de moins de 90 jours"),
    "ind_police_report": ("Presentó denuncia policial", "Filed a police report", "A déposé plainte"),
    "new_claim": ("Nueva", "New", "Nouvelle"),
    "evaluate": ("Evaluar (reglas)", "Evaluate (rules)", "Évaluer (règles)"),
    "analyze_ai": ("✨ Analizar con IA", "✨ Analyze with AI", "✨ Analyser avec l'IA"),
    "save_case": ("Guardar caso", "Save case", "Enregistrer le dossier"),
    "assessment": ("Evaluación", "Assessment", "Évaluation"),
    "bad_amount": ("El importe no es válido.", "The amount is not valid.", "Le montant n'est pas valide."),
    "need_customer": ("Indica al menos el cliente y el importe.", "Enter at least the customer and the amount.",
                      "Indiquez au moins le client et le montant."),
    "case_saved": ("Caso {id} guardado.", "Case {id} saved.", "Dossier {id} enregistré."),
    # evaluación
    "ev_header": ("Tipología: {typology}\nPrioridad: {priority} (urgencia {urgency}/100) · "
                  "Riesgo de inconsistencia: {consistency}/100",
                  "Typology: {typology}\nPriority: {priority} (urgency {urgency}/100) · Consistency risk: {consistency}/100",
                  "Typologie : {typology}\nPriorité : {priority} (urgence {urgency}/100) · "
                  "Risque d'incohérence : {consistency}/100"),
    "ev_deadlines": ("Plazos: acuse {ack} · abono provisional {provisional} · resolución {resolution}",
                     "Deadlines: acknowledgment {ack} · provisional credit {provisional} · resolution {resolution}",
                     "Délais : accusé {ack} · crédit provisoire {provisional} · résolution {resolution}"),
    "ev_flags": ("⚠ Señales de alerta", "⚠ Red flags", "⚠ Signaux d'alerte"),
    "ev_no_flags": ("Sin señales de alerta por reglas.", "No rule-based red flags.", "Aucun signal d'alerte."),
    "ev_actions": ("✅ Acciones recomendadas", "✅ Recommended actions", "✅ Actions recommandées"),
    "ev_documents": ("📎 Documentos a solicitar", "📎 Documents to request", "📎 Documents à demander"),
    "ev_ai": ("✨ Análisis de la IA", "✨ AI analysis", "✨ Analyse de l'IA"),
    "ev_disclaimer": ("Apoyo a la decisión: la resolución final corresponde a un analista.",
                      "Decision support only: a human analyst makes the final decision.",
                      "Aide à la décision : la décision finale revient à un analyste."),
    "ai_summary": ("Resumen", "Summary", "Résumé"),
    "ai_facts": ("Hechos clave", "Key facts", "Faits clés"),
    "ai_inconsistencies": ("Inconsistencias", "Inconsistencies", "Incohérences"),
    "ai_missing": ("Información que falta", "Missing information", "Informations manquantes"),
    "ai_questions": ("Preguntas para el cliente", "Questions for the customer", "Questions pour le client"),
    "ai_actions": ("Próximos pasos", "Next steps", "Prochaines étapes"),
    "ai_liability": ("Visión preliminar de responsabilidad", "Preliminary liability view",
                     "Vision préliminaire de la responsabilité"),
    "ai_typology": ("Tipología según la IA: {typology} · riesgo {risk}", "AI typology: {typology} · risk {risk}",
                    "Typologie selon l'IA : {typology} · risque {risk}"),
    "prio_high": ("ALTA", "HIGH", "HAUTE"),
    "prio_medium": ("MEDIA", "MEDIUM", "MOYENNE"),
    "prio_low": ("BAJA", "LOW", "BASSE"),
    "risk_high": ("alto", "high", "élevé"),
    "risk_medium": ("medio", "medium", "moyen"),
    "risk_low": ("bajo", "low", "faible"),
    "typ_merchant_dispute": ("Disputa comercial (no es fraude)", "Merchant dispute (not fraud)",
                             "Litige commercial (pas une fraude)"),
    "typ_identity_theft": ("Suplantación de identidad", "Identity theft", "Usurpation d'identité"),
    "typ_app_scam": ("Estafa con pago autorizado (ingeniería social)", "Authorized push payment scam",
                     "Escroquerie au paiement autorisé"),
    "typ_sim_swap": ("Duplicado de SIM (SIM swapping)", "SIM swap", "Échange de SIM (SIM swap)"),
    "typ_phishing_vishing": ("Phishing / vishing (robo de credenciales)", "Phishing / vishing (stolen credentials)",
                             "Hameçonnage / vishing (identifiants volés)"),
    "typ_account_takeover": ("Toma de control de la cuenta", "Account takeover", "Prise de contrôle du compte"),
    "typ_lost_stolen_card": ("Tarjeta perdida o robada", "Lost or stolen card", "Carte perdue ou volée"),
    "typ_counterfeit_skimming": ("Tarjeta clonada (skimming)", "Counterfeit card (skimming)", "Carte contrefaite (skimming)"),
    "typ_card_not_present": ("Fraude con tarjeta no presente (en línea)", "Card-not-present fraud (online)",
                             "Fraude carte non présente (en ligne)"),
    "typ_undetermined": ("Por determinar", "Undetermined", "À déterminer"),
    "flag_recall_window": ("Pago autorizado reciente: pedir la retirada de fondos al banco receptor YA (ventana de 24-48 h).",
                           "Recent authorized payment: request a funds recall from the receiving bank NOW (24-48 h window).",
                           "Paiement autorisé récent : demander le rappel des fonds à la banque bénéficiaire MAINTENANT (24-48 h)."),
    "flag_late": ("Reclamación presentada {days} días después de la operación.",
                  "Claim filed {days} days after the transaction.", "Réclamation déposée {days} jours après l'opération."),
    "flag_very_late": ("Reclamación muy tardía ({days} días): revisar plazos de reclamación aplicables.",
                       "Very late claim ({days} days): check the applicable claim deadlines.",
                       "Réclamation très tardive ({days} jours) : vérifier les délais applicables."),
    "flag_repeat": ("Cliente con {n} reclamaciones previas en 12 meses.", "Customer with {n} prior claims in 12 months.",
                    "Client avec {n} réclamations antérieures en 12 mois."),
    "flag_prior": ("Cliente con una reclamación previa.", "Customer with one prior claim.",
                   "Client avec une réclamation antérieure."),
    "flag_recognizes": ("El cliente reconoce al comercio: confirmar si es fraude o una disputa.",
                        "Customer recognizes the merchant: confirm whether it is fraud or a dispute.",
                        "Le client reconnaît le commerçant : confirmer s'il s'agit d'une fraude ou d'un litige."),
    "flag_contradiction_card": ("Contradicción: tarjeta «perdida/robada» pero el cliente la conserva.",
                                "Contradiction: card “lost/stolen” but the customer still has it.",
                                "Contradiction : carte « perdue/volée » mais le client l'a toujours."),
    "flag_new_account": ("Cuenta reciente (menos de 90 días).", "Recent account (under 90 days).",
                         "Compte récent (moins de 90 jours)."),
    "flag_negligence": ("El cliente compartió credenciales: valorar negligencia según la normativa.",
                        "Customer shared credentials: assess negligence under the applicable rules.",
                        "Le client a communiqué ses identifiants : évaluer la négligence selon la réglementation."),
    "flag_future_date": ("La fecha de la operación es posterior a la de recepción.",
                         "The transaction date is after the date received.",
                         "La date de l'opération est postérieure à la date de réception."),
    "flag_not_fraud": ("Parece una disputa comercial: tramitar por la vía de contracargo/disputa, no de fraude.",
                       "Looks like a merchant dispute: handle through the chargeback/dispute route, not fraud.",
                       "Ressemble à un litige commercial : traiter par la voie de rétrofacturation/litige."),
    "act_verify_identity": ("Verificar la identidad del cliente y los datos de contacto.",
                            "Verify the customer's identity and contact details.",
                            "Vérifier l'identité du client et ses coordonnées."),
    "act_statement": ("Documentar la declaración firmada del cliente con todas las operaciones reclamadas.",
                      "Document the customer's signed statement listing every disputed transaction.",
                      "Documenter la déclaration signée du client avec toutes les opérations contestées."),
    "act_block_card": ("Bloquear la tarjeta y emitir una nueva.", "Block the card and reissue a new one.",
                       "Bloquer la carte et en émettre une nouvelle."),
    "act_auth_logs": ("Revisar los registros de autenticación (3-D Secure, OTP, biometría, dispositivo).",
                      "Review authentication logs (3-D Secure, OTP, biometrics, device).",
                      "Examiner les journaux d'authentification (3-D Secure, OTP, biométrie, appareil)."),
    "act_merchant_data": ("Solicitar al comercio/adquirente los datos de la operación (IP, envío, cuenta).",
                          "Request transaction data from the merchant/acquirer (IP, shipping, account).",
                          "Demander au commerçant/acquéreur les données de l'opération (IP, livraison, compte)."),
    "act_chargeback_fraud": ("Valorar contracargo por fraude (p. ej. Visa 10.x / Mastercard 4837) dentro de plazo.",
                             "Assess a fraud chargeback (e.g. Visa 10.x / Mastercard 4837) within the time limit.",
                             "Évaluer une rétrofacturation pour fraude (ex. Visa 10.x / Mastercard 4837) dans les délais."),
    "act_entry_mode": ("Comprobar el modo de entrada (chip, banda, sin contacto) de cada operación.",
                       "Check the POS entry mode (chip, magstripe, contactless) of each transaction.",
                       "Vérifier le mode de saisie (puce, piste, sans contact) de chaque opération."),
    "act_cpp": ("Buscar un punto de compromiso común con otras tarjetas afectadas (análisis masivo).",
                "Look for a common point of compromise with other affected cards (batch analysis).",
                "Rechercher un point de compromission commun avec d'autres cartes (analyse de masse)."),
    "act_loss_timeline": ("Contrastar la hora de la pérdida/robo con la de las operaciones.",
                          "Compare the time of loss/theft with the transaction times.",
                          "Comparer l'heure de la perte/du vol avec celle des opérations."),
    "act_pin_usage": ("Si se usó PIN, revisar cómo pudo conocerse (¿anotado con la tarjeta?).",
                      "If the PIN was used, review how it could have been known (written with the card?).",
                      "Si le PIN a été utilisé, vérifier comment il a pu être connu (noté avec la carte ?)."),
    "act_reset_credentials": ("Restablecer contraseñas y revocar sesiones y dispositivos vinculados.",
                              "Reset passwords and revoke sessions and linked devices.",
                              "Réinitialiser les mots de passe et révoquer sessions et appareils liés."),
    "act_negligence": ("Evaluar si hubo negligencia grave del cliente según la normativa y la política interna.",
                       "Assess whether there was gross negligence under the regulation and internal policy.",
                       "Évaluer une éventuelle négligence grave selon la réglementation et la politique interne."),
    "act_report_phishing": ("Reportar el número/dominio fraudulento y alertar a otros clientes si procede.",
                            "Report the fraudulent number/domain and alert other customers if relevant.",
                            "Signaler le numéro/domaine frauduleux et alerter d'autres clients si besoin."),
    "act_lock_access": ("Bloquear el acceso a banca en línea y móvil de inmediato.",
                        "Lock online and mobile banking access immediately.",
                        "Bloquer immédiatement l'accès à la banque en ligne et mobile."),
    "act_device_ip": ("Analizar IP, dispositivo y ubicación de los accesos sospechosos.",
                      "Analyze IP, device and location of the suspicious logins.",
                      "Analyser l'IP, l'appareil et la localisation des connexions suspectes."),
    "act_recall_funds": ("Solicitar la retención/devolución de fondos al banco receptor.",
                         "Request a hold/recall of funds from the receiving bank.",
                         "Demander le blocage/rappel des fonds à la banque bénéficiaire."),
    "act_carrier": ("Confirmar con la operadora la fecha y el canal del cambio de SIM.",
                    "Confirm the date and channel of the SIM change with the carrier.",
                    "Confirmer avec l'opérateur la date et le canal du changement de SIM."),
    "act_mule": ("Reportar la cuenta receptora como posible cuenta mula.", "Report the receiving account as a possible mule.",
                 "Signaler le compte bénéficiaire comme possible compte mule."),
    "act_reimbursement_rules": ("Revisar las reglas de reembolso aplicables a estafas con pago autorizado.",
                                "Check the reimbursement rules that apply to authorized push payment scams.",
                                "Vérifier les règles de remboursement applicables aux escroqueries au paiement autorisé."),
    "act_freeze_product": ("Congelar el producto abierto de forma fraudulenta.", "Freeze the fraudulently opened product.",
                           "Geler le produit ouvert frauduleusement."),
    "act_kyc_review": ("Revisar la documentación de alta (KYC) y la firma.", "Review the onboarding (KYC) documents and signature.",
                       "Examiner les documents d'ouverture (KYC) et la signature."),
    "act_bureau": ("Notificar a los burós/centrales de riesgo para corregir el historial.",
                   "Notify credit bureaus to correct the record.", "Informer les centrales de risques pour corriger l'historique."),
    "act_police": ("Pedir al cliente que presente denuncia policial.", "Ask the customer to file a police report.",
                   "Demander au client de déposer plainte."),
    "act_contact_merchant": ("Pedir al cliente que contacte primero con el comercio y guarde la evidencia.",
                             "Ask the customer to contact the merchant first and keep the evidence.",
                             "Demander au client de contacter d'abord le commerçant et de garder les preuves."),
    "act_dispute_route": ("Reclasificar como disputa comercial y comunicarlo al cliente.",
                          "Reclassify as a merchant dispute and inform the customer.",
                          "Reclasser en litige commercial et en informer le client."),
    "act_chargeback_dispute": ("Valorar contracargo por producto no recibido (p. ej. Visa 13.1 / Mastercard 4855).",
                               "Assess a non-receipt chargeback (e.g. Visa 13.1 / Mastercard 4855).",
                               "Évaluer une rétrofacturation pour non-réception (ex. Visa 13.1 / Mastercard 4855)."),
    "act_more_info": ("Pedir más información al cliente para determinar la tipología.",
                      "Ask the customer for more information to determine the typology.",
                      "Demander plus d'informations au client pour déterminer la typologie."),
    "doc_claim_form": ("Formulario de reclamación firmado", "Signed claim form", "Formulaire de réclamation signé"),
    "doc_id": ("Documento de identidad", "Identity document", "Pièce d'identité"),
    "doc_statement_marked": ("Extracto con las operaciones reclamadas marcadas", "Statement with the disputed items marked",
                             "Relevé avec les opérations contestées signalées"),
    "doc_card_possession": ("Declaración de que conserva la tarjeta", "Statement that the card is in possession",
                            "Déclaration de possession de la carte"),
    "doc_loss_report": ("Fecha y hora de la pérdida o robo", "Date and time of the loss or theft",
                        "Date et heure de la perte ou du vol"),
    "doc_evidence_messages": ("Capturas de llamadas, SMS o correos recibidos", "Screenshots of calls, SMS or emails received",
                              "Captures des appels, SMS ou e-mails reçus"),
    "doc_carrier_letter": ("Certificado de la operadora sobre el cambio de SIM", "Carrier letter about the SIM change",
                           "Attestation de l'opérateur sur le changement de SIM"),
    "doc_police": ("Denuncia policial", "Police report", "Dépôt de plainte"),
    "doc_police_attached": ("Copia de la denuncia policial (ya presentada)", "Copy of the police report (already filed)",
                            "Copie de la plainte (déjà déposée)"),
    "doc_transfer_receipt": ("Comprobante de la transferencia", "Transfer receipt", "Justificatif du virement"),
    "doc_identity_affidavit": ("Declaración jurada de suplantación de identidad", "Identity theft affidavit",
                               "Déclaration sur l'honneur d'usurpation d'identité"),
    "doc_merchant_contact": ("Comunicaciones con el comercio", "Correspondence with the merchant",
                             "Échanges avec le commerçant"),
    "doc_purchase_proof": ("Comprobante de compra y condiciones de entrega", "Proof of purchase and delivery terms",
                           "Preuve d'achat et conditions de livraison"),
    # casos
    "st_received": ("Recibida", "Received", "Reçue"),
    "st_investigating": ("En investigación", "Investigating", "En enquête"),
    "st_pending_customer": ("Pendiente del cliente", "Pending customer", "En attente du client"),
    "st_provisional_credit": ("Abono provisional", "Provisional credit", "Crédit provisoire"),
    "st_resolved_favor": ("Resuelta a favor", "Resolved in favor", "Résolue en faveur"),
    "st_resolved_rejected": ("Resuelta - rechazada", "Resolved - rejected", "Résolue - rejetée"),
    "st_closed": ("Cerrada", "Closed", "Clôturée"),
    "st_all": ("Todos", "All", "Tous"),
    "st_open": ("Abiertos", "Open", "Ouverts"),
    "status": ("Estado", "Status", "Statut"),
    "filter": ("Filtrar", "Filter", "Filtrer"),
    "open_case": ("Abrir en el formulario", "Open in the form", "Ouvrir dans le formulaire"),
    "set_status": ("Cambiar estado", "Change status", "Changer le statut"),
    "delete_case": ("Eliminar", "Delete", "Supprimer"),
    "confirm_delete": ("¿Eliminar el caso {id}?", "Delete case {id}?", "Supprimer le dossier {id} ?"),
    "export_cases": ("Exportar a Excel…", "Export to Excel…", "Exporter vers Excel…"),
    "select_case": ("Selecciona un caso de la lista.", "Select a case in the list.", "Sélectionnez un dossier."),
    "c_id": ("Caso", "Case", "Dossier"),
    "c_received": ("Recibida", "Received", "Reçue"),
    "c_customer": ("Cliente", "Customer", "Client"),
    "c_typology": ("Tipología", "Typology", "Typologie"),
    "c_amount": ("Importe", "Amount", "Montant"),
    "c_currency": ("Moneda", "Currency", "Devise"),
    "c_priority": ("Prioridad", "Priority", "Priorité"),
    "c_status": ("Estado", "Status", "Statut"),
    "c_due": ("Vence", "Due", "Échéance"),
    "c_days_left": ("Días restantes", "Days left", "Jours restants"),
    "sla_box": ("Plazos (ajústalos a tu normativa)", "Deadlines (adjust to your regulation)",
                "Délais (adaptez-les à votre réglementation)"),
    "sla_ack": ("Acuse (días hábiles)", "Acknowledgment (business days)", "Accusé (jours ouvrés)"),
    "sla_provisional": ("Abono provisional (días hábiles)", "Provisional credit (business days)",
                        "Crédit provisoire (jours ouvrés)"),
    "sla_resolution": ("Resolución (días naturales)", "Resolution (calendar days)", "Résolution (jours calendaires)"),
    "sla_late": ("Aviso tardío a partir de (días)", "Late report after (days)", "Signalement tardif après (jours)"),
    "sla_high": ("Importe alto desde", "High amount from", "Montant élevé à partir de"),
    "sla_saved": ("Plazos guardados.", "Deadlines saved.", "Délais enregistrés."),
    "sheet_cases": ("Casos", "Cases", "Dossiers"),
    "kpi_line": ("Abiertos: {open} · Vencidos: {overdue} · Vencen en 5 días: {soon} · Importe abierto: {amount:,.2f}",
                 "Open: {open} · Overdue: {overdue} · Due in 5 days: {soon} · Open amount: {amount:,.2f}",
                 "Ouverts : {open} · En retard : {overdue} · Échéance sous 5 jours : {soon} · Montant ouvert : {amount:,.2f}"),
    # cartas
    "letter_case": ("Caso", "Case", "Dossier"),
    "current_form": ("(formulario actual)", "(current form)", "(formulaire actuel)"),
    "letter_type": ("Tipo de carta", "Letter type", "Type de courrier"),
    "lt_ack": ("Acuse de recibo", "Acknowledgment", "Accusé de réception"),
    "lt_info_request": ("Solicitud de documentos", "Request for documents", "Demande de documents"),
    "lt_provisional": ("Abono provisional", "Provisional credit", "Crédit provisoire"),
    "lt_favorable": ("Resolución favorable", "Favorable resolution", "Décision favorable"),
    "lt_unfavorable": ("Resolución desfavorable", "Unfavorable resolution", "Décision défavorable"),
    "lt_dispute": ("Reorientar a disputa comercial", "Redirect to merchant dispute", "Réorientation vers un litige"),
    "letter_lang": ("Idioma de la carta", "Letter language", "Langue du courrier"),
    "lang_es": ("Español", "Spanish", "Espagnol"),
    "lang_en": ("Inglés", "English", "Anglais"),
    "lang_fr": ("Francés", "French", "Français"),
    "company": ("Entidad", "Institution", "Établissement"),
    "reason": ("Motivo (para resolución desfavorable)", "Reason (for unfavorable resolution)",
               "Motif (pour décision défavorable)"),
    "gen_letter": ("Generar carta", "Generate letter", "Générer le courrier"),
    "improve_letter": ("✨ Mejorar redacción", "✨ Improve wording", "✨ Améliorer la rédaction"),
    "export_word": ("Exportar a Word…", "Export to Word…", "Exporter vers Word…"),
    "letter": ("Carta (editable)", "Letter (editable)", "Courrier (modifiable)"),
    # análisis masivo
    "batch_hint": (
        "Analiza un Excel/CSV de reclamaciones: duplicados, clientes con 3+ reclamaciones en 90 días, avisos tardíos, "
        "importes altos y comercios con picos de casos (posible punto de compromiso).",
        "Analyzes an Excel/CSV of claims: duplicates, customers with 3+ claims in 90 days, late reports, high amounts "
        "and merchants with spikes of cases (possible point of compromise).",
        "Analyse un Excel/CSV de réclamations : doublons, clients avec 3+ réclamations en 90 jours, signalements tardifs, "
        "montants élevés et commerçants avec pics de dossiers (possible point de compromission).",
    ),
    "open_claims": ("Abrir Excel/CSV…", "Open Excel/CSV…", "Ouvrir Excel/CSV…"),
    "mapping": ("Columnas", "Columns", "Colonnes"),
    "m_claim_id": ("Nº reclamación", "Claim ID", "N° réclamation"),
    "m_customer_id": ("ID cliente", "Customer ID", "ID client"),
    "m_claim_date": ("Fecha reclamación", "Claim date", "Date réclamation"),
    "m_txn_date": ("Fecha operación", "Transaction date", "Date opération"),
    "m_amount": ("Importe", "Amount", "Montant"),
    "m_channel": ("Canal", "Channel", "Canal"),
    "m_merchant": ("Comercio", "Merchant", "Commerçant"),
    "cluster_min": ("Casos mínimos para alerta de comercio", "Min. cases for merchant alert",
                    "Nb min. de cas pour alerte commerçant"),
    "run_batch": ("Analizar", "Analyze", "Analyser"),
    "batch_ai": ("✨ Informe de patrones", "✨ Pattern report", "✨ Rapport de tendances"),
    "export_batch": ("Exportar Excel…", "Export Excel…", "Exporter Excel…"),
    "need_amount_map": ("Indica al menos la columna de importe.", "Map at least the amount column.",
                        "Indiquez au moins la colonne du montant."),
    "batch_summary": (
        "Reclamaciones: {claims} · Importe: {amount:,.2f} · Para revisar (≥25 pts): {flagged}\n"
        "Duplicadas: {duplicates} · Reclamantes recurrentes: {repeat} · Tardías: {late} · Importe alto: {high}\n"
        "⚠ Comercios con pico de casos (posible punto de compromiso): {cpp}",
        "Claims: {claims} · Amount: {amount:,.2f} · To review (≥25 pts): {flagged}\n"
        "Duplicates: {duplicates} · Repeat claimants: {repeat} · Late: {late} · High amount: {high}\n"
        "⚠ Merchants with a spike of cases (possible point of compromise): {cpp}",
        "Réclamations : {claims} · Montant : {amount:,.2f} · À revoir (≥25 pts) : {flagged}\n"
        "Doublons : {duplicates} · Réclamants récurrents : {repeat} · Tardives : {late} · Montant élevé : {high}\n"
        "⚠ Commerçants avec pic de dossiers (possible point de compromission) : {cpp}",
    ),
    "b_duplicate": ("Duplicada", "Duplicate", "Doublon"),
    "b_repeat": ("Recurrente 90 días", "Repeat in 90 days", "Récurrent 90 jours"),
    "b_late": ("Aviso tardío", "Late report", "Signalement tardif"),
    "b_date_error": ("Fechas incoherentes", "Inconsistent dates", "Dates incohérentes"),
    "b_high_amount": ("Importe alto", "High amount", "Montant élevé"),
    "b_round": ("Importe redondo", "Round amount", "Montant rond"),
    "b_cpp": ("Comercio con pico de casos", "Merchant with case spike", "Commerçant avec pic"),
    "score": ("Puntuación revisión", "Review score", "Score de revue"),
    "flags": ("Señales", "Signals", "Signaux"),
    "sheet_triage": ("Triaje", "Triage", "Tri"),
    "sheet_summary": ("Resumen", "Summary", "Synthèse"),
    "sheet_merchants": ("Comercios", "Merchants", "Commerçants"),
    "k_claims": ("Reclamaciones", "Claims", "Réclamations"),
    "k_amount": ("Importe", "Amount", "Montant"),
    "k_flagged": ("Para revisar", "To review", "À revoir"),
    "k_duplicates": ("Duplicadas", "Duplicates", "Doublons"),
    "k_repeat": ("Reclamantes recurrentes", "Repeat claimants", "Réclamants récurrents"),
    "k_late": ("Avisos tardíos", "Late reports", "Signalements tardifs"),
    "k_high": ("Importes altos", "High amounts", "Montants élevés"),
    "k_cpp": ("Posibles puntos de compromiso", "Possible points of compromise", "Points de compromission possibles"),
    "channel": ("Canal", "Channel", "Canal"),
    "merchant": ("Comercio", "Merchant", "Commerçant"),
    "customers": ("Clientes distintos", "Distinct customers", "Clients distincts"),
    "peak_30d": ("Pico de casos en 30 días", "Peak cases in 30 days", "Pic de cas sur 30 jours"),
    "peak_start": ("Inicio del pico", "Peak start", "Début du pic"),
    "suspect": ("Alerta", "Alert", "Alerte"),
}

LETTERS = {
    "ack": {
        "es": "# Acuse de recibo de su reclamación {claim_id}\n> {company} · {today}\nEstimado/a {customer}:\n"
              "Hemos recibido su reclamación por {amount} {currency} relacionada con la operación del {txn_date} "
              "({merchant}). Ya estamos investigando el caso.\nLe informaremos de la resolución, a más tardar, el "
              "**{due}**. Si necesitamos más información, nos pondremos en contacto con usted.\n"
              "Por su seguridad, nunca le pediremos claves, PIN ni códigos por teléfono, SMS o correo.\n"
              "Atentamente,\n**Departamento de Reclamaciones por Fraude**",
        "en": "# Acknowledgment of your claim {claim_id}\n> {company} · {today}\nDear {customer},\n"
              "We have received your claim for {amount} {currency} regarding the transaction of {txn_date} "
              "({merchant}). We are already investigating the case.\nWe will inform you of the outcome no later than "
              "**{due}**. If we need more information, we will contact you.\n"
              "For your security, we will never ask for passwords, PINs or codes by phone, SMS or email.\n"
              "Kind regards,\n**Fraud Claims Department**",
        "fr": "# Accusé de réception de votre réclamation {claim_id}\n> {company} · {today}\nMadame, Monsieur {customer},\n"
              "Nous avons bien reçu votre réclamation de {amount} {currency} concernant l'opération du {txn_date} "
              "({merchant}). Notre enquête est en cours.\nNous vous informerons de notre décision au plus tard le "
              "**{due}**. Si nous avons besoin d'informations complémentaires, nous vous contacterons.\n"
              "Pour votre sécurité, nous ne vous demanderons jamais de mot de passe, de PIN ni de code par téléphone, "
              "SMS ou e-mail.\nCordialement,\n**Service des réclamations pour fraude**",
    },
    "info_request": {
        "es": "# Documentación necesaria para su reclamación {claim_id}\n> {company} · {today}\nEstimado/a {customer}:\n"
              "Para continuar con la investigación de su reclamación por {amount} {currency}, necesitamos que nos "
              "envíe la siguiente documentación:\n{documents}\nLe rogamos que nos la haga llegar en un plazo de 10 días. "
              "Sin ella, podríamos no poder completar el análisis de su caso.\nAtentamente,\n"
              "**Departamento de Reclamaciones por Fraude**",
        "en": "# Documents needed for your claim {claim_id}\n> {company} · {today}\nDear {customer},\n"
              "To continue investigating your claim for {amount} {currency}, we need you to send us the following "
              "documents:\n{documents}\nPlease send them within 10 days. Without them, we may not be able to complete "
              "the review of your case.\nKind regards,\n**Fraud Claims Department**",
        "fr": "# Documents nécessaires pour votre réclamation {claim_id}\n> {company} · {today}\nMadame, Monsieur {customer},\n"
              "Afin de poursuivre l'enquête sur votre réclamation de {amount} {currency}, merci de nous transmettre les "
              "documents suivants :\n{documents}\nNous vous remercions de nous les adresser sous 10 jours. Sans ces "
              "éléments, nous pourrions ne pas être en mesure de finaliser l'analyse de votre dossier.\nCordialement,\n"
              "**Service des réclamations pour fraude**",
    },
    "provisional": {
        "es": "# Abono provisional - reclamación {claim_id}\n> {company} · {today}\nEstimado/a {customer}:\n"
              "Mientras completamos la investigación, hemos realizado un **abono provisional de {amount} {currency}** "
              "en su cuenta.\nEste abono es provisional: si la investigación concluye que la operación fue autorizada, "
              "podría revertirse, lo que le comunicaríamos previamente por escrito. La resolución definitiva se le "
              "notificará antes del **{due}**.\nAtentamente,\n**Departamento de Reclamaciones por Fraude**",
        "en": "# Provisional credit - claim {claim_id}\n> {company} · {today}\nDear {customer},\n"
              "While we complete our investigation, we have applied a **provisional credit of {amount} {currency}** to "
              "your account.\nThis credit is provisional: if the investigation concludes that the transaction was "
              "authorized, it may be reversed, and we would notify you in writing beforehand. You will receive the final "
              "decision before **{due}**.\nKind regards,\n**Fraud Claims Department**",
        "fr": "# Crédit provisoire - réclamation {claim_id}\n> {company} · {today}\nMadame, Monsieur {customer},\n"
              "Dans l'attente de la fin de notre enquête, nous avons effectué un **crédit provisoire de {amount} "
              "{currency}** sur votre compte.\nCe crédit est provisoire : si l'enquête conclut que l'opération était "
              "autorisée, il pourra être annulé, ce dont nous vous informerons préalablement par écrit. La décision "
              "définitive vous sera notifiée avant le **{due}**.\nCordialement,\n**Service des réclamations pour fraude**",
    },
    "favorable": {
        "es": "# Resolución de su reclamación {claim_id}\n> {company} · {today}\nEstimado/a {customer}:\n"
              "Hemos concluido la investigación de su reclamación por {amount} {currency} y nos complace informarle "
              "de que se ha **resuelto a su favor**. El importe queda abonado de forma definitiva en su cuenta.\n"
              "Le recomendamos revisar sus movimientos con frecuencia y activar las alertas de operaciones.\n"
              "Gracias por su confianza.\nAtentamente,\n**Departamento de Reclamaciones por Fraude**",
        "en": "# Outcome of your claim {claim_id}\n> {company} · {today}\nDear {customer},\n"
              "We have completed the investigation of your claim for {amount} {currency} and are pleased to inform you "
              "that it has been **resolved in your favor**. The amount has been permanently credited to your account.\n"
              "We recommend reviewing your transactions regularly and enabling transaction alerts.\n"
              "Thank you for your trust.\nKind regards,\n**Fraud Claims Department**",
        "fr": "# Décision concernant votre réclamation {claim_id}\n> {company} · {today}\nMadame, Monsieur {customer},\n"
              "Nous avons terminé l'enquête sur votre réclamation de {amount} {currency} et avons le plaisir de vous "
              "informer qu'elle a été **résolue en votre faveur**. Le montant est définitivement crédité sur votre "
              "compte.\nNous vous recommandons de consulter régulièrement vos opérations et d'activer les alertes.\n"
              "Merci de votre confiance.\nCordialement,\n**Service des réclamations pour fraude**",
    },
    "unfavorable": {
        "es": "# Resolución de su reclamación {claim_id}\n> {company} · {today}\nEstimado/a {customer}:\n"
              "Hemos concluido la investigación de su reclamación por {amount} {currency} relacionada con la operación "
              "del {txn_date}. Tras analizar la información disponible, no podemos aceptar la reclamación por el "
              "siguiente motivo:\n- {reason}\nSi el abono provisional se realizó, se revertirá en un plazo mínimo de 5 "
              "días hábiles desde esta comunicación.\nSi no está de acuerdo, puede aportar nueva información o "
              "presentar una reclamación ante el servicio de atención al cliente o la autoridad supervisora "
              "competente. Puede solicitarnos copia de la documentación en la que se basa esta decisión.\n"
              "Atentamente,\n**Departamento de Reclamaciones por Fraude**",
        "en": "# Outcome of your claim {claim_id}\n> {company} · {today}\nDear {customer},\n"
              "We have completed the investigation of your claim for {amount} {currency} regarding the transaction of "
              "{txn_date}. After reviewing the available information, we are unable to accept the claim for the "
              "following reason:\n- {reason}\nIf a provisional credit was applied, it will be reversed no sooner than 5 "
              "business days from this notice.\nIf you disagree, you may provide new information or file a complaint "
              "with customer service or the competent supervisory authority. You may request a copy of the documents "
              "this decision is based on.\nKind regards,\n**Fraud Claims Department**",
        "fr": "# Décision concernant votre réclamation {claim_id}\n> {company} · {today}\nMadame, Monsieur {customer},\n"
              "Nous avons terminé l'enquête sur votre réclamation de {amount} {currency} concernant l'opération du "
              "{txn_date}. Après analyse des informations disponibles, nous ne pouvons pas donner suite à votre "
              "réclamation pour le motif suivant :\n- {reason}\nSi un crédit provisoire a été effectué, il sera annulé "
              "au plus tôt 5 jours ouvrés après ce courrier.\nEn cas de désaccord, vous pouvez nous transmettre de "
              "nouveaux éléments ou saisir le service clients ou l'autorité de contrôle compétente. Vous pouvez nous "
              "demander une copie des documents sur lesquels repose cette décision.\nCordialement,\n"
              "**Service des réclamations pour fraude**",
    },
    "dispute": {
        "es": "# Su reclamación {claim_id}: disputa con el comercio\n> {company} · {today}\nEstimado/a {customer}:\n"
              "Según la información facilitada, la operación de {amount} {currency} con {merchant} corresponde a una "
              "compra que usted reconoce, pero con un problema en la entrega o el servicio. Este caso no se trata "
              "como fraude, sino como **disputa comercial**.\nLe recomendamos:\n- Contactar con el comercio y guardar "
              "la respuesta.\n- Enviarnos el comprobante de compra y las comunicaciones con el comercio.\n"
              "Con esa documentación iniciaremos la reclamación ante la red de pagos si procede.\nAtentamente,\n"
              "**Departamento de Reclamaciones**",
        "en": "# Your claim {claim_id}: merchant dispute\n> {company} · {today}\nDear {customer},\n"
              "Based on the information provided, the {amount} {currency} transaction with {merchant} is a purchase you "
              "recognize but with a delivery or service problem. This case is not handled as fraud but as a **merchant "
              "dispute**.\nWe recommend that you:\n- Contact the merchant and keep their reply.\n- Send us the proof "
              "of purchase and your correspondence with the merchant.\nWith these documents we will start a dispute "
              "with the card network if applicable.\nKind regards,\n**Claims Department**",
        "fr": "# Votre réclamation {claim_id} : litige commercial\n> {company} · {today}\nMadame, Monsieur {customer},\n"
              "D'après les informations fournies, l'opération de {amount} {currency} avec {merchant} correspond à un "
              "achat que vous reconnaissez, mais avec un problème de livraison ou de service. Ce dossier n'est pas "
              "traité comme une fraude mais comme un **litige commercial**.\nNous vous recommandons de :\n- Contacter "
              "le commerçant et conserver sa réponse.\n- Nous transmettre la preuve d'achat et vos échanges avec le "
              "commerçant.\nAvec ces documents, nous engagerons si nécessaire une contestation auprès du réseau de "
              "paiement.\nCordialement,\n**Service des réclamations**",
    },
}
