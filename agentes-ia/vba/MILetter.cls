VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "MILetter"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
' MoreInfo Pilot - the No Pay Decision Letter form, made from the fields of the chosen template: one box per field
' (a value that appears several times, such as the customer name, is typed once), drop-down lists, the date of
' today, the whole address on one line, and several reasons with "+ Add another" (a reason can be chosen once).
Option Explicit

Private Const ROW_H As Single = 22

Private mForm As Object
Private mHooks As Collection
Private mFrame As Object
Private mFields As Collection
Private mN As Long
Private mCtl() As Object          ' the input of each field
Private mLbl() As Object
Private mExtra() As Collection    ' more values of a field with several values: Array(input, remove button)
Private mAddBtn() As Object
Private mSerial As Long
Private mLabelW As Single
Private mCtlW As Single

Private mTplName As String
Private mTplPath As String
Private mAccepted As Boolean
Private mPreviewSig As String
Private mPreviewedOK As Boolean
Private mValues As Object

Private mRoles As Object          ' address role -> field number
Private mAddrRow As Long          ' the address row goes before this field (0: no address fields)
Private mAddrLbl As Object
Private mAddrBox As Object
Private mAddrBtn As Object
Private mAddrHint As Object
Private mAddrLen As Long
Private mBuilding As Boolean

' ================================================================ public

' Shows the form (modal). True when the analyst adds the letter; then read Values and Previewed.
Public Function Run(ByVal tplName As String, ByVal tplPath As String, ByVal fields As Collection, _
                    ByVal oldValues As Object, ByVal caseNo As String, ByVal analyst As String, _
                    ByVal lang As String) As Boolean
    Dim sw As Single, sh As Single, fw As Single, fh As Single, w As Single, h As Single, c As Object
    Dim i As Long, f As Object, value As Variant, items As Variant, k As Long
    mTplName = tplName
    mTplPath = tplPath
    Set mFields = fields
    mN = fields.Count
    If mN = 0 Then Exit Function
    ReDim mCtl(1 To mN)
    ReDim mLbl(1 To mN)
    ReDim mExtra(1 To mN)
    ReDim mAddBtn(1 To mN)
    Set mHooks = New Collection
    mBuilding = True

    Set mForm = VBA.UserForms.Add("MIForm")
    Set mForm.Owner = Me
    ScreenPoints sw, sh
    fw = 580
    If fw > sw - 20 Then fw = sw - 20
    fh = 600
    If fh > sh - 20 Then fh = sh - 20
    mForm.Width = fw
    mForm.Height = fh
    mForm.Caption = "No Pay Decision Letter - " & tplName
    mForm.BackColor = RGB(250, 250, 250)
    w = mForm.InsideWidth
    h = mForm.InsideHeight

    Set c = NewLabel(mForm, "Template: " & tplName, 10, 6, w - 20, 18, True)
    c.Font.Size = 12
    Set c = NewLabel(mForm, "Fill in the fields of the letter. A field marked x2, x3... appears several times in the " & _
        "letter (for example the customer name, also shown as a title): type it once. Paste the whole address in " & _
        """Full address (one line)"". Use ""+ Add another"" to choose more than one reason; a reason can be chosen " & _
        "only once. The letter is saved as PDF in the letter folders when you upload.", 10, 26, w - 20, 44)
    c.ForeColor = RGB(91, 107, 117)

    Set mFrame = NewCtl(mForm, "Forms.Frame.1", "", 8, 74, w - 16, h - 74 - 40)
    mFrame.Caption = ""
    mFrame.BackColor = RGB(255, 255, 255)
    mFrame.ScrollBars = 2
    mFrame.KeepScrollBarsVisible = 0
    mLabelW = 150
    mCtlW = mFrame.InsideWidth - mLabelW - 34
    If mCtlW < 120 Then mCtlW = 120

    FindAddressFields
    For i = 1 To mN
        Set f = mFields(i)
        value = Empty
        If Not oldValues Is Nothing Then
            If oldValues.Exists(f("key")) Then value = oldValues(f("key"))
        End If
        If IsEmpty(value) Then value = DefaultValue(f, caseNo, analyst, lang)
        Set mLbl(i) = NewLabel(mFrame, LabelText(f), 6, 0, mLabelW, 16)
        If f("multi") Then
            If IsArray(value) Then items = value Else items = Array(CStr(value))
            If UBound(items) < LBound(items) Then items = Array("")
            Set mCtl(i) = MakeInput(i, "f:" & i, CStr(items(LBound(items))))
            Set mExtra(i) = New Collection
            Set mAddBtn(i) = NewButton(mFrame, "a:" & i, "+ Add another", 0, 0, 100)
            For k = LBound(items) + 1 To UBound(items)
                AddValue i, CStr(items(k))
            Next
            UpdateAdd i
        Else
            Set mCtl(i) = MakeInput(i, "f:" & i, FlatValue(value))
        End If
        If i = mAddrRow Then BuildAddressRow
    Next

    NewButton mForm, "preview", "Preview letter (PDF)", 10, h - 32, 130
    NewButton mForm, "ok", "Add letter to the documents", w - 260, h - 32, 170, True
    NewButton mForm, "cancel", "Cancel", w - 84, h - 32, 74
    Relayout
    mBuilding = False
    mForm.Show 1   ' modal
    Run = mAccepted
    Cleanup
End Function

Public Property Get Values() As Object
    Set Values = mValues
End Property

Public Property Get Previewed() As Boolean
    Previewed = mPreviewedOK
End Property

' ================================================================ events

Public Sub OnEvent(ByVal key As String, ByVal evt As String)
    Dim parts As Variant, i As Long
    If mBuilding Then Exit Sub
    On Error GoTo Fail
    parts = Split(key, ":")
    Select Case parts(0)
        Case "ok": Accept
        Case "cancel": mForm.Hide
        Case "preview": DoPreview
        Case "addrfill": FillAddress
        Case "addr"
            If evt = "change" Then   ' a whole address pasted: split it right away
                If Len(mAddrBox.Text) - mAddrLen > 10 Then FillAddress
                mAddrLen = Len(mAddrBox.Text)
            End If
        Case "a"
            AddValue CLng(parts(1)), ""
            Relayout
        Case "x"
            RemoveValue CLng(parts(1)), CStr(parts(2))
        Case "f", "m"
            i = CLng(parts(1))
            If mFields(i)("multi") Then
                If evt = "drop" Then LimitChoices i, ControlOf(key)
                If evt = "change" Then UpdateAdd i
            End If
    End Select
    Exit Sub
Fail:
    ShowError "Something went wrong in the letter form."
End Sub

Public Function OnKey(ByVal key As String, ByVal keyCode As Long, ByVal shift As Integer) As Boolean
    If key = "addr" And keyCode = 13 Then   ' Enter in the address box
        On Error GoTo Fail
        FillAddress
        OnKey = True
    End If
    Exit Function
Fail:
    ShowError "The address could not be split."
End Function

' The X button: same as Cancel.
Public Function OnClosing(ByVal closeMode As Integer) As Boolean
    If closeMode = 0 Then   ' vbFormControlMenu
        mForm.Hide
        OnClosing = True
    End If
End Function

' ================================================================ building

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
                          ByVal w As Single, ByVal h As Single, Optional ByVal isBold As Boolean = False) As Object
    Dim c As Object
    Set c = NewCtl(parent, "Forms.Label.1", "", l, t, w, h)
    c.Caption = text
    c.BackStyle = 0
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

Private Function LabelText(ByVal f As Object) As String
    LabelText = f("label")
    If f("count") > 1 Then LabelText = LabelText & "  (x" & f("count") & ")"
End Function

' Case number, analyst and today's date are filled in automatically.
Private Function DefaultValue(ByVal f As Object, ByVal caseNo As String, ByVal analyst As String, _
                              ByVal lang As String) As Variant
    Dim label As String, w As Variant
    DefaultValue = f("value")
    If Len(f("value")) > 0 Then Exit Function
    label = Fold(f("label"))
    For Each w In Array("case", "claim", "dossier", "reclamation")
        If InStr(1, label, w) > 0 And Len(caseNo) > 0 Then
            DefaultValue = caseNo
            Exit Function
        End If
    Next
    If (InStr(1, label, "analyst") > 0 Or InStr(1, label, "analyste") > 0) And Len(analyst) > 0 Then
        DefaultValue = analyst
    ElseIf f("kind") = "date" Then
        DefaultValue = DateText(lang, Date)
    End If
End Function

Private Function FieldOptions(ByVal i As Long) As Variant
    Dim o As String
    o = mFields(i)("options")
    If Len(o) = 0 Then FieldOptions = Array() Else FieldOptions = Split(o, Chr(30))
End Function

Private Function OptionCount(ByVal i As Long) As Long
    Dim o As Variant
    o = FieldOptions(i)
    OptionCount = UBound(o) - LBound(o) + 1
End Function

Private Function MakeInput(ByVal i As Long, ByVal key As String, ByVal value As String) As Object
    Dim c As Object, kind As String
    kind = mFields(i)("kind")
    If kind = "dropdown" Or kind = "combo" Then
        Set c = NewCtl(mFrame, "Forms.ComboBox.1", key, 0, 0, mCtlW, 18)
        If kind = "dropdown" Then c.Style = 2 Else c.Style = 0
        c.ListRows = 12
        If OptionCount(i) > 0 Then c.List = FieldOptions(i)
        SetInput c, value
    Else
        Set c = NewCtl(mFrame, "Forms.TextBox.1", key, 0, 0, mCtlW, 18)
        c.Text = value
    End If
    Set MakeInput = c
End Function

Private Sub SetInput(ByVal c As Object, ByVal value As String)
    Dim k As Long
    If TypeName(c) = "ComboBox" Then
        For k = 0 To c.ListCount - 1
            If c.List(k) = value Then
                c.ListIndex = k
                Exit Sub
            End If
        Next
        If c.Style = 2 Then
            c.ListIndex = -1
        Else
            c.Text = value
        End If
    Else
        c.Text = value
    End If
End Sub

Private Function ControlOf(ByVal key As String) As Object
    Dim parts As Variant, i As Long, item As Variant
    parts = Split(key, ":")
    i = CLng(parts(1))
    If parts(0) = "f" Then
        Set ControlOf = mCtl(i)
    Else
        item = mExtra(i).Item(CStr(parts(2)))
        Set ControlOf = item(0)
    End If
End Function

' ================================================================ several values (reasons)

Private Function AddValue(ByVal i As Long, ByVal value As String) As Object
    Dim c As Object, b As Object
    If OptionCount(i) > 0 And 1 + mExtra(i).Count >= OptionCount(i) And mFields(i)("kind") = "dropdown" Then
        Exit Function   ' every option is already used
    End If
    mSerial = mSerial + 1
    Set c = MakeInput(i, "m:" & i & ":" & mSerial, value)
    Set b = NewButton(mFrame, "x:" & i & ":" & mSerial, "x", 0, 0, 22)
    mExtra(i).Add Array(c, b), CStr(mSerial)
    UpdateAdd i
    Set AddValue = c
End Function

Private Sub RemoveValue(ByVal i As Long, ByVal serial As String)
    Dim item As Variant
    item = mExtra(i).Item(serial)
    item(0).Visible = False   ' hidden (not deleted: the button that was clicked is still running)
    item(1).Visible = False
    mExtra(i).Remove serial
    UpdateAdd i
    Relayout
End Sub

Private Sub UpdateAdd(ByVal i As Long)
    Dim n As Long
    If mAddBtn(i) Is Nothing Then Exit Sub
    n = OptionCount(i)
    mAddBtn(i).Enabled = (n = 0 Or 1 + mExtra(i).Count < n Or mFields(i)("kind") <> "dropdown")
End Sub

' The list of a reason only offers the reasons that are not chosen on another line.
Private Sub LimitChoices(ByVal i As Long, ByVal c As Object)
    Dim taken As String, item As Variant, o As Variant, free As String, current As String, sep As String
    sep = Chr(30)
    current = c.Text
    If Not mCtl(i) Is c Then taken = taken & sep & mCtl(i).Text & sep
    For Each item In mExtra(i)
        If Not item(0) Is c Then taken = taken & sep & item(0).Text & sep
    Next
    For Each o In FieldOptions(i)
        If InStr(1, taken, sep & o & sep) = 0 Then
            If Len(free) > 0 Then free = free & sep
            free = free & o
        End If
    Next
    If Len(free) = 0 Then
        c.Clear
    Else
        c.List = Split(free, sep)
    End If
    SetInput c, current
End Sub

' ================================================================ address on one line

Private Sub FindAddressFields()
    Dim i As Long, f As Object, role As String, assigned As String
    Set mRoles = CreateObject("Scripting.Dictionary")
    For i = 1 To mN
        Set f = mFields(i)
        If (f("kind") = "text" Or f("kind") = "dropdown" Or f("kind") = "combo") And Not f("multi") Then
            role = AddressRole(f("label"), assigned)
            If Len(role) > 0 Then
                mRoles(role) = i
                assigned = assigned & "|" & role & "|"
            End If
        End If
    Next
    If Not (mRoles.Exists("line1") And mRoles.Count >= 2) Then mRoles.RemoveAll
    mAddrRow = 0
    For i = 1 To mN
        If IsAddressField(i) Then
            mAddrRow = i
            Exit For
        End If
    Next
End Sub

Private Function IsAddressField(ByVal i As Long) As Boolean
    Dim r As Variant
    For Each r In mRoles.Keys
        If mRoles(r) = i Then
            IsAddressField = True
            Exit Function
        End If
    Next
End Function

Private Sub BuildAddressRow()
    Set mAddrLbl = NewLabel(mFrame, "Full address (one line)", 6, 0, mLabelW, 28, True)
    Set mAddrBox = NewCtl(mFrame, "Forms.TextBox.1", "addr", 0, 0, mCtlW - 92, 18)
    Set mAddrBtn = NewButton(mFrame, "addrfill", "Fill address", 0, 0, 86)
    Set mAddrHint = NewLabel(mFrame, "Paste or type the whole address and press Enter, e.g. 221 Main Street, Apt 4B, " & _
                             "Toronto ON M5V 2T6.", 0, 0, mCtlW, 26)
    mAddrHint.ForeColor = RGB(91, 107, 117)
End Sub

Private Function DictGet(ByVal d As Object, ByVal key As String) As String
    If d.Exists(key) Then DictGet = d(key)
End Function

Public Sub FillAddress()
    Dim parts As Variant, found As Object, opts As Variant, role As Variant, target As String, i As Long
    Dim v As String, names As String, missing As String, hint As String, pf As Object, filled As Long
    If mAddrBox Is Nothing Then Exit Sub
    If Len(Trim$(mAddrBox.Text)) = 0 Then Exit Sub
    parts = SplitAddress(mAddrBox.Text)
    Set found = CreateObject("Scripting.Dictionary")
    If Len(parts(ADDR_LINE1)) > 0 Then found("line1") = parts(ADDR_LINE1)
    If Len(parts(ADDR_LINE2)) > 0 Then found("line2") = parts(ADDR_LINE2)
    If Len(parts(ADDR_CITY)) > 0 Then found("city") = parts(ADDR_CITY)
    If Len(parts(ADDR_POSTAL)) > 0 Then found("postal") = parts(ADDR_POSTAL)
    If Len(parts(ADDR_PROVINCE)) > 0 Then
        opts = Empty
        If mRoles.Exists("province") Then
            Set pf = mFields(mRoles("province"))
            If pf("kind") = "dropdown" Then opts = FieldOptions(mRoles("province"))
        End If
        found("province") = ProvinceOption(parts(ADDR_PROVINCE), parts(ADDR_PROVINCE_WRITTEN), opts)
    End If
    ' what has no field of its own goes with the closest field
    If found.Exists("line2") And Not mRoles.Exists("line2") Then
        found("line1") = DictGet(found, "line1") & ", " & found("line2")
        found.Remove "line2"
    End If
    If found.Exists("city") And Not mRoles.Exists("city") Then
        found("line1") = DictGet(found, "line1") & ", " & found("city")
        found.Remove "city"
    End If
    For Each role In Array("province", "postal")
        If found.Exists(role) Then
            If Len(found(role)) > 0 And Not mRoles.Exists(role) Then
                If found.Exists("city") Then target = "city" Else target = "line1"
                found(target) = Trim$(DictGet(found, target) & " " & found(role))
                found.Remove role
            End If
        End If
    Next
    ' every address field is filled; the ones not found are cleared (no data from a previous address)
    For i = 1 To mN
        For Each role In mRoles.Keys
            If mRoles(role) = i Then
                v = DictGet(found, CStr(role))
                SetInput mCtl(i), v
                If Len(v) > 0 Then
                    filled = filled + 1
                    If Len(names) > 0 Then names = names & ", "
                    names = names & mFields(i)("label")
                ElseIf role <> "line2" Then   ' line 2 (unit, suite) is optional
                    If Len(missing) > 0 Then missing = missing & ", "
                    missing = missing & mFields(i)("label")
                End If
            End If
        Next
    Next
    If filled < 2 Then
        hint = "The address could not be split. Separate the parts with commas: street, unit, city, province and " & _
               "postal code."
    ElseIf Len(missing) > 0 Then
        hint = "Filled: " & names & ". Not found: " & missing & "; complete it below."
    Else
        hint = "Filled: " & names & ". Check them below."
    End If
    v = DictGet(found, "postal")
    If Len(v) > 0 And mRoles.Exists("postal") Then
        If Not ValidPostal(v) And Not IsDigitChar(Left$(v, 1)) Then
            hint = hint & " ! Check the postal code """ & v & """: Canadian postal codes look like A1A 1A1."
        End If
    End If
    mAddrHint.Caption = hint
    mAddrLen = Len(mAddrBox.Text)
End Sub

' ================================================================ layout

Private Sub Relayout()
    Dim i As Long, y As Single, x As Single, item As Variant
    x = mLabelW + 12
    y = 6
    For i = 1 To mN
        If i = mAddrRow And Not mAddrBox Is Nothing Then
            mAddrLbl.Top = y + 2
            mAddrBox.Left = x
            mAddrBox.Top = y
            mAddrBtn.Left = x + mCtlW - 86
            mAddrBtn.Top = y - 1
            mAddrHint.Left = x
            mAddrHint.Top = y + 21
            y = y + 52
        End If
        mLbl(i).Top = y + 3
        mCtl(i).Left = x
        mCtl(i).Top = y
        y = y + ROW_H
        If mFields(i)("multi") Then
            For Each item In mExtra(i)
                item(0).Left = x
                item(0).Top = y
                item(0).Width = mCtlW - 26
                item(1).Left = x + mCtlW - 22
                item(1).Top = y - 1
                y = y + ROW_H
            Next
            mAddBtn(i).Left = x
            mAddBtn(i).Top = y
            y = y + ROW_H + 2
        End If
    Next
    mFrame.ScrollHeight = y + 8
End Sub

' ================================================================ values, preview and accept

Private Function CollectValues() As Object
    Dim d As Object, i As Long, item As Variant, list As String, sep As String, v As String
    sep = Chr(30)
    Set d = CreateObject("Scripting.Dictionary")
    For i = 1 To mN
        If mFields(i)("multi") Then
            list = ""
            v = Trim$(mCtl(i).Text)
            If Len(v) > 0 Then list = v
            For Each item In mExtra(i)
                v = Trim$(item(0).Text)
                If Len(v) > 0 And InStr(1, sep & list & sep, sep & v & sep) = 0 Then
                    If Len(list) > 0 Then list = list & sep
                    list = list & v
                End If
            Next
            If Len(list) = 0 Then d(mFields(i)("key")) = "" Else d(mFields(i)("key")) = Split(list, sep)
        Else
            d(mFields(i)("key")) = Trim$(mCtl(i).Text)
        End If
    Next
    Set CollectValues = d
End Function

Private Function Signature(ByVal d As Object) As String
    Dim k As Variant, s As String
    For Each k In d.Keys
        s = s & k & "=" & FlatValue(d(k)) & Chr(31)
    Next
    Signature = s
End Function

Private Sub DoPreview()
    Dim v As Object
    Set v = CollectValues()
    PreviewLetter mTplPath, mTplName, v
    gStep = ""
    mPreviewSig = Signature(v)
End Sub

Private Sub Accept()
    Dim v As Object, i As Long, missing As String
    Set v = CollectValues()
    For i = 1 To mN
        If Len(FlatValue(v(mFields(i)("key")))) = 0 Then
            If Len(missing) > 0 Then missing = missing & ", "
            missing = missing & mFields(i)("label")
        End If
    Next
    If Len(missing) > 0 Then
        If Not Ask("These fields are empty: " & missing & "." & vbCrLf & vbCrLf & "Add the letter anyway?") Then Exit Sub
    End If
    Set mValues = v
    mPreviewedOK = (Len(mPreviewSig) > 0 And Signature(v) = mPreviewSig)
    mAccepted = True
    mForm.Hide
End Sub

Private Sub Cleanup()
    Dim h As Variant
    On Error Resume Next
    For Each h In mHooks
        h.Release
    Next
    Set mHooks = New Collection
    Set mForm.Owner = Nothing
    Unload mForm
    Set mForm = Nothing
End Sub
