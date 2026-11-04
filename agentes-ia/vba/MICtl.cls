VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "MICtl"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
' MoreInfo Pilot - passes the events of a control created by code to its window (MIMain or MILetter):
' Owner.OnEvent key, "click" / "change" / "dblclick" / "drop", and Owner.OnKey key, keyCode, shift.
Option Explicit

Public Key As String
Private mOwner As Object
Private WithEvents Btn As MSForms.CommandButton
Private WithEvents Cbo As MSForms.ComboBox
Private WithEvents Lst As MSForms.ListBox
Private WithEvents Txt As MSForms.TextBox
Private WithEvents Opt As MSForms.OptionButton
Private WithEvents Chk As MSForms.CheckBox
Private WithEvents Lbl As MSForms.Label

Public Sub Attach(ByVal ctl As Object, ByVal ctlKey As String, ByVal owner As Object)
    Key = ctlKey
    Set mOwner = owner
    Select Case TypeName(ctl)
        Case "CommandButton": Set Btn = ctl
        Case "ComboBox": Set Cbo = ctl
        Case "ListBox": Set Lst = ctl
        Case "TextBox": Set Txt = ctl
        Case "OptionButton": Set Opt = ctl
        Case "CheckBox": Set Chk = ctl
        Case "Label": Set Lbl = ctl
    End Select
End Sub

Public Sub Release()
    Set mOwner = Nothing
    Set Btn = Nothing
    Set Cbo = Nothing
    Set Lst = Nothing
    Set Txt = Nothing
    Set Opt = Nothing
    Set Chk = Nothing
    Set Lbl = Nothing
End Sub

Private Sub Fire(ByVal evt As String)
    If mOwner Is Nothing Then Exit Sub
    CallByName mOwner, "OnEvent", VbMethod, Key, evt
End Sub

Private Sub KeyPressed(ByVal KeyCode As MSForms.ReturnInteger, ByVal Shift As Integer)
    If mOwner Is Nothing Then Exit Sub
    If CallByName(mOwner, "OnKey", VbMethod, Key, CLng(KeyCode.Value), Shift) Then KeyCode.Value = 0
End Sub

Private Sub Btn_Click()
    Fire "click"
End Sub

Private Sub Btn_KeyDown(ByVal KeyCode As MSForms.ReturnInteger, ByVal Shift As Integer)
    KeyPressed KeyCode, Shift
End Sub

Private Sub Cbo_Change()
    Fire "change"
End Sub

Private Sub Cbo_DropButtonClick()
    Fire "drop"
End Sub

Private Sub Cbo_KeyDown(ByVal KeyCode As MSForms.ReturnInteger, ByVal Shift As Integer)
    KeyPressed KeyCode, Shift
End Sub

Private Sub Lst_Click()
    Fire "click"
End Sub

Private Sub Lst_DblClick(ByVal Cancel As MSForms.ReturnBoolean)
    Fire "dblclick"
End Sub

Private Sub Lst_KeyDown(ByVal KeyCode As MSForms.ReturnInteger, ByVal Shift As Integer)
    KeyPressed KeyCode, Shift
End Sub

Private Sub Txt_Change()
    Fire "change"
End Sub

Private Sub Txt_KeyDown(ByVal KeyCode As MSForms.ReturnInteger, ByVal Shift As Integer)
    KeyPressed KeyCode, Shift
End Sub

Private Sub Opt_Click()
    Fire "click"
End Sub

Private Sub Chk_Click()
    Fire "click"
End Sub

Private Sub Lbl_Click()
    Fire "click"
End Sub
