"""Texts of MoreInfo Pilot (English only for now: the same text in the three slots of the suite)."""


def _en(text):
    return (text, text, text)


STRINGS = {key: _en(text) for key, text in {
    "tagline": "Fraud package evidence: screenshots → CASE,MOREINFO.pdf or Excel, saved to your folders",
    "tab_package": "📎 MoreInfo package",
    "tab_documents": "📄 No Pay Decision Letter & documents",
    "tab_settings": "⚙ Folders & options",
    "docs_intro": "Add the No Pay Decision Letter and any other case documents (Digital Footprints, Web extractions, "
                  "Voice Match, Approvals…). Word files and images are saved as PDF; PDF, Excel, text and email "
                  "files keep their format. They go to the same folders as the MoreInfo, named CASE,MOREINFO with "
                  "the next number (CASE,MOREINFO1, CASE,MOREINFO2…). They are uploaded together with the MoreInfo "
                  "package, or on their own with “Upload documents only”.",
    "drop_here": "Drag and drop files here  •  Ctrl+V to paste  •  click to browse",
    "drop_unavailable": "Ctrl+V to paste  •  click to browse your PC",
    "browse_docs": "Browse PC…",
    "paste_docs": "Paste (Ctrl+V)",
    "upload_docs": "Upload documents only",
    "dcol_n": "#",
    "dcol_file": "File",
    "dcol_type": "Type",
    "dcol_saved": "Saved as",
    "dcol_dest": "Goes to",
    "dest_main": "MoreInfo folder",
    "dest_letter": "Letter folders ({n})",
    "toggle_letter": "✉ Mark / unmark as decision letter",
    "need_document_selection": "Select a document in the list first.",
    "letter_box": "No Pay Decision Letter from your template",
    "template": "Template",
    "load_template": "Add template (.docx)…",
    "rename_template": "Rename…",
    "remove_template": "Remove",
    "template_name_prompt": "Name for this letter template (for example “Credit card – English” or "
                            "“Carte de débit – French”):",
    "template_exists": "There is already a template called “{name}”.",
    "template_remove_confirm": "Remove the template “{name}” from MoreInfo Pilot?",
    "preview_doc": "👁 Preview",
    "letter_preview": "👁 Preview letter (PDF)",
    "preview_opened": "Preview opened: {name}",
    "letter_not_previewed": "The No Pay Decision Letter has not been previewed yet. Check it before it is "
                            "uploaded.\n\nYes = open the preview now\nNo = upload without previewing",
    "fill_letter": "Fill in the letter…",
    "template_none": "No template yet: add the blank letters (.docx), one per product or language, and give "
                     "each one a name. They are kept for every new case.",
    "template_loaded": "“{name}”: {n} field(s) to fill. Choose the right template for the case, then “Fill in "
                       "the letter…”. Double-click the letter in the list to edit it again.",
    "template_bad": "The template could not be read: {detail}",
    "template_no_fields": "No fields were found in this template. Use Word content controls (text, drop-down, "
                          "date) or placeholders like [Customer Name].",
    "letter_title": "No Pay Decision Letter",
    "letter_intro": "Fill in the fields of the letter. A field marked ×2, ×3… appears several times in the letter "
                    "(for example the customer name, also shown as a title): type it once. The letter is saved as "
                    "PDF in the letter folders when you upload.",
    "letter_add": "Add letter to the documents",
    "letter_missing": "These fields are empty: {names}.\n\nAdd the letter anyway?",
    "letter_added": "Decision letter added to the documents (it will be saved as PDF in the letter folders).",
    "same_format": "Same format",
    "doc_types": "Case documents",
    "docs_added": "{n} document(s) added",
    "nothing_to_paste": "There is nothing to paste. Copy a file in File Explorer, an image or the text of an email "
                        "and try again.",
    "need_documents": "Add at least one document first.",
    "docs_reminder": "⚠ Don't forget to upload the No Pay Decision Letter and other documents as applicable "
                     "(Digital Footprints, Web extractions, Voice Match, Approvals, etc). Click here to add them.",
    "docs_attached": "✔ {n} case document(s) ready in “No Pay Decision Letter & documents”. They will be uploaded "
                     "with the MoreInfo.",
    "docs_alert": "Don't forget to upload the No Pay Decision Letter and other documents as applicable (Digital "
                  "Footprints, Web extractions, Voice Match, Approvals, etc).\n\nYes = upload the MoreInfo now "
                  "without documents\nNo = go to the documents tab first",
    "doc_text_only": "Note: Microsoft Word is not available, so “{name}” was saved as a text-only PDF. Check it or "
                     "upload it again from a PC with Word.",
    "doc_kept": "Note: Microsoft Word is not available, so “{name}” was uploaded in its original format.",
    "case": "Case #",
    "analyst": "Analyst",
    "output": "Output",
    "mode_pdf": "Word → PDF (all screenshots, grouped by your sections)",
    "mode_excel": "Excel (add an “Additional info” tab with the screenshots to the downloaded transaction file)",
    "excel_file": "Transaction file",
    "browse": "Browse…",
    "screenshots": "Screenshots",
    "section": "Section",
    "paste": "Paste screenshot (Ctrl+V)",
    "add_images": "Add image files…",
    "remove": "Remove",
    "up": "▲",
    "down": "▼",
    "caption": "Caption…",
    "add_section": "＋",
    "need_section": "Create your first section (for example “Customer profile”). Sections are saved for next time.",
    "section_prompt": "Section name:",
    "section_exists": "There is already a section called “{name}”.",
    "need_section_selection": "Select a section in the list first.",
    "section_in_use": "“{name}” has screenshots in the current case. Move or remove them first.",
    "sections_box": "Sections (your own names and order; saved for every new case)",
    "section_add": "Add section…",
    "section_rename": "Rename…",
    "sections_hint": "The PDF and the Excel tab show the screenshots grouped by these sections, in this order. "
                     "You can also add a section with ＋ next to the section list.",
    "caption_prompt": "Caption for this screenshot (optional):",
    "auto_capture": "Auto-add every new screenshot copied (Win+Shift+S)",
    "col_n": "#",
    "col_section": "Section",
    "col_caption": "Caption",
    "col_size": "Size",
    "create": "Create and save",
    "new_case": "New case",
    "open_folder": "Open output folder",
    "result": "Result",
    "preview": "Preview",
    "no_clipboard_image": "There is no image in the clipboard. Take a screenshot (Win+Shift+S or Print Screen) "
                          "and try again.",
    "clipboard_error": "The clipboard could not be read: {detail}",
    "added_n": "{n} screenshot(s) added to “{section}”",
    "need_excel": "Choose the transaction Excel file first.",
    "need_case": "Enter the case number.",
    "need_shots": "Add at least one screenshot.",
    "need_selection": "Select a screenshot first.",
    "no_folders": "Choose the MoreInfo & documents folder (and the letter folders) in “Folders & options” "
                  "first.",
    "new_case_confirm": "Clear the screenshots and documents to start a new case?",
    "done_title": "Package ready",
    "engine_word": "PDF created with Microsoft Word.",
    "engine_builtin": "PDF created with the built-in generator (Microsoft Word not used).",
    "engine_excel": "Excel file created with a new “{sheet}” tab.",
    "created": "Created:",
    "copied_to": "Saved to:",
    "copy_errors": "Could not save to:",
    "kept": "No destination folder could be written, so the files were kept here: {folder}",
    # settings
    "main_folder": "MoreInfo & documents folder (one folder)",
    "letter_folders": "No Pay Decision Letter folders (the letter is saved in each one, for example 2)",
    "letter_folders_hint": "Only the decision letter goes to these folders. If the list is empty, the letter goes to "
                           "the MoreInfo folder.",
    "add_folder": "Add folder…",
    "add_path": "Add path…",
    "path_prompt": "Folder path (for example \\\\server\\Fraud\\Packages):",
    "use_word": "Use Microsoft Word for the PDF when it is installed (otherwise the built-in generator)",
    "keep_docx": "Also save the Word (.docx) file",
    "base_name": "File name after the case number",
    "save_settings": "Save options",
    "settings_saved": "Options saved.",
    "folder_missing": "(not reachable now)",
    "offline": "Works offline",
}.items()}
