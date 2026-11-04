VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "MIMain"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
' MoreInfo Pilot - the main window, with three tabs: "MoreInfo package" (screenshots), "No Pay Decision Letter &
' documents" and "Folders & options". The controls are created by code on the blank UserForm MIForm.
Option Explicit

Private mForm As Object
Private mHooks As Collection
Private mStore As Object          ' hidden Word document that keeps the screenshots of the case
Private mNextId As Long
Private mBusy As Boolean
Private mSyncing As Boolean
Private mPollSeq As Long
Private mLastOutput As String

' screenshots, in the order of the sections
Private mShotId() As Long
Private mShotSec() As String
Private mShotCap() As String
Private mShotCount As Long

' case documents (the No Pay Decision Letter and the others)
Private mDocPath() As String
Private mDocLetter() As Boolean
Private mDocTpl() As String       ' template of a letter filled in the app ("" for other documents)
Private mDocVals() As Variant     ' its values (Scripting.Dictionary), to edit it again
Private mDocPrev() As Boolean     ' previewed
Private mDocCount As Long

' options
Private mFolder As String
Private mLetterFolders As Collection
Private mSections As Collection
Private mTplNames As Collection
Private mTplFiles As Collection
Private mKeepDocx As Boolean
Private mBase As String

' controls
Private mp As Object, lblStatus As Object
Private txtCase As Object, txtAnalyst As Object, optPdf As Object, optExcel As Object, txtExcel As Object
Private btnExcel As Object, cboSection As Object, chkAuto As Object, lstShots As Object, imgPreview As Object
Private lblReminder As Object, txtResult As Object
Private txtCase2 As Object, cboTemplate As Object, lblTplInfo As Object, lstDocs As Object
Private txtFolder As Object, lstLetterFolders As Object, lstSections As Object, chkKeepDocx As Object, txtBase As Object

' ================================================================ start and close

Public Sub Start()
    Dim sw As Single, sh As Single, fw As Single, fh As Single
    mBusy = True   ' no events while the window is being built
    LoadPrefs
    Set mHooks = New Collection
    gStep = "Preparing the screenshot store"
    Set mStore = Documents.Add(Visible:=False)
    mStore.Saved = True
    gStep = "Loading the blank UserForm called MIForm"
    Set mForm = VBA.UserForms.Add("MIForm")
    Set mForm.Owner = Me
    ScreenPoints sw, sh
    fw = 770
    If fw > sw - 20 Then fw = sw - 20
    fh = 545
    If fh > sh - 20 Then fh = sh - 20
    mForm.Width = fw
    mForm.Height = fh
    mForm.Caption = APP_NAME & " - " & APP_AUTHOR
    mForm.BackColor = RGB(246, 248, 250)
    gStep = "Building the window"
    BuildWindow
    RefreshAll
    gStep = ""
    mBusy = False
    mForm.Show 0   ' modeless: Word can be used while the window is open
End Sub

Public Sub ShowWindow()
    On Error Resume Next
    mForm.Show 0
End Sub

' MIForm asks before closing (X button). Returns True to keep the window open.
Public Function OnClosing(ByVal closeMode As Integer) As Boolean
    If mShotCount > 0 Or mDocCount > 0 Then
        If Not Ask("Close MoreInfo Pilot? The screenshots and documents of the current case that were not uploaded " & _
                   "will be lost.") Then
            OnClosing = True
            Exit Function
        End If
    End If
    Cleanup
End Function

Private Sub Cleanup()
    Dim h As Variant
    On Error Resume Next
    For Each h In mHooks
        h.Release
    Next
    Set mHooks = New Collection
    If Not mStore Is Nothing Then mStore.Close SaveChanges:=False
    Set mStore = Nothing
    Set mForm.Owner = Nothing
    Set mForm = Nothing
    MainClosed
End Sub

' ================================================================ auto-capture (called every second by MIPilot)

Public Property Get WantsPolling() As Boolean
    On Error Resume Next
    If mForm Is Nothing Then Exit Property
    WantsPolling = (chkAuto.Value = True) And Not mBusy
End Property

Public Sub PollClipboard()
    Dim seq As Long
    seq = ClipboardSeq()
    If seq = mPollSeq Then Exit Sub
    mPollSeq = seq
    If ClipboardHasImage() Then PasteScreenshot True
End Sub

' ================================================================ events of the controls (from MICtl)

Public Sub OnEvent(ByVal key As String, ByVal evt As String)
    If mBusy Then Exit Sub
    On Error GoTo Fail
    Select Case key & ":" & evt
        Case "case:change": SyncCase txtCase, txtCase2
        Case "case2:change": SyncCase txtCase2, txtCase
        Case "mode:click": ModeChanged
        Case "excel:click": PickExcel
        Case "addsection:click": AddSection
        Case "paste:click": PasteScreenshot False
        Case "addimages:click": AddImages
        Case "auto:click": AutoChanged
        Case "shots:click": ShowPreview
        Case "shots:dblclick", "caption:click": EditCaption
        Case "remove:click": RemoveShot
        Case "up:click": MoveShot -1
        Case "down:click": MoveShot 1
        Case "previewpdf:click": PreviewMoreInfo
        Case "reminder:click": mp.Value = 1
        Case "create:click": CreatePackageNow
        Case "newcase:click": NewCase
        Case "openout:click": OpenOutput
        Case "template:change": ShowTemplateInfo
        Case "addtpl:click": AddTemplate
        Case "renametpl:click": RenameTemplate
        Case "removetpl:click": RemoveTemplate
        Case "fill:click": FillLetter
        Case "browsedocs:click": BrowseDocuments
        Case "pastedocs:click": PasteDocuments
        Case "removedoc:click": RemoveSelectedDoc
        Case "toggleletter:click": ToggleLetter
        Case "previewdoc:click": PreviewDocument
        Case "docs:dblclick": EditOrPreview
        Case "uploaddocs:click": RunUpload False
        Case "browsefolder:click": BrowseMainFolder
        Case "addlf:click": AddLetterFolder False
        Case "addlp:click": AddLetterFolder True
        Case "removelf:click": RemoveLetterFolder
        Case "addsec:click": AddSection
        Case "renamesec:click": RenameSection
        Case "removesec:click": RemoveSection
        Case "secup:click": MoveSection -1
        Case "secdown:click": MoveSection 1
        Case "savesettings:click": SaveSettings
    End Select
    Exit Sub
Fail:
    mBusy = False
    ShowError "Something went wrong."
    Status "Ready"
End Sub

' Ctrl+V pastes a screenshot (first tab) or documents (second tab). Returns True when handled.
Public Function OnKey(ByVal key As String, ByVal keyCode As Long, ByVal shift As Integer) As Boolean
    If mBusy Then Exit Function
    If keyCode <> 86 Or (shift And 2) = 0 Then Exit Function
    If key = "case" Or key = "case2" Then Exit Function   ' normal paste in the text boxes
    On Error GoTo Fail
    If mp.Value = 0 Then
        PasteScreenshot False
        OnKey = True
    ElseIf mp.Value = 1 Then
        PasteDocuments
        OnKey = True
    End If
    Exit Function
Fail:
    ShowError "Something went wrong."
End Function

' ================================================================ building the window

Private Sub Hook(ByVal c As Object, ByVal key As String)
    Dim h As MICtl
    Set h = New MICtl
    h.Attach c, key, Me
    mHooks.Add h
End Sub

Private Function NewCtl(ByVal parent As Object, ByVal progId As String, ByVal key As String, ByVal l As Single, _
                        ByVal t As Single, ByVal w As Single, ByVal h As Single, Optional ByVal caption As String = "") _
                        As Object
    Dim c As Object
    Set c = parent.Controls.Add(progId)
    If w < 10 Then w = 10
    If h < 8 Then h = 8
    c.Left = l
    c.Top = t
    c.Width = w
    c.Height = h
    On Error Resume Next
    c.Font.Name = "Segoe UI"
    c.Font.Size = 9
    If Len(caption) > 0 Then c.Caption = caption
    On Error GoTo 0
    If Len(key) > 0 Then Hook c, key
    Set NewCtl = c
End Function

Private Function NewLabel(ByVal parent As Object, ByVal text As String, ByVal l As Single, ByVal t As Single, _
                          ByVal w As Single, ByVal h As Single, Optional ByVal isBold As Boolean = False, _
                          Optional ByVal key As String = "") As Object
    Dim c As Object
    Set c = NewCtl(parent, "Forms.Label.1", key, l, t, w, h)
    c.Caption = text
    c.BackStyle = 0   ' transparent
    c.WordWrap = True
    c.Font.Bold = isBold
    Set NewLabel = c
End Function

Private Function NewButton(ByVal parent As Object, ByVal key As String, ByVal caption As String, ByVal l As Single, _
                           ByVal t As Single, ByVal w As Single, Optional ByVal accent As Boolean = False) As Object
    Dim c As Object
    Set c = NewCtl(parent, "Forms.CommandButton.1", key, l, t, w, 20, caption)
    If accent Then
        c.BackColor = RGB(14, 116, 144)
        c.ForeColor = RGB(255, 255, 255)
        c.Font.Bold = True
    End If
    Set NewButton = c
End Function

Private Function NewList(ByVal parent As Object, ByVal key As String, ByVal l As Single, ByVal t As Single, _
                         ByVal w As Single, ByVal h As Single, ByVal columns As Long, ByVal widths As String) As Object
    Dim c As Object
    Set c = NewCtl(parent, "Forms.ListBox.1", key, l, t, w, h)
    c.ColumnCount = columns
    If Len(widths) > 0 Then c.ColumnWidths = widths
    c.IntegralHeight = False
    Set NewList = c
End Function

Private Function MaxS(ByVal a As Single, ByVal b As Single) As Single
    If a > b Then MaxS = a Else MaxS = b
End Function

Private Sub BuildWindow()
    Dim w As Single, h As Single, c As Object, pw As Single
    w = mForm.InsideWidth
    h = mForm.InsideHeight
    Set c = NewCtl(mForm, "Forms.Label.1", "", 0, 0, w, 40)
    c.BackStyle = 1
    c.BackColor = RGB(14, 116, 144)
    Set c = NewLabel(mForm, APP_NAME, 12, 3, 300, 22, True)
    c.Font.Size = 14
    c.ForeColor = RGB(255, 255, 255)
    Set c = NewLabel(mForm, "Fraud package evidence: screenshots -> CASE,MOREINFO.pdf or Excel, saved to your folders", _
                     12, 23, w - 24, 14)
    c.ForeColor = RGB(238, 242, 247)
    Set lblStatus = NewLabel(mForm, "Ready", 8, h - 16, w / 2, 14)
    Set c = NewLabel(mForm, APP_AUTHOR & "   |   v" & APP_VERSION & "   |   Works offline", w / 2, h - 16, w / 2 - 8, 14)
    c.TextAlign = 3   ' right
    c.ForeColor = RGB(91, 107, 117)
    Set mp = NewCtl(mForm, "Forms.MultiPage.1", "", 6, 44, w - 12, h - 44 - 20)
    Do While mp.Pages.Count < 3
        mp.Pages.Add
    Loop
    mp.Pages(0).Caption = "MoreInfo package"
    mp.Pages(1).Caption = "No Pay Decision Letter & documents"
    mp.Pages(2).Caption = "Folders & options"
    pw = mp.Width - 14
    BuildPackagePage mp.Pages(0), pw
    BuildDocumentsPage mp.Pages(1), pw
    BuildSettingsPage mp.Pages(2), pw
    mp.Value = 0
End Sub

Private Sub Scrollable(ByVal page As Object, ByVal contentHeight As Single)
    page.ScrollBars = 2              ' vertical, when the window is smaller than the content
    page.KeepScrollBarsVisible = 0
    page.ScrollHeight = contentHeight
End Sub

Private Sub BuildPackagePage(ByVal pg As Object, ByVal pw As Single)
    Dim y As Single, c As Object, listW As Single
    y = 6
    NewLabel pg, "Case #", 6, y + 3, 40, 14
    Set txtCase = NewCtl(pg, "Forms.TextBox.1", "case", 48, y, 150, 18)
    NewLabel pg, "Analyst", 212, y + 3, 44, 14
    Set txtAnalyst = NewCtl(pg, "Forms.TextBox.1", "", 258, y, 180, 18)
    txtAnalyst.Text = GetPref("Analyst")

    y = 32
    NewLabel pg, "Output", 6, y, 100, 14, True
    Set optPdf = NewCtl(pg, "Forms.OptionButton.1", "mode", 12, y + 16, pw - 24, 16, _
                        "Word -> PDF (all screenshots, grouped by your sections)")
    Set optExcel = NewCtl(pg, "Forms.OptionButton.1", "mode", 12, y + 34, pw - 24, 16, _
                          "Excel (add an ""Additional info"" tab with the screenshots to the downloaded transaction file)")
    optPdf.GroupName = "output"
    optExcel.GroupName = "output"
    optPdf.Value = True
    NewLabel pg, "Transaction file", 24, y + 57, 80, 14
    Set txtExcel = NewCtl(pg, "Forms.TextBox.1", "", 104, y + 54, MaxS(80, pw - 210), 18)
    txtExcel.Locked = True
    Set btnExcel = NewButton(pg, "excel", "Browse...", pw - 98, y + 53, 92)

    y = 112
    NewLabel pg, "Screenshots", 6, y, 100, 14, True
    y = 128
    NewLabel pg, "Section", 6, y + 3, 40, 14
    Set cboSection = NewCtl(pg, "Forms.ComboBox.1", "section", 48, y, 170, 18)
    cboSection.Style = 2   ' pick from the list
    NewButton pg, "addsection", "+", 222, y - 1, 22
    NewButton pg, "paste", "Paste screenshot (Ctrl+V)", 250, y - 1, 150, True
    NewButton pg, "addimages", "Add image files...", 406, y - 1, 110
    Set chkAuto = NewCtl(pg, "Forms.CheckBox.1", "auto", 6, y + 24, 420, 16, _
                         "Auto-add every new screenshot copied (Win+Shift+S)")

    y = 172
    listW = MaxS(200, pw - 260)
    NewLabel pg, "#", 10, y, 20, 12
    NewLabel pg, "Section", 30, y, 120, 12
    NewLabel pg, "Caption", 172, y, 200, 12
    NewLabel pg, "Preview", listW + 14, y, 100, 12
    Set lstShots = NewList(pg, "shots", 6, y + 14, listW, 118, 3, "22;142;400")
    Set imgPreview = NewCtl(pg, "Forms.Image.1", "", listW + 14, y + 14, MaxS(60, pw - listW - 20), 118)
    imgPreview.PictureSizeMode = 3   ' zoom
    imgPreview.BorderStyle = 1
    imgPreview.BackColor = RGB(255, 255, 255)

    y = 308
    NewButton pg, "caption", "Caption...", 6, y, 70
    NewButton pg, "remove", "Remove", 80, y, 60
    NewButton pg, "up", "Up", 144, y, 40
    NewButton pg, "down", "Down", 188, y, 44
    NewButton pg, "previewpdf", "Preview MoreInfo (PDF)", 236, y, 140

    y = 334
    Set lblReminder = NewLabel(pg, "", 6, y, pw - 12, 28, True, "reminder")
    lblReminder.BackStyle = 1

    y = 368
    NewButton pg, "create", "Create and save", 6, y, 120, True
    NewButton pg, "newcase", "New case", 132, y, 80
    NewButton pg, "openout", "Open output folder", 218, y, 120
    Set txtResult = NewCtl(pg, "Forms.TextBox.1", "", 6, y + 26, pw - 12, 66)
    txtResult.MultiLine = True
    txtResult.WordWrap = True
    txtResult.ScrollBars = 2
    txtResult.Locked = True
    Scrollable pg, y + 98
End Sub

Private Sub BuildDocumentsPage(ByVal pg As Object, ByVal pw As Single)
    Dim y As Single, c As Object
    y = 6
    NewLabel pg, "Case #", 6, y + 3, 40, 14
    Set txtCase2 = NewCtl(pg, "Forms.TextBox.1", "case2", 48, y, 150, 18)
    y = 30
    NewLabel pg, "Add the No Pay Decision Letter and any other case documents (Digital Footprints, Web extractions, " & _
        "Voice Match, Approvals...). Word files and images are saved as PDF; PDF, Excel, text and email files keep " & _
        "their format. They are named CASE,MOREINFO with the next number (CASE,MOREINFO1, CASE,MOREINFO2...) and " & _
        "uploaded with the MoreInfo package, or on their own with ""Upload documents only"".", 6, y, pw - 12, 40

    y = 76
    NewLabel pg, "No Pay Decision Letter from your template", 6, y, 300, 14, True
    y = 92
    NewLabel pg, "Template", 6, y + 3, 48, 14
    Set cboTemplate = NewCtl(pg, "Forms.ComboBox.1", "template", 56, y, 220, 18)
    cboTemplate.Style = 2
    NewButton pg, "addtpl", "Add template (.docx)...", 282, y - 1, 124
    NewButton pg, "renametpl", "Rename...", 410, y - 1, 62
    NewButton pg, "removetpl", "Remove", 476, y - 1, 56
    NewButton pg, "fill", "Fill in the letter...", MaxS(536, pw - 128), y - 1, 122, True
    Set lblTplInfo = NewLabel(pg, "", 6, y + 24, pw - 12, 26)
    lblTplInfo.ForeColor = RGB(91, 107, 117)

    y = 146
    NewButton pg, "browsedocs", "Browse PC...", 6, y, 80, True
    NewButton pg, "pastedocs", "Paste (Ctrl+V)", 90, y, 86
    NewButton pg, "removedoc", "Remove", 180, y, 60
    NewButton pg, "toggleletter", "Mark / unmark as decision letter", 244, y, 176
    NewButton pg, "previewdoc", "Preview", 424, y, 60
    NewButton pg, "uploaddocs", "Upload documents only", MaxS(490, pw - 136), y, 130
    y = 170
    Set c = NewLabel(pg, "Tip: copy files in File Explorer (Ctrl+C) and press Paste. A screenshot or the text of an " & _
                     "email can be pasted too. Double-click the letter to edit it again.", 6, y, pw - 12, 14)
    c.ForeColor = RGB(91, 107, 117)
    y = 190
    NewLabel pg, "#", 10, y, 20, 12
    NewLabel pg, "File", 30, y, 200, 12
    NewLabel pg, "Type", 362, y, 50, 12
    NewLabel pg, "Saved as", 412, y, 70, 12
    NewLabel pg, "Goes to", 482, y, 150, 12
    Set lstDocs = NewList(pg, "docs", 6, y + 14, pw - 12, 190, 5, "22;330;50;70;160")
    Scrollable pg, y + 210
End Sub

Private Sub BuildSettingsPage(ByVal pg As Object, ByVal pw As Single)
    Dim y As Single, bx As Single, c As Object
    bx = pw - 100
    y = 6
    NewLabel pg, "MoreInfo & documents folder (one folder)", 6, y, 400, 14, True
    Set txtFolder = NewCtl(pg, "Forms.TextBox.1", "", 6, y + 16, bx - 12, 18)
    NewButton pg, "browsefolder", "Browse...", bx, y + 15, 92

    y = 48
    NewLabel pg, "No Pay Decision Letter folders (the letter is saved in each one, for example 2)", 6, y, 500, 14, True
    Set lstLetterFolders = NewList(pg, "letterfolders", 6, y + 16, bx - 12, 64, 1, "")
    NewButton pg, "addlf", "Add folder...", bx, y + 16, 92
    NewButton pg, "addlp", "Add path...", bx, y + 38, 92
    NewButton pg, "removelf", "Remove", bx, y + 60, 92
    Set c = NewLabel(pg, "Only the decision letter goes to these folders. If the list is empty, the letter goes to " & _
                     "the MoreInfo folder.", 6, y + 84, pw - 12, 14)
    c.ForeColor = RGB(91, 107, 117)

    y = 154
    NewLabel pg, "Sections (your own names and order; saved for every new case)", 6, y, 500, 14, True
    Set lstSections = NewList(pg, "sections", 6, y + 16, bx - 12, 104, 1, "")
    NewButton pg, "addsec", "Add section...", bx, y + 16, 92
    NewButton pg, "renamesec", "Rename...", bx, y + 38, 92
    NewButton pg, "removesec", "Remove", bx, y + 60, 92
    NewButton pg, "secup", "Up", bx, y + 82, 44
    NewButton pg, "secdown", "Down", bx + 48, y + 82, 44
    Set c = NewLabel(pg, "The PDF and the Excel tab show the screenshots grouped by these sections, in this order. " & _
                     "You can also add a section with + next to the section list.", 6, y + 124, pw - 12, 26)
    c.ForeColor = RGB(91, 107, 117)

    y = 306
    Set chkKeepDocx = NewCtl(pg, "Forms.CheckBox.1", "", 6, y, 300, 16, "Also save the Word (.docx) file")
    NewLabel pg, "File name after the case number", 6, y + 27, 170, 14
    Set txtBase = NewCtl(pg, "Forms.TextBox.1", "", 180, y + 24, 120, 18)
    NewButton pg, "savesettings", "Save options", 6, y + 52, 110, True
    Set c = NewLabel(pg, "Options and letter templates are kept for this Windows user (templates: " & _
                     TemplatesFolder() & ").", 6, y + 78, pw - 12, 26)
    c.ForeColor = RGB(91, 107, 117)
    Scrollable pg, y + 110
End Sub

' ================================================================ options

Private Sub LoadPrefs()
    mFolder = GetPref("Folder")
    Set mLetterFolders = GetList("LetterFolder")
    Set mSections = GetList("Section")
    Set mTplNames = GetList("TemplateName")
    Set mTplFiles = GetList("TemplateFile")
    mKeepDocx = GetPref("KeepDocx", "0") = "1"
    mBase = GetPref("Base", "MOREINFO")
    If Len(mBase) = 0 Then mBase = "MOREINFO"
End Sub

Private Sub SavePrefs()
    SetPref "Folder", mFolder
    SetList "LetterFolder", mLetterFolders
    SetList "Section", mSections
    SetList "TemplateName", mTplNames
    SetList "TemplateFile", mTplFiles
    If mKeepDocx Then SetPref "KeepDocx", "1" Else SetPref "KeepDocx", "0"
    SetPref "Base", mBase
End Sub

Private Sub RefreshAll()
    FillSections
    FillShots
    FillTemplates
    FillDocs
    FillSettings
    ModeChanged
    UpdateReminder
End Sub

Private Sub Status(ByVal msg As String)
    On Error Resume Next
    lblStatus.Caption = msg
    mForm.Repaint
End Sub

Private Function IndexIn(ByVal c As Collection, ByVal value As String) As Long
    Dim i As Long
    For i = 1 To c.Count
        If LCase$(c(i)) = LCase$(value) Then
            IndexIn = i
            Exit Function
        End If
    Next
End Function

Private Sub ReplaceAt(ByVal c As Collection, ByVal i As Long, ByVal value As String)
    c.Remove i
    If i > c.Count Then c.Add value Else c.Add value, , i
End Sub

Private Sub SwapAt(ByVal c As Collection, ByVal i As Long, ByVal j As Long)
    Dim a As String, b As String
    a = c(i)
    b = c(j)
    ReplaceAt c, i, b
    ReplaceAt c, j, a
End Sub

Private Function AskText(ByVal prompt As String, Optional ByVal initial As String = "", _
                         Optional ByRef cancelled As Boolean) As String
    Dim s As String
    s = InputBox(prompt, APP_NAME, initial)
    cancelled = (StrPtr(s) = 0)
    AskText = Trim$(s)
End Function

' ================================================================ tab 1: MoreInfo package

Private Sub SyncCase(ByVal src As Object, ByVal dst As Object)
    If mSyncing Then Exit Sub
    mSyncing = True
    If dst.Text <> src.Text Then dst.Text = src.Text
    mSyncing = False
End Sub

Private Sub ModeChanged()
    Dim isExcel As Boolean
    isExcel = (optExcel.Value = True)
    txtExcel.Enabled = isExcel
    btnExcel.Enabled = isExcel
End Sub

Private Sub PickExcel()
    Dim files As Collection
    Set files = PickFiles("Choose the transaction file", "Excel", "*.xlsx;*.xlsm;*.xls;*.csv", False)
    If files.Count > 0 Then txtExcel.Text = files(1)
End Sub

Private Function SectionIndex(ByVal name As String) As Long
    SectionIndex = IndexIn(mSections, name)
    If SectionIndex = 0 Then SectionIndex = 9999
End Function

Private Sub FillSections(Optional ByVal pick As String = "")
    Dim current As String, s As Variant, i As Long
    current = pick
    If Len(current) = 0 And cboSection.ListIndex >= 0 Then current = cboSection.Text
    cboSection.Clear
    lstSections.Clear
    For Each s In mSections
        cboSection.AddItem CStr(s)
        lstSections.AddItem CStr(s)
    Next
    If mSections.Count > 0 Then
        i = IndexIn(mSections, current)
        If i = 0 Then i = 1
        cboSection.ListIndex = i - 1
    End If
End Sub

Private Function NeedSection(ByVal quiet As Boolean) As Boolean
    If mSections.Count = 0 Then
        If quiet Then Exit Function
        Info "Create your first section (for example ""Customer profile""). Sections are saved for every new case."
        AddSection
    End If
    NeedSection = cboSection.ListIndex >= 0
End Function

Private Sub AddSection()
    Dim name As String, cancelled As Boolean
    name = AskText("Section name:", "", cancelled)
    If cancelled Or Len(name) = 0 Then Exit Sub
    If IndexIn(mSections, name) > 0 Then
        Warn "There is already a section called """ & name & """."
        Exit Sub
    End If
    mSections.Add name
    SavePrefs
    FillSections name
End Sub

Private Sub PasteScreenshot(ByVal quiet As Boolean)
    If Not NeedSection(quiet) Then Exit Sub
    If Not ClipboardHasImage() Then
        If Not quiet Then Warn "There is no image in the clipboard. Take a screenshot (Win+Shift+S or Print Screen) " & _
                               "and try again."
        Exit Sub
    End If
    mNextId = mNextId + 1
    gStep = "Pasting the screenshot"
    If PasteImageInto(mStore, mNextId) Then
        InsertShot mNextId, cboSection.Text
        Status "Screenshot added to """ & cboSection.Text & """ (" & mShotCount & " in total)"
    ElseIf Not quiet Then
        Warn "The clipboard image could not be pasted. Take the screenshot again and retry."
    End If
    gStep = ""
    mPollSeq = ClipboardSeq()
End Sub

Private Sub AddImages()
    Dim files As Collection, f As Variant
    If Not NeedSection(False) Then Exit Sub
    Set files = PickFiles("Add image files", "Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tif;*.tiff", True)
    For Each f In files
        mNextId = mNextId + 1
        gStep = "Adding " & FileNameOf(CStr(f))
        AddImageFileInto mStore, CStr(f), mNextId
        InsertShot mNextId, cboSection.Text
    Next
    gStep = ""
    If files.Count > 0 Then Status files.Count & " image(s) added to """ & cboSection.Text & """"
End Sub

Private Sub AutoChanged()
    If chkAuto.Value = True Then
        mPollSeq = ClipboardSeq()   ' what is already in the clipboard is not added
        StartPolling
        Status "Auto-add is on: every screenshot you copy (Win+Shift+S) goes to the selected section."
    Else
        Status "Auto-add is off."
    End If
End Sub

Private Sub InsertShot(ByVal id As Long, ByVal sec As String)
    Dim pos As Long, i As Long
    pos = mShotCount
    For i = 0 To mShotCount - 1
        If SectionIndex(mShotSec(i)) > SectionIndex(sec) Then
            pos = i
            Exit For
        End If
    Next
    ReDim Preserve mShotId(0 To mShotCount)
    ReDim Preserve mShotSec(0 To mShotCount)
    ReDim Preserve mShotCap(0 To mShotCount)
    For i = mShotCount To pos + 1 Step -1
        mShotId(i) = mShotId(i - 1)
        mShotSec(i) = mShotSec(i - 1)
        mShotCap(i) = mShotCap(i - 1)
    Next
    mShotId(pos) = id
    mShotSec(pos) = sec
    mShotCap(pos) = ""
    mShotCount = mShotCount + 1
    FillShots pos
End Sub

' Keeps the screenshots grouped in the order of the sections (after the sections are reordered).
Private Sub SortShots()
    Dim i As Long, j As Long, id As Long, sec As String, cap As String
    For i = 1 To mShotCount - 1
        id = mShotId(i)
        sec = mShotSec(i)
        cap = mShotCap(i)
        j = i - 1
        Do While j >= 0
            If SectionIndex(mShotSec(j)) <= SectionIndex(sec) Then Exit Do
            mShotId(j + 1) = mShotId(j)
            mShotSec(j + 1) = mShotSec(j)
            mShotCap(j + 1) = mShotCap(j)
            j = j - 1
        Loop
        mShotId(j + 1) = id
        mShotSec(j + 1) = sec
        mShotCap(j + 1) = cap
    Next
End Sub

Private Sub FillShots(Optional ByVal pick As Long = -1)
    Dim i As Long
    lstShots.Clear
    For i = 0 To mShotCount - 1
        lstShots.AddItem CStr(i + 1)
        lstShots.List(i, 1) = mShotSec(i)
        lstShots.List(i, 2) = mShotCap(i)
    Next
    If pick >= 0 And pick < mShotCount Then
        lstShots.ListIndex = pick
    Else
        ClearPreview
    End If
End Sub

Private Sub ClearPreview()
    On Error Resume Next
    Set imgPreview.Picture = Nothing
End Sub

Private Sub ShowPreview()
    Dim i As Long
    i = lstShots.ListIndex
    If i < 0 Or i >= mShotCount Then
        ClearPreview
        Exit Sub
    End If
    On Error Resume Next   ' the preview is only a help
    Set imgPreview.Picture = LoadPicture(ThumbnailFile(mStore, mShotId(i)))
End Sub

Private Function SelectedShot() As Long
    SelectedShot = lstShots.ListIndex
    If SelectedShot < 0 Or SelectedShot >= mShotCount Then
        Info "Select a screenshot first."
        SelectedShot = -1
    End If
End Function

Private Sub EditCaption()
    Dim i As Long, s As String, cancelled As Boolean
    i = SelectedShot()
    If i < 0 Then Exit Sub
    s = AskText("Caption for this screenshot (optional):", mShotCap(i), cancelled)
    If cancelled Then Exit Sub
    mShotCap(i) = s
    FillShots i
End Sub

Private Sub RemoveShot()
    Dim i As Long, k As Long
    i = SelectedShot()
    If i < 0 Then Exit Sub
    RemoveImageFrom mStore, mShotId(i)
    For k = i To mShotCount - 2
        mShotId(k) = mShotId(k + 1)
        mShotSec(k) = mShotSec(k + 1)
        mShotCap(k) = mShotCap(k + 1)
    Next
    mShotCount = mShotCount - 1
    If mShotCount = 0 Then
        Erase mShotId
        Erase mShotSec
        Erase mShotCap
    End If
    If i >= mShotCount Then i = mShotCount - 1
    FillShots i
End Sub

Private Sub MoveShot(ByVal stepBy As Long)
    Dim i As Long, j As Long, id As Long, sec As String, cap As String
    i = SelectedShot()
    If i < 0 Then Exit Sub
    j = i + stepBy
    If j < 0 Or j >= mShotCount Then Exit Sub
    If mShotSec(j) <> mShotSec(i) Then Exit Sub   ' screenshots move within their section
    id = mShotId(i): sec = mShotSec(i): cap = mShotCap(i)
    mShotId(i) = mShotId(j): mShotSec(i) = mShotSec(j): mShotCap(i) = mShotCap(j)
    mShotId(j) = id: mShotSec(j) = sec: mShotCap(j) = cap
    FillShots j
End Sub

Private Sub PreviewMoreInfo()
    Dim d As Object, pdf As String
    If mShotCount = 0 Then
        Warn "Add at least one screenshot."
        Exit Sub
    End If
    Status "Creating the preview..."
    Set d = BuildMoreInfoDoc(mStore, CleanCase(txtCase.Text), txtAnalyst.Text, mShotId, mShotSec, mShotCap, mShotCount)
    pdf = JoinPath(NewWorkFolder("preview"), "MoreInfo preview.pdf")
    ExportPdf d, pdf
    d.Close SaveChanges:=False
    gStep = ""
    OpenFile pdf
    Status "Preview opened."
End Sub

Private Sub UpdateReminder()
    If mDocCount = 0 Then
        lblReminder.Caption = "! Don't forget to upload the No Pay Decision Letter and other documents as applicable " & _
            "(Digital Footprints, Web extractions, Voice Match, Approvals, etc). Click here to add them."
        lblReminder.BackColor = RGB(255, 244, 214)
        lblReminder.ForeColor = RGB(138, 97, 0)
    Else
        lblReminder.Caption = "OK: " & mDocCount & " case document(s) ready in ""No Pay Decision Letter & documents"". " & _
            "They will be uploaded with the MoreInfo."
        lblReminder.BackColor = RGB(231, 244, 232)
        lblReminder.ForeColor = RGB(46, 125, 50)
    End If
End Sub

Private Sub NewCase()
    If mShotCount > 0 Or mDocCount > 0 Then
        If Not Ask("Clear the screenshots and documents to start a new case?") Then Exit Sub
    End If
    mStore.Content.Delete
    mStore.Saved = True
    mShotCount = 0
    Erase mShotId
    Erase mShotSec
    Erase mShotCap
    mDocCount = 0
    Erase mDocPath
    Erase mDocLetter
    Erase mDocTpl
    Erase mDocVals
    Erase mDocPrev
    txtCase.Text = ""
    txtExcel.Text = ""
    txtResult.Text = ""
    FillShots
    FillDocs
    UpdateReminder
    Status "New case."
End Sub

Private Sub OpenOutput()
    Dim folder As String
    folder = mLastOutput
    If Len(folder) = 0 Then folder = mFolder
    If Len(folder) > 0 Then
        If Fso.FolderExists(folder) Then OpenFolder folder
    End If
End Sub

Private Sub CreatePackageNow()
    Dim answer As VbMsgBoxResult
    If optExcel.Value = True Then
        If Len(txtExcel.Text) = 0 Then
            Warn "Choose the transaction Excel file first."
            Exit Sub
        End If
    ElseIf mShotCount = 0 Then
        Warn "Add at least one screenshot."
        Exit Sub
    End If
    If mDocCount = 0 Then   ' reminder: the MoreInfo alone is not the complete package
        answer = MsgBox("Don't forget to upload the No Pay Decision Letter and other documents as applicable " & _
            "(Digital Footprints, Web extractions, Voice Match, Approvals, etc)." & vbCrLf & vbCrLf & _
            "Yes = upload the MoreInfo now without documents" & vbCrLf & "No = go to the documents tab first", _
            vbYesNoCancel + vbExclamation, APP_NAME)
        If answer = vbCancel Then Exit Sub
        If answer = vbNo Then
            mp.Value = 1
            Exit Sub
        End If
    End If
    RunUpload True
End Sub

Private Sub RunUpload(ByVal includeMoreInfo As Boolean)
    Dim caseNo As String, i As Long, answer As VbMsgBoxResult, needsMain As Boolean, report As String, mode As String
    caseNo = CleanCase(txtCase.Text)
    If Len(caseNo) = 0 Then
        Warn "Enter the case number."
        Exit Sub
    End If
    For i = 0 To mDocCount - 1   ' control: the letter is checked before it is uploaded
        If Len(mDocTpl(i)) > 0 And Not mDocPrev(i) Then
            answer = MsgBox("The No Pay Decision Letter has not been previewed yet. Check it before it is uploaded." & _
                vbCrLf & vbCrLf & "Yes = open the preview now" & vbCrLf & "No = upload without previewing", _
                vbYesNoCancel + vbExclamation, APP_NAME)
            If answer = vbCancel Then Exit Sub
            If answer = vbYes Then
                mDocPrev(i) = True
                mp.Value = 1
                PreviewDoc i
                Exit Sub
            End If
            Exit For
        End If
    Next
    If Not includeMoreInfo And mDocCount = 0 Then
        Warn "Add at least one document first."
        Exit Sub
    End If
    needsMain = includeMoreInfo
    For i = 0 To mDocCount - 1
        If Not mDocLetter(i) Then needsMain = True
    Next
    If (needsMain And Len(mFolder) = 0) Or (Len(mFolder) = 0 And mLetterFolders.Count = 0) Then
        Warn "Choose the MoreInfo & documents folder (and the letter folders) in ""Folders & options"" first."
        mp.Value = 2
        Exit Sub
    End If
    SetPref "Analyst", txtAnalyst.Text
    If optExcel.Value = True Then mode = "excel" Else mode = "pdf"
    mBusy = True
    Status "Creating and saving... please wait."
    mForm.MousePointer = 11   ' hourglass
    On Error GoTo Fail
    report = CreatePackage(mStore, caseNo, txtAnalyst.Text, mShotId, mShotSec, mShotCap, mShotCount, mDocPath, _
                           mDocLetter, mDocCount, mFolder, mLetterFolders, mode, txtExcel.Text, mBase, mKeepDocx, _
                           includeMoreInfo)
    On Error GoTo 0
    mBusy = False
    mForm.MousePointer = 0
    mPollSeq = ClipboardSeq()
    txtResult.Text = report
    mLastOutput = mFolder
    If Len(mLastOutput) = 0 And mLetterFolders.Count > 0 Then mLastOutput = mLetterFolders(1)
    Status "Done."
    If InStr(1, report, "Could not save") > 0 Or InStr(1, report, "were kept here") > 0 Then
        MsgBox report, vbExclamation, "Package ready"
    Else
        MsgBox report, vbInformation, "Package ready"
    End If
    Exit Sub
Fail:
    mBusy = False
    mForm.MousePointer = 0
    mPollSeq = ClipboardSeq()
    ShowError "The package could not be created."
    Status "Ready"
End Sub

' ================================================================ tab 2: letter and documents

Private Function TemplatePath(ByVal name As String) As String
    Dim i As Long
    i = IndexIn(mTplNames, name)
    If i > 0 Then TemplatePath = JoinPath(TemplatesFolder(), mTplFiles(i))
End Function

Private Sub FillTemplates(Optional ByVal pick As String = "")
    Dim current As String, s As Variant, i As Long
    current = pick
    If Len(current) = 0 And cboTemplate.ListIndex >= 0 Then current = cboTemplate.Text
    cboTemplate.Clear
    For Each s In mTplNames
        cboTemplate.AddItem CStr(s)
    Next
    If mTplNames.Count > 0 Then
        i = IndexIn(mTplNames, current)
        If i = 0 Then i = 1
        cboTemplate.ListIndex = i - 1
    End If
    ShowTemplateInfo
End Sub

Private Sub ShowTemplateInfo()
    If cboTemplate.ListIndex < 0 Then
        lblTplInfo.Caption = "No template yet: add the blank letters (.docx), one per product or language, and give " & _
            "each one a name. They are kept for every new case."
    Else
        lblTplInfo.Caption = """" & cboTemplate.Text & """: choose the right template for the case, then ""Fill in " & _
            "the letter..."". The letter is saved as PDF in the letter folders when you upload."
    End If
End Sub

Private Function AskTemplateName(ByVal initial As String, ByVal current As String) As String
    Dim name As String, cancelled As Boolean
    name = AskText("Name for this letter template (for example ""Credit card - English"" or " & _
                   """Carte de debit - French""):", initial, cancelled)
    If cancelled Or Len(name) = 0 Then Exit Function
    If LCase$(name) <> LCase$(current) And IndexIn(mTplNames, name) > 0 Then
        Warn "There is already a template called """ & name & """."
        Exit Function
    End If
    AskTemplateName = name
End Function

Private Sub AddTemplate()
    Dim files As Collection, path As String, fields As Collection, lang As String, name As String, n As Long
    Dim dest As String
    Set files = PickFiles("Add a blank letter template", "Word templates", "*.docx;*.dotx;*.docm", False)
    If files.Count = 0 Then Exit Sub
    path = files(1)
    Status "Reading the template..."
    Set fields = ScanTemplate(path, lang)
    gStep = ""
    If fields.Count = 0 Then
        Warn "No fields were found in this template. Use Word content controls (text, drop-down, date) or " & _
             "placeholders like [Customer Name]."
        Exit Sub
    End If
    name = AskTemplateName(StemOf(path), "")
    If Len(name) = 0 Then Exit Sub
    n = 1
    Do While Fso.FileExists(JoinPath(TemplatesFolder(), "template_" & n & FileExt(path)))
        n = n + 1
    Loop
    dest = JoinPath(TemplatesFolder(), "template_" & n & FileExt(path))
    Fso.CopyFile path, dest, True
    mTplNames.Add name
    mTplFiles.Add FileNameOf(dest)
    SavePrefs
    FillTemplates name
    Status """" & name & """ added: " & fields.Count & " field(s) to fill."
End Sub

Private Sub RenameTemplate()
    Dim i As Long, name As String
    i = cboTemplate.ListIndex + 1
    If i < 1 Then Exit Sub
    name = AskTemplateName(mTplNames(i), mTplNames(i))
    If Len(name) = 0 Then Exit Sub
    ReplaceAt mTplNames, i, name
    SavePrefs
    FillTemplates name
End Sub

Private Sub RemoveTemplate()
    Dim i As Long
    i = cboTemplate.ListIndex + 1
    If i < 1 Then Exit Sub
    If Not Ask("Remove the template """ & mTplNames(i) & """ from MoreInfo Pilot?") Then Exit Sub
    On Error Resume Next
    Fso.DeleteFile JoinPath(TemplatesFolder(), mTplFiles(i)), True
    On Error GoTo 0
    mTplNames.Remove i
    mTplFiles.Remove i
    SavePrefs
    FillTemplates
End Sub

Private Sub FillLetter()
    If cboTemplate.ListIndex < 0 Then
        Info "No template yet: add the blank letters (.docx), one per product or language, and give each one a name."
        Exit Sub
    End If
    OpenLetter cboTemplate.Text, Nothing
End Sub

Private Sub OpenLetter(ByVal tplName As String, ByVal oldValues As Object)
    Dim path As String, fields As Collection, lang As String, dlg As MILetter
    path = TemplatePath(tplName)
    If Len(path) = 0 Or Not Fso.FileExists(path) Then
        Warn "The template """ & tplName & """ is no longer available. Add it again."
        Exit Sub
    End If
    Status "Reading the template..."
    Set fields = ScanTemplate(path, lang)
    gStep = ""
    Status "Ready"
    If fields.Count = 0 Then
        Warn "No fields were found in this template."
        Exit Sub
    End If
    Set dlg = New MILetter
    If dlg.Run(tplName, path, fields, oldValues, txtCase.Text, txtAnalyst.Text, lang) Then
        LetterReady tplName, path, dlg.Values, dlg.Previewed
    End If
End Sub

' The filled letter goes first in the documents (one letter per case); it is saved as PDF when uploaded.
Private Sub LetterReady(ByVal tplName As String, ByVal path As String, ByVal values As Object, ByVal previewed As Boolean)
    Dim dest As String, i As Long
    Status "Filling in the letter..."
    dest = FillTemplate(path, values, JoinPath(NewWorkFolder("letter"), "No Pay Decision Letter - " & _
                        SafeFileName(tplName) & ".docx"))
    gStep = ""
    For i = mDocCount - 1 To 0 Step -1
        If Len(mDocTpl(i)) > 0 Then RemoveDoc i
    Next
    InsertDoc 0, dest, True, tplName, values, previewed
    FillDocs 0
    UpdateReminder
    mp.Value = 1
    Status "Decision letter added to the documents (it will be saved as PDF in the letter folders)."
End Sub

Private Sub InsertDoc(ByVal pos As Long, ByVal path As String, ByVal isLetter As Boolean, ByVal tplName As String, _
                      ByVal values As Object, ByVal previewed As Boolean)
    Dim i As Long
    ReDim Preserve mDocPath(0 To mDocCount)
    ReDim Preserve mDocLetter(0 To mDocCount)
    ReDim Preserve mDocTpl(0 To mDocCount)
    ReDim Preserve mDocVals(0 To mDocCount)
    ReDim Preserve mDocPrev(0 To mDocCount)
    For i = mDocCount To pos + 1 Step -1
        mDocPath(i) = mDocPath(i - 1)
        mDocLetter(i) = mDocLetter(i - 1)
        mDocTpl(i) = mDocTpl(i - 1)
        If IsObject(mDocVals(i - 1)) Then Set mDocVals(i) = mDocVals(i - 1) Else mDocVals(i) = Empty
        mDocPrev(i) = mDocPrev(i - 1)
    Next
    mDocPath(pos) = path
    mDocLetter(pos) = isLetter
    mDocTpl(pos) = tplName
    If values Is Nothing Then mDocVals(pos) = Empty Else Set mDocVals(pos) = values
    mDocPrev(pos) = previewed
    mDocCount = mDocCount + 1
End Sub

Private Sub RemoveDoc(ByVal pos As Long)
    Dim i As Long
    For i = pos To mDocCount - 2
        mDocPath(i) = mDocPath(i + 1)
        mDocLetter(i) = mDocLetter(i + 1)
        mDocTpl(i) = mDocTpl(i + 1)
        If IsObject(mDocVals(i + 1)) Then Set mDocVals(i) = mDocVals(i + 1) Else mDocVals(i) = Empty
        mDocPrev(i) = mDocPrev(i + 1)
    Next
    mDocCount = mDocCount - 1
    If mDocCount = 0 Then
        Erase mDocPath
        Erase mDocLetter
        Erase mDocTpl
        Erase mDocVals
        Erase mDocPrev
    End If
End Sub

Private Sub AddDocuments(ByVal paths As Collection)
    Dim p As Variant
    For Each p In paths
        If Len(p) > 0 Then InsertDoc mDocCount, CStr(p), False, "", Nothing, False
    Next
    FillDocs mDocCount - 1
    UpdateReminder
    If paths.Count > 0 Then Status paths.Count & " document(s) added"
End Sub

Private Sub FillDocs(Optional ByVal pick As Long = -1)
    Dim i As Long, ext As String, dest As String, n As Long
    lstDocs.Clear
    n = mLetterFolders.Count
    For i = 0 To mDocCount - 1
        ext = FileExt(mDocPath(i))
        lstDocs.AddItem CStr(i + 1)
        If mDocLetter(i) Then
            lstDocs.List(i, 1) = "[Letter] " & FileNameOf(mDocPath(i))
            If n > 0 Then dest = "Letter folders (" & n & ")" Else dest = "MoreInfo folder"
        Else
            lstDocs.List(i, 1) = FileNameOf(mDocPath(i))
            dest = "MoreInfo folder"
        End If
        lstDocs.List(i, 2) = UCase$(Mid$(ext, 2))
        If DocumentTarget(mDocPath(i)) = ".pdf" Then lstDocs.List(i, 3) = "PDF" Else lstDocs.List(i, 3) = "Same format"
        lstDocs.List(i, 4) = dest
    Next
    If pick >= 0 And pick < mDocCount Then lstDocs.ListIndex = pick
End Sub

Private Function SelectedDoc() As Long
    SelectedDoc = lstDocs.ListIndex
    If SelectedDoc < 0 Or SelectedDoc >= mDocCount Then
        Info "Select a document in the list first."
        SelectedDoc = -1
    End If
End Function

Private Sub BrowseDocuments()
    AddDocuments PickFiles("Add case documents", "Case documents", "*.pdf;*.docx;*.doc;*.rtf;*.odt;*.xlsx;*.xlsm;" & _
                           "*.xls;*.csv;*.txt;*.msg;*.eml;*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tif;*.tiff", True)
End Sub

Private Sub PasteDocuments()
    Dim c As New Collection
    If ClipboardHasFiles() Then
        Set c = ClipboardFiles()
    ElseIf ClipboardHasImage() Then
        c.Add PastedDocument(True)
    ElseIf ClipboardHasText() Then
        c.Add PastedDocument(False)
    Else
        Warn "There is nothing to paste. Copy a file in File Explorer, an image or the text of an email and try again."
        Exit Sub
    End If
    gStep = ""
    mPollSeq = ClipboardSeq()
    AddDocuments c
End Sub

Private Sub RemoveSelectedDoc()
    Dim i As Long
    i = SelectedDoc()
    If i < 0 Then Exit Sub
    RemoveDoc i
    FillDocs i - 1
    UpdateReminder
End Sub

Private Sub ToggleLetter()
    Dim i As Long
    i = SelectedDoc()
    If i < 0 Then Exit Sub
    mDocLetter(i) = Not mDocLetter(i)
    FillDocs i
End Sub

Private Sub PreviewDocument()
    Dim i As Long
    i = SelectedDoc()
    If i < 0 Then Exit Sub
    PreviewDoc i
End Sub

Private Sub PreviewDoc(ByVal i As Long)
    Dim pdf As String
    Status "Opening the preview..."
    If Len(mDocTpl(i)) > 0 Then mDocPrev(i) = True
    If DocumentTarget(mDocPath(i)) = ".pdf" And FileExt(mDocPath(i)) <> ".pdf" Then
        pdf = JoinPath(NewWorkFolder("preview"), StemOf(mDocPath(i)) & ".pdf")
        PrepareDocument mDocPath(i), pdf
        gStep = ""
        OpenFile pdf
    Else
        OpenFile mDocPath(i)
    End If
    Status "Preview opened."
End Sub

Private Sub EditOrPreview()
    Dim i As Long
    i = lstDocs.ListIndex
    If i < 0 Or i >= mDocCount Then Exit Sub
    If Len(mDocTpl(i)) > 0 And IsObject(mDocVals(i)) Then
        OpenLetter mDocTpl(i), mDocVals(i)   ' edit the letter again
    Else
        PreviewDoc i
    End If
End Sub

' ================================================================ tab 3: folders and options

Private Sub FillSettings()
    Dim f As Variant
    txtFolder.Text = mFolder
    lstLetterFolders.Clear
    For Each f In mLetterFolders
        lstLetterFolders.AddItem CStr(f)
    Next
    chkKeepDocx.Value = mKeepDocx
    txtBase.Text = mBase
End Sub

Private Sub BrowseMainFolder()
    Dim p As String
    p = PickFolder("MoreInfo & documents folder")
    If Len(p) = 0 Then Exit Sub
    mFolder = NoSlash(p)
    SavePrefs
    FillSettings
    FillDocs
    Status "Folder saved."
End Sub

Private Sub AddLetterFolder(ByVal typed As Boolean)
    Dim p As String, cancelled As Boolean
    If typed Then
        p = AskText("Folder path (for example \\server\Fraud\Letters):", "", cancelled)
        If cancelled Then Exit Sub
    Else
        p = PickFolder("No Pay Decision Letter folder")
    End If
    p = NoSlash(p)
    If Len(p) = 0 Then Exit Sub
    If IndexIn(mLetterFolders, p) > 0 Then Exit Sub
    If Not Fso.FolderExists(p) Then
        If Not Ask("The folder """ & p & """ cannot be reached now. Add it anyway?") Then Exit Sub
    End If
    mLetterFolders.Add p
    SavePrefs
    FillSettings
    FillDocs
End Sub

Private Sub RemoveLetterFolder()
    Dim i As Long
    i = lstLetterFolders.ListIndex + 1
    If i < 1 Then Exit Sub
    mLetterFolders.Remove i
    SavePrefs
    FillSettings
    FillDocs
End Sub

Private Function SelectedSection() As Long
    SelectedSection = lstSections.ListIndex + 1
    If SelectedSection < 1 Then Info "Select a section in the list first."
End Function

Private Sub RenameSection()
    Dim i As Long, name As String, old As String, k As Long, cancelled As Boolean
    i = SelectedSection()
    If i < 1 Then Exit Sub
    old = mSections(i)
    name = AskText("Section name:", old, cancelled)
    If cancelled Or Len(name) = 0 Or name = old Then Exit Sub
    If LCase$(name) <> LCase$(old) And IndexIn(mSections, name) > 0 Then
        Warn "There is already a section called """ & name & """."
        Exit Sub
    End If
    ReplaceAt mSections, i, name
    For k = 0 To mShotCount - 1
        If mShotSec(k) = old Then mShotSec(k) = name
    Next
    SavePrefs
    FillSections name
    FillShots
    lstSections.ListIndex = i - 1
End Sub

Private Sub RemoveSection()
    Dim i As Long, k As Long
    i = SelectedSection()
    If i < 1 Then Exit Sub
    For k = 0 To mShotCount - 1
        If mShotSec(k) = mSections(i) Then
            Warn """" & mSections(i) & """ has screenshots in the current case. Move or remove them first."
            Exit Sub
        End If
    Next
    mSections.Remove i
    SavePrefs
    FillSections
End Sub

Private Sub MoveSection(ByVal stepBy As Long)
    Dim i As Long, j As Long
    i = SelectedSection()
    If i < 1 Then Exit Sub
    j = i + stepBy
    If j < 1 Or j > mSections.Count Then Exit Sub
    SwapAt mSections, i, j
    SavePrefs
    SortShots
    FillSections
    FillShots
    lstSections.ListIndex = j - 1
End Sub

Private Sub SaveSettings()
    Dim baseText As String
    mFolder = NoSlash(txtFolder.Text)
    baseText = CleanCase(txtBase.Text)
    If Len(baseText) = 0 Then baseText = "MOREINFO"
    mBase = baseText
    mKeepDocx = (chkKeepDocx.Value = True)
    SavePrefs
    FillSettings
    FillDocs
    Info "Options saved."
End Sub
