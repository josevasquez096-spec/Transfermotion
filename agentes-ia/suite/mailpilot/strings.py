STRINGS = {
    "tagline": ("Agente para Outlook: carpetas, búsqueda avanzada, etiquetas, reglas y redacción en inglés",
                "Outlook agent: folders, advanced search, tags, rules and English writing",
                "Agent Outlook : dossiers, recherche avancée, catégories, règles et rédaction en anglais"),
    "tab_mailbox": ("📁 Buzón y carpetas", "📁 Mailbox & folders", "📁 Boîte et dossiers"),
    "tab_search": ("🔍 Buscar y filtrar", "🔍 Search & filter", "🔍 Rechercher et filtrer"),
    "tab_tags": ("🏷 Etiquetas", "🏷 Tags", "🏷 Catégories"),
    "tab_rules": ("⚙ Reglas", "⚙ Rules", "⚙ Règles"),
    "tab_writing": ("✍ Redacción en inglés", "✍ English writing", "✍ Rédaction en anglais"),
    "tab_analysis": ("🛡 Análisis y seguridad", "🛡 Analysis & security", "🛡 Analyse et sécurité"),
    # conexión
    "connect_outlook": ("Conectar con Outlook", "Connect to Outlook", "Se connecter à Outlook"),
    "connect_demo": ("Modo demostración", "Demo mode", "Mode démonstration"),
    "open_shared": ("Abrir buzón compartido…", "Open shared mailbox…", "Ouvrir une boîte partagée…"),
    "conn_off": ("Sin conexión: conecta con Outlook (clásico) o prueba el modo demostración.",
                 "Not connected: connect to (classic) Outlook or try the demo mode.",
                 "Non connecté : connectez-vous à Outlook (classique) ou essayez le mode démonstration."),
    "conn_demo": ("Modo demostración · datos ficticios, no se toca ningún buzón real",
                  "Demo mode · sample data, no real mailbox is touched",
                  "Mode démonstration · données fictives, aucune vraie boîte n'est modifiée"),
    "conn_outlook": ("Conectado a Outlook · {n} buzones o archivos", "Connected to Outlook · {n} mailboxes or files",
                     "Connecté à Outlook · {n} boîtes ou fichiers"),
    "mp_no_windows": (
        "La conexión con Outlook solo funciona en Windows con Outlook clásico. ¿Abrir el modo demostración?",
        "The Outlook connection only works on Windows with classic Outlook. Open the demo mode?",
        "La connexion à Outlook ne fonctionne que sous Windows avec Outlook classique. Ouvrir le mode démonstration ?"),
    "mp_connecting": ("Conectando con Outlook…", "Connecting to Outlook…", "Connexion à Outlook…"),
    "mp_loading": ("Cargando…", "Loading…", "Chargement…"),
    "mp_searching": ("Buscando…", "Searching…", "Recherche…"),
    "mp_analyzing": ("Analizando…", "Analyzing…", "Analyse…"),
    "mp_progress": ("Buscando… {seen} correos revisados · {found} encontrados",
                    "Searching… {seen} messages checked · {found} found",
                    "Recherche… {seen} messages examinés · {found} trouvés"),
    "mp_progress_scan": ("Analizando… {seen} correos revisados", "Analyzing… {seen} messages checked",
                         "Analyse… {seen} messages examinés"),
    "shared_prompt": ("Dirección del buzón compartido (por ejemplo, reclamaciones@banco.com).\nNecesitas permiso "
                      "de lectura en ese buzón.",
                      "Shared mailbox address (for example, claims@bank.com).\nYou need read permission on it.",
                      "Adresse de la boîte partagée (par exemple, reclamations@banque.com).\nVous devez avoir le "
                      "droit de lecture."),
    "shared_prompt_demo": ("En la demostración puedes abrir: {address}", "In the demo you can open: {address}",
                           "Dans la démonstration, vous pouvez ouvrir : {address}"),
    "shared_opened": ("Buzón abierto: {name}", "Mailbox opened: {name}", "Boîte ouverte : {name}"),
    "mp_need_connect": ("Primero conecta con Outlook o abre el modo demostración (pestaña «Buzón y carpetas»).",
                        "First connect to Outlook or open the demo mode (“Mailbox & folders” tab).",
                        "Connectez-vous d'abord à Outlook ou ouvrez le mode démonstration (onglet « Boîte et "
                        "dossiers »)."),
    "mp_need_folder": ("Selecciona primero una carpeta en la pestaña «Buzón y carpetas».",
                       "First select a folder in the “Mailbox & folders” tab.",
                       "Sélectionnez d'abord un dossier dans l'onglet « Boîte et dossiers »."),
    "mp_need_selection": ("Selecciona uno o varios correos.", "Select one or more messages.",
                          "Sélectionnez un ou plusieurs messages."),
    # carpetas y lista
    "folder_menu": ("Carpeta ▾", "Folder ▾", "Dossier ▾"),
    "refresh": ("↻ Actualizar", "↻ Refresh", "↻ Actualiser"),
    "folder_new": ("Nueva subcarpeta…", "New subfolder…", "Nouveau sous-dossier…"),
    "folder_rename": ("Renombrar carpeta…", "Rename folder…", "Renommer le dossier…"),
    "folder_move": ("Mover carpeta a…", "Move folder to…", "Déplacer le dossier vers…"),
    "folder_delete": ("Eliminar carpeta", "Delete folder", "Supprimer le dossier"),
    "folder_new_prompt": ("Nombre de la nueva carpeta dentro de «{parent}»:",
                          "Name of the new folder inside “{parent}”:",
                          "Nom du nouveau dossier dans « {parent} » :"),
    "folder_rename_prompt": ("Nuevo nombre de la carpeta:", "New folder name:", "Nouveau nom du dossier :"),
    "folder_delete_confirm": (
        "¿Eliminar la carpeta «{name}»? Outlook la moverá, con sus correos, a Elementos eliminados.",
        "Delete the folder “{name}”? Outlook will move it, with its messages, to Deleted Items.",
        "Supprimer le dossier « {name} » ? Outlook le déplacera, avec ses messages, dans Éléments supprimés."),
    "folder_move_store": ("Solo se pueden mover carpetas dentro del mismo buzón.",
                          "Folders can only be moved within the same mailbox.",
                          "Les dossiers ne peuvent être déplacés que dans la même boîte."),
    "period": ("Periodo", "Period", "Période"),
    "p7": ("Últimos 7 días", "Last 7 days", "7 derniers jours"),
    "p30": ("Últimos 30 días", "Last 30 days", "30 derniers jours"),
    "p90": ("Últimos 90 días", "Last 90 days", "90 derniers jours"),
    "p365": ("Último año", "Last year", "Dernière année"),
    "pall": ("Todo", "All", "Tout"),
    "actions": ("Acciones ▾", "Actions ▾", "Actions ▾"),
    "export_excel": ("Exportar a Excel…", "Export to Excel…", "Exporter vers Excel…"),
    "mail_count": ("{n} correos en «{folder}»", "{n} messages in “{folder}”", "{n} messages dans « {folder} »"),
    "mail_count_more": ("Se muestran los {n} más recientes de «{folder}»: elige un periodo más corto o usa Buscar.",
                        "Showing the {n} most recent in “{folder}”: choose a shorter period or use Search.",
                        "Affichage des {n} plus récents de « {folder} » : choisissez une période plus courte ou "
                        "utilisez Rechercher."),
    "col_received": ("Fecha", "Date", "Date"),
    "col_sender": ("De", "From", "De"),
    "col_subject": ("Asunto", "Subject", "Objet"),
    "col_categories": ("Etiquetas", "Tags", "Catégories"),
    "col_size": ("Tamaño", "Size", "Taille"),
    "col_folder": ("Carpeta", "Folder", "Dossier"),
    "col_email": ("Dirección", "Address", "Adresse"),
    "col_count": ("Correos", "Messages", "Messages"),
    "col_unread": ("No leídos", "Unread", "Non lus"),
    "col_size_mb": ("Tamaño (MB)", "Size (MB)", "Taille (Mo)"),
    "col_size_kb": ("Tamaño (KB)", "Size (KB)", "Taille (Ko)"),
    "col_last": ("Último", "Latest", "Dernier"),
    "col_first": ("Primero", "First", "Premier"),
    "col_domain": ("Dominio", "Domain", "Domaine"),
    "col_internal": ("Interno", "Internal", "Interne"),
    "col_month": ("Mes", "Month", "Mois"),
    "col_claim": ("Reclamación", "Claim", "Réclamation"),
    "col_customers": ("Remitentes externos", "External senders", "Expéditeurs externes"),
    "col_folders": ("Carpetas", "Folders", "Dossiers"),
    "col_date": ("Fecha", "Date", "Date"),
    "col_score": ("Puntuación", "Score", "Score"),
    "col_risk": ("Riesgo", "Risk", "Risque"),
    "col_signals": ("Señales", "Signals", "Signaux"),
    "col_kind": ("Tipo", "Type", "Type"),
    "col_value": ("Dato (enmascarado)", "Value (masked)", "Donnée (masquée)"),
    # vista previa
    "pv_subject": ("Asunto", "Subject", "Objet"),
    "pv_from": ("De", "From", "De"),
    "pv_to": ("Para", "To", "À"),
    "pv_cc": ("CC", "CC", "Cc"),
    "pv_date": ("Fecha", "Date", "Date"),
    "pv_folder": ("Carpeta", "Folder", "Dossier"),
    "pv_categories": ("Etiquetas", "Tags", "Catégories"),
    "pv_attachments": ("Adjuntos", "Attachments", "Pièces jointes"),
    "warn_phishing": ("⚠ Posible phishing (puntuación {score}, riesgo {level}): {signals}. No abras enlaces ni "
                      "adjuntos y repórtalo al equipo de seguridad.",
                      "⚠ Possible phishing (score {score}, {level} risk): {signals}. Do not open links or "
                      "attachments; report it to the security team.",
                      "⚠ Hameçonnage possible (score {score}, risque {level}) : {signals}. N'ouvrez ni liens ni "
                      "pièces jointes et signalez-le à l'équipe sécurité."),
    "warn_card": ("⚠ Este correo contiene {n} número(s) de tarjeta completo(s). Por seguridad (PCI DSS) no deberían "
                  "guardarse ni reenviarse en claro.",
                  "⚠ This message contains {n} full card number(s). For security (PCI DSS) they should not be "
                  "stored or forwarded in clear text.",
                  "⚠ Ce message contient {n} numéro(s) de carte complet(s). Par sécurité (PCI DSS), ils ne doivent "
                  "pas être conservés ni transférés en clair."),
    "risk_high": ("alto", "high", "élevé"),
    "risk_medium": ("medio", "medium", "moyen"),
    "risk_low": ("bajo", "low", "faible"),
    # acciones sobre correos
    "act_move": ("Mover a carpeta…", "Move to folder…", "Déplacer vers un dossier…"),
    "act_tag": ("Etiquetar…", "Tag…", "Catégoriser…"),
    "act_read": ("Marcar como leído", "Mark as read", "Marquer comme lu"),
    "act_unread": ("Marcar como no leído", "Mark as unread", "Marquer comme non lu"),
    "act_flag": ("Marcar para seguimiento", "Flag for follow-up", "Marquer pour suivi"),
    "act_unflag": ("Quitar marca de seguimiento", "Clear flag", "Effacer l'indicateur"),
    "act_open": ("Abrir en Outlook", "Open in Outlook", "Ouvrir dans Outlook"),
    "act_save_msg": ("Guardar como archivo…", "Save as file…", "Enregistrer comme fichier…"),
    "act_save_att": ("Guardar adjuntos…", "Save attachments…", "Enregistrer les pièces jointes…"),
    "act_summary_ai": ("✨ Resumir y proponer respuesta", "✨ Summarize and suggest a reply",
                       "✨ Résumer et proposer une réponse"),
    "act_select_all": ("Seleccionar todos", "Select all", "Tout sélectionner"),
    "act_delete": ("Eliminar", "Delete", "Supprimer"),
    "moved_n": ("{n} correos movidos a «{folder}»", "{n} messages moved to “{folder}”",
                "{n} messages déplacés vers « {folder} »"),
    "tagged_n": ("Etiquetas actualizadas en {n} correos", "Tags updated on {n} messages",
                 "Catégories mises à jour sur {n} messages"),
    "updated_n": ("{n} correos actualizados", "{n} messages updated", "{n} messages mis à jour"),
    "delete_confirm": ("¿Eliminar {n} correos? Se moverán a Elementos eliminados.",
                       "Delete {n} messages? They will be moved to Deleted Items.",
                       "Supprimer {n} messages ? Ils seront déplacés dans Éléments supprimés."),
    "deleted_n": ("{n} correos eliminados", "{n} messages deleted", "{n} messages supprimés"),
    "open_demo": ("En el modo demostración no hay Outlook: el correo se ve en la vista previa.",
                  "There is no Outlook in demo mode: the message is shown in the preview.",
                  "Pas d'Outlook en mode démonstration : le message s'affiche dans l'aperçu."),
    "files_saved": ("Se guardaron {n} archivos en:\n{folder}\n\n¿Abrir la carpeta?",
                    "{n} files saved in:\n{folder}\n\nOpen the folder?",
                    "{n} fichiers enregistrés dans :\n{folder}\n\nOuvrir le dossier ?"),
    "nothing_saved": ("No se guardó ningún archivo.", "No file was saved.", "Aucun fichier enregistré."),
    "no_attachments": ("Los correos elegidos no tienen adjuntos.", "The selected messages have no attachments.",
                       "Les messages sélectionnés n'ont pas de pièce jointe."),
    "sheet_messages": ("Correos", "Messages", "Messages"),
    "summary_title": ("✨ Resumen del correo", "✨ Message summary", "✨ Résumé du message"),
    "summary": ("Resumen", "Summary", "Résumé"),
    "actions_needed": ("Qué hay que hacer", "What needs to be done", "Ce qu'il faut faire"),
    "suggested_reply": ("Respuesta propuesta (en inglés)", "Suggested reply (in English)",
                        "Réponse proposée (en anglais)"),
    "reply_to_writing": ("Llevar a Redacción", "Open in Writing", "Ouvrir dans Rédaction"),
    "yes": ("Sí", "Yes", "Oui"),
    "no": ("No", "No", "Non"),
    "none": ("ninguna", "none", "aucune"),
    # buscar
    "search": ("Buscar", "Search", "Rechercher"),
    "stop": ("Detener", "Stop", "Arrêter"),
    "syntax_help": ("Ayuda de búsqueda", "Search help", "Aide de recherche"),
    "scope": ("Ámbito", "Scope", "Portée"),
    "sc_folder": ("Carpeta seleccionada", "Selected folder", "Dossier sélectionné"),
    "sc_subfolders": ("Carpeta y subcarpetas", "Folder and subfolders", "Dossier et sous-dossiers"),
    "sc_store": ("Todo el buzón", "Whole mailbox", "Toute la boîte"),
    "sc_all": ("Todos los buzones y archivos", "All mailboxes and files", "Toutes les boîtes et fichiers"),
    "sc_inbox": ("Bandeja de entrada", "Inbox", "Boîte de réception"),
    "whole_word": ("Palabra completa", "Whole word", "Mot entier"),
    "exact_match": ("Mayúsculas y acentos exactos (más rápido en buzones grandes)",
                    "Exact case and accents (faster in large mailboxes)",
                    "Casse et accents exacts (plus rapide dans les grandes boîtes)"),
    "max_results": ("Máximo", "Max.", "Max."),
    "quick_filters": ("Filtros rápidos:", "Quick filters:", "Filtres rapides :"),
    "qf_unread": ("No leídos", "Unread", "Non lus"),
    "qf_attachment": ("Con adjuntos", "With attachments", "Avec pièces jointes"),
    "qf_external": ("Externos", "External", "Externes"),
    "qf_phishing": ("Phishing", "Phishing", "Hameçonnage"),
    "qf_card": ("Tarjetas", "Cards", "Cartes"),
    "qf_claim": ("Reclamaciones", "Claims", "Réclamations"),
    "qf_week": ("Última semana", "Last week", "Dernière semaine"),
    "saved_searches": ("Búsquedas guardadas", "Saved searches", "Recherches enregistrées"),
    "save_search": ("Guardar búsqueda…", "Save search…", "Enregistrer la recherche…"),
    "delete_search": ("Eliminar", "Delete", "Supprimer"),
    "save_search_prompt": ("Nombre de la búsqueda:", "Search name:", "Nom de la recherche :"),
    "search_builtin": ("Las búsquedas de ejemplo no se pueden eliminar.", "Sample searches cannot be deleted.",
                       "Les recherches d'exemple ne peuvent pas être supprimées."),
    "mp_need_saved": ("Elige primero una búsqueda guardada.", "First choose a saved search.",
                      "Choisissez d'abord une recherche enregistrée."),
    "mp_need_query": ("Escribe primero una búsqueda.", "Type a search first.", "Saisissez d'abord une recherche."),
    "rule_from_search": ("Crear regla con esta búsqueda", "Create rule from this search",
                         "Créer une règle avec cette recherche"),
    "results": ("{n} resultados · {seen} correos revisados", "{n} results · {seen} messages checked",
                "{n} résultats · {seen} messages examinés"),
    "results_more": ("Se alcanzó el máximo: {n} resultados ({seen} revisados). Afina la búsqueda o sube el máximo.",
                     "Limit reached: {n} results ({seen} checked). Refine the search or raise the limit.",
                     "Limite atteinte : {n} résultats ({seen} examinés). Affinez la recherche ou augmentez la "
                     "limite."),
    "results_stopped": ("Búsqueda detenida: {n} resultados ({seen} revisados).",
                        "Search stopped: {n} results ({seen} checked).",
                        "Recherche arrêtée : {n} résultats ({seen} examinés)."),
    "ss_unread_claims": ("Reclamaciones sin leer", "Unread claims", "Réclamations non lues"),
    "ss_phishing": ("Posible phishing", "Possible phishing", "Hameçonnage possible"),
    "ss_cards": ("Tarjetas o IBAN escritos en el correo", "Cards or IBANs written in messages",
                 "Cartes ou IBAN écrits dans les messages"),
    "ss_external_links": ("Externos con enlaces", "External with links", "Externes avec liens"),
    "ss_big": ("Adjuntos de más de 5 MB", "Attachments over 5 MB", "Pièces jointes de plus de 5 Mo"),
    "ss_chargebacks": ("Contracargos", "Chargebacks", "Rétrofacturations"),
    "ss_flagged": ("Marcados para seguimiento", "Flagged for follow-up", "Marqués pour suivi"),
    "ss_week": ("No leídos de la última semana", "Unread from last week", "Non lus de la dernière semaine"),
    # etiquetas
    "tags_list": ("Etiquetas de Outlook (categorías)", "Outlook tags (categories)", "Catégories Outlook"),
    "tag_new": ("Nueva…", "New…", "Nouvelle…"),
    "tag_rename": ("Renombrar…", "Rename…", "Renommer…"),
    "tag_color": ("Color…", "Color…", "Couleur…"),
    "tag_delete": ("Eliminar", "Delete", "Supprimer"),
    "tag_show": ("Ver correos", "Show messages", "Voir les messages"),
    "bulk_tag": ("Etiquetado en lote", "Bulk tagging", "Catégorisation en lot"),
    "tag": ("Etiqueta", "Tag", "Catégorie"),
    "search_label": ("Búsqueda", "Search", "Recherche"),
    "preview_btn": ("Vista previa", "Preview", "Aperçu"),
    "tag_apply": ("Poner etiqueta a todos", "Tag all", "Catégoriser tout"),
    "tag_remove": ("Quitar etiqueta a todos", "Untag all", "Retirer la catégorie de tout"),
    "bulk_hint": ("Primero pulsa «Vista previa» para ver qué correos cumplen la búsqueda; después pon o quita la "
                  "etiqueta a todos. La búsqueda usa la misma sintaxis que «Buscar y filtrar».",
                  "First click “Preview” to see which messages match the search; then tag or untag them all. The "
                  "search uses the same syntax as “Search & filter”.",
                  "Cliquez d'abord sur « Aperçu » pour voir les messages concernés, puis ajoutez ou retirez la "
                  "catégorie à tous. La recherche utilise la même syntaxe que « Rechercher et filtrer »."),
    "tag_name": ("Nombre", "Name", "Nom"),
    "tag_color_label": ("Color", "Color", "Couleur"),
    "tag_rename_prompt": ("Nuevo nombre de la etiqueta:", "New tag name:", "Nouveau nom de la catégorie :"),
    "tag_retag_confirm": ("¿Cambiar también «{old}» por «{new}» en los correos que ya la tienen?\n(Se busca en todos "
                          "los buzones conectados; puede tardar.)",
                          "Also replace “{old}” with “{new}” on messages that already have it?\n(All connected "
                          "mailboxes are searched; it may take a while.)",
                          "Remplacer aussi « {old} » par « {new} » dans les messages qui l'ont déjà ?\n(Toutes les "
                          "boîtes connectées sont parcourues ; cela peut prendre du temps.)"),
    "tag_delete_confirm": ("¿Eliminar la etiqueta «{name}» de la lista de Outlook?",
                           "Delete the tag “{name}” from Outlook's list?",
                           "Supprimer la catégorie « {name} » de la liste d'Outlook ?"),
    "tag_untag_confirm": ("¿Quitar también «{name}» de los correos que la tienen?\n(Si no, la conservarán sin color.)",
                          "Also remove “{name}” from the messages that have it?\n(Otherwise they keep it, without "
                          "color.)",
                          "Retirer aussi « {name} » des messages qui l'ont ?\n(Sinon, ils la garderont, sans "
                          "couleur.)"),
    "mp_need_category": ("Elige una etiqueta.", "Choose a tag.", "Choisissez une catégorie."),
    "mp_need_preview": ("Pulsa antes «Vista previa».", "Click “Preview” first.", "Cliquez d'abord sur « Aperçu »."),
    "bulk_add_confirm": ("¿Poner la etiqueta «{name}» a {n} correos?", "Tag {n} messages with “{name}”?",
                         "Ajouter la catégorie « {name} » à {n} messages ?"),
    "bulk_remove_confirm": ("¿Quitar la etiqueta «{name}» de {n} correos?", "Remove the tag “{name}” from {n} messages?",
                            "Retirer la catégorie « {name} » de {n} messages ?"),
    "cat_dialog_title": ("Etiquetas", "Tags", "Catégories"),
    "cat_new": ("Nueva etiqueta", "New tag", "Nouvelle catégorie"),
    "cat_create": ("Crear", "Create", "Créer"),
    "cat_some": ("algunos", "some", "certains"),
    "c_red": ("Rojo", "Red", "Rouge"),
    "c_orange": ("Naranja", "Orange", "Orange"),
    "c_yellow": ("Amarillo", "Yellow", "Jaune"),
    "c_green": ("Verde", "Green", "Vert"),
    "c_teal": ("Verde azulado", "Teal", "Bleu-vert"),
    "c_blue": ("Azul", "Blue", "Bleu"),
    "c_purple": ("Morado", "Purple", "Violet"),
    "c_maroon": ("Granate", "Maroon", "Bordeaux"),
    "c_steel": ("Gris acero", "Steel", "Gris acier"),
    "c_gray": ("Gris", "Gray", "Gris"),
    "c_darkgreen": ("Verde oscuro", "Dark green", "Vert foncé"),
    "c_darkblue": ("Azul oscuro", "Dark blue", "Bleu foncé"),
    # reglas
    "rules_list": ("Mis reglas", "My rules", "Mes règles"),
    "rcol_on": ("Activa", "On", "Active"),
    "rcol_name": ("Nombre", "Name", "Nom"),
    "rcol_query": ("Búsqueda", "Search", "Recherche"),
    "rule_new": ("Nueva", "New", "Nouvelle"),
    "rule_delete": ("Eliminar", "Delete", "Supprimer"),
    "move_up": ("↑ Subir", "↑ Up", "↑ Monter"),
    "move_down": ("↓ Bajar", "↓ Down", "↓ Descendre"),
    "rule_edit": ("Regla", "Rule", "Règle"),
    "rule_name": ("Nombre", "Name", "Nom"),
    "rule_move": ("Mover a", "Move to", "Déplacer vers"),
    "choose": ("Elegir…", "Choose…", "Choisir…"),
    "rule_tag": ("Poner etiquetas:", "Add tags:", "Ajouter les catégories :"),
    "rule_read": ("Marcar como leído", "Mark as read", "Marquer comme lu"),
    "rule_flag": ("Marcar para seguimiento", "Flag for follow-up", "Marquer pour suivi"),
    "rule_enabled": ("Activa", "Enabled", "Active"),
    "rule_save": ("Guardar regla", "Save rule", "Enregistrer la règle"),
    "rule_test": ("Probar (sin cambiar nada)", "Test (no changes)", "Tester (sans rien modifier)"),
    "rule_run": ("Ejecutar ahora", "Run now", "Exécuter maintenant"),
    "rule_outlook": ("Crear regla en Outlook…", "Create Outlook rule…", "Créer une règle Outlook…"),
    "rule_scope": ("Dónde se ejecutan", "Where rules run", "Où s'exécutent les règles"),
    "rules_run_all": ("Ejecutar todas las reglas activas", "Run all active rules", "Exécuter toutes les règles actives"),
    "rule_need_fields": ("La regla necesita un nombre y una búsqueda.", "The rule needs a name and a search.",
                         "La règle a besoin d'un nom et d'une recherche."),
    "rule_saved": ("Regla «{name}» guardada", "Rule “{name}” saved", "Règle « {name} » enregistrée"),
    "rule_delete_confirm": ("¿Eliminar la regla «{name}»?", "Delete the rule “{name}”?",
                            "Supprimer la règle « {name} » ?"),
    "rules_none_active": ("No hay reglas activas.", "There are no active rules.", "Aucune règle active."),
    "rule_plan": ("Correos afectados: {n} · mover {moved} · etiquetar {tagged} · marcar como leídos {read} · "
                  "seguimiento {flagged}",
                  "Messages affected: {n} · move {moved} · tag {tagged} · mark as read {read} · flag {flagged}",
                  "Messages concernés : {n} · déplacer {moved} · catégoriser {tagged} · marquer comme lus {read} "
                  "· suivi {flagged}"),
    "rule_missing_folder": ("No se encontró la carpeta destino de: {names}. Elige la carpeta de nuevo.",
                            "Destination folder not found for: {names}. Choose the folder again.",
                            "Dossier de destination introuvable pour : {names}. Choisissez-le à nouveau."),
    "rule_apply_confirm": ("¿Aplicar los cambios ahora?", "Apply the changes now?", "Appliquer les modifications ?"),
    "rule_nothing": ("Ningún correo necesita cambios.", "No message needs changes.",
                     "Aucun message ne nécessite de modification."),
    "rule_done": ("Hecho: {moved} movidos, {categorized} etiquetados, {read} marcados como leídos y {flagged} para "
                  "seguimiento.",
                  "Done: {moved} moved, {categorized} tagged, {read} marked as read and {flagged} flagged.",
                  "Terminé : {moved} déplacés, {categorized} catégorisés, {read} marqués comme lus et {flagged} "
                  "marqués pour suivi."),
    "rule_outlook_intro": ("Se creará en Outlook la regla «{name}», que se aplicará sola a los correos que lleguen:",
                           "The Outlook rule “{name}” will be created and applied automatically to incoming mail:",
                           "La règle Outlook « {name} » sera créée et appliquée automatiquement aux messages "
                           "entrants :"),
    "rule_outlook_when": ("Cuando el correo:", "When the message:", "Quand le message :"),
    "rule_outlook_except": ("Excepto si:", "Except if:", "Sauf si :"),
    "rule_outlook_actions": ("Entonces:", "Then:", "Alors :"),
    "rule_outlook_confirm": ("¿Crear la regla en Outlook?", "Create the rule in Outlook?",
                             "Créer la règle dans Outlook ?"),
    "rule_outlook_done": ("Regla «{name}» creada en Outlook. La verás en Archivo › Administrar reglas y alertas.",
                          "Rule “{name}” created in Outlook. You will find it in File › Manage Rules & Alerts.",
                          "Règle « {name} » créée dans Outlook. Elle figure dans Fichier › Gérer les règles et les "
                          "alertes."),
    "rule_outlook_demo": ("Regla «{name}» creada (demostración: no se guarda en ningún Outlook).",
                          "Rule “{name}” created (demo: it is not saved in any Outlook).",
                          "Règle « {name} » créée (démonstration : elle n'est enregistrée dans aucun Outlook)."),
    "rule_not_convertible": (
        "Outlook no puede crear esta regla: solo admite palabras en el asunto o el cuerpo, la dirección del "
        "remitente, adjuntos e importancia (una condición de cada tipo). La regla sigue funcionando desde MailPilot "
        "con «Ejecutar ahora».",
        "Outlook cannot create this rule: it only supports words in the subject or body, the sender's address, "
        "attachments and importance (one condition of each type). The rule still works from MailPilot with “Run "
        "now”.",
        "Outlook ne peut pas créer cette règle : il n'accepte que des mots dans l'objet ou le corps, l'adresse de "
        "l'expéditeur, les pièces jointes et l'importance (une condition de chaque type). La règle reste utilisable "
        "depuis MailPilot avec « Exécuter maintenant »."),
    "rule_note_read": ("Nota: las reglas de Outlook no pueden marcar como leído; eso solo lo hará MailPilot.",
                       "Note: Outlook rules cannot mark as read; only MailPilot will do that.",
                       "Remarque : les règles Outlook ne peuvent pas marquer comme lu ; seul MailPilot le fera."),
    "rule_no_actions": ("La regla de Outlook necesita una acción: mover a una carpeta, poner etiquetas o marcar para "
                        "seguimiento.",
                        "The Outlook rule needs an action: move to a folder, add tags or flag for follow-up.",
                        "La règle Outlook a besoin d'une action : déplacer, catégoriser ou marquer pour suivi."),
    "rc_subject": ("tiene en el asunto", "has in the subject", "contient dans l'objet"),
    "rc_body": ("tiene en el cuerpo", "has in the body", "contient dans le corps"),
    "rc_body_or_subject": ("tiene en el asunto o el cuerpo", "has in the subject or body",
                           "contient dans l'objet ou le corps"),
    "rc_sender_address": ("viene de una dirección que contiene", "comes from an address containing",
                          "provient d'une adresse contenant"),
    "rc_has_attachment": ("tiene adjuntos", "has attachments", "a des pièces jointes"),
    "rc_importance": ("tiene importancia", "has importance", "a l'importance"),
    "imp_high": ("alta", "high", "haute"),
    "imp_normal": ("normal", "normal", "normale"),
    "imp_low": ("baja", "low", "basse"),
    # redacción en inglés
    "from_outlook": ("Traer de Outlook", "Get from Outlook", "Récupérer d'Outlook"),
    "apply_outlook": ("Aplicar en Outlook", "Apply in Outlook", "Appliquer dans Outlook"),
    "new_draft": ("Nuevo borrador en Outlook", "New Outlook draft", "Nouveau brouillon Outlook"),
    "subject": ("Asunto", "Subject", "Objet"),
    "draft_editable": ("Borrador de Outlook: las correcciones se aplican en él sin perder formato ni firma.",
                       "Outlook draft: fixes are applied to it without losing formatting or signature.",
                       "Brouillon Outlook : les corrections s'y appliquent sans perdre la mise en forme ni la "
                       "signature."),
    "draft_readonly": ("Correo de solo lectura (ya enviado): copia el texto o crea un borrador nuevo.",
                       "Read-only message (already sent): copy the text or create a new draft.",
                       "Message en lecture seule (déjà envoyé) : copiez le texte ou créez un nouveau brouillon."),
    "wt_review": ("Revisión", "Review", "Révision"),
    "wt_phrases": ("Frases", "Phrases", "Phrases"),
    "wt_templates": ("Plantillas", "Templates", "Modèles"),
    "check_now": ("Revisar", "Check", "Vérifier"),
    "apply_safe": ("Aplicar correcciones seguras", "Apply safe fixes", "Appliquer les corrections sûres"),
    "icol_kind": ("Tipo", "Type", "Type"),
    "icol_text": ("Texto", "Text", "Texte"),
    "icol_suggestion": ("Sugerencia", "Suggestion", "Suggestion"),
    "apply_fix": ("Aplicar", "Apply", "Appliquer"),
    "ignore": ("Ignorar", "Ignore", "Ignorer"),
    "add_dictionary": ("Añadir al diccionario", "Add to dictionary", "Ajouter au dictionnaire"),
    "ai_writing": ("✨ Con IA (necesita internet)", "✨ With AI (needs internet)", "✨ Avec l'IA (nécessite internet)"),
    "ai_improve": ("✨ Mejorar redacción", "✨ Improve writing", "✨ Améliorer la rédaction"),
    "ai_translate": ("✨ Traducir al inglés", "✨ Translate into English", "✨ Traduire en anglais"),
    "tone_professional": ("Profesional", "Professional", "Professionnel"),
    "tone_friendly": ("Cercano", "Friendly", "Chaleureux"),
    "tone_concise": ("Conciso", "Concise", "Concis"),
    "tone_firm": ("Firme pero cortés", "Firm but polite", "Ferme mais courtois"),
    "tone_apologetic": ("De disculpa", "Apologetic", "D'excuse"),
    "kind_spelling": ("Ortografía", "Spelling", "Orthographe"),
    "kind_grammar": ("Gramática", "Grammar", "Grammaire"),
    "kind_esl": ("Error típico", "Common mistake", "Erreur fréquente"),
    "kind_punctuation": ("Puntuación", "Punctuation", "Ponctuation"),
    "kind_style": ("Estilo", "Style", "Style"),
    "kind_tone": ("Tono", "Tone", "Ton"),
    "kind_clarity": ("Claridad", "Clarity", "Clarté"),
    "kind_card": ("Tarjeta", "Card", "Carte"),
    "kind_iban": ("IBAN", "IBAN", "IBAN"),
    "no_issues": ("✔ No se encontraron problemas.", "✔ No issues found.", "✔ Aucun problème trouvé."),
    "writing_stats": ("{words} palabras · {sentences} frases · legibilidad {score} ({level}) · voz pasiva: {passive} "
                      "· {found}",
                      "{words} words · {sentences} sentences · readability {score} ({level}) · passive voice: "
                      "{passive} · {found}",
                      "{words} mots · {sentences} phrases · lisibilité {score} ({level}) · voix passive : {passive} "
                      "· {found}"),
    "lvl_very_easy": ("muy fácil", "very easy", "très facile"),
    "lvl_easy": ("fácil", "easy", "facile"),
    "lvl_medium": ("normal", "standard", "standard"),
    "lvl_hard": ("difícil", "difficult", "difficile"),
    "insert": ("Insertar", "Insert", "Insérer"),
    "use_template": ("Usar plantilla", "Use template", "Utiliser le modèle"),
    "mp_need_template": ("Elige una plantilla.", "Choose a template.", "Choisissez un modèle."),
    "replace_text_confirm": ("¿Reemplazar el texto actual?", "Replace the current text?", "Remplacer le texte actuel ?"),
    "dictionary_only_spelling": ("Solo se pueden añadir al diccionario las palabras marcadas como ortografía.",
                                 "Only words marked as spelling can be added to the dictionary.",
                                 "Seuls les mots signalés en orthographe peuvent être ajoutés au dictionnaire."),
    "no_changes": ("No hay cambios que aplicar.", "There are no changes to apply.", "Aucune modification à appliquer."),
    "applied_n": ("Se aplicaron {n} cambios en el borrador de Outlook.", "{n} changes applied to the Outlook draft.",
                  "{n} modifications appliquées au brouillon Outlook."),
    "failed_n": ("{n} cambios no se encontraron en el borrador (quizá se editó en Outlook): revísalos a mano.",
                 "{n} changes were not found in the draft (maybe it was edited in Outlook): check them by hand.",
                 "{n} modifications introuvables dans le brouillon (peut-être modifié dans Outlook) : vérifiez-les "
                 "à la main."),
    "draft_created": ("Borrador creado y abierto en Outlook.", "Draft created and opened in Outlook.",
                      "Brouillon créé et ouvert dans Outlook."),
    "draft_created_demo": ("Borrador guardado en «Borradores» (demostración).", "Draft saved in “Drafts” (demo).",
                           "Brouillon enregistré dans « Brouillons » (démonstration)."),
    "ai_result_title": ("✨ Propuesta de la IA", "✨ AI proposal", "✨ Proposition de l'IA"),
    "ai_body": ("Texto", "Text", "Texte"),
    "ai_changes": ("Cambios principales", "Main changes", "Principales modifications"),
    "use_text": ("Usar este texto", "Use this text", "Utiliser ce texte"),
    "pc_greetings": ("Saludos", "Greetings", "Salutations"),
    "pc_openings": ("Para empezar", "Openings", "Introductions"),
    "pc_requests": ("Peticiones", "Requests", "Demandes"),
    "pc_followup": ("Seguimiento", "Follow-up", "Relances"),
    "pc_apologies": ("Disculpas", "Apologies", "Excuses"),
    "pc_bad_news": ("Malas noticias", "Bad news", "Mauvaises nouvelles"),
    "pc_closings": ("Despedidas", "Closings", "Formules de fin"),
    "pc_claims": ("Reclamaciones de fraude", "Fraud claims", "Réclamations de fraude"),
    "tpl_ack": ("Acuse de recibo de reclamación", "Claim acknowledgement", "Accusé de réception de réclamation"),
    "tpl_docs": ("Solicitud de documentos", "Document request", "Demande de documents"),
    "tpl_credit": ("Abono provisional", "Provisional credit", "Crédit provisoire"),
    "tpl_favorable": ("Resolución favorable", "Favorable outcome", "Décision favorable"),
    "tpl_unfavorable": ("Resolución desfavorable", "Unfavorable outcome", "Décision défavorable"),
    "tpl_chargeback": ("Documentación de contracargo", "Chargeback documentation", "Dossier de rétrofacturation"),
    "tpl_phishing": ("Aviso de phishing a clientes", "Phishing warning to customers",
                     "Alerte hameçonnage aux clients"),
    "tpl_internal": ("Seguimiento interno de un caso", "Internal case follow-up", "Suivi interne d'un dossier"),
    # análisis
    "internal_domains": ("Dominios internos", "Internal domains", "Domaines internes"),
    "claim_pattern": ("Patrón de reclamación", "Claim pattern", "Modèle de réclamation"),
    "an_overview": ("Resumen del buzón", "Mailbox overview", "Vue d'ensemble"),
    "an_phishing": ("Detectar phishing", "Detect phishing", "Détecter l'hameçonnage"),
    "an_sensitive": ("Datos sensibles", "Sensitive data", "Données sensibles"),
    "an_claims": ("Índice de reclamaciones", "Claims index", "Index des réclamations"),
    "an_ai": ("✨ Sugerir organización", "✨ Suggest organization", "✨ Suggérer une organisation"),
    "suggestions": ("Sugerencias", "Suggestions", "Suggestions"),
    "sugg_search": ("Ver correos", "Show messages", "Voir les messages"),
    "sugg_rule": ("Crear regla", "Create rule", "Créer une règle"),
    "an_tag_phishing": ("Etiquetar todos como phishing", "Tag all as phishing", "Catégoriser tout comme hameçonnage"),
    "an_move_junk": ("Mover todos a Correo no deseado", "Move all to Junk Email", "Tout déplacer vers Courrier "
                                                                                   "indésirable"),
    "an_overview_text": ("{total} correos · {unread} sin leer · {flagged} con seguimiento · {attachments} con adjuntos "
                         "· {size_mb} MB\n{senders} remitentes distintos en {folders} carpetas · del {oldest} al "
                         "{newest}",
                         "{total} messages · {unread} unread · {flagged} flagged · {attachments} with attachments · "
                         "{size_mb} MB\n{senders} different senders in {folders} folders · from {oldest} to {newest}",
                         "{total} messages · {unread} non lus · {flagged} avec suivi · {attachments} avec pièces "
                         "jointes · {size_mb} Mo\n{senders} expéditeurs différents dans {folders} dossiers · du "
                         "{oldest} au {newest}"),
    "an_has_suggestions": ("Hay {n} sugerencias para ordenar el buzón (panel de la derecha).",
                           "There are {n} suggestions to tidy up the mailbox (right panel).",
                           "{n} suggestions pour ranger la boîte (panneau de droite)."),
    "an_phishing_text": ("{n} correos sospechosos entre {checked} correos externos revisados. Revísalos antes de abrir "
                         "enlaces o adjuntos y repórtalos al equipo de seguridad.",
                         "{n} suspicious messages among {checked} external messages checked. Review them before "
                         "opening links or attachments and report them to the security team.",
                         "{n} messages suspects parmi {checked} messages externes examinés. Vérifiez-les avant "
                         "d'ouvrir liens ou pièces jointes et signalez-les à l'équipe sécurité."),
    "an_sensitive_text": ("{n} datos sensibles en {msgs} correos (de {checked} revisados). Las tarjetas completas no "
                          "deberían circular por correo (PCI DSS): elimina o enmascara esos datos.",
                          "{n} sensitive values in {msgs} messages ({checked} checked). Full card numbers should not "
                          "travel by email (PCI DSS): delete or mask them.",
                          "{n} données sensibles dans {msgs} messages ({checked} examinés). Les numéros de carte "
                          "complets ne doivent pas circuler par e-mail (PCI DSS) : supprimez-les ou masquez-les."),
    "an_claims_text": ("{n} reclamaciones encontradas en {checked} correos.", "{n} claims found in {checked} messages.",
                       "{n} réclamations trouvées dans {checked} messages."),
    "an_ai_need_overview": ("Pulsa antes «Resumen del buzón»: la IA trabaja con esas estadísticas (remitentes, "
                            "dominios y carpetas), no con el contenido de los correos.",
                            "First click “Mailbox overview”: the AI works with those statistics (senders, domains "
                            "and folders), not with the content of the messages.",
                            "Cliquez d'abord sur « Vue d'ensemble » : l'IA travaille avec ces statistiques "
                            "(expéditeurs, domaines et dossiers), pas avec le contenu des messages."),
    "ai_rules_title": ("✨ Reglas propuestas por la IA", "✨ Rules suggested by the AI", "✨ Règles proposées par l'IA"),
    "ai_rules": ("Reglas", "Rules", "Règles"),
    "ai_notes": ("Consejos", "Tips", "Conseils"),
    "ai_rules_add": ("Añadir a mis reglas (desactivadas)", "Add to my rules (disabled)",
                     "Ajouter à mes règles (désactivées)"),
    "ai_rules_added": ("Se añadieron {n} reglas desactivadas: revísalas y actívalas en la pestaña «Reglas».",
                       "{n} disabled rules added: review and enable them in the “Rules” tab.",
                       "{n} règles désactivées ajoutées : vérifiez-les et activez-les dans l'onglet « Règles »."),
    "mp_need_suggestion": ("Elige una sugerencia.", "Choose a suggestion.", "Choisissez une suggestion."),
    "phishing_category": ("Phishing", "Phishing", "Hameçonnage"),
    "junk": ("Correo no deseado", "Junk Email", "Courrier indésirable"),
    "junk_confirm": ("¿Mover {n} correos a Correo no deseado?", "Move {n} messages to Junk Email?",
                     "Déplacer {n} messages vers Courrier indésirable ?"),
    "sheet_senders": ("Remitentes", "Senders", "Expéditeurs"),
    "sheet_domains": ("Dominios", "Domains", "Domaines"),
    "sheet_months": ("Por mes", "By month", "Par mois"),
    "sheet_phishing": ("Phishing", "Phishing", "Hameçonnage"),
    "sheet_sensitive": ("Datos sensibles", "Sensitive data", "Données sensibles"),
    "sheet_claims": ("Reclamaciones", "Claims", "Réclamations"),
    "sug_newsletter": ("Envío automático: {sender} ({n} correos) → moverlo a una carpeta",
                       "Automatic sender: {sender} ({n} messages) → move to a folder",
                       "Envoi automatique : {sender} ({n} messages) → déplacer vers un dossier"),
    "sug_domain": ("{domain} envía muchos correos ({n}) → ponerles una etiqueta",
                   "{domain} sends many messages ({n}) → tag them",
                   "{domain} envoie beaucoup de messages ({n}) → les catégoriser"),
    "sug_claims": ("{n} correos de reclamaciones sin etiqueta → etiquetarlos", "{n} untagged claim messages → tag them",
                   "{n} messages de réclamation sans catégorie → les catégoriser"),
    "sug_old_unread": ("{n} correos sin leer de hace más de 30 días → revisarlos o marcarlos como leídos",
                       "{n} unread messages older than 30 days → review them or mark them as read",
                       "{n} messages non lus de plus de 30 jours → les traiter ou les marquer comme lus"),
    "sug_flags": ("{n} correos marcados hace más de 14 días → revisar el seguimiento",
                  "{n} messages flagged more than 14 days ago → review the follow-up",
                  "{n} messages marqués il y a plus de 14 jours → revoir le suivi"),
    "sug_big": ("{n} correos con adjuntos grandes ({mb} MB) → archivarlos o guardar los adjuntos",
                "{n} messages with large attachments ({mb} MB) → archive them or save the attachments",
                "{n} messages avec de grosses pièces jointes ({mb} Mo) → les archiver ou enregistrer les pièces "
                "jointes"),
    # señales de phishing
    "ph_external": ("remitente externo", "external sender", "expéditeur externe"),
    "ph_lookalike": ("dominio que imita al de la empresa", "domain imitating the company's",
                     "domaine imitant celui de l'entreprise"),
    "ph_impersonation": ("nombre que suplanta a un departamento o marca", "name impersonating a department or brand",
                         "nom usurpant un service ou une marque"),
    "ph_freemail": ("cuenta de correo gratuita", "free email account", "messagerie gratuite"),
    "ph_name_email": ("el nombre muestra otra dirección", "the name shows another address",
                      "le nom affiche une autre adresse"),
    "ph_reply_to": ("las respuestas van a otra dirección", "replies go to another address",
                    "les réponses vont à une autre adresse"),
    "ph_urgency": ("urgencia o amenazas", "urgency or threats", "urgence ou menaces"),
    "ph_credentials": ("pide claves, códigos o pagos", "asks for passwords, codes or payments",
                       "demande des mots de passe, codes ou paiements"),
    "ph_link_mismatch": ("el enlace no lleva a donde dice", "the link does not go where it says",
                         "le lien ne mène pas où il l'indique"),
    "ph_ip_link": ("enlace a una dirección IP", "link to an IP address", "lien vers une adresse IP"),
    "ph_shortener": ("enlace acortado", "shortened link", "lien raccourci"),
    "ph_tld": ("enlace a un dominio de riesgo", "link to a risky domain", "lien vers un domaine à risque"),
    "ph_attachment": ("adjunto peligroso", "dangerous attachment", "pièce jointe dangereuse"),
    # errores
    "q_err_paren": ("Revisa los paréntesis de la búsqueda.", "Check the parentheses in the search.",
                    "Vérifiez les parenthèses de la recherche."),
    "q_err_regex": ("Expresión regular no válida: {detail}", "Invalid regular expression: {detail}",
                    "Expression régulière non valide : {detail}"),
    "q_err_date": ("Fecha no válida: «{detail}». Usa 2026-10-01, 01/10/2026, hoy, ayer o 7d.",
                   "Invalid date: “{detail}”. Use 2026-10-01, 10/01/2026, today, yesterday or 7d.",
                   "Date non valide : « {detail} ». Utilisez 2026-10-01, 01/10/2026, aujourd'hui, hier ou 7d."),
    "q_err_size": ("Tamaño no válido: «{detail}». Ejemplos: >2mb, <500kb.",
                   "Invalid size: “{detail}”. Examples: >2mb, <500kb.",
                   "Taille non valide : « {detail} ». Exemples : >2mo, <500ko."),
    "q_err_has": ("«has:{detail}» no existe. Usa: attachment, card, iban, claim, phone, amount, link, category, flag.",
                  "“has:{detail}” does not exist. Use: attachment, card, iban, claim, phone, amount, link, category, "
                  "flag.",
                  "« has:{detail} » n'existe pas. Utilisez : attachment, card, iban, claim, phone, amount, link, "
                  "category, flag."),
    "q_err_is": ("«is:{detail}» no existe. Usa: unread, read, flagged, important, external, internal, phishing, "
                 "uncategorized.",
                 "“is:{detail}” does not exist. Use: unread, read, flagged, important, external, internal, phishing, "
                 "uncategorized.",
                 "« is:{detail} » n'existe pas. Utilisez : unread, read, flagged, important, external, internal, "
                 "phishing, uncategorized."),
    "q_err_importance": ("Importancia no válida: «{detail}». Usa high, normal o low.",
                         "Invalid importance: “{detail}”. Use high, normal or low.",
                         "Importance non valide : « {detail} ». Utilisez high, normal ou low."),
    "mp_err_no_outlook": ("No se encontró Outlook clásico ({detail}). MailPilot necesita Outlook para Windows (no el "
                          "«nuevo Outlook» ni la versión web). Mientras tanto puedes usar el modo demostración.",
                          "Classic Outlook was not found ({detail}). MailPilot needs Outlook for Windows (not the "
                          "“new Outlook” or the web version). Meanwhile you can use the demo mode.",
                          "Outlook classique est introuvable ({detail}). MailPilot a besoin d'Outlook pour Windows "
                          "(pas du « nouvel Outlook » ni de la version web). En attendant, utilisez le mode "
                          "démonstration."),
    "mp_err_no_pywin32": ("Falta el componente pywin32 para comunicarse con Outlook. Usa MailPilot.exe o instala "
                          "pywin32.",
                          "The pywin32 component needed to talk to Outlook is missing. Use MailPilot.exe or install "
                          "pywin32.",
                          "Le composant pywin32 nécessaire pour communiquer avec Outlook est absent. Utilisez "
                          "MailPilot.exe ou installez pywin32."),
    "mp_err_denied": ("Outlook bloqueó el acceso ({detail}). Acepta el aviso de seguridad de Outlook o pide a TI que "
                      "permita MailPilot.",
                      "Outlook blocked access ({detail}). Accept Outlook's security prompt or ask IT to allow "
                      "MailPilot.",
                      "Outlook a bloqué l'accès ({detail}). Acceptez l'alerte de sécurité d'Outlook ou demandez au "
                      "service informatique d'autoriser MailPilot."),
    "mp_err_com": ("Outlook devolvió un error: {detail}", "Outlook returned an error: {detail}",
                   "Outlook a renvoyé une erreur : {detail}"),
    "mp_err_not_found": ("No se encontró el elemento (quizá se movió o se eliminó). Pulsa «Actualizar».",
                         "The item was not found (it may have been moved or deleted). Click “Refresh”.",
                         "Élément introuvable (il a peut-être été déplacé ou supprimé). Cliquez sur « Actualiser »."),
    "mp_err_shared_failed": ("No se pudo abrir el buzón compartido «{detail}». Revisa la dirección y que tengas "
                             "permiso.",
                             "Could not open the shared mailbox “{detail}”. Check the address and your permissions.",
                             "Impossible d'ouvrir la boîte partagée « {detail} ». Vérifiez l'adresse et vos droits."),
    "mp_err_folder_name": ("Nombre de carpeta no válido: «{detail}» (no puede estar vacío ni llevar / o \\).",
                           "Invalid folder name: “{detail}” (it cannot be empty or contain / or \\).",
                           "Nom de dossier non valide : « {detail} » (il ne peut pas être vide ni contenir / ou \\)."),
    "mp_err_folder_exists": ("Ya existe una carpeta «{detail}» ahí.", "A folder “{detail}” already exists there.",
                             "Un dossier « {detail} » existe déjà à cet endroit."),
    "mp_err_folder_special": ("«{detail}» es una carpeta del sistema: no se puede renombrar, mover ni eliminar.",
                              "“{detail}” is a system folder: it cannot be renamed, moved or deleted.",
                              "« {detail} » est un dossier système : impossible de le renommer, déplacer ou "
                              "supprimer."),
    "mp_err_folder_loop": ("No se puede mover «{detail}» dentro de sí misma.", "“{detail}” cannot be moved into itself.",
                           "Impossible de déplacer « {detail} » dans lui-même."),
    "mp_err_category_name": ("Nombre de etiqueta no válido: «{detail}» (no puede llevar comas ni punto y coma).",
                             "Invalid tag name: “{detail}” (it cannot contain commas or semicolons).",
                             "Nom de catégorie non valide : « {detail} » (pas de virgule ni de point-virgule)."),
    "mp_err_category_exists": ("Ya existe la etiqueta «{detail}».", "The tag “{detail}” already exists.",
                               "La catégorie « {detail} » existe déjà."),
    "mp_err_no_current": ("No hay ningún borrador ni correo abierto o seleccionado en Outlook.",
                          "There is no draft or message open or selected in Outlook.",
                          "Aucun brouillon ni message ouvert ou sélectionné dans Outlook."),
    "mp_err_rule": ("Condición de regla no admitida: {detail}", "Unsupported rule condition: {detail}",
                    "Condition de règle non prise en charge : {detail}"),
}

HELP = {
    "es": """BÚSQUEDA AVANZADA (sin internet)

Palabras sueltas          fraude tarjeta          deben aparecer todas (asunto, remitente, destinatarios,
                                                  etiquetas o cuerpo); da igual mayúsculas y acentos
Frase exacta              "cargo no reconocido"
Excluir                   -boletín   -from:noreply
Una u otra                contracargo OR chargeback      (también: O, OU, |)
Agrupar                   (urgente OR prioritario) is:unread
Expresión regular         re:"R-\\d{4}-\\d+"      asunto:/^RE:/

CAMPOS (se pueden escribir en español, inglés o francés)
  from: / de: / remitente:          from:visa.com   de:"Laura Méndez"
  to: / para:   cc:                 para:fraude@banco.com
  subject: / asunto:                asunto:reclamación
  body: / cuerpo:                   cuerpo:"código de seguridad"
  category: / etiqueta:             etiqueta:urgente
  domain: / dominio:                dominio:gmail.com
  folder: / carpeta: / in:          carpeta:contracargos
  filename: / adjunto:              adjunto:pdf

TIENE (has: / tiene:)
  attachment (adjunto) · card (tarjeta: número completo válido) · iban · claim (reclamación)
  phone (teléfono) · amount (importe) · link (enlace) · category (etiqueta) · flag

ES (is: / es:)
  unread (no_leído) · read (leído) · flagged (marcado) · important (importante)
  external (externo) · internal (interno) · phishing (sospechoso) · uncategorized (sin_etiqueta)

FECHAS Y TAMAÑO
  after:2026-09-01   desde:01/09/2026   before:2026-10-01   hasta:hoy   on:ayer
  newer:7d (últimos:7d)   older:3m      unidades: h, d, w/s (semanas), m (meses), y/a (años)
  size:>2mb   larger:1mb   smaller:200kb   importance:high (importancia:alta)

OPCIONES
  Palabra completa: «carg» no encontrará «cargo».
  Mayúsculas y acentos exactos: distingue «Reclamación» de «reclamacion» y, en buzones grandes de Exchange,
  deja que Outlook filtre primero (mucho más rápido).

EJEMPLOS
  has:claim is:unread newer:7d
  from:visa.com OR from:mastercard.com -is:read
  is:external has:link "verify your account"
  has:card -carpeta:eliminados
""",
    "en": """ADVANCED SEARCH (works offline)

Words                     fraud card              all must appear (subject, sender, recipients,
                                                  tags or body); case and accents are ignored
Exact phrase              "unrecognized charge"
Exclude                   -newsletter   -from:noreply
Either                    chargeback OR dispute          (also: |)
Group                     (urgent OR priority) is:unread
Regular expression        re:"R-\\d{4}-\\d+"      subject:/^RE:/

FIELDS (they can also be written in Spanish or French)
  from:                             from:visa.com   from:"Emma Wilson"
  to:   cc:                         to:fraud@bank.com
  subject:                          subject:claim
  body:                             body:"security code"
  category: / tag:                  tag:urgent
  domain:                           domain:gmail.com
  folder: / in:                     in:chargebacks
  filename: / attachment:           filename:pdf

HAS (has:)
  attachment · card (valid full card number) · iban · claim · phone · amount · link · category · flag

IS (is:)
  unread · read · flagged · important · external · internal · phishing · uncategorized

DATES AND SIZE
  after:2026-09-01   before:10/01/2026   before:today   on:yesterday
  newer:7d   older:3m      units: h, d, w (weeks), m (months), y (years)
  size:>2mb   larger:1mb   smaller:200kb   importance:high

OPTIONS
  Whole word: “carg” will not find “charge”.
  Exact case and accents: tells “Claim” from “claim” and, in large Exchange mailboxes, lets Outlook
  filter first (much faster).

EXAMPLES
  has:claim is:unread newer:7d
  from:visa.com OR from:mastercard.com -is:read
  is:external has:link "verify your account"
  has:card -in:deleted
""",
    "fr": """RECHERCHE AVANCÉE (sans internet)

Mots                      fraude carte            tous doivent apparaître (objet, expéditeur, destinataires,
                                                  catégories ou corps) ; casse et accents ignorés
Phrase exacte             "débit non reconnu"
Exclure                   -newsletter   -from:noreply
L'un ou l'autre           rétrofacturation OR chargeback      (aussi : OU, |)
Grouper                   (urgent OU prioritaire) is:unread
Expression régulière      re:"R-\\d{4}-\\d+"      objet:/^RE:/

CHAMPS (aussi en espagnol ou en anglais)
  from: / de: / expediteur:         de:visa.com   de:"Pierre Lefèvre"
  to: / destinataire:   cc:         to:fraude@banque.com
  subject: / objet: / sujet:        objet:réclamation
  body: / corps:                    corps:"code de sécurité"
  category: / etiquette:            etiquette:urgent
  domain: / domaine:                domaine:gmail.com
  folder: / dossier: / dans:        dossier:rétrofacturations
  filename: / fichier:              fichier:pdf

A (has: / avec:)
  attachment (pj) · card (carte : numéro complet valide) · iban · claim (réclamation)
  phone (téléphone) · amount (montant) · link (lien) · category (étiquette) · flag

EST (is: / est:)
  unread (nonlu) · read (lu) · flagged (suivi) · important
  external (externe) · internal (interne) · phishing (suspect) · uncategorized

DATES ET TAILLE
  after:2026-09-01   apres:01/09/2026   before:2026-10-01   avant:aujourd'hui   on:hier
  newer:7d (derniers:7j)   older:3m      unités : h, d/j, w/s (semaines), m (mois), y/a (années)
  size:>2mo   larger:1mb   smaller:200ko   importance:haute

OPTIONS
  Mot entier : « carte » ne trouvera pas « cartes ».
  Casse et accents exacts : distingue « Réclamation » de « reclamation » et, dans les grandes boîtes Exchange,
  laisse Outlook filtrer d'abord (bien plus rapide).

EXEMPLES
  has:claim is:unread newer:7d
  from:visa.com OR from:mastercard.com -is:read
  is:external has:link "verify your account"
  has:card -dossier:supprimés
""",
}
