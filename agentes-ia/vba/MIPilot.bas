Attribute VB_Name = "MIPilot"
' MoreInfo Pilot for Word - Created by Jose Vasquez.
' Builds the "MoreInfo" evidence of a fraud package (screenshots -> CASE,MOREINFO.pdf or an "Additional info" tab
' in the transaction Excel), fills the No Pay Decision Letter from the bank's Word templates and saves every
' document of the case in the chosen folders, numbered CASE,MOREINFO1, CASE,MOREINFO2... Works offline.
'
' Start: macro MoreInfoPilot (button "MoreInfo Pilot" on the Add-ins tab when the template is in Word's STARTUP folder).
Option Explicit

Public Const APP_NAME As String = "MoreInfo Pilot"
Public Const APP_AUTHOR As String = "Created by Jose Vasquez"
Public Const APP_VERSION As String = "1.0 (Word)"
Public Const EXCEL_SHEET As String = "Additional info"
Private Const REG_APP As String = "MoreInfoPilot"
Private Const REG_SECTION As String = "Settings"

Private Declare PtrSafe Function GetClipboardSequenceNumber Lib "user32" () As Long
Private Declare PtrSafe Function IsClipboardFormatAvailable Lib "user32" (ByVal wFormat As Long) As Long
Private Declare PtrSafe Function OpenClipboard Lib "user32" (ByVal hWnd As LongPtr) As Long
Private Declare PtrSafe Function CloseClipboard Lib "user32" () As Long
Private Declare PtrSafe Function GetClipboardData Lib "user32" (ByVal wFormat As Long) As LongPtr
Private Declare PtrSafe Function DragQueryFileW Lib "shell32" (ByVal hDrop As LongPtr, ByVal iFile As Long, _
    ByVal lpszFile As LongPtr, ByVal cch As Long) As Long
Private Declare PtrSafe Function GetSystemMetrics Lib "user32" (ByVal nIndex As Long) As Long
Private Declare PtrSafe Function GetDC Lib "user32" (ByVal hWnd As LongPtr) As LongPtr
Private Declare PtrSafe Function ReleaseDC Lib "user32" (ByVal hWnd As LongPtr, ByVal hDC As LongPtr) As Long
Private Declare PtrSafe Function GetDeviceCaps Lib "gdi32" (ByVal hDC As LongPtr, ByVal nIndex As Long) As Long

Private mMain As MIMain
Private mPollScheduled As Boolean
Private mFso As Object
Public gStep As String   ' what the app is doing; shown if something fails, to find the problem quickly

' ---------------------------------------------------------------- start

Public Sub MoreInfoPilot()
    On Error GoTo Fail
    gStep = "Opening the window"
    If mMain Is Nothing Then
        Set mMain = New MIMain
        mMain.Start
    Else
        mMain.ShowWindow
    End If
    Exit Sub
Fail:
    ShowError "MoreInfo Pilot could not open."
    Set mMain = Nothing
End Sub

' Called by the main window when it closes.
Public Sub MainClosed()
    Set mMain = Nothing
End Sub

' Word runs AutoExec when the template is loaded from its STARTUP folder: adds the button on the Add-ins tab.
Public Sub AutoExec()
    AddMenuButton
End Sub

Public Sub AddMenuButton()
    Dim bar As Object, btn As Object
    On Error Resume Next
    CustomizationContext = ThisDocument
    Set bar = CommandBars(APP_NAME)
    If bar Is Nothing Then Set bar = CommandBars.Add(Name:=APP_NAME, Position:=1, Temporary:=True)   ' msoBarTop
    If bar.Controls.Count = 0 Then
        Set btn = bar.Controls.Add(Type:=1, Temporary:=True)   ' msoControlButton
        btn.Caption = APP_NAME
        btn.Style = 3   ' msoButtonIconAndCaption
        btn.FaceId = 487
        btn.TooltipText = "Build the MoreInfo, fill the No Pay Decision Letter and upload the case documents"
        btn.OnAction = "MoreInfoPilot"
    End If
    bar.Visible = True
    ThisDocument.Saved = True
End Sub

' ---------------------------------------------------------------- messages

Public Sub ShowError(ByVal what As String)
    Dim msg As String
    msg = what & vbCrLf & vbCrLf & "Error " & Err.Number & ": " & Err.Description
    If Len(gStep) > 0 Then msg = msg & vbCrLf & "Step: " & gStep
    msg = msg & vbCrLf & vbCrLf & "(Press Ctrl+C to copy this message.)"
    MsgBox msg, vbExclamation, APP_NAME
End Sub

Public Sub Info(ByVal msg As String)
    MsgBox msg, vbInformation, APP_NAME
End Sub

Public Sub Warn(ByVal msg As String)
    MsgBox msg, vbExclamation, APP_NAME
End Sub

Public Function Ask(ByVal msg As String) As Boolean
    Ask = MsgBox(msg, vbQuestion + vbYesNo, APP_NAME) = vbYes
End Function

' ---------------------------------------------------------------- settings (stored for this Windows user)

Public Function GetPref(ByVal key As String, Optional ByVal def As String = "") As String
    GetPref = GetSetting(REG_APP, REG_SECTION, key, def)
End Function

Public Sub SetPref(ByVal key As String, ByVal value As String)
    SaveSetting REG_APP, REG_SECTION, key, value
End Sub

Public Function GetList(ByVal key As String) As Collection
    Dim c As New Collection, n As Long, i As Long, v As String
    n = Val(GetPref(key & "Count", "0"))
    For i = 1 To n
        v = GetPref(key & CStr(i))
        If Len(v) > 0 Then c.Add v
    Next
    Set GetList = c
End Function

Public Sub SetList(ByVal key As String, ByVal items As Collection)
    Dim i As Long
    SetPref key & "Count", CStr(items.Count)
    For i = 1 To items.Count
        SetPref key & CStr(i), CStr(items(i))
    Next
End Sub

' ---------------------------------------------------------------- files and folders

Public Function Fso() As Object
    If mFso Is Nothing Then Set mFso = CreateObject("Scripting.FileSystemObject")
    Set Fso = mFso
End Function

Public Function NoSlash(ByVal path As String) As String
    path = Trim$(path)
    Do While Len(path) > 3 And Right$(path, 1) = "\"
        path = Left$(path, Len(path) - 1)
    Loop
    NoSlash = path
End Function

Public Function JoinPath(ByVal folder As String, ByVal name As String) As String
    folder = NoSlash(folder)
    If Right$(folder, 1) = "\" Then JoinPath = folder & name Else JoinPath = folder & "\" & name
End Function

Public Sub EnsureFolder(ByVal path As String)
    Dim parent As String
    path = NoSlash(path)
    If Len(path) = 0 Then Exit Sub
    If Fso.FolderExists(path) Then Exit Sub
    parent = Fso.GetParentFolderName(path)
    If Len(parent) > 0 And parent <> path Then EnsureFolder parent
    If Not Fso.FolderExists(path) Then Fso.CreateFolder path
End Sub

Public Function DataFolder() As String
    DataFolder = JoinPath(Environ$("APPDATA"), "MoreInfoPilot")
    EnsureFolder DataFolder
End Function

Public Function TemplatesFolder() As String
    TemplatesFolder = JoinPath(DataFolder(), "Templates")
    EnsureFolder TemplatesFolder
End Function

' A new empty folder in %TEMP% for the files being built (deleted after the upload).
Public Function NewWorkFolder(ByVal tag As String) As String
    Dim path As String
    Randomize
    path = JoinPath(JoinPath(Environ$("TEMP"), "MoreInfoPilot"), tag & "_" & Format$(Now, "yyyymmdd_hhnnss") & "_" & _
                    CStr(Int(Rnd * 100000)))
    EnsureFolder path
    NewWorkFolder = path
End Function

Public Sub DeleteFolderQuietly(ByVal path As String)
    On Error Resume Next
    If Len(path) > 0 Then Fso.DeleteFolder NoSlash(path), True
End Sub

Public Function StemOf(ByVal fileName As String) As String
    Dim dotPos As Long
    fileName = FileNameOf(fileName)
    dotPos = InStrRev(fileName, ".")
    If dotPos > 1 Then StemOf = Left$(fileName, dotPos - 1) Else StemOf = fileName
End Function

' A name that is safe for a file (no \ / : * ? " < > |).
Public Function SafeFileName(ByVal s As String) As String
    Dim c As Variant
    For Each c In Array("\", "/", ":", "*", "?", """", "<", ">", "|")
        s = Replace(s, c, "-")
    Next
    SafeFileName = Trim$(s)
End Function

Public Sub OpenFile(ByVal path As String)
    CreateObject("Shell.Application").ShellExecute path
End Sub

Public Sub OpenFolder(ByVal path As String)
    Shell "explorer.exe """ & NoSlash(path) & """", vbNormalFocus
End Sub

Public Function PickFolder(ByVal title As String) As String
    With Application.FileDialog(4)   ' msoFileDialogFolderPicker
        .Title = title
        .AllowMultiSelect = False
        If .Show = -1 Then PickFolder = .SelectedItems(1)
    End With
End Function

Public Function PickFiles(ByVal title As String, ByVal filterName As String, ByVal patterns As String, _
                          ByVal multi As Boolean) As Collection
    Dim c As New Collection, item As Variant
    With Application.FileDialog(3)   ' msoFileDialogFilePicker
        .Title = title
        .AllowMultiSelect = multi
        .Filters.Clear
        If Len(patterns) > 0 Then .Filters.Add filterName, patterns
        .Filters.Add "All files", "*.*"
        If .Show = -1 Then
            For Each item In .SelectedItems
                c.Add CStr(item)
            Next
        End If
    End With
    Set PickFiles = c
End Function

' Screen size in points (the unit of the windows), to fit small laptop screens.
Public Sub ScreenPoints(ByRef w As Single, ByRef h As Single)
    Dim dc As LongPtr, dpi As Long
    dc = GetDC(0)
    dpi = GetDeviceCaps(dc, 90)   ' LOGPIXELSY
    ReleaseDC 0, dc
    If dpi <= 0 Then dpi = 96
    w = GetSystemMetrics(16) * 72 / dpi   ' SM_CXFULLSCREEN
    h = GetSystemMetrics(17) * 72 / dpi   ' SM_CYFULLSCREEN
    If w < 400 Then w = 1000
    If h < 300 Then h = 700
End Sub

' ---------------------------------------------------------------- clipboard

Public Function ClipboardSeq() As Long
    ClipboardSeq = GetClipboardSequenceNumber()
End Function

Public Function ClipboardHasImage() As Boolean
    ClipboardHasImage = IsClipboardFormatAvailable(2) <> 0 Or IsClipboardFormatAvailable(8) <> 0 Or _
                        IsClipboardFormatAvailable(17) <> 0   ' CF_BITMAP, CF_DIB, CF_DIBV5
End Function

Public Function ClipboardHasFiles() As Boolean
    ClipboardHasFiles = IsClipboardFormatAvailable(15) <> 0   ' CF_HDROP (files copied in File Explorer)
End Function

Public Function ClipboardHasText() As Boolean
    ClipboardHasText = IsClipboardFormatAvailable(13) <> 0 Or IsClipboardFormatAvailable(1) <> 0
End Function

' Files copied in File Explorer (Ctrl+C).
Public Function ClipboardFiles() As Collection
    Dim c As New Collection, h As LongPtr, n As Long, i As Long, length As Long, buf As String
    Set ClipboardFiles = c
    If OpenClipboard(0) = 0 Then Exit Function
    h = GetClipboardData(15)
    If h <> 0 Then
        n = DragQueryFileW(h, -1, 0, 0)
        For i = 0 To n - 1
            length = DragQueryFileW(h, i, 0, 0)
            buf = String$(length + 1, vbNullChar)
            DragQueryFileW h, i, StrPtr(buf), length + 1
            c.Add Left$(buf, length)
        Next
    End If
    CloseClipboard
End Function

' Auto-capture: every second the window checks if a new screenshot was copied (Win+Shift+S).
Public Sub StartPolling()
    If mPollScheduled Then Exit Sub
    mPollScheduled = True
    Application.OnTime When:=Now + TimeSerial(0, 0, 1), Name:="MoreInfoPilot_Poll"
End Sub

Public Sub MoreInfoPilot_Poll()
    mPollScheduled = False
    If mMain Is Nothing Then Exit Sub
    On Error Resume Next
    If mMain.WantsPolling Then
        mMain.PollClipboard
        StartPolling
    End If
End Sub

' ---------------------------------------------------------------- Word documents built by the app

' Range at the start of a new empty paragraph at the end of the document.
Public Function NewParaRange(ByVal d As Object) As Object
    Dim r As Object
    If d.Paragraphs.Count = 1 And Len(d.Paragraphs(1).Range.Text) <= 1 Then
        Set r = d.Paragraphs(1).Range
    Else
        d.Content.InsertParagraphAfter
        Set r = d.Paragraphs(d.Paragraphs.Count).Range
    End If
    r.Collapse 1   ' wdCollapseStart
    Set NewParaRange = r
End Function

Private Function AddPara(ByVal d As Object, ByVal text As String, ByVal size As Single, ByVal isBold As Boolean, _
                         ByVal isItalic As Boolean, ByVal color As Long, ByVal align As Long, _
                         Optional ByVal heading As Boolean = False) As Object
    Dim r As Object, p As Object
    Set r = NewParaRange(d)
    Set p = r.Paragraphs(1)
    If heading Then p.Style = d.Styles(-3) Else p.Style = d.Styles(-1)   ' wdStyleHeading2 / wdStyleNormal
    r.InsertAfter text
    Set r = p.Range
    r.Font.Size = size
    r.Font.Bold = isBold
    r.Font.Italic = isItalic
    r.Font.Color = color
    p.Alignment = align
    Set AddPara = r
End Function

Private Sub SetMargins(ByVal d As Object, ByRef usableWidth As Single, ByRef usableHeight As Single)
    With d.PageSetup
        .LeftMargin = CentimetersToPoints(1.5)
        .RightMargin = CentimetersToPoints(1.5)
        .TopMargin = CentimetersToPoints(1.5)
        .BottomMargin = CentimetersToPoints(1.5)
        usableWidth = .PageWidth - .LeftMargin - .RightMargin
        usableHeight = .PageHeight - .TopMargin - .BottomMargin
    End With
End Sub

Private Sub FitPicture(ByVal ils As Object, ByVal maxW As Single, ByVal maxH As Single)
    Dim w As Single, h As Single, k As Single
    w = ils.Width
    h = ils.Height
    If w <= 0 Or h <= 0 Then Exit Sub
    k = 1
    If w > maxW Then k = maxW / w
    If h * k > maxH Then k = maxH / h
    If k < 1 Then
        ils.LockAspectRatio = -1   ' msoTrue
        ils.Width = w * k
        ils.Height = h * k
    End If
End Sub

' The MoreInfo document (Word, not saved): case header, then every screenshot under its section with its caption.
Public Function BuildMoreInfoDoc(ByVal store As Object, ByVal caseNo As String, ByVal analyst As String, _
                                 ids As Variant, secs As Variant, caps As Variant, ByVal count As Long) As Object
    Dim d As Object, i As Long, current As String, ils As Object, r As Object, usableW As Single, usableH As Single
    gStep = "Creating the MoreInfo document"
    Set d = Documents.Add(Visible:=False)
    SetMargins d, usableW, usableH
    d.Styles(-1).Font.Name = "Calibri"
    d.Styles(-1).Font.Size = 10
    AddPara d, "MoreInfo - Case " & caseNo, 16, True, False, RGB(14, 116, 144), 0
    If Len(analyst) = 0 Then analyst = "-"
    AddPara d, "Prepared by: " & analyst & "    Date: " & Format$(Now, "yyyy-mm-dd hh:nn"), 10, False, False, _
            RGB(85, 85, 85), 0
    For i = 0 To count - 1
        gStep = "Adding screenshot " & (i + 1) & " to the MoreInfo"
        If secs(i) <> current Or i = 0 Then
            current = secs(i)
            AddPara d, current, 13, True, False, RGB(31, 56, 100), 0, True
        End If
        Set r = NewParaRange(d)
        r.Paragraphs(1).Style = d.Styles(-1)
        r.FormattedText = store.Bookmarks("S" & ids(i)).Range.FormattedText
        Set ils = d.InlineShapes(d.InlineShapes.Count)
        FitPicture ils, usableW, usableH - 40
        ils.Range.Paragraphs(1).Alignment = 1   ' center
        If Len(caps(i)) > 0 Then AddPara d, CStr(caps(i)), 10, False, True, RGB(0, 0, 0), 1
    Next
    Set BuildMoreInfoDoc = d
End Function

Public Sub ExportPdf(ByVal d As Object, ByVal pdfPath As String)
    d.ExportAsFixedFormat OutputFileName:=pdfPath, ExportFormat:=17   ' wdExportFormatPDF
End Sub

' A document that is already open in Word (so the app does not close it).
Private Function OpenDocument(ByVal path As String) As Object
    Dim d As Object
    For Each d In Documents
        If LCase$(d.FullName) = LCase$(path) Then
            Set OpenDocument = d
            Exit Function
        End If
    Next
End Function

Public Sub WordToPdf(ByVal src As String, ByVal pdfPath As String)
    Dim d As Object, wasOpen As Boolean
    gStep = "Saving " & FileNameOf(src) & " as PDF"
    Set d = OpenDocument(src)
    wasOpen = Not d Is Nothing
    If Not wasOpen Then
        Set d = Documents.Open(FileName:=src, ConfirmConversions:=False, ReadOnly:=True, _
                               AddToRecentFiles:=False, Visible:=False)
    End If
    ExportPdf d, pdfPath
    If Not wasOpen Then d.Close SaveChanges:=False
End Sub

Public Sub ImageToPdf(ByVal src As String, ByVal pdfPath As String)
    Dim d As Object, ils As Object, usableW As Single, usableH As Single
    gStep = "Saving " & FileNameOf(src) & " as PDF"
    Set d = Documents.Add(Visible:=False)
    SetMargins d, usableW, usableH
    Set ils = d.InlineShapes.AddPicture(FileName:=src, LinkToFile:=False, SaveWithDocument:=True, _
                                        Range:=d.Paragraphs(1).Range)
    FitPicture ils, usableW, usableH - 20
    ExportPdf d, pdfPath
    d.Close SaveChanges:=False
End Sub

' Saves one case document in the work folder: Word files and images as PDF, the rest as they are.
Public Function PrepareDocument(ByVal src As String, ByVal targetPath As String) As String
    Dim ext As String
    ext = FileExt(src)
    If ext = ".pdf" Then
        Fso.CopyFile src, targetPath, True
    ElseIf IsImageType(ext) Then
        ImageToPdf src, targetPath
    ElseIf IsWordType(ext) Then
        WordToPdf src, targetPath
    Else
        Fso.CopyFile src, targetPath, True
    End If
    PrepareDocument = targetPath
End Function

' ---------------------------------------------------------------- screenshots kept in a hidden document

' Pastes the image of the clipboard at the end of the store document and names it S<id>. False if there is none.
Public Function PasteImageInto(ByVal store As Object, ByVal id As Long) As Boolean
    Dim r As Object, inlineBefore As Long, shapesBefore As Long, ils As Object
    If Not ClipboardHasImage() Then Exit Function
    inlineBefore = store.InlineShapes.Count
    shapesBefore = store.Shapes.Count
    Set r = NewParaRange(store)
    On Error Resume Next
    r.PasteSpecial Link:=False, DataType:=5, Placement:=0   ' bitmap, in line with text
    If Err.Number <> 0 Then
        Err.Clear
        Set r = store.Paragraphs(store.Paragraphs.Count).Range
        r.Collapse 1
        r.Paste
    End If
    Err.Clear
    If store.Shapes.Count > shapesBefore Then store.Shapes(store.Shapes.Count).ConvertToInlineShape
    On Error GoTo 0
    If store.InlineShapes.Count > inlineBefore Then
        Set ils = store.InlineShapes(store.InlineShapes.Count)
        store.Bookmarks.Add Name:="S" & id, Range:=ils.Range
        PasteImageInto = True
    Else
        store.Paragraphs(store.Paragraphs.Count).Range.Text = ""
    End If
    store.Saved = True
End Function

Public Sub AddImageFileInto(ByVal store As Object, ByVal path As String, ByVal id As Long)
    Dim r As Object, ils As Object
    Set r = NewParaRange(store)
    Set ils = store.InlineShapes.AddPicture(FileName:=path, LinkToFile:=False, SaveWithDocument:=True, Range:=r)
    store.Bookmarks.Add Name:="S" & id, Range:=ils.Range
    store.Saved = True
End Sub

Public Sub RemoveImageFrom(ByVal store As Object, ByVal id As Long)
    On Error Resume Next
    store.Bookmarks("S" & id).Range.Paragraphs(1).Range.Delete
    store.Saved = True
End Sub

' Picture file of a screenshot for the preview (metafile).
Public Function ThumbnailFile(ByVal store As Object, ByVal id As Long) As String
    Dim bits() As Byte, f As Integer, path As String
    bits = store.Bookmarks("S" & id).Range.EnhMetaFileBits
    path = JoinPath(JoinPath(Environ$("TEMP"), "MoreInfoPilot"), "preview_" & id & ".emf")
    EnsureFolder Fso.GetParentFolderName(path)
    If Fso.FileExists(path) Then Fso.DeleteFile path, True
    f = FreeFile
    Open path For Binary Access Write As #f
    Put #f, , bits
    Close #f
    ThumbnailFile = path
End Function

' A pasted screenshot or text as a case document: saved as a Word file (-> PDF) or a .txt file.
Public Function PastedDocument(ByVal asImage As Boolean) As String
    Dim d As Object, path As String, usableW As Single, usableH As Single
    Set d = Documents.Add(Visible:=False)
    If asImage Then
        SetMargins d, usableW, usableH
        d.Paragraphs(1).Range.PasteSpecial Link:=False, DataType:=5, Placement:=0
        If d.InlineShapes.Count > 0 Then FitPicture d.InlineShapes(1), usableW, usableH - 20
        path = JoinPath(NewWorkFolder("paste"), "Pasted screenshot " & Format$(Now, "yyyy-mm-dd hhnnss") & ".docx")
        d.SaveAs2 FileName:=path, FileFormat:=16   ' wdFormatDocumentDefault
    Else
        d.Paragraphs(1).Range.PasteSpecial DataType:=2   ' wdPasteText
        path = JoinPath(NewWorkFolder("paste"), "Pasted text " & Format$(Now, "yyyy-mm-dd hhnnss") & ".txt")
        d.SaveAs2 FileName:=path, FileFormat:=2, Encoding:=65001   ' wdFormatText, UTF-8
    End If
    d.Close SaveChanges:=False
    PastedDocument = path
End Function

' ---------------------------------------------------------------- Excel: "Additional info" tab

Private Function SheetExists(ByVal wb As Object, ByVal name As String) As Boolean
    Dim ws As Object
    For Each ws In wb.Sheets
        If LCase$(ws.Name) = LCase$(name) Then
            SheetExists = True
            Exit Function
        End If
    Next
End Function

Public Sub BuildExcel(ByVal store As Object, ByVal src As String, ByVal dst As String, ByVal caseNo As String, _
                      ByVal analyst As String, ids As Variant, secs As Variant, caps As Variant, ByVal count As Long)
    Dim xl As Object, wb As Object, ws As Object, shp As Object, sheetName As String, n As Long, row As Long
    Dim i As Long, current As String, fileFormat As Long, before As Long
    gStep = "Opening Excel"
    Set xl = CreateObject("Excel.Application")
    On Error GoTo Fail
    xl.Visible = False
    xl.DisplayAlerts = False
    gStep = "Opening the transaction file " & FileNameOf(src)
    Set wb = xl.Workbooks.Open(FileName:=src, UpdateLinks:=0, ReadOnly:=True, AddToMru:=False)
    sheetName = EXCEL_SHEET
    n = 2
    Do While SheetExists(wb, sheetName)
        sheetName = Left$(EXCEL_SHEET, 28) & " " & n
        n = n + 1
    Loop
    gStep = "Adding the """ & sheetName & """ tab"
    Set ws = wb.Worksheets.Add(After:=wb.Sheets(wb.Sheets.Count))
    ws.Name = sheetName
    ws.Range("A1").Value = sheetName & " - Case " & caseNo
    ws.Range("A1").Font.Bold = True
    ws.Range("A1").Font.Size = 14
    ws.Range("A1").Font.Color = RGB(14, 116, 144)
    If Len(analyst) = 0 Then analyst = "-"
    ws.Range("A2").Value = "Prepared by: " & analyst & "    Date: " & Format$(Now, "yyyy-mm-dd hh:nn")
    row = 4
    ws.Activate
    For i = 0 To count - 1
        If secs(i) <> current Or i = 0 Then
            current = secs(i)
            ws.Cells(row, 1).Value = current
            ws.Cells(row, 1).Font.Bold = True
            ws.Cells(row, 1).Font.Size = 12
            row = row + 1
        End If
        If Len(caps(i)) > 0 Then
            ws.Cells(row, 1).Value = caps(i)
            ws.Cells(row, 1).Font.Italic = True
            row = row + 1
        End If
        gStep = "Copying screenshot " & (i + 1) & " to Excel"
        store.Bookmarks("S" & ids(i)).Range.Copy
        ws.Cells(row, 1).Select
        before = ws.Shapes.Count
        ws.Paste
        If ws.Shapes.Count = before Then ws.PasteSpecial Format:="Bitmap"
        If ws.Shapes.Count = before Then Err.Raise vbObjectError + 2, , "The screenshot could not be pasted in Excel."
        Set shp = ws.Shapes(ws.Shapes.Count)
        shp.LockAspectRatio = -1
        If shp.Width > 675 Then shp.Width = 675   ' about 900 pixels, like the Python version
        shp.Left = ws.Cells(row, 1).Left
        shp.Top = ws.Cells(row, 1).Top
        row = shp.BottomRightCell.row + 2
    Next
    ws.Cells(1, 1).Select
    fileFormat = 51   ' xlOpenXMLWorkbook (.xlsx)
    If FileExt(dst) = ".xlsm" Then fileFormat = 52
    gStep = "Saving " & FileNameOf(dst)
    wb.SaveAs FileName:=dst, FileFormat:=fileFormat
    wb.Close SaveChanges:=False
    xl.Quit
    Exit Sub
Fail:
    Dim number As Long, description As String
    number = Err.Number
    description = Err.Description
    On Error Resume Next
    If Not wb Is Nothing Then wb.Close SaveChanges:=False
    xl.Quit
    On Error GoTo 0
    Err.Raise number, , description
End Sub

' ---------------------------------------------------------------- numbering and upload

' Numbers already used by this case in the folders, as "|0||3|".
Public Function UsedNumbers(ByVal caseNo As String, ByVal baseName As String, ByVal folders As Collection) As String
    Dim folder As Variant, name As String, n As Long, used As String
    For Each folder In folders
        If Len(folder) > 0 Then
            On Error Resume Next
            name = Dir$(JoinPath(CStr(folder), caseNo & "," & baseName & "*"))
            If Err.Number <> 0 Then name = ""
            On Error GoTo 0
            Do While Len(name) > 0
                n = TakenNumber(name, caseNo, baseName)
                If n >= 0 Then used = used & "|" & n & "|"
                name = Dir$()
            Loop
        End If
    Next
    UsedNumbers = used
End Function

' Builds CASE,MOREINFO (+ the case documents, numbered after it) and saves them in the folders.
' The MoreInfo and the documents go to `folder`; documents marked as the letter go to every letter folder.
' Returns the report shown to the analyst.
Public Function CreatePackage(ByVal store As Object, ByVal caseNo As String, ByVal analyst As String, _
        ids As Variant, secs As Variant, caps As Variant, ByVal shotCount As Long, _
        docPaths As Variant, docIsLetter As Variant, ByVal docCount As Long, _
        ByVal folder As String, ByVal letterFolders As Collection, ByVal mode As String, ByVal excelSource As String, _
        ByVal baseName As String, ByVal keepDocx As Boolean, ByVal includeMoreInfo As Boolean) As String
    Dim exts() As String, extCount As Long, every As New Collection, f As Variant, names As Variant
    Dim work As String, planFile() As String, planLetter() As Boolean, planCount As Long, i As Long, k As Long
    Dim mainExt As String, mainPath As String, d As Object, docxPath As String, saved As String
    Dim copied As String, errors As String, failed As String, report As String, dest As String, copiedCount As Long
    Dim letterF As New Collection, extraDocx As String

    caseNo = CleanCase(caseNo)
    For Each f In letterFolders
        If Len(f) > 0 Then letterF.Add NoSlash(CStr(f))
    Next
    If letterF.Count = 0 And Len(folder) > 0 Then letterF.Add NoSlash(folder)
    folder = NoSlash(folder)

    ReDim exts(0 To docCount)
    If includeMoreInfo Then
        mainExt = ".pdf"
        If mode = "excel" Then
            mainExt = ".xlsx"
            If FileExt(excelSource) = ".xlsm" Then mainExt = ".xlsm"
        End If
        exts(extCount) = mainExt
        extCount = extCount + 1
    End If
    For i = 0 To docCount - 1
        exts(extCount) = DocumentTarget(docPaths(i))
        extCount = extCount + 1
    Next
    ReDim Preserve exts(0 To extCount - 1)

    If Len(folder) > 0 Then every.Add folder
    For Each f In letterF
        If InStr(1, "|" & JoinCollection(every, "|") & "|", "|" & f & "|", vbTextCompare) = 0 Then every.Add f
    Next
    gStep = "Checking the numbers already used in the folders"
    names = NextNames(caseNo, baseName, UsedNumbers(caseNo, baseName, every), exts)

    work = NewWorkFolder(caseNo)
    ReDim planFile(0 To extCount + 1)
    ReDim planLetter(0 To extCount + 1)
    k = 0
    If includeMoreInfo Then
        mainPath = JoinPath(work, CStr(names(0)))
        If mode = "excel" Then
            BuildExcel store, excelSource, mainPath, caseNo, analyst, ids, secs, caps, shotCount
        Else
            Set d = BuildMoreInfoDoc(store, caseNo, analyst, ids, secs, caps, shotCount)
            gStep = "Saving " & names(0)
            ExportPdf d, mainPath
            If keepDocx Then
                docxPath = JoinPath(work, StemOf(CStr(names(0))) & ".docx")
                d.SaveAs2 FileName:=docxPath, FileFormat:=16
                extraDocx = docxPath
            End If
            d.Close SaveChanges:=False
        End If
        planFile(planCount) = mainPath
        planCount = planCount + 1
        If Len(extraDocx) > 0 Then
            planFile(planCount) = extraDocx
            planCount = planCount + 1
        End If
        k = 1
    End If
    For i = 0 To docCount - 1
        gStep = "Preparing " & FileNameOf(docPaths(i))
        saved = PrepareDocument(CStr(docPaths(i)), JoinPath(work, CStr(names(k + i))))
        planFile(planCount) = saved
        planLetter(planCount) = docIsLetter(i)
        planCount = planCount + 1
    Next

    ' upload: every file to its folder(s); a folder that fails is skipped for the rest
    For i = 0 To planCount - 1
        If planLetter(i) Then
            For Each f In letterF
                CopyTo planFile(i), CStr(f), copied, errors, failed, copiedCount
            Next
        Else
            CopyTo planFile(i), folder, copied, errors, failed, copiedCount
        End If
    Next

    report = ""
    If includeMoreInfo Then
        If mode = "excel" Then
            report = "Excel file created with a new """ & EXCEL_SHEET & """ tab." & vbCrLf & vbCrLf
        Else
            report = "PDF created with Microsoft Word." & vbCrLf & vbCrLf
        End If
    End If
    report = report & "Created:" & vbCrLf
    For i = 0 To planCount - 1
        report = report & "  - " & FileNameOf(planFile(i)) & vbCrLf
    Next
    If Len(copied) > 0 Then report = report & "Saved to:" & vbCrLf & copied
    If Len(errors) > 0 Then report = report & "Could not save to:" & vbCrLf & errors
    If copiedCount > 0 Then
        DeleteFolderQuietly work
    Else
        report = report & vbCrLf & "No destination folder could be written, so the files were kept here: " & work
    End If
    gStep = ""
    CreatePackage = report
End Function

Private Sub CopyTo(ByVal file As String, ByVal folder As String, ByRef copied As String, ByRef errors As String, _
                   ByRef failed As String, ByRef copiedCount As Long)
    Dim dest As String
    If Len(folder) = 0 Then Exit Sub
    If InStr(1, failed, "|" & folder & "|", vbTextCompare) > 0 Then Exit Sub
    gStep = "Saving " & FileNameOf(file) & " in " & folder
    On Error GoTo Fail
    EnsureFolder folder
    dest = JoinPath(folder, FileNameOf(file))
    If Fso.FileExists(dest) Then Err.Raise vbObjectError + 1, , FileNameOf(dest) & " already exists"
    Fso.CopyFile file, dest, False
    copied = copied & "  - " & dest & vbCrLf
    copiedCount = copiedCount + 1
    Exit Sub
Fail:
    failed = failed & "|" & folder & "|"
    errors = errors & "  - " & folder & ": " & Err.Description & vbCrLf
End Sub

Public Function JoinCollection(ByVal c As Collection, ByVal sep As String) As String
    Dim v As Variant, out As String
    For Each v In c
        If Len(out) > 0 Then out = out & sep
        out = out & CStr(v)
    Next
    JoinCollection = out
End Function

' ---------------------------------------------------------------- letter templates

' Content controls of the document, the ones in headers and footers too, without repeats.
Private Function AllControls(ByVal d As Object) As Collection
    Dim c As New Collection, seen As Object, sec As Object, hf As Object, cc As Object
    Set seen = CreateObject("Scripting.Dictionary")
    For Each cc In d.ContentControls
        AddControl c, seen, cc
    Next
    On Error Resume Next
    For Each sec In d.Sections
        For Each hf In sec.Headers
            For Each cc In hf.Range.ContentControls
                AddControl c, seen, cc
            Next
        Next
        For Each hf In sec.Footers
            For Each cc In hf.Range.ContentControls
                AddControl c, seen, cc
            Next
        Next
    Next
    On Error GoTo 0
    Set AllControls = c
End Function

Private Sub AddControl(ByVal c As Collection, ByVal seen As Object, ByVal cc As Object)
    Dim inner As Object
    If seen.Exists(cc.ID) Then Exit Sub
    seen.Add cc.ID, True
    c.Add cc
    For Each inner In cc.Range.ContentControls   ' controls inside other controls (e.g. a repeating section)
        AddControl c, seen, inner
    Next
End Sub

' A control the analyst fills: text, rich text, drop-down, combo box or date, with no other control inside.
Private Function IsFillable(ByVal cc As Object) As Boolean
    Dim inner As Object
    Select Case cc.Type
        Case 0, 1, 3, 4, 6   ' rich text, text, combo box, drop-down list, date
        Case Else
            Exit Function
    End Select
    For Each inner In cc.Range.ContentControls
        If inner.ID <> cc.ID Then Exit Function
    Next
    IsFillable = True
End Function

' The field a control belongs to: controls bound to the same data, or with the same Tag/Title, are one field.
Public Function ControlKey(ByVal cc As Object) As String
    Dim mapped As Boolean
    On Error Resume Next
    mapped = cc.XMLMapping.IsMapped
    On Error GoTo 0
    If mapped Then
        ControlKey = "xp:" & cc.XMLMapping.XPath
    ElseIf Len(Trim$(cc.Tag)) > 0 Then
        ControlKey = "cc:" & LCase$(Trim$(cc.Tag))
    ElseIf Len(Trim$(cc.Title)) > 0 Then
        ControlKey = "cc:" & LCase$(Trim$(cc.Title))
    Else
        ControlKey = "cc:#" & cc.ID
    End If
End Function

Private Function ControlLabel(ByVal cc As Object) As String
    Dim xp As String, p As Long
    If Len(Trim$(cc.Title)) > 0 Then
        ControlLabel = Trim$(cc.Title)
    ElseIf Len(Trim$(cc.Tag)) > 0 Then
        ControlLabel = Trim$(cc.Tag)
    Else
        On Error Resume Next
        xp = cc.XMLMapping.XPath
        On Error GoTo 0
        If Len(xp) > 0 Then
            xp = Mid$(xp, InStrRev(xp, "/") + 1)
            p = InStr(1, xp, "[")
            If p > 0 Then xp = Left$(xp, p - 1)
            p = InStr(1, xp, ":")
            If p > 0 Then xp = Mid$(xp, p + 1)
        End If
        ControlLabel = xp
    End If
End Function

Private Function ControlKind(ByVal cc As Object) As String
    Select Case cc.Type
        Case 4: ControlKind = "dropdown"
        Case 3: ControlKind = "combo"
        Case 6: ControlKind = "date"
        Case Else: ControlKind = "text"
    End Select
End Function

Private Function ControlOptions(ByVal cc As Object) As String
    Dim e As Object, out As String
    If cc.Type <> 3 And cc.Type <> 4 Then Exit Function
    For Each e In cc.DropdownListEntries
        If Len(e.Value) > 0 And Len(Trim$(e.Text)) > 0 Then   ' Word's "Choose an item." has no value
            out = out & Chr(30) & e.Text
        End If
    Next
    If Len(out) > 0 Then ControlOptions = Mid$(out, 2)
End Function

Private Function RepeatingParent(ByVal cc As Object) As Object
    Dim p As Object, q As Object, steps As Long
    On Error Resume Next
    Set p = cc.ParentContentControl
    Do While Not p Is Nothing And steps < 20
        If p.Type = 9 Then   ' wdContentControlRepeatingSection
            Set RepeatingParent = p
            Exit Function
        End If
        Set q = Nothing
        Set q = p.ParentContentControl
        Set p = q
        steps = steps + 1
    Loop
End Function

' True when nothing else is written on the control's line (a bullet with only the control).
Private Function AloneOnLine(ByVal cc As Object) As Boolean
    Dim para As Object, other As String
    On Error GoTo Done
    Set para = cc.Range.Paragraphs(1).Range
    If para.InlineShapes.Count > 0 Or para.Fields.Count > 0 Then Exit Function
    other = Replace(para.Text, cc.Range.Text, "", 1, 1)
    other = StripChars(other, " " & vbTab & vbCr & vbLf & Chr(7) & Chr(11) & ".,;:-" & ChrW(8226) & ChrW(8211))
    AloneOnLine = Len(other) = 0
Done:
End Function

' A field of the letter form (a Scripting.Dictionary).
Private Function NewField(ByVal key As String, ByVal label As String, ByVal kind As String, ByVal options As String, _
                          ByVal value As String, ByVal multi As Boolean) As Object
    Dim f As Object
    Set f = CreateObject("Scripting.Dictionary")
    f("key") = key
    f("label") = label
    f("kind") = kind
    f("options") = options        ' separated by Chr(30)
    f("value") = value
    f("count") = 1
    f("multi") = multi
    Set NewField = f
End Function

Private Sub AddField(ByVal fields As Collection, ByVal byKey As Object, ByVal f As Object)
    Dim old As Object, opt As Variant
    If byKey.Exists(f("key")) Then
        Set old = byKey(f("key"))
        old("count") = old("count") + 1
        If f("multi") Then old("multi") = True
        If Len(f("options")) > 0 Then
            For Each opt In Split(f("options"), Chr(30))
                If InStr(1, Chr(30) & old("options") & Chr(30), Chr(30) & opt & Chr(30)) = 0 Then
                    If Len(old("options")) > 0 Then old("options") = old("options") & Chr(30)
                    old("options") = old("options") & opt
                End If
            Next
        End If
        If Len(old("value")) = 0 Then old("value") = f("value")
    Else
        fields.Add f
        byKey.Add f("key"), f
    End If
End Sub

' Opens a template (hidden) and lists its fields, in the order they appear. Also returns its language.
Public Function ScanTemplate(ByVal path As String, ByRef lang As String) As Collection
    Dim d As Object, fields As New Collection, byKey As Object, cc As Object, ff As Object, label As Variant
    Dim kind As String, value As String, multi As Boolean, i As Long, entries As String, n As Long
    gStep = "Reading the template " & FileNameOf(path)
    Set byKey = CreateObject("Scripting.Dictionary")
    Set d = Documents.Open(FileName:=path, ConfirmConversions:=False, ReadOnly:=True, AddToRecentFiles:=False, _
                           Visible:=False)
    On Error GoTo Fail
    For Each cc In AllControls(d)
        If IsFillable(cc) Then
            n = n + 1
            kind = ControlKind(cc)
            If cc.ShowingPlaceholderText Then value = "" Else value = cc.Range.Text
            multi = Not RepeatingParent(cc) Is Nothing
            If Not multi And (kind = "dropdown" Or kind = "combo") Then multi = AloneOnLine(cc)
            label = ControlLabel(cc)
            If Len(label) = 0 Then label = "Field " & n
            AddField fields, byKey, NewField(ControlKey(cc), CStr(label), kind, ControlOptions(cc), value, multi)
        End If
    Next
    For Each ff In d.FormFields   ' older forms: text and drop-down form fields
        If ff.Type = 70 Then
            AddField fields, byKey, NewField("ff:" & LCase$(ff.Name), ff.Name, "text", "", ff.Result, False)
        ElseIf ff.Type = 83 Then
            entries = ""
            For i = 1 To ff.DropDown.ListEntries.Count
                If i > 1 Then entries = entries & Chr(30)
                entries = entries & ff.DropDown.ListEntries(i).Name
            Next
            AddField fields, byKey, NewField("ff:" & LCase$(ff.Name), ff.Name, "dropdown", entries, ff.Result, False)
        End If
    Next
    For Each label In PlaceholderLabels(d.Content.Text)   ' [Customer Name] or {{Customer Name}}
        If PlaceholderOutsideControls(d, CStr(label)) Then
            AddField fields, byKey, NewField("ph:" & LCase$(label), CStr(label), "text", "", "", False)
        End If
    Next
    lang = GuessLanguage(d.Content.Text)
    d.Close SaveChanges:=False
    Set ScanTemplate = fields
    Exit Function
Fail:
    Dim number As Long, description As String
    number = Err.Number
    description = Err.Description
    On Error Resume Next
    d.Close SaveChanges:=False
    On Error GoTo 0
    Err.Raise number, , description
End Function

Private Function PlaceholderOutsideControls(ByVal d As Object, ByVal label As String) As Boolean
    Dim pattern As Variant, r As Object
    For Each pattern In Array("[" & label & "]", "{{" & label & "}}", "{{ " & label & " }}")
        Set r = d.Content
        With r.Find
            .ClearFormatting
            .Text = pattern
            .MatchCase = False
            .MatchWildcards = False
            .Forward = True
            .Wrap = 0   ' wdFindStop
        End With
        Do While r.Find.Execute
            If r.ParentContentControl Is Nothing Then
                PlaceholderOutsideControls = True
                Exit Function
            End If
            r.Collapse 0
        Loop
    Next
End Function

' Value as text: several values written together ("A; B").
Public Function FlatValue(ByVal v As Variant) As String
    Dim x As Variant, out As String
    If IsArray(v) Then
        For Each x In v
            If Len(x) > 0 Then
                If Len(out) > 0 Then out = out & "; "
                out = out & x
            End If
        Next
        FlatValue = out
    Else
        FlatValue = CStr(v)
    End If
End Function

Private Sub SetControl(ByVal cc As Object, ByVal v As String)
    Dim wasLocked As Boolean, i As Long, found As Boolean
    wasLocked = cc.LockContents
    If wasLocked Then cc.LockContents = False
    If cc.Type = 3 Or cc.Type = 4 Then
        For i = 1 To cc.DropdownListEntries.Count
            If cc.DropdownListEntries(i).Text = v Or cc.DropdownListEntries(i).Value = v Then
                cc.DropdownListEntries(i).Select
                found = True
                Exit For
            End If
        Next
        If Not found And cc.Type = 3 Then cc.Range.Text = v   ' a combo box also takes its own text
    Else
        cc.Range.Text = v
    End If
    If wasLocked Then cc.LockContents = True
End Sub

' An empty field: no grey example text in the letter, and its line goes away when nothing else is on it.
Private Sub BlankControl(ByVal cc As Object)
    Dim parent As Object, keepLine As Boolean
    On Error Resume Next
    cc.LockContentControl = False
    cc.LockContents = False
    If AloneOnLine(cc) Then
        keepLine = cc.Range.Information(12)   ' wdWithInTable: a table cell keeps its line
        Set parent = cc.ParentContentControl
        If Not parent Is Nothing Then
            If parent.Range.Paragraphs.Count <= 1 Then keepLine = True
        End If
        If Not keepLine Then
            cc.Range.Paragraphs(1).Range.Delete
            Exit Sub
        End If
    End If
    cc.Delete True
End Sub

' Several values (several reasons): the Word repeating-section item, or the bullet line, is repeated.
Private Function RepeatValues(ByVal d As Object, ByVal cc As Object, ByVal key As String, items As Variant, _
                              ByVal done As Object) As Boolean
    Dim rs As Object, k As Long, newItem As Object, c As Object, anchor As Object, ins As Object
    Set rs = RepeatingParent(cc)
    If Not rs Is Nothing Then
        SetControl cc, CStr(items(0))
        done(cc.ID) = True
        rs.AllowInsertDeleteSection = True
        For k = 1 To UBound(items)
            Set newItem = rs.RepeatingSectionItems(rs.RepeatingSectionItems.Count).InsertItemAfter
            For Each c In newItem.Range.ContentControls
                If ControlKey(c) = key Or Left$(key, 4) = "cc:#" Then
                    If IsFillable(c) And Not done.Exists(c.ID) Then
                        SetControl c, CStr(items(k))
                        done(c.ID) = True
                    End If
                End If
            Next
        Next
        RepeatValues = True
    ElseIf AloneOnLine(cc) Then
        SetControl cc, CStr(items(0))
        done(cc.ID) = True
        Set anchor = cc.Range.Paragraphs(1)
        For k = 1 To UBound(items)
            Set ins = d.Range(anchor.Range.End, anchor.Range.End)
            ins.FormattedText = anchor.Range.FormattedText
            Set anchor = anchor.Next
            For Each c In anchor.Range.ContentControls
                If Not done.Exists(c.ID) Then
                    SetControl c, CStr(items(k))
                    done(c.ID) = True
                End If
            Next
        Next
        RepeatValues = True
    End If
End Function

Private Function UniqueItems(ByVal v As Variant) As Variant
    Dim x As Variant, out As String, sep As String
    sep = Chr(30)
    For Each x In v
        If Len(x) > 0 Then
            If InStr(1, sep & out & sep, sep & x & sep) = 0 Then
                If Len(out) > 0 Then out = out & sep
                out = out & x
            End If
        End If
    Next
    If Len(out) = 0 Then UniqueItems = Array() Else UniqueItems = Split(out, sep)
End Function

' Writes a copy of the template with the values (Scripting.Dictionary: field key -> text, or an array of texts for
' a field with several values). Fields left empty are blank in the letter. Returns the path of the copy.
Public Function FillTemplate(ByVal templatePath As String, ByVal values As Object, ByVal destPath As String) As String
    Dim d As Object, cc As Object, ff As Object, done As Object, empties As New Collection, key As String
    Dim v As Variant, items As Variant, i As Long, k As Variant, label As String, text As String
    gStep = "Filling in the letter"
    EnsureFolder Fso.GetParentFolderName(destPath)
    If FileExt(templatePath) = ".docx" Then
        Fso.CopyFile templatePath, destPath, True
        Set d = Documents.Open(FileName:=destPath, ConfirmConversions:=False, AddToRecentFiles:=False, Visible:=False)
    Else   ' .dotx / .docm: a new document made from it, saved as .docx
        Set d = Documents.Add(Template:=templatePath, Visible:=False)
        d.SaveAs2 FileName:=destPath, FileFormat:=16
    End If
    On Error GoTo Fail
    If d.ProtectionType <> -1 Then d.Unprotect   ' wdNoProtection
    Set done = CreateObject("Scripting.Dictionary")
    ' 1. several values: repeat the item or bullet for each extra value
    For Each cc In AllControls(d)
        If IsFillable(cc) And Not done.Exists(cc.ID) Then
            key = ControlKey(cc)
            If values.Exists(key) Then
                If IsArray(values(key)) Then
                    items = UniqueItems(values(key))
                    If UBound(items) >= 1 Then RepeatValues d, cc, key, items, done
                End If
            End If
        End If
    Next
    ' 2. one value per field (several values on one line are written together)
    For Each cc In AllControls(d)
        If IsFillable(cc) And Not done.Exists(cc.ID) Then
            key = ControlKey(cc)
            text = ""
            If values.Exists(key) Then text = FlatValue(values(key))
            If Len(text) > 0 Then SetControl cc, text Else empties.Add cc
        End If
    Next
    ' 3. empty fields: blank, and their line goes away when nothing else is on it
    For Each cc In empties
        BlankControl cc
    Next
    ' 4. older form fields and placeholders written in the text
    For Each ff In d.FormFields
        key = "ff:" & LCase$(ff.Name)
        If values.Exists(key) Then
            text = FlatValue(values(key))
            If ff.Type = 83 Then
                For i = 1 To ff.DropDown.ListEntries.Count
                    If ff.DropDown.ListEntries(i).Name = text Then ff.DropDown.Value = i
                Next
            ElseIf ff.Type = 70 Then
                ff.Result = text
            End If
        End If
    Next
    For Each k In values.Keys
        If Left$(k, 3) = "ph:" Then
            label = Mid$(k, 4)
            text = FlatValue(values(k))
            ReplaceEverywhere d, "[" & label & "]", text
            ReplaceEverywhere d, "{{" & label & "}}", text
            ReplaceEverywhere d, "{{ " & label & " }}", text
        End If
    Next
    d.Fields.Update   ' REF fields repeat other fields
    d.Save
    d.Close SaveChanges:=False
    FillTemplate = destPath
    Exit Function
Fail:
    Dim number As Long, description As String
    number = Err.Number
    description = Err.Description
    On Error Resume Next
    d.Close SaveChanges:=False
    On Error GoTo 0
    Err.Raise number, , description
End Function

Private Sub ReplaceEverywhere(ByVal d As Object, ByVal findText As String, ByVal replaceText As String)
    Dim story As Object, r As Object
    For Each story In d.StoryRanges
        Do While Not story Is Nothing
            Set r = story.Duplicate
            With r.Find
                .ClearFormatting
                .Text = findText
                .MatchCase = False
                .MatchWildcards = False
                .Forward = True
                .Wrap = 0
            End With
            Do While r.Find.Execute
                If r.ParentContentControl Is Nothing Then r.Text = replaceText
                r.Collapse 0
            Loop
            Set story = story.NextStoryRange
        Loop
    Next
End Sub

' Builds the letter as PDF (exactly as it will be uploaded) and opens it.
Public Sub PreviewLetter(ByVal templatePath As String, ByVal templateName As String, ByVal values As Object)
    Dim work As String, docx As String, pdf As String
    work = NewWorkFolder("preview")
    docx = FillTemplate(templatePath, values, JoinPath(work, "No Pay Decision Letter - " & _
                        SafeFileName(templateName) & ".docx"))
    pdf = JoinPath(work, StemOf(docx) & ".pdf")
    WordToPdf docx, pdf
    gStep = ""
    OpenFile pdf
End Sub
